"use strict";

(() => {
  const form = document.getElementById("postcheck-form");
  const fileInput = document.getElementById("clip-file");
  const promptInput = document.getElementById("clip-prompt");
  const modelInput = document.getElementById("clip-model");
  const preview = document.getElementById("clip-preview");
  const button = document.getElementById("review-button");
  const error = document.getElementById("postcheck-error");
  const results = document.getElementById("postcheck-results");
  const announcement = document.getElementById("review-announcement");
  const maxBytes = 30 * 1024 * 1024;
  const maxSeconds = 30;
  let selectedFile = null;
  let previewUrl = null;
  let duration = null;
  let available = false;
  let busy = false;
  let durationInvalid = false;

  const finite = value => typeof value === "number" && Number.isFinite(value);
  const rate = value => finite(value) && value >= 0 && value <= 1;
  const percent = value => rate(value) ? `${(value * 100).toFixed(1)}%` : "Unavailable";

  function updateButton() { button.disabled = !available || busy || !selectedFile || durationInvalid; }
  function clearError() {
    error.hidden = true;
    error.textContent = "";
    promptInput.removeAttribute("aria-invalid");
  }
  function showError(message, invalidPrompt = false) {
    error.textContent = message;
    error.hidden = false;
    if (invalidPrompt) promptInput.setAttribute("aria-invalid", "true");
  }
  function resetResult() {
    document.getElementById("verdict-card").classList.remove("verdict-pass", "verdict-flagged");
    document.getElementById("verdict-state").textContent = "NO CLIP REVIEWED";
    document.getElementById("verdict-value").textContent = "A closer look.";
    document.getElementById("verdict-description").textContent = "Review sampled frames for visible defects in your existing clip.";
    document.getElementById("reviewed-clip").hidden = true;
    document.getElementById("defects").hidden = true;
    document.getElementById("defects").replaceChildren();
    document.getElementById("feedback-before").textContent = "—";
    document.getElementById("feedback-after").textContent = "—";
    document.getElementById("feedback-history").textContent = "The original historical human-vote estimate will be shown separately.";
    document.getElementById("feedback-receipt").hidden = true;
    document.getElementById("feedback-description").textContent = "This proxy can incorporate machine feedback. It is not a change to the public historical both-bad vote rate.";
    document.querySelector(".feedback-card").classList.remove("risk-increased", "risk-decreased");
    document.getElementById("sampling-note").textContent = "Review targets 2 fps; the default video sampling rate is 1 fps. Sampling may miss flicker shorter than 0.5 seconds.";
  }
  function removeClip() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
    selectedFile = null;
    duration = null;
    durationInvalid = false;
    fileInput.value = "";
    preview.removeAttribute("src");
    preview.load();
    preview.hidden = true;
    document.getElementById("clip-selected").hidden = true;
    document.getElementById("upload-zone").hidden = false;
    clearError();
    resetResult();
    updateButton();
  }
  function updateFileMeta() {
    if (!selectedFile) return;
    const size = `${(selectedFile.size / 1024 / 1024).toFixed(1)} MiB`;
    document.getElementById("clip-filemeta").textContent = `${size}${finite(duration) ? ` · ${duration.toFixed(1)}s` : " · duration verified by server"}`;
  }
  function chooseFile(file) {
    if (busy) return;
    removeClip();
    if (!file) return;
    if (!file.size) { showError("Choose a video file that is not empty."); return; }
    if (file.size > maxBytes) { showError("Choose a clip no larger than 30 MiB."); return; }
    if ((file.type && file.type !== "video/mp4") || (!file.type && !/\.mp4$/i.test(file.name))) { showError("Choose an MP4 video clip for this review."); return; }
    selectedFile = file;
    document.getElementById("clip-filename").textContent = file.name;
    document.getElementById("clip-selected").hidden = false;
    document.getElementById("upload-zone").hidden = true;
    updateFileMeta();
    previewUrl = URL.createObjectURL(file);
    preview.src = previewUrl;
    preview.hidden = false;
    updateButton();
  }
  fileInput.addEventListener("change", () => chooseFile(fileInput.files[0]));
  document.getElementById("remove-clip").addEventListener("click", removeClip);
  const zone = document.getElementById("upload-zone");
  ["dragenter", "dragover"].forEach(name => zone.addEventListener(name, event => { event.preventDefault(); if (!busy) zone.classList.add("dragging"); }));
  ["dragleave", "drop"].forEach(name => zone.addEventListener(name, event => { event.preventDefault(); zone.classList.remove("dragging"); }));
  zone.addEventListener("drop", event => {
    if (busy) return;
    const files = event.dataTransfer?.files;
    if (files?.length > 1) { showError("Choose one video clip at a time."); return; }
    chooseFile(files?.[0]);
  });
  preview.addEventListener("loadedmetadata", () => {
    duration = finite(preview.duration) ? preview.duration : null;
    durationInvalid = finite(duration) && duration > maxSeconds;
    updateFileMeta();
    if (durationInvalid) showError("Choose a clip no longer than 30 seconds.");
    updateButton();
  });
  preview.addEventListener("error", () => {
    if (selectedFile) document.getElementById("clip-filemeta").textContent = `${(selectedFile.size / 1024 / 1024).toFixed(1)} MiB · preview unavailable; server will verify the clip`;
  });
  document.getElementById("reuse-prompt").addEventListener("click", () => {
    const prompt = document.getElementById("prompt").value.trim();
    if (!prompt) { showError("Add a prompt above first, or describe the clip here.", true); promptInput.focus(); return; }
    promptInput.value = prompt;
    clearError();
    resetResult();
    promptInput.focus();
  });
  promptInput.addEventListener("input", () => { clearError(); resetResult(); });
  modelInput.addEventListener("input", resetResult);

  function timeInSeconds(defect) {
    if (finite(defect.seconds) && defect.seconds >= 0) return defect.seconds;
    if (typeof defect.timecode !== "string") return null;
    const parts = defect.timecode.match(/^(\d{1,2}):(\d{2})(?:\.(\d+))?$/);
    return parts ? Number(parts[1]) * 60 + Number(parts[2]) + Number(`0.${parts[3] || 0}`) : null;
  }
  function timeLabel(seconds) {
    if (!finite(seconds)) return "Time not supplied";
    return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
  }
  function render(data, label) {
    const verdict = typeof data.pass_bool === "boolean" ? data.pass_bool : null;
    const card = document.getElementById("verdict-card");
    card.classList.toggle("verdict-pass", verdict === true);
    card.classList.toggle("verdict-flagged", verdict === false);
    document.getElementById("verdict-state").textContent = verdict === null ? "NO VERDICT" : data.reused_stored_review === true ? "STORED REVIEW REUSED" : "MACHINE REVIEW COMPLETE";
    document.getElementById("verdict-value").textContent = verdict === true ? "Pass" : verdict === false ? "Flagged" : "Inconclusive";
    document.getElementById("verdict-description").textContent = verdict === true ? "No defects flagged in the sampled frames." : verdict === false ? "The machine review flagged defects in the sampled frames." : "The service did not provide a pass or fail verdict.";
    const reviewed = document.getElementById("reviewed-clip");
    reviewed.textContent = `Owner-provided AI clip · ${label}${finite(data.reviewed_duration_seconds) ? ` · ${data.reviewed_duration_seconds.toFixed(1)}s reviewed` : ""}${data.reused_stored_review === true ? " · stored review reused" : ""}`;
    reviewed.hidden = false;
    const defects = document.getElementById("defects");
    defects.replaceChildren();
    const items = Array.isArray(data.defects) ? data.defects.filter(item => item && typeof item.reason === "string") : [];
    defects.hidden = !items.length;
    items.forEach(defect => {
      const row = document.createElement("div");
      row.className = "defect-row";
      const seconds = timeInSeconds(defect);
      const time = document.createElement(finite(seconds) ? "button" : "span");
      time.className = "defect-time";
      time.textContent = timeLabel(seconds);
      if (finite(seconds)) {
        time.type = "button";
        time.setAttribute("aria-label", `Jump to ${timeLabel(seconds)} in the clip`);
        time.addEventListener("click", () => { if (finite(preview.duration)) preview.currentTime = Math.min(seconds, preview.duration); preview.focus(); });
      }
      const description = document.createElement("p");
      if (typeof defect.category === "string" && defect.category.trim()) {
        const category = document.createElement("strong");
        category.textContent = `${defect.category.replaceAll("_", " ")} · `;
        description.append(category);
      }
      description.append(document.createTextNode(defect.reason));
      row.append(time, description);
      defects.append(row);
    });
    document.getElementById("feedback-before").textContent = percent(data.risk_before);
    document.getElementById("feedback-after").textContent = percent(data.risk_after);
    const feedbackCard = document.querySelector(".feedback-card");
    feedbackCard.classList.toggle("risk-increased", rate(data.risk_before) && rate(data.risk_after) && data.risk_after > data.risk_before);
    feedbackCard.classList.toggle("risk-decreased", rate(data.risk_before) && rate(data.risk_after) && data.risk_after < data.risk_before);
    document.getElementById("feedback-history").textContent = rate(data.historical_p_fail) ? `Separate historical human-vote estimate: ${percent(data.historical_p_fail)}.` : "A historical human-vote estimate is unavailable for this prompt.";
    document.getElementById("feedback-description").textContent = `${typeof data.risk_semantics === "string" && data.risk_semantics.trim() ? data.risk_semantics : "The before/after values are a feedback-adjusted proxy."} The public historical both-bad vote rate is separate and does not change from this machine review.`;
    const feedbackReceipt = document.getElementById("feedback-receipt");
    feedbackReceipt.hidden = false;
    const count = Number.isInteger(data.feedback?.count) && data.feedback.count >= 0 ? ` · ${data.feedback.count} machine feedback record${data.feedback.count === 1 ? "" : "s"}` : "";
    feedbackReceipt.textContent = data.feedback_recorded === true ? `${data.reused_stored_review === true ? "Stored review reused; existing machine feedback retained" : data.feedback_created === false ? "Existing machine feedback retained" : "Machine feedback recorded"}${count}.` : "Feedback recording was not confirmed by the service.";
    const fps = finite(data.analysis?.sampling_fps) && data.analysis.sampling_fps > 0 ? data.analysis.sampling_fps : null;
    const defaultFpsValue = data.analysis?.default_video_sampling_fps ?? data.analysis?.default_video_fps;
    const defaultFps = finite(defaultFpsValue) && defaultFpsValue > 0 ? defaultFpsValue : null;
    document.getElementById("sampling-note").textContent = fps ? `Reviewed at ${fps} fps${defaultFps ? ` (default video sampling: ${defaultFps} fps)` : ""}. Sampling may miss flicker shorter than ${(1 / fps).toFixed(1)} seconds.` : "The service did not report a sampling rate. Frame sampling can miss brief flicker and other defects between sampled frames.";
    announcement.textContent = `Machine review complete: ${verdict === true ? "pass" : verdict === false ? "defects flagged" : "inconclusive"}. This is separate from historical human votes.`;
  }

  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (busy) return;
    clearError();
    if (!available) { showError("Upload review is not connected in the current service mode."); return; }
    if (!selectedFile) { showError("Choose an existing video clip first."); return; }
    if (selectedFile.size > maxBytes || durationInvalid) { showError("Choose a clip up to 30 MiB and 30 seconds."); return; }
    const prompt = promptInput.value.trim();
    if (!prompt || prompt.length > 4000) { showError(!prompt ? "Describe what should happen in the clip." : "Keep the clip prompt to 4,000 characters or fewer.", true); promptInput.focus(); return; }
    const label = modelInput.value.trim() || "owner-upload";
    const body = new FormData();
    body.append("video", selectedFile, selectedFile.name);
    body.append("prompt", prompt);
    body.append("model", label);
    resetResult();
    document.getElementById("verdict-state").textContent = "REVIEWING SAMPLED FRAMES";
    document.getElementById("verdict-value").textContent = "Reading the clip.";
    busy = true;
    document.getElementById("review-progress").hidden = false;
    updateButton();
    button.classList.add("loading");
    document.getElementById("review-button-label").textContent = "Reviewing sampled frames…";
    results.setAttribute("aria-busy", "true");
    form.querySelectorAll("input,textarea,button").forEach(element => { element.disabled = true; });
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000);
    announcement.textContent = "Uploading your existing clip for machine review.";
    try {
      const response = await fetch("/postcheck", {method: "POST", credentials: "same-origin", body, signal: controller.signal});
      let data;
      try { data = await response.json(); } catch { throw new Error("The review service returned an unreadable response."); }
      if (!response.ok) throw new Error(typeof data?.detail === "string" ? data.detail : `The clip review could not be completed (${response.status}).`);
      if (!data || typeof data !== "object" || Array.isArray(data)) throw new Error("The review service returned an incomplete response.");
      render(data, label);
    } catch (exception) {
      showError(exception.name === "AbortError" ? "The clip review took too long. No new result is shown." : exception instanceof TypeError ? "Could not reach the clip review service. Check your connection." : exception.message || "The clip review could not be completed.");
      document.getElementById("verdict-state").textContent = "REVIEW NOT COMPLETED";
      document.getElementById("verdict-value").textContent = "Unavailable";
      document.getElementById("verdict-description").textContent = "No machine verdict was returned for this request.";
      announcement.textContent = "The clip review could not be completed. No new verdict was created in the interface.";
    } finally {
      clearTimeout(timeout);
      busy = false;
      document.getElementById("review-progress").hidden = true;
      form.querySelectorAll("input,textarea,button").forEach(element => { element.disabled = false; });
      button.classList.remove("loading");
      document.getElementById("review-button-label").textContent = "Review this clip";
      results.setAttribute("aria-busy", "false");
      updateButton();
    }
  });

  window.preflightStatusReady.then(status => {
    available = status?.postcheck === true;
    document.getElementById("postcheck-status").textContent = available ? "Clip review available" : "Clip review unavailable";
    document.getElementById("postcheck-availability").textContent = available ? "Upload-only review is connected. Your clip is sent only when you press Review." : "Upload review is unavailable in the current service mode. You can prepare a clip and prompt here.";
    updateButton();
  });
  window.addEventListener("beforeunload", () => { if (previewUrl) URL.revokeObjectURL(previewUrl); });
})();
