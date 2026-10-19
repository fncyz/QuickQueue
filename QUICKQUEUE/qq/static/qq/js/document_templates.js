(() => {
  const app = document.getElementById("document-template-app");
  if (!app) return;

  const endpoint = app.dataset.endpoint;
  const list = document.getElementById("template-list");
  const search = document.getElementById("template-search");
  const dialog = document.getElementById("template-dialog");
  const form = document.getElementById("template-form");
  const feedback = document.getElementById("feedback");
  const serviceField = document.getElementById("template-service");
  const nameField = document.getElementById("template-name");
  const fileField = document.getElementById("template-file");
  const viewer = document.getElementById("template-viewer");
  const viewerFrame = document.getElementById("viewer-frame");
  const viewerTitle = document.getElementById("viewer-title");
  const viewerDownload = document.getElementById("viewer-download");
  let templates = [];
  let editing = null;

  const csrf = () => document.cookie.split("; ").find((value) => value.startsWith("csrftoken="))?.split("=")[1] || "";
  const escapeHtml = (value) => {
    const node = document.createElement("span");
    node.textContent = value == null ? "" : String(value);
    return node.innerHTML;
  };
  const escapeAttribute = (value) => escapeHtml(value).replaceAll('"', "&quot;").replaceAll("'", "&#39;");
  const say = (message, error = false) => {
    feedback.textContent = message;
    feedback.className = error ? "error" : "success";
  };

  async function api(url = endpoint, options = {}) {
    options.headers = {...(options.headers || {}), "X-CSRFToken": csrf()};
    const response = await fetch(url, options);
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(Object.values(data).flat().join(" ") || "Request failed.");
    }
    return response.status === 204 ? null : response.json();
  }

  function iconClass(type) {
    const normalized = String(type || "").toUpperCase();
    if (normalized === "PDF") return "pdf";
    if (["DOC", "DOCX", "ODT"].includes(normalized)) return "word";
    return "generic";
  }

  function emptyState(filtered) {
    if (filtered) {
      return '<div class="template-empty"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m16 16 4 4"/></svg><b>No matching document templates.</b><span>Try another filename or service name.</span></div>';
    }
    return '<div class="template-empty"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h9l4 4v14H6zM15 3v5h5M9 13h6M9 17h6"/></svg><b>No document templates uploaded yet.</b><span>Upload a template to get started.</span></div>';
  }

  function card(template) {
    const type = template.file_type || "FILE";
    const filename = template.file_name || template.name;
    const updated = template.updated_at ? new Date(template.updated_at).toLocaleDateString(undefined, {
      year: "numeric", month: "short", day: "numeric",
    }) : "Not available";
    return `<article class="template-card" data-template-id="${template.id}">
      <div class="template-card-preview"><span class="file-icon ${iconClass(type)}" data-type="${escapeAttribute(type)}"><svg viewBox="0 0 24 28" aria-hidden="true"><path d="M4 2h10l6 6v18H4z"/><path d="M14 2v7h6M8 14h8M8 18h8"/></svg></span></div>
      <div class="template-card-body"><h2 class="template-card-title" title="${escapeAttribute(filename)}">${escapeHtml(filename)}</h2><p class="template-service">${escapeHtml(template.service_name)}</p><div class="template-metadata"><span><b>${escapeHtml(type)}</b> · Version ${template.version}</span><time datetime="${escapeAttribute(template.updated_at)}">Updated ${escapeHtml(updated)}</time></div></div>
      <button class="template-menu-toggle" type="button" aria-label="Actions for ${escapeAttribute(filename)}" aria-haspopup="menu" aria-expanded="false">···</button>
      <div class="template-menu" role="menu" hidden><button role="menuitem" class="view" type="button">View Template</button><a role="menuitem" href="${escapeAttribute(template.download_url)}">Download Template</a><button role="menuitem" class="replace" type="button">Replace Template</button><button role="menuitem" class="delete" type="button">Delete</button></div>
    </article>`;
  }

  function render() {
    const query = search.value.trim().toLocaleLowerCase();
    const visible = templates.filter((template) => !query ||
      String(template.file_name || template.name).toLocaleLowerCase().includes(query) ||
      String(template.service_name).toLocaleLowerCase().includes(query)
    );
    list.innerHTML = visible.length ? visible.map(card).join("") : emptyState(Boolean(query));
  }

  async function load() {
    try {
      templates = await api();
      render();
    } catch (error) {
      say(error.message, true);
      list.innerHTML = emptyState(false);
    }
  }

  function open(template = null) {
    editing = template;
    form.reset();
    document.getElementById("dialog-label").textContent = template ? "REPLACE TEMPLATE" : "NEW TEMPLATE";
    document.getElementById("dialog-title").textContent = template ? "Replace document template" : "Upload document template";
    serviceField.disabled = Boolean(template);
    if (template) {
      serviceField.value = template.service;
      nameField.value = template.name;
    }
    dialog.showModal();
  }

  function closeMenus(except = null) {
    document.querySelectorAll(".template-menu:not([hidden])").forEach((menu) => {
      if (menu === except) return;
      menu.hidden = true;
      menu.previousElementSibling.setAttribute("aria-expanded", "false");
    });
  }

  document.getElementById("open-upload").addEventListener("click", () => open());
  document.querySelectorAll(".close").forEach((button) => button.addEventListener("click", () => dialog.close()));
  search.addEventListener("input", render);

  list.addEventListener("click", async (event) => {
    const cardElement = event.target.closest(".template-card");
    if (!cardElement) return;
    const template = templates.find((item) => String(item.id) === cardElement.dataset.templateId);
    if (!template) return;
    const toggle = event.target.closest(".template-menu-toggle");
    if (toggle) {
      const menu = toggle.nextElementSibling;
      const opening = menu.hidden;
      closeMenus(menu);
      menu.hidden = !opening;
      toggle.setAttribute("aria-expanded", String(opening));
      if (opening) menu.querySelector('[role="menuitem"]').focus();
      return;
    }
    if (event.target.closest(".replace")) {
      closeMenus();
      open(template);
      return;
    }
    if (event.target.closest(".view")) {
      closeMenus();
      viewerTitle.textContent = template.file_name || template.name;
      viewerDownload.href = template.download_url;
      viewerFrame.src = template.preview_url;
      viewer.showModal();
      return;
    }
    if (event.target.closest(".delete") && window.confirm("Delete this template?")) {
      try {
        await api(`${endpoint}${template.id}/`, {method: "DELETE"});
        say("Template deleted.");
        await load();
      } catch (error) {
        say(error.message, true);
      }
    }
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".template-card")) closeMenus();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    const openMenu = document.querySelector(".template-menu:not([hidden])");
    if (openMenu) {
      const toggle = openMenu.previousElementSibling;
      closeMenus();
      toggle.focus();
    }
  });

  function closeViewer() {
    viewer.close();
    viewerFrame.removeAttribute("src");
  }

  document.getElementById("viewer-close").addEventListener("click", closeViewer);
  viewer.addEventListener("click", (event) => {
    if (event.target === viewer) closeViewer();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = fileField.files[0];
    if (file && file.size > 10 * 1024 * 1024) {
      say("Template files must not exceed 10MB.", true);
      return;
    }
    const data = new FormData(form);
    try {
      await api(editing ? `${endpoint}${editing.id}/` : endpoint, {
        method: editing ? "PATCH" : "POST",
        body: data,
      });
      dialog.close();
      say(editing ? "Template replaced." : "Template uploaded.");
      await load();
    } catch (error) {
      say(error.message, true);
    }
  });

  load();
})();
