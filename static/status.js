"use strict";

window.preflightStatusReady = fetch("/api/status", {headers: {"Accept": "application/json"}})
  .then(response => { if (!response.ok) throw new Error("Service status unavailable"); return response.json(); })
  .then(status => {
    if (!status || typeof status !== "object") throw new Error("Service status unavailable");
    window.preflightStatus = status;
    const cloud = status.mode === "cloud";
    const local = status.mode === "local-g0";
    const label = document.getElementById("mode-label");
    const pill = document.querySelector(".mode-pill");
    if (label) label.textContent = cloud ? "CLOUD MODE" : local ? "LOCAL PREVIEW" : "STATUS UNKNOWN";
    if (pill) { pill.classList.toggle("pending", !cloud && !local); pill.classList.toggle("cloud", cloud); }
    const footer = document.getElementById("service-status");
    if (footer) footer.textContent = cloud ? "CLOUD STATISTICAL CHECK" : local ? "LOCAL STATISTICAL MODE" : "SERVICE MODE UNKNOWN";
    const runtime = document.getElementById("runtime-note");
    if (runtime) runtime.textContent = cloud ? (status.cloud_run === true ? "This check runs on Cloud Run." : "Connected statistical check.") : local ? "This check runs locally." : "Service mode could not be confirmed.";
    const session = document.getElementById("session-row");
    if (session) session.hidden = status.agent_platform_session !== true;
    return status;
  })
  .catch(() => {
    const label = document.getElementById("mode-label");
    if (label) label.textContent = "STATUS UNAVAILABLE";
    const footer = document.getElementById("service-status");
    if (footer) footer.textContent = "SERVICE STATUS UNAVAILABLE";
    const runtime = document.getElementById("runtime-note");
    if (runtime) runtime.textContent = "Service mode could not be confirmed.";
    return null;
  });
