const controls = document.querySelector("#controls");
const questionForm = document.querySelector("#question-form");
const questionInput = document.querySelector("#question");
const conversation = document.querySelector("#conversation");
const chatList = document.querySelector("#chat-list");
const status = document.querySelector("#status");
const template = document.querySelector("#message-template");
let activeChatId = null;

const modelNames = {
  "deepseek-flash": "DeepSeek Flash",
  "deepseek-v4-pro": "DeepSeek V4 Pro",
};

function settings() {
  return {
    mode: controls.mode.value,
    model: controls.model.value,
    strategy: controls.strategy.value,
    retrieval_mode: controls.retrieval_mode.value,
    candidate_top_k: Number(controls["candidate-top-k"].value),
    final_top_k: Number(controls["final-top-k"].value),
  };
}

function setBusy(busy, text = "") {
  document.querySelector("#send").disabled = busy;
  document.querySelector("#compare").disabled = busy;
  document.querySelector("#compare-retrieval").disabled = busy;
  status.classList.toggle("error", false);
  status.textContent = text;
}

function showError(error) {
  status.classList.add("error");
  status.textContent = `Ошибка: ${error.message}`;
}

async function request(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "Request failed");
  return payload;
}

function clearEmptyState() {
  const empty = conversation.querySelector(".empty-state");
  if (empty) empty.remove();
}

function usageText(usage = {}) {
  const input = usage.prompt_tokens ?? "-";
  const output = usage.completion_tokens ?? "-";
  const total = usage.total_tokens ?? "-";
  return `LLM usage: input ${input}, output ${output}, total ${total}`;
}

function appendSources(container, sources) {
  if (!sources?.length) return;
  sources.forEach((source) => {
    const item = document.createElement("article");
    item.className = "source-card";
    const metadata = document.createElement("p");
    const rerank = source.rerank_score == null ? "-" : Number(source.rerank_score).toFixed(4);
    metadata.textContent = `[${source.number}] ${source.file}\n${source.section_path || source.section}\nchunk: ${source.chunk_id}\nsimilarity: ${Number(source.similarity_score ?? source.score).toFixed(4)} · rerank: ${rerank}`;
    item.append(metadata);
    container.append(item);
  });
}

function appendQuotes(container, quotes) {
  if (!quotes?.length) return;
  quotes.forEach((quote) => {
    const item = document.createElement("figure");
    item.className = "quote-card";
    const label = document.createElement("figcaption");
    label.textContent = `Quote from source [${quote.source_number}] · ${quote.file} · ${quote.section_path || quote.section}`;
    const text = document.createElement("blockquote");
    text.textContent = `“${quote.quote}”`;
    item.append(label, text);
    container.append(item);
  });
}

function appendMessage(message) {
  clearEmptyState();
  const node = template.content.cloneNode(true);
  const article = node.querySelector(".message");
  const isUser = message.role === "user";
  article.classList.add(isUser ? "user-message" : "assistant-message");
  node.querySelector(".role").textContent = isUser ? "User" : `Assistant${message.compareLabel ? ` - ${message.compareLabel}` : ""}`;
  node.querySelector(".model").textContent = message.model ? modelNames[message.model] || message.model : "";
  node.querySelector(".message-content").textContent = message.content || message.answer;
  const sourcesSection = node.querySelector(".sources-section");
  const quotesSection = node.querySelector(".quotes-section");
  const insufficient = node.querySelector(".insufficient-context");
  if (message.sources?.length) {
    sourcesSection.hidden = false;
    appendSources(node.querySelector(".sources"), message.sources);
  }
  if (message.quotes?.length) {
    quotesSection.hidden = false;
    appendQuotes(node.querySelector(".quotes"), message.quotes);
  }
  insufficient.hidden = message.status !== "insufficient_context";
  const details = node.querySelector(".rag-details");
  if (isUser) {
    node.querySelector(".answer-title").remove();
    insufficient.remove();
    sourcesSection.remove();
    quotesSection.remove();
    details.remove();
  } else {
    const retrieved = (message.sources || []).map((source) => `final #${source.final_rank ?? source.number}, FAISS #${source.original_rank ?? source.number}: similarity ${Number(source.similarity_score ?? source.score).toFixed(4)}, rerank ${source.rerank_score == null ? "-" : Number(source.rerank_score).toFixed(4)} | ${source.file} | ${source.section}\n${source.text}`).join("\n\n") || "No chunks reached the context.";
    const retrieval = message.retrieval || {};
    const timing = Object.entries(message.timings || {}).map(([name, value]) => `${name}: ${value} ms`).join("\n") || "-";
    const candidates = (retrieval.candidates || []).map((source) => `FAISS #${source.original_rank}: ${Number(source.similarity_score).toFixed(4)}, threshold ${source.passed_threshold ?? "-"}, rerank ${source.rerank_score == null ? "-" : Number(source.rerank_score).toFixed(4)}, final ${source.final_rank ?? "-"} | ${source.file} | ${source.section}`).join("\n") || "-";
    details.querySelector("div").textContent = `model: ${message.model}\nmode: ${message.mode}\nanswer status: ${message.status ?? "legacy"}\nretrieval mode: ${message.retrieval_mode ?? "-"}\nstrategy: ${message.strategy ?? "-"}\n\nOriginal question:\n${message.original_question ?? "-"}\n\nRewritten query:\n${message.rewritten_query ?? "-"}\n\nCandidate Top-K: ${retrieval.candidate_top_k ?? "-"}\nCandidates retrieved: ${retrieval.candidates_found ?? "-"}\nSimilarity filter threshold: ${retrieval.similarity_threshold ?? "-"}\nPassed filter: ${retrieval.after_filter ?? "-"}\nFinal Top-K: ${retrieval.final_top_k ?? message.top_k ?? "-"}\nContext status: ${retrieval.context_status ?? "not applicable"}\nBest similarity: ${retrieval.best_similarity ?? "-"}\nContext threshold: ${retrieval.min_context_similarity ?? "-"}\nFinal sources: ${message.sources?.length ?? 0}\nValidated quotes: ${message.quotes?.length ?? 0}\n\nTimings:\n${timing}\n\nFAISS candidates:\n${candidates}\n\ncontext chunks:\n${retrieved}\n\n${usageText(message.usage)}`;
  }
  conversation.append(node);
  conversation.scrollTop = conversation.scrollHeight;
}

