(function () {
  const tabs = Array.from(document.querySelectorAll("[data-tab]"));
  const panels = Array.from(document.querySelectorAll(".tab-content"));
  const validIds = new Set(tabs.map((tab) => tab.dataset.tab));
  // Tab đầu tiên là fallback khi không có hash hoặc hash không hợp lệ
  const firstTabId = tabs.length > 0 ? tabs[0].dataset.tab : "overview";

  function showTab(id, options) {
    const nextId = validIds.has(id) ? id : firstTabId;
    tabs.forEach((tab) => {
      const active = tab.dataset.tab === nextId;
      tab.classList.toggle("active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    panels.forEach((panel) => {
      const active = panel.id === `tab-${nextId}`;
      panel.classList.toggle("active", active);
      panel.hidden = !active;
    });
    if (!options || options.updateHash !== false) {
      history.replaceState(null, "", `#${nextId}`);
    }
    if (!options || options.scroll !== false) {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => showTab(tab.dataset.tab));
    tab.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight"].includes(event.key)) {
        return;
      }
      event.preventDefault();
      const direction = event.key === "ArrowRight" ? 1 : -1;
      const next = tabs[(index + direction + tabs.length) % tabs.length];
      next.focus();
      showTab(next.dataset.tab, { scroll: false });
    });
  });

  window.addEventListener("hashchange", () => showTab(location.hash.slice(1), { updateHash: false, scroll: false }));
  showTab(location.hash.slice(1), { updateHash: false, scroll: false });
})();
