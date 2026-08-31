(function () {
  "use strict";

  const root = document.querySelector("[data-search-root]");
  if (!root) return;

  const form = root.querySelector("[data-search-form]");
  const input = root.querySelector("[data-search-input]");
  const summary = root.querySelector("[data-search-summary]");
  const results = root.querySelector("[data-search-results]");
  let posts = [];

  function normalize(value) {
    return String(value || "").toLocaleLowerCase("zh-CN");
  }

  function clearResults() {
    while (results.firstChild) results.removeChild(results.firstChild);
  }

  function createResult(post) {
    const article = document.createElement("article");
    article.className = "search-result";

    const meta = document.createElement("div");
    meta.className = "search-result-meta";
    meta.textContent = [post.date].concat(post.categories || []).join(" · ");

    const title = document.createElement("h2");
    const link = document.createElement("a");
    link.href = post.url;
    link.textContent = post.title;
    title.appendChild(link);

    const excerpt = document.createElement("p");
    excerpt.textContent = post.excerpt || "暂无摘要";

    const tags = document.createElement("div");
    tags.className = "search-result-tags";
    (post.tags || []).slice(0, 4).forEach(function (tag) {
      const item = document.createElement("span");
      item.textContent = "#" + tag;
      tags.appendChild(item);
    });

    article.append(meta, title, excerpt, tags);
    return article;
  }

  function runSearch(rawQuery, updateUrl) {
    const query = rawQuery.trim();
    clearResults();

    if (updateUrl) {
      const url = new URL(window.location.href);
      if (query) url.searchParams.set("q", query);
      else url.searchParams.delete("q");
      window.history.replaceState({}, "", url);
    }

    if (!query) {
      summary.textContent = "输入关键词开始搜索。";
      return;
    }

    const needle = normalize(query);
    const matches = posts.filter(function (post) {
      return normalize([
        post.title,
        post.excerpt,
        post.content,
        (post.categories || []).join(" "),
        (post.tags || []).join(" ")
      ].join(" ")).includes(needle);
    });

    summary.textContent = matches.length
      ? "找到 " + matches.length + " 篇相关文章"
      : "没有找到与“" + query + "”相关的文章";
    matches.forEach(function (post) { results.appendChild(createResult(post)); });
  }

  fetch(root.dataset.indexUrl)
    .then(function (response) {
      if (!response.ok) throw new Error("Search index request failed");
      return response.json();
    })
    .then(function (data) {
      posts = data;
      const query = new URLSearchParams(window.location.search).get("q") || "";
      input.value = query;
      if (query) runSearch(query, false);
    })
    .catch(function () {
      summary.textContent = "搜索索引暂时不可用，请稍后再试。";
    });

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    runSearch(input.value, true);
  });
})();
