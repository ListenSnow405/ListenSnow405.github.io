(function () {
  "use strict";

  const key = "listensnow-theme";
  const root = document.documentElement;
  const system = window.matchMedia("(prefers-color-scheme: dark)");
  let preference = "system";

  function normalize(value) {
    return value === "light" || value === "dark" || value === "paper" ? value : "system";
  }

  function apply() {
    root.dataset.theme = preference === "system" ? (system.matches ? "dark" : "light") : preference;
    document.querySelectorAll("[data-theme-select]").forEach(function (select) {
      select.value = preference;
    });
  }

  try {
    preference = normalize(localStorage.getItem(key));
  } catch (_) { /* Storage can be disabled; switching still works for this page. */ }
  apply();

  system.addEventListener("change", function () {
    if (preference === "system") apply();
  });
  window.addEventListener("storage", function (event) {
    if (event.key === key || event.key === null) {
      preference = normalize(event.newValue);
      apply();
    }
  });
  document.addEventListener("DOMContentLoaded", function () {
    apply();
    document.querySelectorAll("[data-theme-select]").forEach(function (select) {
      select.addEventListener("change", function () {
        preference = normalize(select.value);
        try {
          if (preference === "system") localStorage.removeItem(key);
          else localStorage.setItem(key, preference);
        } catch (_) { /* Keep the current choice even without persistent storage. */ }
        apply();
      });
    });
    const control = document.querySelector(".theme-control");
    if (control) control.hidden = false;
  });
})();
