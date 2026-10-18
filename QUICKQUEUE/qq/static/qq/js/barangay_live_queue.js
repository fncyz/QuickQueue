(function () {
  "use strict";

  const monitor = document.querySelector(".live-monitor-page");
  const clock = document.getElementById("live-clock");
  const toggle = document.getElementById("fullscreen-toggle");
  let refreshInProgress = false;

  if (!monitor || !clock || !toggle) return;

  function updateClock() {
    clock.textContent = new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Manila",
      hour: "numeric",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date());
  }

  function syncFullscreen() {
    const active = document.fullscreenElement === monitor;
    toggle.classList.toggle("is-fullscreen", active);
    toggle.title = active ? "Exit Fullscreen" : "Enter Fullscreen";
    toggle.setAttribute("aria-label", toggle.title);
  }

  async function refreshQueue() {
    if (document.hidden || refreshInProgress) return;
    refreshInProgress = true;
    try {
      const response = await fetch(monitor.dataset.refreshUrl || window.location.href, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        cache: "no-store",
      });
      if (!response.ok) return;
      const page = new DOMParser().parseFromString(await response.text(), "text/html");
      const current = document.querySelector("[data-live-region]");
      const incoming = page.querySelector("[data-live-region]");
      if (current && incoming && current.innerHTML !== incoming.innerHTML) {
        current.replaceWith(incoming);
      }
    } catch (_error) {
      // Retain the last verified queue state during temporary connectivity failures.
    } finally {
      refreshInProgress = false;
    }
  }

  toggle.addEventListener("click", async function () {
    if (!document.fullscreenEnabled) {
      toggle.title = "Fullscreen is not supported by this browser";
      return;
    }
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await monitor.requestFullscreen();
    } catch (_error) {
      toggle.title = "Unable to enter fullscreen";
    }
  });

  document.addEventListener("fullscreenchange", syncFullscreen);
  updateClock();
  window.setInterval(updateClock, 1000);
  window.setInterval(refreshQueue, 10000);
})();
