/**
 * Left sidebar: assemblies/parts list, sub-component ghost/hide/focus controls,
 * and build summary bar.
 */

import { getCompOpts, isActive, store } from "./state.js";
import { applyCompVisuals, loadAssembly, loadPart } from "./viewport.js";
import { renderParamSheet, scrollParamSheetTop } from "./params_panel.js";

const partsList = document.getElementById("parts");
const summary = document.getElementById("summary");

let onSidebarError = () => {};
export function setSidebarErrorHandler(fn) {
  onSidebarError = fn;
}

export function renderSidebar() {
  partsList.innerHTML = "";
  const state = store.state;

  const addSection = (title, items, type) => {
    if (!items.length) return;
    const aliases = (state.params && state.params.aliases) || {};
    const header = document.createElement("li");
    header.className = "section";
    header.textContent = title;
    partsList.appendChild(header);

    for (const item of items) {
      const active = isActive(type, item.name);
      const li = document.createElement("li");
      li.className = "part" + (active ? " active" : "");
      li.dataset.status = item.status;

      const meta =
        item.status === "ok"
          ? type === "assembly"
            ? `${item.components.length} components · ${item.duration_ms.toFixed(0)} ms`
            : `${item.volume_mm3.toLocaleString()} mm³ · ${item.duration_ms.toFixed(0)} ms`
          : "build failed";

      const modShort = item.module ? item.module.split(".").pop() : item.name;
      const aliasName = aliases[item.name] || aliases[modShort];
      const displayTitle =
        aliasName && aliasName !== item.name
          ? `${aliasName} (${item.name})`
          : item.name;

      li.innerHTML = `
        <span class="dot"></span>
        <span class="name"></span>
        <span class="meta"></span>`;
      li.querySelector(".name").textContent = displayTitle;
      li.querySelector(".meta").textContent = meta;

      li.addEventListener("click", () => {
        if (item.status !== "ok") {
          onSidebarError(`${item.name}\n\n${item.error || "build failed"}`);
          return;
        }
        store.current = { type, name: item.name };
        store.activeSubComp = null;
        store.paramTab = "active";
        renderSidebar();
        renderParamSheet(true);
        scrollParamSheetTop();
        if (type === "part") loadPart(item);
        else loadAssembly(item);
      });

      partsList.appendChild(li);

      if (active && type === "assembly" && item.components) {
        const compUl = document.createElement("ul");
        compUl.className = "comp-list";
        for (const comp of item.components) {
          const opts = getCompOpts(item.name, comp.name);
          const compLi = document.createElement("li");
          compLi.className =
            "comp-item" +
            (opts.hidden ? " is-hidden" : "") +
            (store.activeSubComp === comp.name ? " active-comp" : "");
          compLi.title = `Click to focus ${comp.name} parameters`;

          compLi.addEventListener("click", (e) => {
            e.stopPropagation();
            store.activeSubComp =
              store.activeSubComp === comp.name ? null : comp.name;
            store.paramTab = "active";
            renderSidebar();
            renderParamSheet(true);
            scrollParamSheetTop();
          });

          const swatch = document.createElement("span");
          swatch.className = "comp-swatch";
          swatch.style.background = comp.color || "#9fb4d0";

          const cname = document.createElement("span");
          cname.className = "comp-name";
          const compAlias = aliases[comp.name];
          cname.textContent =
            compAlias && compAlias !== comp.name
              ? `${compAlias} (${comp.name})`
              : comp.name;

          const ghostBtn = document.createElement("button");
          ghostBtn.type = "button";
          ghostBtn.className = "comp-btn" + (opts.ghost ? " active" : "");
          ghostBtn.title = "Toggle ghost (25% opacity)";
          ghostBtn.textContent = "ghost";
          ghostBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            opts.ghost = !opts.ghost;
            ghostBtn.classList.toggle("active", opts.ghost);
            applyCompVisuals(item.name, comp.name);
          });

          const hideBtn = document.createElement("button");
          hideBtn.type = "button";
          hideBtn.className = "comp-btn" + (opts.hidden ? " active" : "");
          hideBtn.title = "Hide / show component";
          hideBtn.textContent = opts.hidden ? "show" : "hide";
          hideBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            opts.hidden = !opts.hidden;
            hideBtn.classList.toggle("active", opts.hidden);
            hideBtn.textContent = opts.hidden ? "show" : "hide";
            compLi.classList.toggle("is-hidden", opts.hidden);
            applyCompVisuals(item.name, comp.name);
          });

          compLi.append(swatch, cname, ghostBtn, hideBtn);
          compUl.appendChild(compLi);
        }
        partsList.appendChild(compUl);
      }
    }
  };

  addSection("Assemblies", state.assemblies || [], "assembly");
  addSection("Parts", state.parts, "part");

  const all = [...state.parts, ...(state.assemblies || [])];
  const ok = all.filter((p) => p.status === "ok").length;
  const bad = all.length - ok;
  const when = state.built_at
    ? new Date(state.built_at * 1000).toLocaleTimeString()
    : "—";

  summary.innerHTML =
    `<span class="${bad ? "bad" : "good"}">` +
    `${bad ? `${bad} failed` : "all ok"}</span>` +
    ` · ${ok} item${ok === 1 ? "" : "s"}` +
    ` · ${state.duration_ms.toFixed(0)} ms · ${when}`;
}
