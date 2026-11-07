/**
 * CAD viewer application entry point.
 * Connects SSE build events to the modular viewport, sidebar, and parameter spreadsheet.
 */

import { findItem, store, urlParams } from "./state.js";
import {
  initViewport,
  loadAssembly,
  loadPart,
  setViewportErrorHandler,
} from "./viewport.js";
import { renderSidebar, setSidebarErrorHandler } from "./sidebar.js";
import { initParamsPanel, renderParamSheet } from "./params_panel.js";

const errorBox = document.getElementById("error");
const errorText = document.getElementById("error-text");
const conn = document.getElementById("conn");

let lastBuiltAt = 0;

function showError(text) {
  errorText.textContent = text;
  errorBox.classList.remove("hidden");
}

function hideError() {
  errorBox.classList.add("hidden");
}

document.getElementById("error-close").addEventListener("click", hideError);
setViewportErrorHandler(showError);
setSidebarErrorHandler(showError);

document.getElementById("rebuild").addEventListener("click", () => {
  fetch("/api/rebuild", { method: "POST" });
});

function applyState(next) {
  store.state = next;
  const state = store.state;

  const all = [...state.parts, ...(state.assemblies || [])];
  const ok = all.filter((p) => p.status === "ok");
  if (!store.current || !ok.some((p) => p.name === store.current.name)) {
    const firstAssembly = (state.assemblies || []).find(
      (p) => p.status === "ok",
    );
    const firstPart = state.parts.find((p) => p.status === "ok");
    store.current = firstAssembly
      ? { type: "assembly", name: firstAssembly.name }
      : firstPart
        ? { type: "part", name: firstPart.name }
        : null;
  }

  const requested = urlParams.get("select");
  if (requested) {
    const part = state.parts.find((p) => p.name === requested);
    const assembly = (state.assemblies || []).find((p) => p.name === requested);
    if (part && part.status === "ok") {
      store.current = { type: "part", name: requested };
    } else if (assembly && assembly.status === "ok") {
      store.current = { type: "assembly", name: requested };
    }
  }

  renderSidebar();
  renderParamSheet(false);

  const errors = all.filter((p) => p.status === "error");
  if (errors.length) {
    showError(errors.map((e) => `${e.name}\n\n${e.error}`).join("\n\n"));
  } else {
    hideError();
  }

  if (store.current && state.built_at !== lastBuiltAt) {
    lastBuiltAt = state.built_at;
    const item = findItem(store.current);
    if (item) {
      if (store.current.type === "part") loadPart(item);
      else loadAssembly(item);
    }
  }
}

function connect() {
  if (urlParams.get("static") === "1") {
    fetch("/api/state")
      .then((response) => response.json())
      .then(applyState);
    return;
  }

  const events = new EventSource("/api/events");

  events.addEventListener("state", (event) => {
    conn.classList.add("live");
    applyState(JSON.parse(event.data));
  });

  events.onopen = () => conn.classList.add("live");
  events.onerror = () => conn.classList.remove("live");
}

initViewport();
initParamsPanel();
connect();
