/**
 * Right-hand Parameters (fx) Spreadsheet, live sliders, formula bindings,
 * presets, and Sync-to-Python controls.
 */

import { activeModuleShort, activeScopeLabel, store } from "./state.js";
import { resizeViewport } from "./viewport.js";

const paramPanel = document.getElementById("param-panel");
const paramOpenBtn = document.getElementById("param-open-btn");
const paramCollapseBtn = document.getElementById("param-collapse-btn");
const paramAddVarBtn = document.getElementById("param-add-var-btn");
const paramSavePresetBtn = document.getElementById("param-save-preset-btn");
const paramSyncPyBtn = document.getElementById("param-sync-py-btn");
const paramResetAllBtn = document.getElementById("param-reset-all-btn");
const paramTabs = document.getElementById("param-tabs");
const presetSelect = document.getElementById("preset-select");
const paramPresetForm = document.getElementById("param-preset-form");
const presetNameInput = document.getElementById("preset-name-input");
const presetCancelBtn = document.getElementById("preset-cancel-btn");
const paramSearch = document.getElementById("param-search");
const paramNewVarForm = document.getElementById("param-new-var-form");
const newVarName = document.getElementById("new-var-name");
const newVarExpr = document.getElementById("new-var-expr");
const newVarDoc = document.getElementById("new-var-doc");
const newVarCancel = document.getElementById("new-var-cancel");
const paramSheet = document.getElementById("param-sheet");
const paramHint = document.getElementById("param-hint");

let paramFilterText = "";
let lastFocusedExprInput = null;
let lastRenderedTabSignature = "";
const rowDomMap = new Map();
let paramUpdateTimer = null;
let pendingUpdates = {};

export function scrollParamSheetTop() {
  paramSheet.scrollTop = 0;
}

