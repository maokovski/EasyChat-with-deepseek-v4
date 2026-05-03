"use strict";

const DEFAULT_STATE = {
  apiKey: "",
  baseUrl: "https://api.deepseek.com",
  model: "deepseek-v4-pro",
  thinking: "disabled",
  theme: "light",
  language: "en",
  messages: [
    {
      role: "system",
      content: "Ready. Add an API key in Settings before sending requests."
    }
  ]
};

const TEXT = {
  en: {
    ready: "Ready",
    settings: "Settings",
    hideSettings: "Close",
    apiKey: "API Key",
    baseUrl: "Base URL",
    model: "Model",
    thinking: "Thinking",
    theme: "Theme",
    language: "Language",
    saveSettings: "Save Settings",
    placeholder: "Ask DeepSeek from Edge...",
    newChat: "New",
    usePage: "Use Page",
    regenerate: "Regenerate",
    save: "Save",
    clear: "Clear",
    send: "Send",
    user: "You",
    assistant: "DeepSeek",
    system: "System",
    missingKey: "Add an API key in Settings first.",
    saved: "Settings saved",
    waiting: "Waiting for DeepSeek...",
    failed: "Request failed",
    empty: "Type a message first.",
    pageAdded: "Page context added to the composer.",
    pageFailed: "Could not read the current page.",
    regenerated: "Regenerating the last answer.",
    noRegenerate: "There is no user message to regenerate.",
    transcriptSaved: "Transcript saved"
  },
  zh: {
    ready: "\u5c31\u7eea",
    settings: "\u8bbe\u7f6e",
    hideSettings: "\u5173\u95ed",
    apiKey: "API Key",
    baseUrl: "Base URL",
    model: "\u6a21\u578b",
    thinking: "\u601d\u8003",
    theme: "\u4e3b\u9898",
    language: "\u8bed\u8a00",
    saveSettings: "\u4fdd\u5b58\u8bbe\u7f6e",
    placeholder: "\u5728 Edge \u4e2d\u8be2\u95ee DeepSeek...",
    newChat: "\u65b0\u5bf9\u8bdd",
    usePage: "\u4f7f\u7528\u9875\u9762",
    regenerate: "\u91cd\u65b0\u751f\u6210",
    save: "\u4fdd\u5b58",
    clear: "\u6e05\u7a7a",
    send: "\u53d1\u9001",
    user: "\u4f60",
    assistant: "DeepSeek",
    system: "\u7cfb\u7edf",
    missingKey: "\u8bf7\u5148\u5728\u8bbe\u7f6e\u4e2d\u586b\u5199 API Key\u3002",
    saved: "\u8bbe\u7f6e\u5df2\u4fdd\u5b58",
    waiting: "\u6b63\u5728\u7b49\u5f85 DeepSeek...",
    failed: "\u8bf7\u6c42\u5931\u8d25",
    empty: "\u8bf7\u5148\u8f93\u5165\u5185\u5bb9\u3002",
    pageAdded: "\u5df2\u5c06\u9875\u9762\u4e0a\u4e0b\u6587\u52a0\u5165\u8f93\u5165\u6846\u3002",
    pageFailed: "\u65e0\u6cd5\u8bfb\u53d6\u5f53\u524d\u9875\u9762\u3002",
    regenerated: "\u6b63\u5728\u91cd\u65b0\u751f\u6210\u4e0a\u4e00\u6761\u56de\u590d\u3002",
    noRegenerate: "\u6ca1\u6709\u53ef\u91cd\u65b0\u751f\u6210\u7684\u7528\u6237\u6d88\u606f\u3002",
    transcriptSaved: "\u5bf9\u8bdd\u5df2\u4fdd\u5b58"
  }
};

const elements = {
  settingsButton: document.getElementById("settingsButton"),
  settingsPanel: document.getElementById("settingsPanel"),
  statusText: document.getElementById("statusText"),
  apiKeyInput: document.getElementById("apiKeyInput"),
  baseUrlInput: document.getElementById("baseUrlInput"),
  modelSelect: document.getElementById("modelSelect"),
  thinkingSelect: document.getElementById("thinkingSelect"),
  themeSelect: document.getElementById("themeSelect"),
  languageSelect: document.getElementById("languageSelect"),
  saveSettingsButton: document.getElementById("saveSettingsButton"),
  messages: document.getElementById("messages"),
  promptInput: document.getElementById("promptInput"),
  newButton: document.getElementById("newButton"),
  pageButton: document.getElementById("pageButton"),
  regenerateButton: document.getElementById("regenerateButton"),
  saveButton: document.getElementById("saveButton"),
  clearButton: document.getElementById("clearButton"),
  sendButton: document.getElementById("sendButton")
};

let state = { ...DEFAULT_STATE };
let isWaiting = false;

function getText(key) {
  return (TEXT[state.language] || TEXT.en)[key] || TEXT.en[key] || key;
}

function setStatus(keyOrText) {
  elements.statusText.textContent = getText(keyOrText) || keyOrText;
}

