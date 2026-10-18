"""Promotion must reject warm candidates and receipts for another source/revision."""
import ast
from copy import deepcopy
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "scripts/release_preview_v4.py"
TREE = ast.parse(SOURCE.read_text())
FUNCTION = next(node for node in TREE.body if isinstance(node, ast.FunctionDef)
                and node.name == "validate_promotion_records")
NAMESPACE = {}
exec(compile(ast.Module(body=[FUNCTION], type_ignores=[]), str(SOURCE), "exec"), NAMESPACE)
validate = NAMESPACE["validate_promotion_records"]


def records():
    digest = "sha256:" + "b" * 64
    runtime = "c" * 64
    gate = {key:True for key in ("V_A", "V_B", "V_D", "V_E", "V_F")}
    gate.update(candidate_revision="preflight-00025-test", build_id="build1",
                production_commit="a" * 40, runtime_source_sha256=runtime)
    candidate = {"revision":gate["candidate_revision"], "build_id":"build1",
                 "runtime_source_sha256":runtime, "live_arm":None,
                 "allowed_env":{"PREFLIGHT_PREVIEW_WARM_ENABLED":"false"}}
    provenance = {"pass":True, "revision":candidate["revision"], "build_id":"build1",
                  "commit":gate["production_commit"], "git_runtime_source_sha256":runtime,
                  "cloud_build_runtime_source_sha256":runtime, "revision_image_digest":digest}
    revision = {"metadata":{"name":candidate["revision"]}, "status":{"imageDigest":"registry/app@" + digest},
                "spec":{"containers":[{"env":[{"name":"PREFLIGHT_PREVIEW_ENABLED", "value":"true"},
                    {"name":"PREFLIGHT_PREVIEW_LIVE_ENABLED", "value":"false"},
                    {"name":"PREFLIGHT_PREVIEW_WARM_ENABLED", "value":"false"}]}]}}
    return gate, candidate, provenance, revision


def test_bound_cache_only_candidate_passes_without_cloud_mutation():
    validate(*records())


@pytest.mark.parametrize("index,field,value", [
    (0,"candidate_revision","preflight-00024-stale"), (0,"build_id","stale"),
    (0,"runtime_source_sha256","bad"), (0,"production_commit","stale"),
    (0,"V_B",False), (2,"pass",False), (2,"revision","preflight-00024-stale"),
    (2,"cloud_build_runtime_source_sha256","bad"),
])
def test_stale_or_failed_gate_is_rejected(index, field, value):
    items = deepcopy(records())
    items[index][field] = value
    with pytest.raises(RuntimeError):
        validate(*items)


@pytest.mark.parametrize("saved", [True, False])
def test_warm_must_be_disabled_in_saved_and_native_revision(saved):
    gate, candidate, provenance, revision = records()
    if saved:
        candidate["allowed_env"]["PREFLIGHT_PREVIEW_WARM_ENABLED"] = "true"
    else:
        revision["spec"]["containers"][0]["env"][2]["value"] = "true"
    with pytest.raises(RuntimeError):
        validate(gate, candidate, provenance, revision)


def test_live_candidate_requires_live_ui_gate():
    gate, candidate, provenance, revision = records()
    candidate["live_arm"] = "P2"
    revision["spec"]["containers"][0]["env"][1]["value"] = "true"
    with pytest.raises(RuntimeError):
        validate(gate, candidate, provenance, revision)
    gate["V_C"] = True
    validate(gate, candidate, provenance, revision)