export function postParamPayload(payload) {
  return fetch("/api/params", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

function queueParamUpdate(key, expr) {
  pendingUpdates[key] = expr;
  if (paramUpdateTimer) clearTimeout(paramUpdateTimer);
  paramUpdateTimer = setTimeout(() => {
    const batch = { ...pendingUpdates };
    pendingUpdates = {};
    paramUpdateTimer = null;
    postParamPayload({ action: "set", updates: batch });
  }, 75);
}

function formatParamValue(field) {
  if (field.type === "bool") return field.value ? "True" : "False";
  if (field.type === "int") {
    return `${field.value}${field.unit ? " " + field.unit : ""}`;
  }
  if (typeof field.value === "number") {
    const decimals = field.step < 0.1 ? 2 : 1;
    return `${field.value.toFixed(decimals)}${field.unit ? " " + field.unit : ""}`;
  }
  return `${field.value}`;
}

export function renderParamTabs() {
  const pstate = store.state.params || { modules: {}, custom: [] };
  const modShorts = Object.keys(pstate.modules || {});
  const scopeLabel = activeScopeLabel();

  paramTabs.innerHTML = "";
  const tabs = [
    { id: "active", label: scopeLabel ? `Active (${scopeLabel})` : "Active" },
    ...modShorts.map((m) => ({ id: m, label: m })),
    { id: "all", label: "All" },
  ];

  for (const t of tabs) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "param-tab" + (store.paramTab === t.id ? " active" : "");
    btn.textContent = t.label;
    btn.addEventListener("click", () => {
      store.paramTab = t.id;
      renderParamTabs();
      renderParamSheet(true);
    });
    paramTabs.appendChild(btn);
  }

  const presets = pstate.presets || [];
  const activePreset = pstate.active_preset || "";
  presetSelect.innerHTML = `<option value="">${presets.length ? "Presets (" + presets.length + ")…" : "No saved presets"}</option>`;
  for (const pname of presets) {
    const opt = document.createElement("option");
    opt.value = pname;
    opt.textContent = pname;
    if (pname === activePreset) opt.selected = true;
    presetSelect.appendChild(opt);
  }

  if (pstate.message && paramHint) {
    paramHint.innerHTML = `<strong style="color:var(--good)">&#10003; ${pstate.message}</strong> · Auto-saved to <code>params_state.json</code>`;
  }
}

function getVisibleSections() {
  const pstate = store.state.params || { modules: {}, custom: [] };
  const modules = pstate.modules || {};
  const custom = pstate.custom || [];
  const partScopes = pstate.part_scopes || {};
  const curMod = activeModuleShort();

  const targetPartName =
    store.paramTab === "active"
      ? store.activeSubComp ||
        (store.current && store.current.type === "part"
          ? store.current.name
          : null)
      : null;
  const scopedKeyList =
    targetPartName && partScopes[targetPartName]
      ? new Set(partScopes[targetPartName])
      : null;

  let targetShorts = [];
  if (scopedKeyList) {
    targetShorts = Object.keys(modules);
  } else if (store.paramTab === "all") {
    targetShorts = Object.keys(modules);
  } else if (store.paramTab === "active") {
    if (curMod && modules[curMod]) {
      targetShorts = [curMod];
    } else {
      targetShorts = Object.keys(modules);
    }
  } else if (modules[store.paramTab]) {
    targetShorts = [store.paramTab];
  } else {
    targetShorts = Object.keys(modules);
  }

  const filter = paramFilterText.trim().toLowerCase();
  const sections = [];

  const filteredCustom = custom.filter((f) => {
    if (!filter) return true;
    return (
      f.name.toLowerCase().includes(filter) ||
      (f.doc && f.doc.toLowerCase().includes(filter)) ||
      (f.expr && f.expr.toLowerCase().includes(filter))
    );
  });
  if (filteredCustom.length) {
    sections.push({
      title: "Custom Variables (Global)",
      moduleShort: "custom",
      fields: filteredCustom,
    });
  }

  const multiModule = targetShorts.length > 1;
  for (const short of targetShorts) {
    const modInfo = modules[short];
    if (!modInfo) continue;
    const byGroup = new Map();
    for (const f of modInfo.fields) {
      if (scopedKeyList && !scopedKeyList.has(f.key)) {
        continue;
      }
      if (filter) {
        const match =
          f.name.toLowerCase().includes(filter) ||
          (f.doc && f.doc.toLowerCase().includes(filter)) ||
          (f.group && f.group.toLowerCase().includes(filter)) ||
          (f.expr && f.expr.toLowerCase().includes(filter));
        if (!match) continue;
      }
      const gname = multiModule ? `${short} · ${f.group}` : f.group;
      if (!byGroup.has(gname)) byGroup.set(gname, []);
      byGroup
        .get(gname)
        .push({ ...f, moduleShort: short, showModuleTag: multiModule });
    }
    for (const [gtitle, fields] of byGroup.entries()) {
      sections.push({
        title: gtitle,
        moduleShort: short,
        fields,
      });
    }
  }

  return sections;
}

function updateRowInPlace(entry, field) {
  const { rowEl, exprInput, controlCell, actCell, docEl } = entry;
  rowEl.classList.toggle("is-modified", !!field.is_modified);
  rowEl.classList.toggle("is-bound", !!field.is_bound);
  rowEl.classList.toggle("has-error", !!field.error);

  if (docEl) {
    docEl.textContent = field.doc || "";
    docEl.title = field.doc || "";
  }

  if (document.activeElement !== exprInput) {
    exprInput.value = field.expr;
  }

  const desiredMode = field.error
    ? "error"
    : field.is_bound
      ? "bound"
      : field.type;

  if (entry.mode !== desiredMode) {
    buildControlCell(entry, field);
  } else if (desiredMode === "error") {
    const badge = controlCell.querySelector(".err-badge");
    if (badge) {
      badge.textContent = `⚠ ${field.error}`;
      badge.title = field.error;
    }
  } else if (desiredMode === "bound") {
    const valSpan = controlCell.querySelector(".bound-val");
    if (valSpan) valSpan.textContent = formatParamValue(field);
    const badge = controlCell.querySelector(".bound-badge");
    if (badge) {
      badge.title =
        `Bound formula: ${field.expr}` +
        (field.deps?.length ? `\nDepends on: ${field.deps.join(", ")}` : "");
    }
  } else if (desiredMode === "float" || desiredMode === "int") {
    const slider = controlCell.querySelector(".param-slider");
    const readout = controlCell.querySelector(".param-val-readout");
    if (slider && document.activeElement !== slider) {
      slider.min = String(field.min);
      slider.max = String(field.max);
      slider.step = String(field.step);
      slider.value = String(field.value);
    }
    if (readout) {
      readout.textContent = formatParamValue(field);
    }
  } else if (desiredMode === "bool") {
    const cb = controlCell.querySelector("input[type='checkbox']");
    if (cb && document.activeElement !== cb) {
      cb.checked = !!field.value;
    }
  }

  buildActCell(actCell, field);
}

function buildControlCell(entry, field) {
  const { controlCell, exprInput } = entry;
  controlCell.innerHTML = "";

  if (field.error) {
    entry.mode = "error";
    const err = document.createElement("span");
    err.className = "err-badge";
    err.textContent = `⚠ ${field.error}`;
    err.title = field.error;
    controlCell.appendChild(err);
    return;
  }

  if (field.is_bound) {
    entry.mode = "bound";
    const badge = document.createElement("span");
    badge.className = "bound-badge";
    badge.title =
      `Bound formula: ${field.expr}` +
      (field.deps?.length ? `\nDepends on: ${field.deps.join(", ")}` : "");
    badge.innerHTML = `<span>&#128279; bound</span><span class="bound-val"></span>`;
    badge.querySelector(".bound-val").textContent = formatParamValue(field);
    controlCell.appendChild(badge);
    return;
  }

  entry.mode = field.type;
  if (field.type === "bool") {
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = !!field.value;
    cb.addEventListener("change", () => {
      const nextExpr = cb.checked ? "True" : "False";
      exprInput.value = nextExpr;
      queueParamUpdate(field.key, nextExpr);
    });
    controlCell.appendChild(cb);
    return;
  }

  const slider = document.createElement("input");
  slider.type = "range";
  slider.className = "param-slider";
  slider.min = String(field.min);
  slider.max = String(field.max);
  slider.step = String(field.step);
  slider.value = String(field.value);

  const readout = document.createElement("span");
  readout.className = "param-val-readout";
  readout.textContent = formatParamValue(field);

  slider.addEventListener("input", () => {
    const num = parseFloat(slider.value);
    const formatted =
      field.type === "int"
        ? String(Math.round(num))
        : String(Number(num.toFixed(3)));
    exprInput.value = formatted;
    readout.textContent =
      field.type === "int"
        ? `${Math.round(num)}${field.unit ? " " + field.unit : ""}`
        : `${num.toFixed(field.step < 0.1 ? 2 : 1)}${field.unit ? " " + field.unit : ""}`;
    queueParamUpdate(field.key, formatted);
  });

  controlCell.append(slider, readout);
}

function buildActCell(actCell, field) {
  actCell.innerHTML = "";
  if (field.key.startsWith("custom.")) {
    if (field.name !== "clearance") {
      const delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.className = "row-act-btn";
      delBtn.title = `Delete custom variable ${field.name}`;
      delBtn.innerHTML = "&times;";
      delBtn.addEventListener("click", () => {
        postParamPayload({ action: "delete_custom", name: field.name });
      });
      actCell.appendChild(delBtn);
    }
    return;
  }

  if (field.is_modified) {
    const resetBtn = document.createElement("button");
    resetBtn.type = "button";
    resetBtn.className = "row-act-btn";
    resetBtn.title = `Reset to default (${field.default_expr})`;
    resetBtn.textContent = "↺";
    resetBtn.addEventListener("click", () => {
      postParamPayload({ action: "reset_param", key: field.key });
    });
    actCell.appendChild(resetBtn);
  }
}

function createParamRow(field) {
  const rowEl = document.createElement("div");
  rowEl.className = "param-row";
  rowEl.dataset.key = field.key;

  const nameCell = document.createElement("div");
  nameCell.className = "param-name-cell";

  const nameBtn = document.createElement("button");
  nameBtn.type = "button";
  nameBtn.className = "param-name-btn";
  nameBtn.title =
    `Click while editing a formula to insert '${field.name}'\n` +
    `Full reference: ${field.key}\nDefault: ${field.default_expr}`;

  const nameText = document.createElement("span");
  nameText.textContent = field.name;
  nameBtn.appendChild(nameText);

  if (field.showModuleTag) {
    const modTag = document.createElement("span");
    modTag.className = "param-mod-tag";
    modTag.textContent = field.moduleShort;
    nameBtn.appendChild(modTag);
  }

  nameBtn.addEventListener("mousedown", (e) => {
    if (
      lastFocusedExprInput &&
      document.activeElement === lastFocusedExprInput
    ) {
      e.preventDefault();
    }
  });

  nameBtn.addEventListener("click", () => {
    if (
      lastFocusedExprInput &&
      document.activeElement === lastFocusedExprInput &&
      lastFocusedExprInput.dataset.key !== field.key
    ) {
      const targetMod = lastFocusedExprInput.dataset.module;
      const sourceMod = field.key.split(".")[0];
      const refToken =
        sourceMod === "custom" || sourceMod === targetMod
          ? field.name
          : field.key;

      let curVal = lastFocusedExprInput.value.trim();
      if (!curVal.startsWith("=")) {
        curVal = "= " + refToken;
      } else {
        curVal = curVal + " " + refToken;
      }
      lastFocusedExprInput.value = curVal;
      lastFocusedExprInput.dispatchEvent(new Event("change"));
    }
  });

  const docEl = document.createElement("span");
  docEl.className = "param-doc";
  docEl.textContent = field.doc || "";
  docEl.title = field.doc || "";

  nameCell.append(nameBtn, docEl);

  const exprCell = document.createElement("div");
  exprCell.className = "expr-cell";

  const exprInput = document.createElement("input");
  exprInput.type = "text";
  exprInput.className = "expr-input";
  exprInput.value = field.expr;
  exprInput.dataset.key = field.key;
  exprInput.dataset.module = field.key.split(".")[0];
  exprInput.spellcheck = false;

  exprInput.addEventListener("focus", () => {
    lastFocusedExprInput = exprInput;
  });

  const commitExpr = () => {
    const val = exprInput.value.trim();
    if (!val) {
      postParamPayload({ action: "reset_param", key: field.key });
      return;
    }
    queueParamUpdate(field.key, val);
  };

  exprInput.addEventListener("change", commitExpr);
  exprInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      commitExpr();
      exprInput.blur();
    } else if (e.key === "Escape") {
      exprInput.value = field.expr;
      exprInput.blur();
    }
  });

  exprCell.appendChild(exprInput);

  const controlCell = document.createElement("div");
  controlCell.className = "control-cell";

  const actCell = document.createElement("div");
  actCell.className = "act-cell";

  rowEl.append(nameCell, exprCell, controlCell, actCell);

  const entry = {
    rowEl,
    exprInput,
    controlCell,
    actCell,
    docEl,
    mode: null,
  };
  updateRowInPlace(entry, field);
  return entry;
}