function showConversation(messages) {
  conversation.replaceChildren();
  if (!messages.length) {
    conversation.innerHTML = '<div class="empty-state">Этот чат пока пуст.</div>';
    return;
  }
  messages.forEach(appendMessage);
}

async function loadChats() {
  const payload = await request("/api/chats");
  chatList.replaceChildren();
  payload.chats.forEach((chat) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = `chat-item${chat.id === activeChatId ? " active" : ""}`;
    item.textContent = chat.title;
    item.addEventListener("click", () => loadChat(chat.id));
    chatList.append(item);
  });
}

async function loadChat(chatId) {
  const chat = await request(`/api/chats/${chatId}`);
  activeChatId = chat.id;
  showConversation(chat.messages);
  await loadChats();
}

document.querySelector("#new-chat").addEventListener("click", () => {
  activeChatId = null;
  showConversation([]);
  questionInput.focus();
  loadChats().catch(showError);
});

document.querySelector("#refresh-chats").addEventListener("click", () => loadChats().catch(showError));

controls.mode.forEach((input) => input.addEventListener("change", () => {
  const enabled = controls.mode.value === "with_rag";
  document.querySelectorAll("#retrieval-mode-control input, #candidate-top-k, #final-top-k").forEach((input) => { input.disabled = !enabled; });
}));

questionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;
  setBusy(true, "DeepSeek формирует ответ...");
  try {
    const payload = await request("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: activeChatId, question, ...settings() }),
    });
    activeChatId = payload.chat_id;
    appendMessage({ role: "user", content: question });
    appendMessage(payload);
    questionInput.value = "";
    await loadChats();
    setBusy(false);
  } catch (error) {
    showError(error);
    setBusy(false);
  }
});

document.querySelector("#compare").addEventListener("click", async () => {
  const question = questionInput.value.trim();
  if (!question) return showError(new Error("Введите вопрос для сравнения"));
  setBusy(true, "Запускаю baseline и RAG с одинаковыми параметрами...");
  try {
    const payload = await request("/api/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, ...settings() }),
    });
    conversation.replaceChildren();
    appendMessage({ role: "user", content: payload.question });
    appendMessage({ ...payload.without_rag, compareLabel: "WITHOUT RAG" });
    appendMessage({ ...payload.with_rag, compareLabel: "WITH RAG" });
    setBusy(false);
  } catch (error) {
    showError(error);
    setBusy(false);
  }
});

document.querySelector("#compare-retrieval").addEventListener("click", async () => {
  const question = questionInput.value.trim();
  if (!question) return showError(new Error("Введите вопрос для сравнения"));
  setBusy(true, "Сравниваю baseline и enhanced retrieval...");
  try {
    const payload = await request("/api/compare-retrieval", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, model: controls.model.value, strategy: controls.strategy.value, candidate_top_k: Number(controls["candidate-top-k"].value), final_top_k: Number(controls["final-top-k"].value) }),
    });
    conversation.replaceChildren();
    appendMessage({ role: "user", content: payload.question });
    appendMessage({ ...payload.baseline, compareLabel: "BASELINE RAG" });
    appendMessage({ ...payload.enhanced, compareLabel: "ENHANCED RAG" });
    setBusy(false);
  } catch (error) {
    showError(error);
    setBusy(false);
  }
});

loadChats().catch(showError);