function applyLanguage() {
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = getText(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = getText(node.dataset.i18nPlaceholder);
  });
  elements.settingsButton.textContent = elements.settingsPanel.hidden
    ? getText("settings")
    : getText("hideSettings");
}

function applyTheme() {
  document.body.classList.toggle("dark", state.theme === "dark");
}

function renderMessages() {
  elements.messages.textContent = "";
  for (const message of state.messages) {
    const item = document.createElement("article");
    item.className = `message ${message.role}`;

    const speaker = document.createElement("div");
    speaker.className = "speaker";
    speaker.textContent = getText(message.role) || message.role;

    const content = document.createElement("div");
    content.textContent = message.content || "";

    item.append(speaker, content);
    elements.messages.append(item);
  }
  elements.messages.scrollTop = elements.messages.scrollHeight;
}

function syncForm() {
  elements.apiKeyInput.value = state.apiKey;
  elements.baseUrlInput.value = state.baseUrl;
  elements.modelSelect.value = state.model;
  elements.thinkingSelect.value = state.thinking;
  elements.themeSelect.value = state.theme;
  elements.languageSelect.value = state.language;
}

async function saveState() {
  await chrome.storage.local.set({ easyChatState: state });
}

async function loadState() {
  const stored = await chrome.storage.local.get("easyChatState");
  state = {
    ...DEFAULT_STATE,
    ...(stored.easyChatState || {})
  };
  if (!Array.isArray(state.messages) || state.messages.length === 0) {
    state.messages = [...DEFAULT_STATE.messages];
  }
}

function getConversationMessages() {
  return state.messages
    .filter((message) => message.role === "user" || message.role === "assistant")
    .map((message) => ({ role: message.role, content: message.content }));
}

function buildRequestBody(messages) {
  const body = {
    model: state.model,
    messages,
    stream: false
  };
  if (state.thinking === "disabled") {
    body.temperature = 0.7;
    body.extra_body = { thinking: { type: "disabled" } };
  } else {
    body.reasoning_effort = state.thinking;
    body.extra_body = { thinking: { type: "enabled" } };
  }
  return body;
}

function endpointUrl() {
  return `${state.baseUrl.replace(/\/+$/, "")}/chat/completions`;
}