export function renderParamSheet(forceRebuildDom = false) {
  renderParamTabs();
  const sections = getVisibleSections();
  const sig = JSON.stringify(
    sections.map((s) => ({
      t: s.title,
      k: s.fields.map((f) => f.key),
    })),
  );

  if (!forceRebuildDom && sig === lastRenderedTabSignature) {
    for (const sec of sections) {
      for (const field of sec.fields) {
        const entry = rowDomMap.get(field.key);
        if (entry) updateRowInPlace(entry, field);
      }
    }
    return;
  }

  lastRenderedTabSignature = sig;
  rowDomMap.clear();
  paramSheet.innerHTML = "";

  for (const sec of sections) {
    const groupRow = document.createElement("div");
    groupRow.className = "param-group-row";
    groupRow.textContent = sec.title;
    paramSheet.appendChild(groupRow);

    for (const field of sec.fields) {
      const entry = createParamRow(field);
      rowDomMap.set(field.key, entry);
      paramSheet.appendChild(entry.rowEl);
    }
  }
}

export function initParamsPanel() {
  paramCollapseBtn.addEventListener("click", () => {
    paramPanel.classList.add("hidden");
    paramOpenBtn.classList.remove("hidden");
    resizeViewport();
  });

  paramOpenBtn.addEventListener("click", () => {
    paramPanel.classList.remove("hidden");
    paramOpenBtn.classList.add("hidden");
    resizeViewport();
  });

  paramResetAllBtn.addEventListener("click", () => {
    postParamPayload({ action: "reset_all" });
  });

  paramSavePresetBtn.addEventListener("click", () => {
    paramPresetForm.classList.toggle("hidden");
    if (!paramPresetForm.classList.contains("hidden")) {
      presetNameInput.focus();
    }
  });

  presetCancelBtn.addEventListener("click", () => {
    paramPresetForm.classList.add("hidden");
  });

  paramPresetForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const name = presetNameInput.value.trim();
    if (!name) return;
    postParamPayload({ action: "save_preset", name });
    presetNameInput.value = "";
    paramPresetForm.classList.add("hidden");
  });

  presetSelect.addEventListener("change", () => {
    const name = presetSelect.value;
    if (!name) return;
    postParamPayload({ action: "load_preset", name });
  });

  paramSyncPyBtn.addEventListener("click", () => {
    postParamPayload({ action: "sync_python" });
  });

  paramSearch.addEventListener("input", () => {
    paramFilterText = paramSearch.value;
    renderParamSheet(true);
  });

  paramAddVarBtn.addEventListener("click", () => {
    paramNewVarForm.classList.toggle("hidden");
    if (!paramNewVarForm.classList.contains("hidden")) {
      newVarName.focus();
    }
  });

  newVarCancel.addEventListener("click", () => {
    paramNewVarForm.classList.add("hidden");
  });

  paramNewVarForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const name = newVarName.value.trim();
    const expr = newVarExpr.value.trim() || "1.0";
    const doc = newVarDoc.value.trim() || "Custom helper variable";
    if (!name) return;
    postParamPayload({
      action: "add_custom",
      name,
      expr,
      unit: "mm",
      doc,
    });
    newVarName.value = "";
    newVarDoc.value = "";
    paramNewVarForm.classList.add("hidden");
  });
}
