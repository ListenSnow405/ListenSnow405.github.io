(function () {
  "use strict";

  const post = document.querySelector(".post");
  const content = post && post.querySelector("[data-post-content]");
  if (!content) return;

  const headings = Array.from(content.querySelectorAll("h2, h3")).filter(function (heading) {
    return heading.textContent.trim().length > 0;
  });

  const usedIds = new Set();
  headings.forEach(function (heading, index) {
    const label = heading.textContent.trim();
    let id = heading.id || "section-" + (index + 1);
    let suffix = 2;
    while (usedIds.has(id)) {
      id = (heading.id || "section-" + (index + 1)) + "-" + suffix;
      suffix += 1;
    }
    heading.id = id;
    heading.dataset.tocLabel = label;
    usedIds.add(id);

    const anchor = document.createElement("a");
    anchor.className = "heading-anchor";
    anchor.href = "#" + encodeURIComponent(id);
    anchor.setAttribute("aria-label", "链接到本节：" + label);
    anchor.textContent = "#";
    heading.appendChild(anchor);
  });

  const toc = post.querySelector("[data-post-toc]");
  const tocList = toc && toc.querySelector("[data-post-toc-list]");
  const tocDetails = toc && toc.querySelector("[data-post-toc-disclosure]");
  const tocScroll = toc && toc.querySelector("[data-post-toc-scroll]");
  const tocEntries = [];
  const chapterItems = [];

  if (toc && tocList && tocDetails && headings.length > 1) {
    let currentChapter = null;
    let currentSublist = null;
    let chapterCount = 0;

    headings.forEach(function (heading) {
      const item = document.createElement("li");
      const link = document.createElement("a");
      link.href = "#" + encodeURIComponent(heading.id);
      link.textContent = heading.dataset.tocLabel;
      item.appendChild(link);

      if (heading.tagName === "H2") {
        item.className = "post-toc-chapter";
        link.className = "post-toc-chapter-link";
        tocList.appendChild(item);
        currentChapter = item;
        currentSublist = null;
        chapterItems.push(item);
        chapterCount += 1;
      } else if (currentChapter) {
        item.className = "post-toc-subitem";
        link.className = "post-toc-subitem-link";
        if (!currentSublist) {
          currentSublist = document.createElement("ol");
          currentSublist.className = "post-toc-sublist";
          currentChapter.appendChild(currentSublist);
        }
        currentSublist.appendChild(item);
      } else {
        item.className = "post-toc-subitem post-toc-orphan";
        link.className = "post-toc-subitem-link";
        tocList.appendChild(item);
      }

      tocEntries.push({
        chapter: currentChapter,
        link: link
      });
    });

    const count = toc.querySelector("[data-post-toc-count]");
    if (count) count.textContent = chapterCount ? chapterCount + " 章" : headings.length + " 节";

    const wideLayout = window.matchMedia("(min-width: 1281px)");
    tocDetails.open = wideLayout.matches;
    wideLayout.addEventListener("change", function (event) {
      tocDetails.open = event.matches;
    });
    toc.hidden = false;
  }

  content.querySelectorAll("pre").forEach(function (pre) {
    let frame = pre.closest(".highlighter-rouge");
    if (!frame || !content.contains(frame)) {
      frame = document.createElement("div");
      pre.parentNode.insertBefore(frame, pre);
      frame.appendChild(pre);
    }

    frame.classList.add("code-block-frame");

    const button = document.createElement("button");
    button.className = "code-copy-button";
    button.type = "button";
    button.textContent = "复制";
    button.setAttribute("aria-label", "复制代码");
    button.setAttribute("aria-live", "polite");

    button.addEventListener("click", function () {
      const text = pre.innerText;
      const copyPromise = navigator.clipboard && window.isSecureContext
        ? navigator.clipboard.writeText(text)
        : new Promise(function (resolve, reject) {
            const textarea = document.createElement("textarea");
            textarea.value = text;
            textarea.setAttribute("readonly", "");
            textarea.style.position = "fixed";
            textarea.style.opacity = "0";
            document.body.appendChild(textarea);
            textarea.select();
            try {
              if (!document.execCommand("copy")) throw new Error("Copy failed");
              resolve();
            } catch (error) {
              reject(error);
            } finally {
              textarea.remove();
            }
          });

      copyPromise.then(function () {
        button.textContent = "已复制";
        button.setAttribute("aria-label", "代码已复制");
        button.classList.add("is-copied");
        window.setTimeout(function () {
          button.textContent = "复制";
          button.setAttribute("aria-label", "复制代码");
          button.classList.remove("is-copied");
        }, 1600);
      }).catch(function () {
        button.textContent = "复制失败";
        button.setAttribute("aria-label", "代码复制失败");
        window.setTimeout(function () {
          button.textContent = "复制";
          button.setAttribute("aria-label", "复制代码");
        }, 1600);
      });
    });

    frame.appendChild(button);
  });

  const progress = post.querySelector("[data-reading-progress]");
  const progressBar = progress && progress.querySelector("span");
  let headingOffsets = [];
  let activeTocIndex = -1;
  let ticking = false;

  function refreshMeasurements() {
    headingOffsets = headings.map(function (heading) {
      return heading.getBoundingClientRect().top + window.scrollY;
    });
    updateScrollState();
  }

  function updateScrollState() {
    ticking = false;
    const contentTop = content.getBoundingClientRect().top + window.scrollY;
    const start = Math.max(0, contentTop - 120);
    const end = Math.max(start + 1, contentTop + content.offsetHeight - window.innerHeight);
    const value = Math.min(1, Math.max(0, (window.scrollY - start) / (end - start)));

    if (progress && progressBar) {
      progressBar.style.transform = "scaleX(" + value + ")";
      progress.classList.toggle("is-visible", window.scrollY >= start && window.scrollY <= end + 120);
    }

    if (tocEntries.length) {
      const marker = window.scrollY + 150;
      let activeIndex = 0;
      headingOffsets.forEach(function (offset, index) {
        if (offset <= marker) activeIndex = index;
      });

      if (activeIndex !== activeTocIndex) {
        tocEntries.forEach(function (entry, index) {
          if (index === activeIndex) entry.link.setAttribute("aria-current", "location");
          else entry.link.removeAttribute("aria-current");
        });
        chapterItems.forEach(function (item) {
          item.classList.remove("is-active-chapter");
        });

        const activeEntry = tocEntries[activeIndex];
        if (activeEntry.chapter) activeEntry.chapter.classList.add("is-active-chapter");
        activeTocIndex = activeIndex;

        if (tocScroll && tocDetails && tocDetails.open) {
          window.requestAnimationFrame(function () {
            const scrollRect = tocScroll.getBoundingClientRect();
            const linkRect = activeEntry.link.getBoundingClientRect();
            if (linkRect.top < scrollRect.top + 8) {
              tocScroll.scrollTop += linkRect.top - scrollRect.top - 8;
            } else if (linkRect.bottom > scrollRect.bottom - 12) {
              tocScroll.scrollTop += linkRect.bottom - scrollRect.bottom + 12;
            }
          });
        }
      }
    }
  }

  function scheduleScrollUpdate() {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(updateScrollState);
  }

  window.addEventListener("scroll", scheduleScrollUpdate, { passive: true });
  window.addEventListener("resize", refreshMeasurements, { passive: true });

  if ("ResizeObserver" in window) {
    const observer = new ResizeObserver(refreshMeasurements);
    observer.observe(content);
  }

  refreshMeasurements();
})();
