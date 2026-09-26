(function () {
  "use strict";

  const key = "listensnow-theme";
  const root = document.documentElement;
  const modes = ["dark", "light", "paper"];
  const labels = { dark: "暗色模式", light: "浅色模式", paper: "暖纸模式" };
  let preference = "dark";

  function normalize(value) {
    return modes.includes(value) ? value : "dark";
  }

  function apply() {
    root.dataset.theme = preference;
    const next = modes[(modes.indexOf(preference) + 1) % modes.length];
    document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
      button.querySelector("[data-theme-label]").textContent = labels[preference];
      button.setAttribute("aria-label", "当前" + labels[preference] + "，切换为" + labels[next]);
      button.title = "切换为" + labels[next];
    });
  }

  try {
    preference = normalize(localStorage.getItem(key));
  } catch (_) { /* Storage can be disabled; switching still works for this page. */ }
  apply();

  window.addEventListener("storage", function (event) {
    if (event.key === key || event.key === null) {
      preference = normalize(event.newValue);
      apply();
    }
  });
  document.addEventListener("DOMContentLoaded", function () {
    apply();
    document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
      button.addEventListener("click", function () {
        preference = modes[(modes.indexOf(preference) + 1) % modes.length];
        try { localStorage.setItem(key, preference); } catch (_) { /* Page-local choice. */ }
        apply();
      });
      button.hidden = false;
    });
  });
})();
