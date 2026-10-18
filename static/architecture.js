"use strict";

(() => {
  const flow = document.getElementById("architecture-flow");
  function box(title, caption, active = true, output = false) {
    const node = document.createElement("div");
    node.className = `flow-box${active ? "" : " inactive"}${output ? " output" : ""}`;
    const heading = document.createElement("strong");
    heading.textContent = title;
    const note = document.createElement("small");
    note.textContent = caption;
    node.append(heading, note);
    return node;
  }
  function arrow() {
    const node = document.createElement("div");
    node.className = "flow-arrow";
    node.textContent = "↓";
    node.setAttribute("aria-hidden", "true");
    return node;
  }
  function split(...nodes) {
    const row = document.createElement("div");
    row.className = "flow-split";
    row.append(...nodes);
    return row;
  }
  window.preflightStatusReady.then(status => {
    const mode = document.getElementById("architecture-mode");
    const description = document.getElementById("architecture-description");
    const list = document.getElementById("component-list");
    flow.replaceChildren();
    list.replaceChildren();
    if (!status || !["cloud", "local-g0"].includes(status.mode)) {
      mode.textContent = "STATUS UNAVAILABLE";
      description.textContent = "The current request path could not be verified. Check the service connection and reload this page.";
      flow.append(box("Connections not confirmed", "No active runtime is claimed.", false));
      return;
    }
    mode.classList.remove("planned");
    mode.textContent = status.mode === "cloud" ? "CURRENT · CLOUD MODE" : "CURRENT · LOCAL PREVIEW";
    flow.append(box("Your prompt", "Browser · one scene description"), arrow());
    if (status.mode === "cloud") {
      description.textContent = "The cloud service checks the evidence and asks the connected agent for a safer rewrite. A candidate appears only after its historical risk estimate improves.";
      flow.append(box(status.cloud_run === true ? "Cloud Run" : "Cloud backend", status.cloud_run === true ? "Active · POST /preflight" : "Cloud Run runtime not confirmed"), arrow());
      flow.append(box("Google ADK agent", status.adk === true ? "Active · risk and rewrite tools" : "Not connected", status.adk === true), arrow());
      flow.append(split(box("Gemini", status.gemini === true ? "Connected · candidate rewrite" : "Not connected", status.gemini === true), box("Firestore", status.firestore === true ? "Connected · check records" : "Not connected", status.firestore === true)), arrow());
      flow.append(box("Agent Platform Sessions", status.agent_platform_session === true ? "Active · session state" : "Not active", status.agent_platform_session === true), arrow());
      flow.append(box("Risk · Why · Guarded rewrite", "A candidate is shown only after a strict risk reduction.", true, true));
      if (status.postcheck === true) {
        const uploadPath = document.createElement("div");
        uploadPath.className = "flow-branch";
        const label = document.createElement("p");
        label.className = "neighbors-title";
        label.textContent = "INDEPENDENT UPLOAD PATH · NO PREFLIGHT REQUIRED";
        uploadPath.append(label, box("Owner-provided AI clip + prompt", "POST /postcheck · no video generation"), arrow(), box("Gemini machine review", "Sampled-frame defects and machine verdict"), arrow(), box("Firestore feedback · adjusted risk", "Original human pairwise votes remain separate.", true, true));
        flow.append(uploadPath);
      }
    } else {
      description.textContent = "The browser sends your prompt to the local backend. Public historical prompt votes provide the risk estimate when coverage is sufficient. Each cloud connection is listed separately.";
      flow.append(box("Local backend", "POST /preflight"), arrow(), split(box("Historical votes", "Public data · local copy"), box("Statistical estimator", "Prompt coverage + vote signal")), arrow(), box("Risk · Why · Illustrative budget", "Or insufficient evidence when coverage is unsupported", true, true));
    }
    const components = [["Cloud Run", "cloud_run"], ["Google ADK", "adk"], ["Gemini rewriting", "gemini"], ["Firestore", "firestore"], ["Agent Platform Sessions", "agent_platform_session"], ["Existing clip review", "postcheck"], ["Image preview (Gemini image model)", "preview"]];
    components.forEach(([name, key], index) => {
      const item = document.createElement("li");
      const count = document.createElement("span");
      count.textContent = String(index + 1).padStart(2, "0");
      const text = document.createElement("div");
      const heading = document.createElement("strong");
      heading.textContent = name;
      const badge = document.createElement("span");
      badge.className = `connection-status${status[key] === true ? " active" : ""}`;
      badge.textContent = status[key] === true ? "Active" : "Not active";
      if (key === "preview") {
        const message = typeof status.preview_mode_message === "string" ? status.preview_mode_message : status.preview === true
          ? `Image preview — Active for sample prompts (saved stills); live generation ${status.preview_mode === "samples+live" ? "on" : "limited"}`
          : "Image preview — Not active; live generation limited";
        heading.textContent = message;
        heading.className = "preview-mode-message";
        badge.hidden = true;
      }
      text.append(heading, badge);
      item.append(count, text);
      list.append(item);
    });
  });
})();
