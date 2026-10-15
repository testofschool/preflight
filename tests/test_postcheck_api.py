import copy
import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from app import create_app
from cloud.postcheck import InvalidClip, PostcheckUnavailable
from cloud.store import StoreRateLimited
from test_cloud_api import ConnectedRewrite, ConnectedStore


class VerdictStore(ConnectedStore):
    def __init__(self):
        self.verdicts = {}
        self.feedback_count = 0

    def get_verdict(self, identifier):
        return copy.deepcopy(self.verdicts.get(identifier))

    def record_verdict(self, prompt, model, pass_bool, defects, *, verdict_id, review):
        self.verdicts[verdict_id] = {'prompt': prompt, 'model': model, 'review': copy.deepcopy(review)}
        self.feedback_count += 1
        return {'created': True, 'verdict_id': verdict_id}

    def difficulty(self, prompt):
        result = super().difficulty(prompt)
        base = result['p_fail']
        result.update(p_fail=min(1, base + self.feedback_count / 100), historical_p_fail=base,
                      postcheck_feedback={'count': self.feedback_count, 'failures': self.feedback_count},
                      risk_semantics='MIXED heuristic proxy; not a calibrated failure probability.')
        return result


class Reviewer:
    model_name = 'fake-reviewer-for-unit-test'

    def __init__(self):
        self.calls = 0
        self.paths = []

    async def review(self, path, prompt, model):
        self.calls += 1
        self.paths.append(Path(path))
        return {'pass_bool': False, 'defects': [{'category': 'physics', 'seconds': 1.5,
                 'timecode': '00:01', 'reason': 'Synthetic fixture observation for unit testing.'}],
                'source_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                'reviewed_duration_seconds': 2, 'analysis': {'sampling_fps': 2, 'actual_model_calls': 0}}


def connected(store=None, reviewer=None):
    store, reviewer = store or VerdictStore(), reviewer or Reviewer()
    app = create_app(mode='cloud', store_factory=lambda: store, rewrite_factory=ConnectedRewrite,
                     postcheck_factory=lambda: reviewer)
    return app, store, reviewer


def upload(client, data=b'unit-test-video-bytes', **fields):
    return client.post('/postcheck', data={'prompt': 'a cat and a dog', 'model': 'unit-test-owner-upload', **fields},
                       files={'video': ('fixture.mp4', data, 'video/mp4')})


def test_upload_logs_verdict_and_reuses_it_without_duplicate_inference():
    app, store, reviewer = connected()
    with TestClient(app) as client:
        first = upload(client)
        assert first.status_code == 200
        body = first.json()
        assert body['pass_bool'] is False
        assert body['feedback_recorded'] and body['feedback_created']
        assert body['risk_after'] > body['risk_before']
        assert body['historical_p_fail'] == body['risk_before']
        assert body['defects'][0]['timecode'] == '00:01'
        assert client.get('/api/status').json()['postcheck'] is True
        assert all(not path.exists() for path in reviewer.paths)
        second = upload(client)
        assert second.status_code == 200
        assert second.json()['verdict_id'] == body['verdict_id']
        assert second.json()['reused_stored_review'] is True
        assert second.json()['feedback_created'] is False
        assert second.json()['risk_before'] == second.json()['risk_after']
        assert reviewer.calls == store.feedback_count == 1


def test_invalid_media_or_upstream_failure_never_writes_a_verdict():
    for failure, status in [(InvalidClip('bad input'), 422), (PostcheckUnavailable('private failure'), 503)]:
        class FailedReviewer(Reviewer):
            async def review(self, path, prompt, model):
                raise failure
        app, store, _ = connected(reviewer=FailedReviewer())
        with TestClient(app) as client:
            result = upload(client)
            assert result.status_code == status
            assert not store.verdicts and store.feedback_count == 0
            assert 'private failure' not in result.text
            assert 'pass_bool' not in result.json()


def test_upload_identity_mismatch_is_rejected_before_store_write():
    class MismatchedReviewer(Reviewer):
        async def review(self, path, prompt, model):
            result = await super().review(path, prompt, model)
            result['source_sha256'] = '0' * 64
            return result
    app, store, _ = connected(reviewer=MismatchedReviewer())
    with TestClient(app) as client:
        assert upload(client).status_code == 503
        assert not store.verdicts


def test_upload_validation_is_bounded_and_temp_paths_are_not_returned():
    app, store, reviewer = connected()
    with TestClient(app) as client:
        assert client.post('/postcheck', json={'video_url': 'https://example.test/video.mp4'}).status_code == 415
        assert upload(client, data=b'').status_code == 422
        assert upload(client, prompt='   ').status_code == 422
        assert upload(client, extra='not-allowed').status_code in (400, 422)
        assert client.post('/postcheck', data={'prompt': 'cat'}, files={'video': ('fake.txt', b'file', 'text/plain')}).status_code == 415
        too_large = client.post('/postcheck', content=b'x', headers={'Content-Type': 'multipart/form-data; boundary=test',
                               'Content-Length': str(31 * 1024 * 1024)})
        assert too_large.status_code == 413
        assert not store.verdicts and not reviewer.calls


def test_postcheck_budget_and_busy_decoder_reject_before_model_calls():
    class LimitedStore(VerdictStore):
        def admit_request(self):
            raise StoreRateLimited(9)
    app, _, reviewer = connected(store=LimitedStore())
    with TestClient(app) as client:
        response = upload(client)
        assert response.status_code == 429 and response.headers['retry-after'] == '9'
        assert reviewer.calls == 0
    app, _, reviewer = connected()
    with TestClient(app) as client:
        # Capacity is checked before parsing or invoking a reviewer.
        app.state.postcheck_slot._value = 0
        response = upload(client)
        assert response.status_code == 429
        assert reviewer.calls == 0


def test_local_mode_does_not_offer_a_fake_video_verdict():
    with TestClient(create_app(mode='local-g0')) as client:
        assert upload(client).status_code == 503
        assert client.get('/api/status').json()['postcheck'] is False


def test_concurrent_equivalent_upload_uses_first_durable_review_without_double_counting():
    class RacingStore(VerdictStore):
        def record_verdict(self, prompt, model, pass_bool, defects, *, verdict_id, review):
            canonical = copy.deepcopy(review)
            canonical['analysis']['elapsed_seconds'] = 0.125
            super().record_verdict(prompt, model, pass_bool, defects, verdict_id=verdict_id, review=canonical)
            raise ValueError('Another instance committed a different timing for this same clip')

    class PaidReviewer(Reviewer):
        async def review(self, path, prompt, model):
            result = await super().review(path, prompt, model)
            result['analysis']['actual_model_calls'] = 3
            return result

    app, store, reviewer = connected(store=RacingStore(), reviewer=PaidReviewer())
    with TestClient(app) as client:
        response = upload(client)
        assert response.status_code == 200
        body = response.json()
        assert body['reused_stored_review'] and body['concurrent_review_discarded']
        assert body['feedback_created'] is False
        assert body['model_calls_this_request'] == 3
        assert body['analysis']['elapsed_seconds'] == 0.125
        assert store.feedback_count == reviewer.calls == 1
