(function () {
  "use strict";

  const key = "listensnow-reading";
  const root = document.documentElement;
  let settings = defaults();

  function defaults() { return { size: "standard", width: "standard", focus: false }; }
  function parse(value) {
    try {
      const data = JSON.parse(value) || {};
      return {
        size: ["large", "larger"].includes(data.size) ? data.size : "standard",
        width: ["compact", "wide"].includes(data.width) ? data.width : "standard",
        focus: data.focus === true
      };
    } catch (_) { return defaults(); }
  }
  function apply() {
    root.dataset.readingSize = settings.size;
    root.dataset.readingWidth = settings.width;
    root.dataset.readingFocus = String(settings.focus);
  }
  try { settings = parse(localStorage.getItem(key)); } catch (_) { /* Use defaults. */ }
  apply();

  document.addEventListener("DOMContentLoaded", function () {
    const tools = document.querySelector(".reading-tools");
    const content = document.querySelector("[data-post-content]");
    if (!tools || !content) return;
    const disclosure = tools.querySelector("details");
    const size = document.getElementById("reading-size");
    const width = document.getElementById("reading-width");
    const focus = tools.querySelector("[data-reading-focus]");
    const exit = tools.querySelector("[data-reading-exit]");
    let anchorFrame = 0;

    function updateControls() {
      size.value = settings.size;
      width.value = settings.width;
      focus.setAttribute("aria-pressed", String(settings.focus));
      focus.textContent = settings.focus ? "退出专注阅读" : "开启专注阅读";
      exit.hidden = !settings.focus;
    }
    function topInset() {
      const nav = document.querySelector(".profile-sidebar");
      return nav && getComputedStyle(nav).position === "sticky" && innerWidth <= 760 && !settings.focus
        ? nav.getBoundingClientRect().height + 12 : 20;
    }
    function change(next, save) {
      // Preserve the visible paragraph when font size or layout changes.
      const inset = topInset();
      const anchor = window.scrollY > 100 && Array.from(content.children).find(function (el) {
        return el.getBoundingClientRect().bottom > inset;
      });
      const offset = anchor ? anchor.getBoundingClientRect().top - inset : 0;
      // Do not let the browser apply a second, native scroll-anchor correction.
      window.cancelAnimationFrame(anchorFrame);
      root.style.overflowAnchor = "none";
      settings = next;
      apply();
      updateControls();
      if (save) {
        try { localStorage.setItem(key, JSON.stringify(settings)); } catch (_) { /* Page-local choice. */ }
      }
      window.dispatchEvent(new Event("readingchange"));
      function restorePosition() {
        if (anchor) {
          window.scrollBy({ top: anchor.getBoundingClientRect().top - topInset() - offset, behavior: "instant" });
        }
      }
      restorePosition();
      let previousHeight = content.getBoundingClientRect().height;
      let stableFrames = 0;
      let frames = 0;
      function settleLayout() {
        restorePosition();
        const height = content.getBoundingClientRect().height;
        stableFrames = Math.abs(height - previousHeight) < 0.5 ? stableFrames + 1 : 0;
        previousHeight = height;
        frames += 1;
        // Inherited font sizes may settle over several rendering frames.
        if ((frames >= 3 && stableFrames >= 2) || frames >= 12) {
          root.style.removeProperty("overflow-anchor");
          window.dispatchEvent(new Event("readingchange"));
        } else {
          anchorFrame = window.requestAnimationFrame(settleLayout);
        }
      }
      anchorFrame = window.requestAnimationFrame(settleLayout);
    }

    size.addEventListener("change", function () { change(Object.assign({}, settings, { size: size.value }), true); });
    width.addEventListener("change", function () { change(Object.assign({}, settings, { width: width.value }), true); });
    focus.addEventListener("click", function () { change(Object.assign({}, settings, { focus: !settings.focus }), true); });
    exit.addEventListener("click", function () {
      change(Object.assign({}, settings, { focus: false }), true);
      tools.querySelector("summary").focus({ preventScroll: true });
    });
    tools.querySelector("[data-reading-reset]").addEventListener("click", function () { change(defaults(), true); });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && disclosure.open) {
        disclosure.open = false;
        tools.querySelector("summary").focus({ preventScroll: true });
      }
    });
    document.addEventListener("click", function (event) {
      if (!tools.contains(event.target)) disclosure.open = false;
    });
    window.addEventListener("storage", function (event) {
      if (event.key === key || event.key === null) change(parse(event.newValue), false);
    });
    updateControls();
    tools.hidden = false;
  });
})();
