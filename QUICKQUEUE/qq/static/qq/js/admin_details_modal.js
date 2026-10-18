(function () {
  "use strict";

  let modal = document.getElementById("admin-details-modal");
  if (!modal) {
    modal = document.createElement("div");
    modal.className = "admin-details-modal";
    modal.id = "admin-details-modal";
    modal.hidden = true;
    modal.innerHTML = '<div class="admin-details-backdrop" data-detail-close></div><section class="admin-details-card" role="dialog" aria-modal="true" aria-labelledby="admin-details-title" aria-describedby="admin-details-status" tabindex="-1"><header><div><small>QUICKQUEUE RECORD</small><h2 id="admin-details-title">Record Details</h2><p id="admin-details-subtitle"></p></div><button type="button" class="admin-details-x" data-detail-close aria-label="Close details">×</button></header><div class="admin-details-body"><p class="admin-details-status" id="admin-details-status" role="status">Select a record to view its details.</p><div class="admin-details-content" id="admin-details-content"></div></div><footer><button type="button" class="admin-details-close" data-detail-close>Close</button></footer></section>';
    document.body.appendChild(modal);
  }

  const card = modal.querySelector(".admin-details-card");
  const title = document.getElementById("admin-details-title");
  const subtitle = document.getElementById("admin-details-subtitle");
  const status = document.getElementById("admin-details-status");
  const content = document.getElementById("admin-details-content");
  let returnFocus = null;
  let requestController = null;

  function detailUrl(trigger) {
    if (trigger.dataset.detailUrl) return trigger.dataset.detailUrl;
    const target = trigger.getAttribute("href") || "";
    const match = target.match(/^#(?:appointment|resident|ticket|other)-(\d+)$/);
    if (!match) return "";
    let kind = "queueTicket";
    if (target.startsWith("#appointment-")) kind = "appointment";
    else if (target.startsWith("#resident-")) kind = "resident";
    const recordType = kind === "queueTicket" ? "queue-ticket" : kind;
    return "/barangay/details/" + recordType + "/" + match[1] + "/";
  }

  function fieldNode(field) {
    const item = document.createElement("div");
    item.className = "admin-details-field";
    const label = document.createElement("small");
    label.textContent = field.label || "Detail";
    const value = document.createElement("b");
    value.textContent = field.value || "—";
    item.append(label, value);
    return item;
  }

  function renderDetails(payload) {
    title.textContent = payload.title || "Record Details";
    subtitle.textContent = payload.subtitle || "";
    content.replaceChildren();
    (payload.sections || []).forEach(function (section) {
      const wrapper = document.createElement("section");
      wrapper.className = "admin-details-section";
      const heading = document.createElement("h3");
      heading.textContent = section.heading || "Information";
      const grid = document.createElement("div");
      grid.className = "admin-details-grid";
      (section.fields || []).forEach(function (field) { grid.appendChild(fieldNode(field)); });
      wrapper.append(heading, grid);
      content.appendChild(wrapper);
    });
    status.hidden = true;
  }

  function showStatus(message, isError) {
    status.hidden = false;
    status.textContent = message;
    status.classList.toggle("error", Boolean(isError));
    content.replaceChildren();
  }

  async function openDetails(trigger) {
    if (requestController) requestController.abort();
    requestController = new AbortController();
    returnFocus = trigger;
    title.textContent = "Record Details";
    subtitle.textContent = "";
    showStatus("Loading record details…", false);
    modal.hidden = false;
    document.body.classList.add("admin-details-open");
    card.focus();
    try {
      const response = await fetch(detailUrl(trigger), {
        headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" },
        cache: "no-store",
        signal: requestController.signal,
      });
      if (!response.ok) throw new Error(response.status === 404 ? "This record could not be found or is not available to your barangay." : "Unable to load this record right now.");
      renderDetails(await response.json());
    } catch (error) {
      if (error.name !== "AbortError") showStatus(error.message || "Unable to load this record right now.", true);
    }
  }

  function closeDetails() {
    if (modal.hidden) return;
    if (requestController) requestController.abort();
    modal.hidden = true;
    document.body.classList.remove("admin-details-open");
    if (returnFocus && document.contains(returnFocus)) returnFocus.focus();
    returnFocus = null;
  }

  document.addEventListener("click", function (event) {
    const trigger = event.target.closest("[data-detail-url],.btn-view[href^='#appointment-'],.btn-view[href^='#resident-'],.btn-view[href^='#ticket-'],.btn-view[href^='#other-']");
    if (trigger) {
      event.preventDefault();
      openDetails(trigger);
      return;
    }
    if (event.target.closest("[data-detail-close]")) closeDetails();
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !modal.hidden) closeDetails();
    if (event.key === "Tab" && !modal.hidden) {
      const focusable = Array.from(modal.querySelectorAll("button:not([disabled]),a[href]")).filter(function (element) { return element.offsetParent !== null; });
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
})();
