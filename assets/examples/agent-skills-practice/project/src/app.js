(function () {
  "use strict";

  const controls = document.querySelector("[data-filters]");
  const query = document.getElementById("query");
  const category = document.getElementById("category");
  const rows = Array.from(document.querySelectorAll("[data-material]"));
  const status = document.getElementById("status");
  const empty = document.getElementById("empty");
  const clear = document.getElementById("clear");
  if (!controls || !query || !category || !status || !empty || !clear) return;

  // HTML 已包含全部资料。脚本成功初始化后才显示筛选入口。
  controls.hidden = false;

  function update() {
    const keyword = query.value.trim().toLocaleLowerCase();
    let visible = 0;
    rows.forEach(function (row) {
      // 分类精确匹配，关键词匹配标题、课程与标签；两个条件取交集。
      const matchesCategory = !category.value || row.dataset.category === category.value;
      const matchesQuery = row.dataset.search.toLocaleLowerCase().includes(keyword);
      row.hidden = !(matchesCategory && matchesQuery);
      if (!row.hidden) visible += 1;
    });
    // 使用文字说明状态，并由 aria-live 温和播报数量变化。
    status.textContent = "显示 " + visible + " / " + rows.length + " 条资料";
    empty.hidden = visible !== 0;
  }

  query.addEventListener("input", update);
  category.addEventListener("change", update);
  clear.addEventListener("click", function () {
    query.value = "";
    category.value = "";
    update();
    query.focus();
  });
  update();
})();
