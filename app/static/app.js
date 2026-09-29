const form = document.querySelector("#search-form");
const results = document.querySelector("#results");
const status = document.querySelector("#status");
const resultCount = document.querySelector("#result-count");
const template = document.querySelector("#result-template");

function setLoading(isLoading) {
  form.querySelector("button").disabled = isLoading;
  status.textContent = isLoading ? "Ищу релевантные фрагменты..." : "";
}

function showResults(items) {
  results.replaceChildren();
  resultCount.textContent = items.length ? `${items.length} найдено` : "Ничего не найдено";
  items.forEach((item, index) => {
    const node = template.content.cloneNode(true);
    const metadata = item.metadata;
    node.querySelector("h3").textContent = `#${index + 1} ${metadata.title}`;
    node.querySelector("strong").textContent = `score: ${item.score.toFixed(4)}`;
    node.querySelector(".source").textContent = metadata.file;
    node.querySelector(".path").textContent = metadata.section_path || metadata.section;
    node.querySelector(".chunk-id").textContent = item.chunk_id;
    node.querySelector("pre").textContent = item.text;
    results.append(node);
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = form.query.value.trim();
  if (!query) return;
  setLoading(true);
  results.replaceChildren();
  resultCount.textContent = "";
  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        strategy: form.strategy.value,
        top_k: Number(form["top-k"].value),
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Search request failed");
    showResults(payload.results);
  } catch (error) {
    status.textContent = `Ошибка: ${error.message}`;
    status.classList.add("error");
  } finally {
    setLoading(false);
  }
});
