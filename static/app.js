"use strict";

(() => {
  const form = document.getElementById("prompt-form");
  const input = document.getElementById("prompt");
  const button = document.getElementById("check-button");
  const buttonLabel = document.getElementById("button-label");
  const error = document.getElementById("prompt-error");
  const results = document.querySelector(".results-panel");
  const riskCard = document.querySelector(".risk-card");
  const state = document.getElementById("result-state");
  const announcement = document.getElementById("results-announcement");
  const why = document.getElementById("why-content");
  const neighbors = document.getElementById("neighbors");
  const samples = [...document.querySelectorAll(".sample")];
  let requestId = 0;
  let lastPrompt = null;
  let lastState = "READY WHEN YOU ARE";
  let hasResult = false;
  let serviceStatus = null;
  let sessionId = null;
  const previewLimited = "Live stills are limited to the sample prompts during judging — shared Gemini image capacity. The risk check still works.";

  function previewModeMessage() {
    if (typeof serviceStatus?.preview_mode_message === "string") return serviceStatus.preview_mode_message;
    return serviceStatus?.preview === true
      ? `Image preview — Active for sample prompts (saved stills); live generation ${serviceStatus.preview_mode === "samples+live" ? "on" : "limited"}`
      : "Image preview — Not active; live generation limited";
  }

  function clearError() {
    error.hidden = true;
    error.textContent = "";
    input.removeAttribute("aria-invalid");
  }

  function showError(message, invalidInput = false) {
    error.textContent = message;
    error.hidden = false;
    if (invalidInput) input.setAttribute("aria-invalid", "true");
  }

  function updateInput() {
    document.getElementById("character-count").textContent = `${input.value.length.toLocaleString("en-US")} / 4,000`;
    samples.forEach(sample => sample.classList.toggle("selected", input.value.trim() === sample.dataset.prompt));
    clearError();
    if (lastPrompt !== null) state.textContent = input.value.trim() === lastPrompt ? lastState : "PROMPT CHANGED";
  }

  input.addEventListener("input", updateInput);
  samples.forEach(sample => sample.addEventListener("click", () => {
    input.value = sample.dataset.prompt;
    updateInput();
    input.focus();
  }));

  function setLoading(loading) {
    button.disabled = loading;
    input.readOnly = loading;
    samples.forEach(sample => { sample.disabled = loading; });
    button.classList.toggle("loading", loading);
    buttonLabel.textContent = loading ? "Checking the evidence…" : "Check this prompt";
    results.classList.toggle("is-loading", loading);
    results.setAttribute("aria-busy", String(loading));
    if (loading) state.textContent = serviceStatus?.mode === "cloud" ? "CHECKING YOUR PROMPT" : "CHECKING EVIDENCE";
  }

  function finite(value) { return typeof value === "number" && Number.isFinite(value); }
  function rate(value) { return finite(value) && value >= 0 && value <= 1; }
  function percent(value) { return `${(value * 100).toFixed(1)}%`; }
  function hasMixedFeedback(data) {
    return (finite(data.postcheck_feedback?.count) && data.postcheck_feedback.count > 0)
      || (typeof data.risk_semantics === "string" && /\bmixed\b/i.test(data.risk_semantics))
      || (rate(data.historical_p_fail) && rate(data.p_fail) && Math.abs(data.historical_p_fail - data.p_fail) > 1e-12);
  }

  function twoSentences(values) {
    const text = (Array.isArray(values) ? values : [values]).filter(value => typeof value === "string" && value.trim()).join(" ");
    if (!text) return "";
    if (typeof Intl.Segmenter === "function") return [...new Intl.Segmenter("en", {granularity: "sentence"}).segment(text)].slice(0, 2).map(item => item.segment.trim()).join(" ");
    return (text.match(/[^.!?]+(?:[.!?](?=\s|$)|$)/g) || [text]).slice(0, 2).join(" ").trim();
  }

  function renderReasons(reasons, fallback) {
    why.replaceChildren();
    why.classList.remove("empty-body");
    const paragraph = document.createElement("p");
    paragraph.textContent = twoSentences(reasons) || fallback;
    why.append(paragraph);
  }

  function rewriteMessage(tagText, message, note) {
    const content = document.getElementById("better-content");
    content.replaceChildren();
    const tag = document.createElement("span");
    tag.className = "feature-tag";
    tag.textContent = tagText;
    const description = document.createElement("p");
    description.className = "rewrite-description";
    description.textContent = message;
    const caption = document.createElement("p");
    caption.className = "subtle-copy";
    caption.textContent = note;
    content.append(tag, description, caption);
  }

  function renderRewrite(data, prompt) {
    const mixed = hasMixedFeedback(data);
    const before = data.p_fail_before;
    const after = data.p_fail_after;
    const candidate = typeof data.rewritten_prompt === "string" ? data.rewritten_prompt.trim() : "";
    const improved = data.rewrite_status === "improved" && candidate && candidate !== prompt && rate(before) && rate(after) && after < before;
    document.querySelector(".better-card").classList.toggle("has-rewrite", Boolean(improved));
    if (!improved) {
      if (data.rewrite_status === "no_safe_rewrite" || data.rewrite_status === "improved") {
        rewriteMessage("NO SAFER REWRITE", mixed ? "No rewrite passed the estimated risk check." : "No rewrite passed the historical risk check.", "Keep your original prompt or try a more specific scene. No alternative is presented as an improvement.");
      } else {
        rewriteMessage("GEMINI REWRITE · UNAVAILABLE", "A rewrite is unavailable for this check.", serviceStatus?.mode === "local-g0" ? "This local build checks historical evidence only." : "The evidence check remains available. No alternative prompt has been approved.");
      }
      return;
    }
    const content = document.getElementById("better-content");
    content.replaceChildren();
    const tag = document.createElement("span");
    tag.className = "feature-tag improved-tag";
    tag.textContent = mixed ? "LOWER ESTIMATED RISK" : "LOWER HISTORICAL RISK";
    const quote = document.createElement("p");
    quote.className = "rewritten-prompt";
    quote.textContent = candidate;
    const comparison = document.createElement("div");
    comparison.className = "rewrite-comparison";
    comparison.setAttribute("aria-label", `${mixed ? "Estimated" : "Historical"} risk: original ${percent(before)}, rewrite ${percent(after)}`);
    const from = document.createElement("span");
    from.textContent = percent(before);
    const arrow = document.createElement("span");
    arrow.textContent = "→";
    arrow.setAttribute("aria-hidden", "true");
    const to = document.createElement("strong");
    to.textContent = percent(after);
    comparison.append(from, arrow, to);
    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "copy-button";
    copy.textContent = "Copy better prompt ↗";
    copy.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(candidate);
        copy.textContent = "Copied ✓";
        announcement.textContent = "Better prompt copied.";
      } catch {
        copy.textContent = "Select the prompt to copy";
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(quote);
        selection.removeAllRanges();
        selection.addRange(range);
        announcement.textContent = "Select and copy the highlighted prompt.";
      }
    });
    const caption = document.createElement("p");
    caption.className = "subtle-copy";
    caption.textContent = mixed ? "This estimate mixes human votes and separate machine clip reviews. A lower score does not guarantee a better video." : "A lower historical estimate is not a guarantee of a better video.";
    const comparisonLabel = document.createElement("p");
    comparisonLabel.className = "subtle-copy rewrite-comparison-label";
    comparisonLabel.textContent = mixed ? "Original → rewrite · estimated risk" : "Original → rewrite · historical risk";
    content.append(tag, comparison, comparisonLabel, quote, copy, caption);
  }

  function renderNeighbors(items, supported) {
    neighbors.replaceChildren();
    const validItems = supported && Array.isArray(items) ? items.filter(item => item && typeof item.prompt === "string" && rate(item.both_bad_rate)).slice(0, 3) : [];
    neighbors.hidden = validItems.length === 0;
    if (!validItems.length) return;
    const title = document.createElement("p");
    title.className = "neighbors-title";
    title.textContent = "SIMILAR HISTORICAL PROMPTS";
    neighbors.append(title);
    validItems.forEach(item => {
      const row = document.createElement("div");
      row.className = "neighbor";
      const text = document.createElement("span");
      text.textContent = item.prompt;
      const value = document.createElement("span");
      value.textContent = percent(item.both_bad_rate);
      value.title = "Historical both-bad vote rate for this prompt";
      row.append(text, value);
      neighbors.append(row);
    });
  }

  function renderBudget(data, supported) {
    const costValue = document.getElementById("cost-value");
    const costNote = document.getElementById("cost-note");
    if (!supported || !finite(data.est_cost_usd) || data.est_cost_usd < 0) {
      costValue.textContent = "Unavailable";
      costNote.textContent = supported ? "No generation has been requested. A generation budget was not provided." : "No budget is estimated when historical coverage is insufficient. No generation has been requested.";
      return;
    }
    costValue.textContent = new Intl.NumberFormat("en-US", {style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 2}).format(data.est_cost_usd);
    const pricing = data.pricing || {};
    const duration = finite(pricing.duration_seconds) && pricing.duration_seconds > 0 ? `${pricing.duration_seconds}s` : "video";
    const attemptCost = finite(pricing.single_attempt_usd) && pricing.single_attempt_usd > 0 ? `$${pricing.single_attempt_usd.toFixed(2)} per ${duration} attempt` : "the configured per-attempt price";
    costNote.textContent = `Illustration using ${attemptCost} and ${hasMixedFeedback(data) ? "the mixed risk estimate" : "historical votes"}, capped at 5 attempts. This is not a Veo cost forecast. No generation has been requested.`;
  }

  function renderPreview(original, rewrite, savedSample = false) {
    const container = document.createElement("div");
    container.className = "preview-controls";
    const status = document.createElement("p");
    status.className = "subtle-copy preview-mode-message";
    status.textContent = previewModeMessage();
    const action = document.createElement("button");
    action.type = "button";
    action.className = "primary-button preview-button";
    const label = savedSample && !rewrite ? "Preview saved sample (unchanged)" : "Preview a still";
    const text = document.createElement("span");
    text.textContent = label;
    const spinner = document.createElement("span");
    spinner.className = "button-spinner";
    spinner.setAttribute("aria-hidden", "true");
    action.append(text, spinner);
    action.disabled = serviceStatus?.preview !== true;
    if (action.disabled) action.title = previewLimited;
    const output = document.createElement("div");
    output.setAttribute("aria-live", "polite");
    if (action.disabled) {
      const message = document.createElement("p");
      message.className = "subtle-copy";
      message.textContent = action.title;
      output.append(message);
    }
    let busy = false;
    let retryAt = 0;
    let originalLink = null;
    async function run(useOriginal) {
      if (busy || Date.now() < retryAt || serviceStatus?.preview !== true) return;
      busy = true;
      action.disabled = true;
      if (originalLink) originalLink.disabled = true;
      action.classList.add("loading");
      text.textContent = "Preparing still…";
      output.replaceChildren();
      try {
        const response = await fetch("/preview", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({prompt: useOriginal || !rewrite ? original : rewrite,
            variant: useOriginal || (!rewrite && !savedSample) ? "original" : "rewrite", session_id: sessionId})});
        const data = await response.json();
        if (!response.ok) {
          const retry = Number(response.headers.get("Retry-After"));
          if (response.status === 429 && retry > 0) retryAt = Date.now() + retry * 1000;
          throw new Error(previewLimited);
        }
        if (typeof data.image_data_url !== "string" || !data.image_data_url.startsWith("data:image/jpeg;base64,"))
          throw new Error(previewLimited);
        const image = document.createElement("img");
        image.src = data.image_data_url;
        image.alt = "Image model still for the selected prompt";
        image.className = "preview-image";
        const caption = document.createElement("p");
        caption.className = "subtle-copy";
        caption.textContent = data.caption;
        const metadata = document.createElement("p");
        metadata.className = "preview-metadata";
        const cached = response.headers.get("X-Preview-Cache") === "hit" || data.cache === "hit";
        const generatedDate = data.generated_date || data.generated_at?.slice(0, 10) || "date unavailable";
        metadata.textContent = typeof data.metadata_label === "string" ? data.metadata_label : cached
          ? `Saved still · generated ${generatedDate} · 0 model calls · $0.00`
          : `Model ${data.model} · ${data.size} · $${Number(data.cost_usd).toFixed(6).replace(/0+$/, "").replace(/\.$/, ".00")} · ${(data.latency_ms / 1000).toFixed(1)} s`;
        const link = document.createElement("a");
        link.href = "https://ai.google.dev/gemini-api/docs/veo";
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "Use as a Veo first frame ↗";
        output.dataset.state = cached ? "cached" : "done";
        output.append(image, caption, metadata, link);
      } catch (error) {
        const message = document.createElement("p");
        message.className = "form-error";
        message.textContent = previewLimited;
        output.dataset.state = retryAt > Date.now() ? "rate-limited" : "error";
        output.append(message);
      } finally {
        busy = false;
        action.disabled = serviceStatus?.preview !== true;
        if (originalLink) originalLink.disabled = action.disabled;
        action.classList.remove("loading");
        text.textContent = label;
      }
    }
    action.addEventListener("click", () => run(false));
    container.append(status, action);
    if (rewrite || savedSample) {
      originalLink = document.createElement("button");
      originalLink.type = "button";
      originalLink.className = "preview-original";
      originalLink.textContent = "Preview the original instead";
      originalLink.disabled = action.disabled;
      originalLink.addEventListener("click", () => run(true));
      container.append(originalLink);
    }
    container.append(output);
    document.getElementById("better-content").append(container);
  }

  function renderResult(data, prompt) {
    riskCard.classList.add("has-result");
    document.querySelector(".better-card").classList.add("has-result");
    state.hidden = false;
    document.querySelector(".risk-card .evidence-boundary").hidden = false;
    const mixed = hasMixedFeedback(data);
    const supported = data.supported !== false && data.coverage_supported !== false && data.coverage?.status !== "unsupported" && rate(data.p_fail);
    const value = document.getElementById("risk-value");
    const unit = document.getElementById("risk-unit");
    const detail = document.getElementById("risk-detail");
    const label = document.getElementById("risk-label");
    riskCard.classList.remove("high-risk", "unsupported");
    if (!supported) {
      value.textContent = "—";
      unit.hidden = true;
      label.textContent = "Outside the available evidence.";
      detail.textContent = "This prompt doesn't match the historical vocabulary. Try describing a scene with a subject and an action.";
      document.getElementById("risk-fill").style.width = "0%";
      riskCard.classList.add("unsupported");
      state.textContent = "LIMITED COVERAGE";
      renderReasons(data.reasons, "This prompt is outside the local dataset’s coverage. Try one of the sample prompts to inspect supported evidence.");
      announcement.textContent = "Check complete. Historical coverage is insufficient. No risk value or generation budget is assigned.";
    } else {
      value.textContent = (data.p_fail * 100).toFixed(1);
      unit.hidden = false;
      label.textContent = mixed ? "Mixed heuristic risk estimate" : "Estimated historical both-bad rate";
      detail.textContent = typeof data.risk_semantics === "string" && data.risk_semantics.trim() ? data.risk_semantics : mixed ? "A proxy combining historical human votes with separate machine clip reviews." : "Statistical estimate from public historical votes on related prompts.";
      document.getElementById("risk-fill").style.width = `${data.p_fail * 100}%`;
      if (data.p_fail >= 0.5) riskCard.classList.add("high-risk");
      state.textContent = serviceStatus?.mode === "local-g0" ? "LOCAL CHECK COMPLETE" : "CHECK COMPLETE";
      renderReasons(data.reasons, mixed ? "This estimate combines historical human votes with separate machine clip reviews. It has not been validated against Veo generations." : "The local estimate is based on public historical votes. It has not been validated against Veo generations.");
      announcement.textContent = `Check complete. Risk estimate: ${percent(data.p_fail)}. This is not a validated Veo failure probability.`;
    }
    renderNeighbors(data.nearest_prompts, supported);
    renderBudget(data, supported);
    renderRewrite(data, prompt);
    const accepted = data.rewrite_status === "improved" && data.rewritten_prompt &&
      data.rewritten_prompt !== prompt && rate(data.p_fail_before) && rate(data.p_fail_after) &&
      data.p_fail_after < data.p_fail_before;
    const savedSample = data.rewrite_source === "pinned-sample";
    if (savedSample) {
      const saved = document.createElement("p");
      saved.className = "subtle-copy sample-rewrite-label saved-rewrite-label";
      saved.textContent = "Sample rewrite (saved)";
      const content = document.getElementById("better-content");
      content.insertBefore(saved, content.querySelector(".rewritten-prompt"));
      if (!accepted) {
        const unchanged = document.createElement("p");
        unchanged.className = "subtle-copy saved-sample-unchanged";
        unchanged.textContent = "No lower-risk rewrite was accepted; the saved sample uses the original prompt.";
        content.append(unchanged);
      }
    }
    if (accepted) {
      const note = document.createElement("p");
      note.className = "subtle-copy";
      note.textContent = "The rewrite is in English; non-English words were not scored.";
      document.getElementById("better-content").append(note);
    }
    renderPreview(prompt, accepted ? data.rewritten_prompt : null, savedSample);
    document.querySelector(".risk-card .evidence-boundary").textContent = mixed ? "This mixes historical human pairwise votes with separate machine clip verdicts. It is not a validated Veo failure probability." : "Historical evidence is a signal, not a validated probability of a Veo generation failing.";
    const historical = document.getElementById("risk-history");
    historical.hidden = !supported || !rate(data.historical_p_fail);
    historical.textContent = rate(data.historical_p_fail) ? `Historical vote estimate: ${percent(data.historical_p_fail)}` : "";
    hasResult = true;
    lastPrompt = prompt;
    lastState = state.textContent;
    const checkedPrompt = document.getElementById("checked-prompt");
    checkedPrompt.textContent = `Checked: “${prompt}”`;
    checkedPrompt.title = prompt;
    checkedPrompt.hidden = false;
  }

  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (button.disabled) return;
    clearError();
    const prompt = input.value.trim();
    if (!prompt) {
      showError("Add a prompt or choose a sample to start.", true);
      input.focus();
      return;
    }
    if (prompt.length > 4000) {
      showError("Keep your prompt to 4,000 characters or fewer.", true);
      input.focus();
      return;
    }
    const thisRequest = ++requestId;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 90000);
    setLoading(true);
    announcement.textContent = "Checking the historical evidence and available rewrite.";
    try {
      const payload = {prompt};
      if (sessionId) payload.session_id = sessionId;
      const response = await fetch("/preflight", {method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload), signal: controller.signal});
      let data;
      try { data = await response.json(); } catch { throw new Error("The service returned an unreadable response. Try the check again."); }
      if (!response.ok) {
        const serverMessage = typeof data?.detail === "string" ? data.detail : typeof data?.error === "string" ? data.error : null;
        throw new Error(serverMessage || `The service could not complete this check (${response.status}). Try again.`);
      }
      if (!data || typeof data !== "object" || Array.isArray(data)) throw new Error("The service returned an incomplete response. Try the check again.");
      if (typeof data.session_id === "string" && data.session_id.length > 0) sessionId = data.session_id;
      if (thisRequest === requestId) renderResult(data, prompt);
    } catch (exception) {
      if (thisRequest !== requestId) return;
      showError(exception.name === "AbortError" ? "The check took too long. Please try again." : exception instanceof TypeError ? "Could not reach the service. Check your connection, then try again." : exception.message || "The check could not be completed. Please try again.");
      state.textContent = "CHECK NOT COMPLETED";
      announcement.textContent = "The check could not be completed. No new estimate was created.";
    } finally {
      clearTimeout(timeout);
      if (thisRequest === requestId) setLoading(false);
    }
  });

  window.preflightStatusReady.then(status => {
    serviceStatus = status;
    if (hasResult) {
      document.querySelectorAll(".preview-mode-message").forEach(message => { message.textContent = previewModeMessage(); });
      document.querySelectorAll(".preview-button, .preview-original").forEach(control => { control.disabled = status?.preview !== true; });
      return;
    }
    if (status?.gemini === true) rewriteMessage("GEMINI REWRITE · CONNECTED", "A rewrite appears only when it passes the risk check.", "A lower estimate does not guarantee a better video.");
    else rewriteMessage("GEMINI REWRITE · UNAVAILABLE", "A rewrite is unavailable in the current mode.", status?.mode === "local-g0" ? "This local build checks historical evidence only." : "The service has not confirmed an active rewrite connection.");
  });
})();
