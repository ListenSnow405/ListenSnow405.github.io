(function () {
  "use strict";

  document.querySelectorAll("[data-nav-shell]").forEach(function (shell) {
    const nav = shell.querySelector("[data-primary-nav]");
    if (!nav) return;

    let frame = 0;

    function updateOverflowState() {
      frame = 0;
      const maxScroll = Math.max(0, nav.scrollWidth - nav.clientWidth);
      shell.classList.toggle("can-scroll-left", nav.scrollLeft > 2);
      shell.classList.toggle("can-scroll-right", nav.scrollLeft < maxScroll - 2);
    }

    function scheduleUpdate() {
      if (frame) return;
      frame = window.requestAnimationFrame(updateOverflowState);
    }

    const current = nav.querySelector('[aria-current="page"]');
    if (current && nav.scrollWidth > nav.clientWidth) {
      const currentStart = current.offsetLeft;
      const currentEnd = currentStart + current.offsetWidth;
      if (currentStart < nav.scrollLeft || currentEnd > nav.scrollLeft + nav.clientWidth) {
        nav.scrollLeft = Math.max(0, currentStart - 8);
      }
    }

    nav.addEventListener("scroll", scheduleUpdate, { passive: true });
    window.addEventListener("resize", scheduleUpdate, { passive: true });

    if ("ResizeObserver" in window) {
      const observer = new ResizeObserver(scheduleUpdate);
      observer.observe(nav);
    }

    updateOverflowState();
  });
})();
