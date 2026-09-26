(function () {
  "use strict";
  const root = document.querySelector("[data-article-browser]");
  if (!root) return;
  const form = root.querySelector("[data-article-filters]");
  const category = form.elements.category;
  const tag = form.elements.tag;
  const summary = root.querySelector("[data-article-summary]");
  const empty = document.querySelector("[data-article-empty]");
  const years = Array.from(document.querySelectorAll(".archive-year"));
  const jumps = Array.from(document.querySelectorAll(".year-jump a"));
  const articles = Array.from(document.querySelectorAll("[data-article]")).map(function (node) {
    return { node: node, categories: JSON.parse(node.dataset.categories), tags: JSON.parse(node.dataset.tags) };
  });

  function restore() {
    const params = new URLSearchParams(window.location.search);
    [category, tag].forEach(function (select) {
      const value = params.get(select.name) || "";
      select.value = Array.from(select.options).some(function (option) { return option.value === value; }) ? value : "";
    });
  }

  function update(save) {
    let count = 0;
    articles.forEach(function (article) {
      const matches = (!category.value || article.categories.includes(category.value)) && (!tag.value || article.tags.includes(tag.value));
      article.node.hidden = !matches;
      if (matches) count += 1;
    });
    years.forEach(function (year, index) {
      const visible = year.querySelectorAll("[data-article]:not([hidden])").length;
      year.hidden = visible === 0;
      if (jumps[index]) {
        jumps[index].hidden = visible === 0;
        jumps[index].querySelector("span").textContent = visible + " 篇";
      }
    });
    summary.textContent = category.value || tag.value ? "找到 " + count + " 篇文章（共 " + articles.length + " 篇）" : "共 " + count + " 篇文章";
    empty.hidden = count !== 0;
    if (save) {
      const url = new URL(window.location.href);
      [category, tag].forEach(function (select) {
        if (select.value) url.searchParams.set(select.name, select.value);
        else url.searchParams.delete(select.name);
      });
      try { window.history.replaceState(null, "", url); } catch (_) { /* Filtering also works when history writes are denied. */ }
    }
  }

  form.addEventListener("change", function () { update(true); });
  form.addEventListener("submit", function (event) { event.preventDefault(); update(true); });
  form.addEventListener("reset", function (event) {
    event.preventDefault();
    category.value = "";
    tag.value = "";
    update(true);
  });
  window.addEventListener("popstate", function () { restore(); update(false); });
  restore();
  update(false);
  form.hidden = false;
})();