async function requestAnswer(messages) {
  const response = await fetch(endpointUrl(), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${state.apiKey}`
    },
    body: JSON.stringify(buildRequestBody(messages))
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.error?.message || response.statusText || response.status;
    throw new Error(detail);
  }
  return payload.choices?.[0]?.message?.content || "";
}

function setWaiting(nextValue) {
  isWaiting = nextValue;
  elements.sendButton.disabled = nextValue;
  elements.regenerateButton.disabled = nextValue;
  elements.pageButton.disabled = nextValue;
}

async function sendPrompt() {
  if (isWaiting) return;
  const prompt = elements.promptInput.value.trim();
  if (!prompt) {
    setStatus("empty");
    return;
  }
  if (!state.apiKey.trim()) {
    elements.settingsPanel.hidden = false;
    applyLanguage();
    setStatus("missingKey");
    return;
  }

  state.messages.push({ role: "user", content: prompt });
  elements.promptInput.value = "";
  renderMessages();
  setWaiting(true);
  setStatus("waiting");

  try {
    const answer = await requestAnswer(getConversationMessages());
    state.messages.push({ role: "assistant", content: answer });
    setStatus("ready");
  } catch (error) {
    state.messages.push({
      role: "system",
      content: `${getText("failed")}: ${error.message || error}`
    });
    setStatus("failed");
  } finally {
    setWaiting(false);
    renderMessages();
    await saveState();
  }
}

async function regenerateLast() {
  if (isWaiting) return;
  while (state.messages.at(-1)?.role === "assistant") {
    state.messages.pop();
  }
  const lastUser = [...state.messages].reverse().find((message) => message.role === "user");
  if (!lastUser) {
    setStatus("noRegenerate");
    return;
  }
  setStatus("regenerated");
  renderMessages();
  setWaiting(true);
  try {
    const answer = await requestAnswer(getConversationMessages());
    state.messages.push({ role: "assistant", content: answer });
    setStatus("ready");
  } catch (error) {
    state.messages.push({
      role: "system",
      content: `${getText("failed")}: ${error.message || error}`
    });
    setStatus("failed");
  } finally {
    setWaiting(false);
    renderMessages();
    await saveState();
  }
}

async function addPageContext() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) {
      throw new Error("No active tab");
    }
    const [result] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        const MAX_TEXT_LENGTH = 6000;
        const MAX_ELEMENTS = 40;
        const BLOCKED_TAGS = new Set([
          "SCRIPT",
          "STYLE",
          "NOSCRIPT",
          "TEMPLATE",
          "SVG",
          "CANVAS"
        ]);

        function isVisible(element) {
          const style = window.getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            Number(style.opacity || "1") > 0 &&
            rect.width > 0 &&
            rect.height > 0
          );
        }

        function cleanText(text) {
          return String(text || "").replace(/\s+/g, " ").trim();
        }

        function readVisibleText() {
          const walker = document.createTreeWalker(
            document.body || document.documentElement,
            NodeFilter.SHOW_TEXT,
            {
              acceptNode(node) {
                const parent = node.parentElement;
                if (!parent || BLOCKED_TAGS.has(parent.tagName) || !isVisible(parent)) {
                  return NodeFilter.FILTER_REJECT;
                }
                return cleanText(node.nodeValue)
                  ? NodeFilter.FILTER_ACCEPT
                  : NodeFilter.FILTER_REJECT;
              }
            }
          );
          const chunks = [];
          let total = 0;
          let node = walker.nextNode();
          while (node && total < MAX_TEXT_LENGTH) {
            const text = cleanText(node.nodeValue);
            chunks.push(text);
            total += text.length + 1;
            node = walker.nextNode();
          }
          return chunks.join("\n").slice(0, MAX_TEXT_LENGTH);
        }

        function describeElement(element) {
          const label =
            element.getAttribute("aria-label") ||
            element.getAttribute("title") ||
            element.getAttribute("placeholder") ||
            element.innerText ||
            element.value ||
            element.name ||
            element.id ||
            "";
          const text = cleanText(label).slice(0, 140);
          if (!text) return "";
          const tag = element.tagName.toLowerCase();
          const role = element.getAttribute("role");
          const href = element.href ? ` -> ${element.href}` : "";
          return `${role || tag}: ${text}${href}`;
        }

        const elementSelector = [
          "a[href]",
          "button",
          "input",
          "textarea",
          "select",
          "[role='button']",
          "[role='link']",
          "[aria-label]"
        ].join(",");
        const elements = [...document.querySelectorAll(elementSelector)]
          .filter(isVisible)
          .map(describeElement)
          .filter(Boolean)
          .slice(0, MAX_ELEMENTS);

        return {
          title: document.title,
          url: location.href,
          selection: String(window.getSelection() || "").trim(),
          text: readVisibleText(),
          elements
        };
      }
    });
    const page = result.result || {};
    const context = [
      `Page title: ${page.title || tab.title || ""}`,
      `URL: ${page.url || tab.url || ""}`,
      page.selection ? `Selected text:\n${page.selection}` : "",
      page.elements?.length ? `Visible interactive elements:\n${page.elements.join("\n")}` : "",
      page.text ? `Visible page text:\n${page.text}` : ""
    ]
      .filter(Boolean)
      .join("\n");
    elements.promptInput.value = `${elements.promptInput.value.trim()}\n\n${context}`.trim();
    setStatus("pageAdded");
  } catch (_error) {
    setStatus("pageFailed");
  }
}

async function saveTranscript() {
  const text = state.messages
    .map((message) => `${message.role.toUpperCase()}\n${message.content}`)
    .join("\n\n");
  const dataUrl = `data:text/plain;charset=utf-8,${encodeURIComponent(text)}`
  await chrome.downloads.download({
    url: dataUrl,
    filename: `easychat-${new Date().toISOString().replace(/[:.]/g, "-")}.txt`,
    saveAs: true
  });
  setStatus("transcriptSaved");
}

async function saveSettings() {
  state.apiKey = elements.apiKeyInput.value.trim();
  state.baseUrl = elements.baseUrlInput.value.trim() || DEFAULT_STATE.baseUrl;
  state.model = elements.modelSelect.value;
  state.thinking = elements.thinkingSelect.value;
  state.theme = elements.themeSelect.value;
  state.language = elements.languageSelect.value;
  applyTheme();
  applyLanguage();
  renderMessages();
  await saveState();
  setStatus("saved");
}

async function newChat() {
  state.messages = [{ role: "system", content: getText("ready") }];
  elements.promptInput.value = "";
  renderMessages();
  await saveState();
  setStatus("ready");
}

async function clearChat() {
  state.messages = [{ role: "system", content: getText("ready") }];
  renderMessages();
  await saveState();
  setStatus("ready");
}

function wireEvents() {
  elements.settingsButton.addEventListener("click", () => {
    elements.settingsPanel.hidden = !elements.settingsPanel.hidden;
    applyLanguage();
  });
  elements.saveSettingsButton.addEventListener("click", saveSettings);
  elements.newButton.addEventListener("click", newChat);
  elements.pageButton.addEventListener("click", addPageContext);
  elements.regenerateButton.addEventListener("click", regenerateLast);
  elements.saveButton.addEventListener("click", saveTranscript);
  elements.clearButton.addEventListener("click", clearChat);
  elements.sendButton.addEventListener("click", sendPrompt);
  elements.promptInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendPrompt();
    }
  });
}

async function boot() {
  await loadState();
  syncForm();
  applyTheme();
  applyLanguage();
  renderMessages();
  setStatus("ready");
  wireEvents();
}

boot();
