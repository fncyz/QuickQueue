document.addEventListener("DOMContentLoaded", function () {
  const root = document.getElementById("qq-notification-root");
  const bell = document.querySelector(".alert-bell,.user-tools .bell");
  if (!root || !bell) return;

  const staffPortal = root.dataset.staffPortal === "1";
  let panel = null;
  let filter = "all";
  let expanded = false;
  let timer = null;
  let loadSequence = 0;

  const esc = (value) => String(value || "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[character]);
  const icon = '<svg viewBox="0 0 24 24"><path d="M7 3h8l4 4v14H7zM15 3v5h5M10 13h6M10 17h6"/></svg>';
  const tone = (type) => type === "CA" ? "red" : type === "DU" ? "green" : type === "EV" ? "orange" : "blue";
  const group = (date) => {
    const itemDate = new Date(date);
    const now = new Date();
    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    if (itemDate.toDateString() === now.toDateString()) return "TODAY";
    if (itemDate.toDateString() === yesterday.toDateString()) return "YESTERDAY";
    return "EARLIER";
  };
  const ago = (date) => {
    const seconds = Math.max(0, (Date.now() - new Date(date)) / 1000);
    if (seconds < 60) return "Just now";
    if (seconds < 3600) return Math.floor(seconds / 60) + " minutes ago";
    if (seconds < 86400) return Math.floor(seconds / 3600) + " hours ago";
    return new Date(date).toLocaleString([], {month: "short", day: "numeric", hour: "numeric", minute: "2-digit"});
  };

  function position() {
    if (!panel) return;
    const bellBox = bell.getBoundingClientRect();
    const width = Math.min(430, innerWidth - 24);
    const top = bellBox.bottom + 10;
    panel.style.top = top + "px";
    panel.style.left = Math.max(12, Math.min(innerWidth - width - 12, bellBox.right - width)) + "px";
    if (staffPortal) {
      const availableHeight = Math.max(260, innerHeight - top - 12);
      panel.style.maxHeight = (expanded ? availableHeight : Math.min(560, availableHeight)) + "px";
    }
  }

  async function mark(id) {
    await fetch(root.dataset.url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": root.dataset.csrf,
      },
      body: JSON.stringify(id ? {notification_id: id} : {}),
    });
  }

  function requestUrl(page) {
    const parameters = new URLSearchParams({format: "json"});
    if (filter === "unread") parameters.set("filter", "unread");
    if (staffPortal && expanded) parameters.set("expanded", "1");
    if (staffPortal) parameters.set("page", String(page || 1));
    return root.dataset.url + "?" + parameters.toString();
  }

  async function fetchPage(page) {
    const response = await fetch(requestUrl(page), {headers: {"X-Requested-With": "XMLHttpRequest"}});
    if (!response.ok) throw new Error("Unable to load notifications.");
    return response.json();
  }

  async function load() {
    const sequence = ++loadSequence;
    try {
      const firstPage = await fetchPage(1);
      if (staffPortal && expanded && firstPage.page_count > 1) {
        const requests = [];
        for (let page = 2; page <= firstPage.page_count; page += 1) requests.push(fetchPage(page));
        const additionalPages = await Promise.all(requests);
        additionalPages.forEach((result) => firstPage.notifications.push(...result.notifications));
      }
      if (panel && sequence === loadSequence) render(firstPage);
    } catch (error) {
      if (panel && sequence === loadSequence) {
        panel.innerHTML = '<div class="qqn-empty">' + esc(error.message) + "</div>";
      }
    }
  }

  function badge(count) {
    let indicator = bell.querySelector("span,i");
    if (!count) {
      if (indicator) indicator.remove();
      return;
    }
    if (!indicator) {
      indicator = document.createElement("span");
      bell.appendChild(indicator);
    }
    indicator.textContent = count;
  }

  function notificationRows(notifications) {
    let lastGroup = "";
    return notifications.map((notification) => {
      const currentGroup = group(notification.created_at);
      const heading = currentGroup !== lastGroup
        ? '<div class="qqn-group">' + (lastGroup = currentGroup) + "</div>"
        : "";
      return heading + '<button class="qqn-item ' + (notification.is_read ? "" : "unread") +
        '" data-id="' + notification.id + '" data-url="' + esc(notification.url) + '" data-tone="' +
        tone(notification.type) + '"><span class="qqn-icon">' + icon +
        '</span><span class="qqn-copy"><b>' + esc(notification.title) + "</b><p>" +
        esc(notification.message) + "</p><time>" + ago(notification.created_at) +
        '</time></span><i class="qqn-dot"></i></button>';
    }).join("");
  }

  function renderStaff(data, rows) {
    const unreadLabel = data.unread_count > 0 ? "Unread (" + data.unread_count + ")" : "Unread";
    panel.classList.toggle("expanded", expanded);
    panel.innerHTML = '<header class="qqn-head"><h2>Notifications</h2><p>Stay updated with recent activities</p></header>' +
      '<div class="qqn-controls"><button class="qqn-filter ' + (filter === "all" ? "active" : "") +
      '" data-filter="all">All</button><button class="qqn-filter ' + (filter === "unread" ? "active" : "") +
      '" data-filter="unread">' + unreadLabel + '</button><button class="qqn-mark">Mark all as read</button></div>' +
      '<div class="qqn-list">' + (rows || '<div class="qqn-empty">No notifications yet.</div>') + "</div>" +
      '<footer class="qqn-foot"><button class="qqn-expand" type="button">' +
      (expanded ? "Show less" : "View all notifications") + "</button></footer>";
    position();
    panel.querySelector(".qqn-expand").onclick = () => {
      expanded = !expanded;
      position();
      load();
    };
  }

  function renderAdmin(data, rows) {
    panel.innerHTML = '<header class="qqn-head"><h2>Notifications</h2><p>Stay updated with recent activities</p>' +
      '<button class="qqn-more" aria-label="Notification options">•••</button></header>' +
      '<div class="qqn-controls"><button class="qqn-filter ' + (filter === "all" ? "active" : "") +
      '" data-filter="all">All (' + data.total_count + ')</button><button class="qqn-filter ' +
      (filter === "unread" ? "active" : "") + '" data-filter="unread">Unread (' + data.unread_count +
      ')</button><button class="qqn-mark">Mark all as read</button></div><div class="qqn-list">' +
      (rows || '<div class="qqn-empty">No notifications yet.</div>') +
      '</div><footer class="qqn-foot"><a href="' + esc(data.history_url) +
      '">View all notifications&nbsp; →</a></footer>';
    panel.querySelector(".qqn-more").onclick = () => { location.href = data.history_url; };
  }

  function render(data) {
    const rows = notificationRows(data.notifications);
    if (staffPortal) renderStaff(data, rows);
    else renderAdmin(data, rows);
    panel.querySelectorAll(".qqn-filter").forEach((button) => {
      button.onclick = () => { filter = button.dataset.filter; load(); };
    });
    panel.querySelector(".qqn-mark").onclick = async () => {
      await mark();
      badge(0);
      load();
    };
    panel.querySelectorAll(".qqn-item").forEach((item) => {
      item.onclick = async () => {
        await mark(item.dataset.id);
        location.href = item.dataset.url;
      };
    });
    badge(data.unread_count);
  }

  function close() {
    if (!panel) return;
    panel.classList.remove("open");
    const closingPanel = panel;
    panel = null;
    setTimeout(() => closingPanel.remove(), 200);
    clearInterval(timer);
  }

  bell.addEventListener("click", function (event) {
    event.preventDefault();
    event.stopImmediatePropagation();
    if (panel) return close();
    panel = document.createElement("section");
    panel.className = "qq-notifications" + (staffPortal ? " staff-panel" : "");
    document.body.appendChild(panel);
    position();
    requestAnimationFrame(() => panel && panel.classList.add("open"));
    load();
    timer = setInterval(load, 15000);
  });
  document.addEventListener("click", (event) => {
    if (panel && !panel.contains(event.target) && !bell.contains(event.target)) close();
  });
  document.addEventListener("keydown", (event) => {
    if (staffPortal && event.key === "Escape" && panel) close();
  });
  addEventListener("resize", position);
});
