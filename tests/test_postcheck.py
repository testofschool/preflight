import json
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from cloud.postcheck import ClipMetadata, Inspection, InvalidClip, PostcheckService, PostcheckUnavailable, PreparedMedia, SampledFrame, frame_batches, prepare_media, probe_clip


class PostcheckTests(unittest.IsolatedAsyncioTestCase):
    def prepared(self, frame_count=20):
        return PreparedMedia(ClipMetadata(frame_count / 2, 640, 360, 1000), "a" * 64, b"test-video", [SampledFrame(index / 2, b"test-jpeg") for index in range(frame_count)])

    def service(self, responses, media=None):
        generate = AsyncMock(side_effect=[SimpleNamespace(text=json.dumps(row), usage_metadata=None) for row in responses])
        client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
        return PostcheckService(client, media_preparer=lambda path: media or self.prepared()), generate

    async def test_video_and_frame_batches_use_absolute_offsets_and_merge_duplicates(self):
        observed = {"reviewable": True, "defects": [{"category": "flicker", "seconds": 8, "reason": "The subject alternates between bright and dark frames."}], "summary": "One visible lighting discontinuity."}
        clear = {"reviewable": True, "defects": [], "summary": "No defect visible in this interval."}
        service, generate = self.service([observed, clear, observed])
        result = await service.review("ignored.mp4", "a bird beside a lake", "owner label")
        self.assertFalse(result["pass_bool"])
        self.assertEqual(len(result["defects"]), 1)
        self.assertEqual(result["defects"][0]["timecode"], "00:08")
        self.assertEqual(result["defects"][0]["evidence_sources"], ["frames-2", "video"])
        self.assertEqual(result["analysis"]["actual_model_calls"], 3)
        self.assertEqual(result["analysis"]["sampling_fps"], 2)
        calls = generate.call_args_list
        video_parts = calls[0].kwargs["contents"].parts
        self.assertTrue(any(part.inline_data and part.inline_data.mime_type == "video/mp4" for part in video_parts))
        later_parts = calls[2].kwargs["contents"].parts
        self.assertTrue(any(part.text and "7.50 seconds" in part.text for part in later_parts))
        self.assertTrue(all(sum(bool(part.inline_data and part.inline_data.mime_type == "image/jpeg") for part in call.kwargs["contents"].parts) <= 16 for call in calls))

    async def test_clean_clip_pass_is_derived_from_all_evidence(self):
        clear = {"reviewable": True, "defects": [], "summary": "No visible defect."}
        service, _ = self.service([clear, clear], media=self.prepared(4))
        result = await service.review("ignored.mp4", "a quiet lake", "owner label")
        self.assertTrue(result["pass_bool"])
        self.assertEqual(result["defects"], [])
        self.assertEqual(result["source_sha256"], "a" * 64)

    async def test_out_of_evidence_timestamp_is_not_returned_or_clamped(self):
        invalid = {"reviewable": True, "defects": [{"category": "physics", "seconds": 20, "reason": "A subject jumps."}], "summary": "Possible motion defect."}
        service, _ = self.service([invalid, invalid], media=self.prepared(4))
        with self.assertRaises(PostcheckUnavailable):
            await service.review("ignored.mp4", "a quiet lake", "owner label")

    async def test_upstream_failure_is_sanitized_without_retry(self):
        generate = AsyncMock(side_effect=RuntimeError("private transport details"))
        client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
        service = PostcheckService(client, media_preparer=lambda path: self.prepared(4))
        with self.assertRaises(PostcheckUnavailable) as caught:
            await service.review("ignored.mp4", "a quiet lake", "owner label")
        self.assertNotIn("private transport", str(caught.exception))
        self.assertEqual(generate.await_count, 2)

    async def test_unreviewable_evidence_is_not_a_clean_pass(self):
        uncertain = {"reviewable": False, "defects": [], "summary": "The media could not be read."}
        service, _ = self.service([uncertain, uncertain], media=self.prepared(4))
        with self.assertRaises(PostcheckUnavailable):
            await service.review("ignored.mp4", "a quiet lake", "owner label")

    def test_frame_batches_cover_all_offsets_with_bounded_overlap(self):
        frames = self.prepared(60).frames
        batches = frame_batches(frames)
        self.assertEqual(len(batches), 4)
        self.assertEqual({frame.seconds for batch in batches for frame in batch}, {frame.seconds for frame in frames})
        self.assertTrue(all(len(batch) <= 16 for batch in batches))
        self.assertTrue(all(left[-1] == right[0] for left, right in zip(batches, batches[1:])))

    def test_probe_enforces_duration_before_any_model_call(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "uploaded.mp4"
            source.write_bytes(bytes.fromhex("000000186674797069736f6d0000020069736f6d6d703432"))
            metadata = {"format": {"duration": "31", "format_name": "mov,mp4,m4a,3gp,3g2,mj2"}, "streams": [{"codec_type": "video", "width": 640, "height": 360}]}
            with patch("cloud.postcheck.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout=json.dumps(metadata).encode())) as run:
                with self.assertRaises(InvalidClip):
                    probe_clip(source)
                arguments = run.call_args
                self.assertNotIn("shell", arguments.kwargs)
                self.assertEqual(arguments.kwargs["timeout"], 4)
                self.assertIn("file,pipe", arguments.args[0])

    def test_renamed_webm_or_avi_is_rejected_by_actual_container_family(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "renamed.mp4"
            source.write_bytes(b"non-MP4 test container")
            for family in ("matroska,webm", "avi", ""):
                with self.subTest(family=family):
                    metadata = {"format": {"duration": "3", "format_name": family}, "streams": [{"codec_type": "video", "width": 640, "height": 360}]}
                    with patch("cloud.postcheck.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout=json.dumps(metadata).encode())):
                        with self.assertRaisesRegex(InvalidClip, "MP4 video container"):
                            probe_clip(source)

    def test_mp4_family_requires_a_valid_file_type_box(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "upload.mp4"
            metadata = {"format": {"duration": "3", "format_name": "mov,mp4,m4a,3gp,3g2,mj2"}, "streams": [{"codec_type": "video", "width": 640, "height": 360}]}
            with patch("cloud.postcheck.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout=json.dumps(metadata).encode())):
                source.write_bytes(b"not-an-MP4-file-type-box")
                with self.assertRaisesRegex(InvalidClip, "file-type box"):
                    probe_clip(source)
                source.write_bytes(bytes.fromhex("000000186674797069736f6d0000020069736f6d6d703432"))
                _path, probed = probe_clip(source)
                self.assertEqual(probed.duration, 3)

    def test_owner_wide_hevc_dimensions_fit_the_decode_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "owner-shaped.mp4"
            source.write_bytes(bytes.fromhex("000000186674797069736f6d0000020069736f6d6d703432"))
            metadata = {"format": {"duration": "8", "format_name": "mov,mp4,m4a,3gp,3g2,mj2"}, "streams": [{"codec_type": "video", "width": 4398, "height": 1886}]}
            with patch("cloud.postcheck.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout=json.dumps(metadata).encode())):
                _path, probed = probe_clip(source)
            self.assertEqual((probed.width, probed.height), (4398, 1886))

    def test_preparation_decodes_once_with_shared_scale_and_bounded_filter_threads(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            source.write_bytes(bytes.fromhex("000000186674797069736f6d0000020069736f6d6d703432"))
            metadata = {"format": {"duration": "2", "format_name": "mov,mp4,m4a,3gp,3g2,mj2"}, "streams": [{"codec_type": "video", "width": 640, "height": 360}]}
            ffmpeg_calls = []

            def run(arguments, **kwargs):
                if arguments[0] == "ffprobe":
                    return SimpleNamespace(returncode=0, stdout=json.dumps(metadata).encode())
                ffmpeg_calls.append((arguments, kwargs))
                normalized = next(Path(value) for value in arguments if str(value).endswith("review.mp4"))
                frames = next(Path(value) for value in arguments if str(value).endswith("frame_%03d.jpg"))
                normalized.write_bytes(b"synthetic normalized test bytes")
                for index in range(4):
                    (frames.parent / f"frame_{index:03d}.jpg").write_bytes(b"synthetic jpeg test bytes")
                return SimpleNamespace(returncode=0)

            with patch("cloud.postcheck.subprocess.run", side_effect=run):
                prepared = prepare_media(source)
            self.assertEqual(len(ffmpeg_calls), 1)
            arguments, options = ffmpeg_calls[0]
            graph = arguments[arguments.index("-filter_complex") + 1]
            self.assertEqual(graph.count("scale="), 1)
            self.assertIn("split=2", graph)
            self.assertIn("fps=15", graph)
            self.assertIn("fps=fps=2:start_time=0", graph)
            self.assertEqual(arguments[arguments.index("-filter_complex_threads") + 1], "1")
            self.assertEqual(options["timeout"], 18)
            self.assertNotIn("shell", options)
            self.assertEqual([frame.seconds for frame in prepared.frames], [0, 0.5, 1, 1.5])
            self.assertEqual(prepared.source_sha256, hashlib.sha256(source.read_bytes()).hexdigest())

    def test_typed_schema_rejects_unknown_defect_category(self):
        with self.assertRaises(ValueError):
            Inspection.model_validate({"reviewable": True, "defects": [{"category": "invented", "seconds": 1, "reason": "Example."}], "summary": "Example."})


if __name__ == "__main__":
    unittest.main()
