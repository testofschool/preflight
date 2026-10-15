"""Provision only this app's resources; keep account configuration out of files."""

import argparse
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import certifi


REGION = "asia-southeast1"
DATABASE = "preflight-aibc"
RUNTIME_ACCOUNT = "preflight-aibc-runtime"
BUILD_ACCOUNT = "preflight-aibc-build"
SECRET = "preflight-aibc-gemini"
SESSION_LABEL = "preflight-aibc-2026-sessions"


class CloudOperations:
    def __init__(self):
        self.project = self.command("configured project", ["gcloud", "config", "get-value", "project"]).strip()
        if not self.project or self.project == "(unset)":
            raise RuntimeError("Set the authorized project in gcloud first")
        self.project_number = self.command("project metadata", ["gcloud", "projects", "describe", self.project,
                                              "--format=value(projectNumber)"]).strip()
        self.key = os.environ.get("_".join(("GEMINI", "API", "KEY")), "")
        self.context = ssl.create_default_context(cafile=certifi.where())

    def scrub(self, message: str) -> str:
        if getattr(self, "key", "") and self.key in message:
            raise RuntimeError("STOP: credential detected in captured operation output")
        for value in (getattr(self, "project", ""), getattr(self, "project_number", "")):
            if value:
                message = message.replace(value, "[PROJECT]")
        return re.sub(r"[\w.+-]+@[\w.-]+", "[ACCOUNT]", message)

    def command(self, label: str, arguments: list[str], *, data: str | None = None) -> str:
        result = subprocess.run(arguments, input=data, capture_output=True, text=True,
                                env={**os.environ, "CLOUDSDK_CORE_DISABLE_PROMPTS": "1"})
        if result.returncode:
            raise RuntimeError(f"{label}: {self.scrub(result.stderr or result.stdout)[:2500]}")
        if getattr(self, "key", "") and self.key in result.stdout + result.stderr:
            raise RuntimeError("STOP: credential detected in captured operation output")
        return result.stdout

    def rest(self, method: str, path: str, body: dict | None = None) -> dict:
        token = self.command("access token", ["gcloud", "auth", "print-access-token"]).strip()
        request = Request(
            f"https://{REGION}-aiplatform.googleapis.com/v1beta1/{path}",
            data=json.dumps(body).encode() if body is not None else None,
            method=method,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, context=self.context, timeout=60) as response:
                return json.load(response)
        except HTTPError as error:
            raise RuntimeError(f"Agent Platform HTTP {error.code}: {self.scrub(error.read().decode())[:2000]}") from None

    def session_engine(self, *, create: bool = False) -> str:
        parent = f"projects/{self.project}/locations/{REGION}"
        entries = self.rest("GET", parent + "/reasoningEngines?pageSize=100").get("reasoningEngines", [])
        matches = [entry for entry in entries if entry.get("displayName") == SESSION_LABEL]
        if matches:
            return matches[0]["name"].split("/")[-1]
        if not create:
            raise RuntimeError("This app's Agent Platform session instance is absent")
        operation = self.rest("POST", parent + "/reasoningEngines", {"displayName": SESSION_LABEL})
        while not operation.get("done"):
            print("session_instance_creation=pending", flush=True)
            time.sleep(5)
            operation = self.rest("GET", operation["name"])
        if operation.get("error"):
            raise RuntimeError(self.scrub(json.dumps(operation["error"])))
        print("session_instance_creation=complete", flush=True)
        return operation["response"]["name"].split("/")[-1]

    def bootstrap(self) -> None:
        databases = json.loads(self.command("list databases", ["gcloud", "firestore", "databases", "list", "--format=json", "--quiet"]))
        if not any(entry["name"].endswith("/" + DATABASE) for entry in databases):
            self.command("create app database", ["gcloud", "firestore", "databases", "create", "--database", DATABASE,
                                                   "--location", REGION, "--type", "firestore-native", "--delete-protection", "--quiet"])
        print("dedicated_firestore_database=ready", flush=True)
        accounts = json.loads(self.command("list service accounts", ["gcloud", "iam", "service-accounts", "list", "--format=json"]))
        for account in (RUNTIME_ACCOUNT, BUILD_ACCOUNT):
            address = f"{account}@{self.project}.iam.gserviceaccount.com"
            if not any(entry["email"] == address for entry in accounts):
                self.command("create app account", ["gcloud", "iam", "service-accounts", "create", account,
                                                      "--display-name", account, "--quiet"])
            roles = ["roles/datastore.user", "roles/aiplatform.user"] if account == RUNTIME_ACCOUNT else ["roles/run.builder"]
            for role in roles:
                self.command("grant app role", ["gcloud", "projects", "add-iam-policy-binding", self.project,
                                                 "--member", "serviceAccount:" + address, "--role", role,
                                                 "--condition=None", "--quiet", "--format=none"])
        print("dedicated_service_accounts=ready", flush=True)
        secrets = json.loads(self.command("list secrets", ["gcloud", "secrets", "list", "--format=json"]))
        if not any(entry["name"].endswith("/" + SECRET) for entry in secrets):
            self.command("create app secret", ["gcloud", "secrets", "create", SECRET, "--replication-policy=automatic", "--quiet"])
        versions = json.loads(self.command("list app secret versions", ["gcloud", "secrets", "versions", "list", SECRET, "--format=json"]))
        if not any(entry.get("state") == "ENABLED" for entry in versions):
            if not self.key:
                raise RuntimeError("Runtime Gemini key is absent")
            self.command("write app secret version", ["gcloud", "secrets", "versions", "add", SECRET, "--data-file=-", "--quiet"], data=self.key)
        self.command("grant app secret access", ["gcloud", "secrets", "add-iam-policy-binding", SECRET,
                                                   "--member", f"serviceAccount:{RUNTIME_ACCOUNT}@{self.project}.iam.gserviceaccount.com",
                                                   "--role", "roles/secretmanager.secretAccessor", "--quiet", "--format=none"])
        print("runtime_secret=ready; value_not_logged=true", flush=True)
        repositories = json.loads(self.command("list artifact repositories", ["gcloud", "artifacts", "repositories", "list", "--location", REGION, "--format=json"]))
        if not any(entry["name"].endswith("/preflight") for entry in repositories):
            self.command("create app artifact repository", ["gcloud", "artifacts", "repositories", "create", "preflight",
                                                               "--location", REGION, "--repository-format=docker", "--quiet"])
        print("dedicated_artifact_repository=ready", flush=True)
        self.session_engine(create=True)
        print("agent_platform_session_service=ready", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["bootstrap", "session-check"])
    arguments = parser.parse_args()
    try:
        operations = CloudOperations()
        if arguments.action == "bootstrap":
            operations.bootstrap()
        else:
            operations.session_engine()
            print("session_service_instance_present=true")
    except Exception as error:
        # CloudOperations only exposes sanitized failures; never print command arguments.
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    main()
