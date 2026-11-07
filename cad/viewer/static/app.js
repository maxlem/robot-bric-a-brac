import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";

const canvas = document.getElementById("view");
const hud = document.getElementById("hud");
const errorBox = document.getElementById("error");
const errorText = document.getElementById("error-text");
const partsList = document.getElementById("parts");
const summary = document.getElementById("summary");
const conn = document.getElementById("conn");
const wireframe = document.getElementById("wireframe");
const fitBtn = document.getElementById("fit");
const clipSliderRow = document.getElementById("clip-slider-row");
const clipSlider = document.getElementById("clip-slider");
const clipVal = document.getElementById("clip-val");
const clipFlipBtn = document.getElementById("clip-flip");
const clipAxisBtns = document.querySelectorAll(".clip-axes .clip-btn");

// Parameter spreadsheet elements
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

const params = new URLSearchParams(location.search);
if (params.get("wireframe") === "1") wireframe.checked = true;

// --- scene ---------------------------------------------------------------

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x0e1116);
renderer.localClippingEnabled = true;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 10000);
camera.up.set(0, 0, 1); // CAD is Z-up
camera.position.set(90, -110, 70);

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.08;

scene.add(new THREE.HemisphereLight(0xdfe8ff, 0x1a1f28, 1.0));

// Key: front-right, above the camera side.
const key = new THREE.DirectionalLight(0xffffff, 1.8);
key.position.set(80, -120, 100);
scene.add(key);

// Fill: front-left, low.
const fill = new THREE.DirectionalLight(0x88aaff, 0.6);
fill.position.set(-90, -40, 40);
scene.add(fill);

// Rim: the opposing corner, behind and above.
const rim = new THREE.DirectionalLight(0xffe0c0, 0.9);
rim.position.set(-80, 120, 80);
scene.add(rim);

const grid = new THREE.GridHelper(200, 20, 0x2b3240, 0x1a1f27);
grid.rotation.x = Math.PI / 2; // lie in the XY plane
grid.material.transparent = true;
grid.material.opacity = 0.7;
scene.add(grid);

const axes = new THREE.AxesHelper(30);
scene.add(axes);

const group = new THREE.Group();
scene.add(group);

const loader = new STLLoader();
let loaded = [];
let loadedGeometries = [];
let current = null;
let lastBuiltAt = 0;
let lastFittedKey = null;
let lastSceneCenter = new THREE.Vector3();
let sceneBounds = new THREE.Box3();
let loadGeneration = 0;
let state = {
  parts: [],
  assemblies: [],
  duration_ms: 0,
  built_at: 0,
  params: { modules: {}, custom: [] },
};

// Per-component state across hot-reloads: key -> { hidden: bool, ghost: bool }
const compState = new Map();

// Section clipping plane state
let clipAxis = params.get("clip") || "off";
let clipFlip = params.get("clip_flip") === "1" ? -1 : 1;
const clipPlane = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0);

// Parameter spreadsheet UI state
let paramTab = params.get("tab") || "active"; // "active" | "all" | <shortModule>
let activeSubComp = null; // selected sub-component inside an assembly
let paramFilterText = "";
let lastFocusedExprInput = null;
let lastRenderedTabSignature = "";
const rowDomMap = new Map(); // key -> { rowEl, exprInput, controlCell, actCell, docEl }
let paramUpdateTimer = null;
let pendingUpdates = {};

// --- scene management ----------------------------------------------------

function clearScene() {
  for (const mesh of loaded) {
    group.remove(mesh);
    mesh.geometry.dispose();
    mesh.material.dispose();
  }
  loaded = [];
  loadedGeometries = [];
}

function getCompKey(assemblyName, compName) {
  return `${assemblyName}__${compName}`;
}

function getCompOpts(assemblyName, compName) {
  const key = getCompKey(assemblyName, compName);
  if (!compState.has(key)) {
    compState.set(key, { hidden: false, ghost: false });
  }
  return compState.get(key);
}

function makeMaterial(color, ghost = false) {
  return new THREE.MeshStandardMaterial({
    color: new THREE.Color(color || "#9fb4d0"),
    metalness: 0.15,
    roughness: 0.55,
    wireframe: wireframe.checked,
    transparent: ghost,
    opacity: ghost ? 0.25 : 1.0,
    depthWrite: !ghost,
    side: THREE.DoubleSide,
    clippingPlanes: clipAxis === "off" ? [] : [clipPlane],
    clipShadows: true,
  });
}

function addMesh(geometry, color, compKey = null, ghost = false, hidden = false) {
  geometry.computeVertexNormals();
  const mesh = new THREE.Mesh(geometry, makeMaterial(color, ghost));
  mesh.visible = !hidden;
  mesh.userData.compKey = compKey;
  mesh.userData.baseColor = color;
  group.add(mesh);
  loaded.push(mesh);
  return mesh;
}

function computeBounds(geometries) {
  const box = new THREE.Box3();
  for (const geometry of geometries) {
    geometry.computeBoundingBox();
    box.union(geometry.boundingBox);
  }
  return box;
}

function placeScene(geometries, resetCamera = false) {
  sceneBounds = computeBounds(geometries);
  const size = sceneBounds.getSize(new THREE.Vector3());

  if (resetCamera || !lastFittedKey) {
    lastSceneCenter = sceneBounds.getCenter(new THREE.Vector3());
    const radius = Math.max(size.length() / 2, 1);

    group.position.set(
      -lastSceneCenter.x,
      -lastSceneCenter.y,
      -lastSceneCenter.z,
    );
    grid.position.set(0, 0, -size.z / 2);
    axes.position.set(0, 0, -size.z / 2);

    const distance =
      (radius / Math.sin(THREE.MathUtils.degToRad(camera.fov / 2))) * 1.15;
    const direction = new THREE.Vector3(1, -1.2, 0.8).normalize();
    camera.position.copy(direction.multiplyScalar(distance));
    camera.near = Math.max(0.1, distance / 100);
    camera.far = distance * 20;
    camera.updateProjectionMatrix();
    controls.target.set(0, 0, 0);
    controls.update();
  } else {
    // Keep exact camera orbit and reference center on hot-reload
    group.position.set(
      -lastSceneCenter.x,
      -lastSceneCenter.y,
      -lastSceneCenter.z,
    );
  }

  updateClippingPlane();
}

function updateClippingPlane() {
  const active = clipAxis !== "off";
  clipSliderRow.classList.toggle("hidden", !active);
  for (const btn of clipAxisBtns) {
    btn.classList.toggle("active", btn.dataset.axis === clipAxis);
  }
  clipFlipBtn.classList.toggle("active", clipFlip < 0);

  for (const mesh of loaded) {
    mesh.material.clippingPlanes = active ? [clipPlane] : [];
    mesh.material.needsUpdate = true;
  }

  if (!active || sceneBounds.isEmpty()) return;

  const axisIdx = clipAxis === "x" ? "x" : clipAxis === "y" ? "y" : "z";
  const minVal = sceneBounds.min[axisIdx];
  const maxVal = sceneBounds.max[axisIdx];
  const midVal = (minVal + maxVal) / 2;
  const halfSpan = Math.max((maxVal - minVal) / 2, 0.5);

  const norm = parseFloat(clipSlider.value) || 0;
  const cadCoord = midVal + norm * halfSpan;
  clipVal.textContent = `${cadCoord.toFixed(1)} mm`;

  const worldCoord = cadCoord - lastSceneCenter[axisIdx];
  const normal = new THREE.Vector3(
    clipAxis === "x" ? -clipFlip : 0,
    clipAxis === "y" ? -clipFlip : 0,
    clipAxis === "z" ? -clipFlip : 0,
  );
  clipPlane.set(normal, clipFlip * worldCoord);
}

// --- loading -------------------------------------------------------------

function selectionKey() {
  return current ? `${current.type}:${current.name}` : null;
}

function loadPart(part) {
  const generation = ++loadGeneration;
  const key = selectionKey();
  const shouldFit = key !== lastFittedKey;
  clearScene();
  loader.load(
    `${part.mesh}?t=${Date.now()}`,
    (geometry) => {
      if (generation !== loadGeneration) return;
      addMesh(geometry, part.color);
      loadedGeometries = [geometry];
      placeScene(loadedGeometries, shouldFit);
      lastFittedKey = key;
      updateHud(part);
    },
    undefined,
    (err) => showError(`Could not load ${part.name}\n\n${err}`),
  );
}

function loadAssembly(assembly) {
  const generation = ++loadGeneration;
  const key = selectionKey();
  const shouldFit = key !== lastFittedKey;
  clearScene();
  const geometries = [];
  const components = assembly.components.filter((c) => c.status === "ok");
  if (!components.length) return;

  let pending = components.length;
  for (const component of components) {
    const opts = getCompOpts(assembly.name, component.name);
    const compKey = getCompKey(assembly.name, component.name);
    loader.load(
      `${component.mesh}?t=${Date.now()}`,
      (geometry) => {
        if (generation !== loadGeneration) return;
        addMesh(geometry, component.color, compKey, opts.ghost, opts.hidden);
        geometries.push(geometry);
        if (--pending === 0) {
          loadedGeometries = geometries;
          placeScene(loadedGeometries, shouldFit);
          lastFittedKey = key;
          updateHud(assembly);
        }
      },
      undefined,
      (err) => showError(`Could not load ${component.name}\n\n${err}`),
    );
  }
}

function applyCompVisuals(assemblyName, compName) {
  const key = getCompKey(assemblyName, compName);
  const opts = getCompOpts(assemblyName, compName);
  for (const mesh of loaded) {
    if (mesh.userData.compKey === key) {
      mesh.visible = !opts.hidden;
      mesh.material.transparent = opts.ghost;
      mesh.material.opacity = opts.ghost ? 0.25 : 1.0;
      mesh.material.depthWrite = !opts.ghost;
      mesh.material.needsUpdate = true;
    }
  }
}

// --- hud -----------------------------------------------------------------

function updateHud(item) {
  if (item.components) {
    const ok = item.components.filter((c) => c.status === "ok").length;
    hud.innerHTML = `
      <strong>${item.name}</strong>
      <span>${ok} components</span>
      <span>${item.bbox.map((v) => v.toFixed(1)).join(" × ")} mm</span>
      <span>${item.duration_ms.toFixed(0)} ms</span>`;
    return;
  }
  const bbox = item.bbox.map((v) => v.toFixed(1)).join(" × ");
  hud.innerHTML = `
    <strong>${item.name}</strong>
    <span>${item.volume_mm3.toLocaleString()} mm³</span>
    <span>${bbox} mm</span>
    <span>${item.triangles.toLocaleString()} tris</span>
    <span>${item.duration_ms.toFixed(0)} ms</span>`;
}

// --- sidebar -------------------------------------------------------------

function findItem(selection) {
  if (!selection) return null;
  const list =
    selection.type === "part" ? state.parts : state.assemblies || [];
  return list.find((item) => item.name === selection.name);
}

function isActive(type, name) {
  return current && current.type === type && current.name === name;
}

function renderSidebar() {
  partsList.innerHTML = "";

  const addSection = (title, items, type) => {
    if (!items.length) return;
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

      li.innerHTML = `
        <span class="dot"></span>
        <span class="name"></span>
        <span class="meta"></span>`;
      li.querySelector(".name").textContent = item.name;
      li.querySelector(".meta").textContent = meta;

      li.addEventListener("click", () => {
        if (item.status !== "ok") {
          showError(`${item.name}\n\n${item.error || "build failed"}`);
          return;
        }
        current = { type, name: item.name };
        activeSubComp = null;
        paramTab = "active";
        renderSidebar();
        renderParamSheet(true);
        paramSheet.scrollTop = 0;
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
            (activeSubComp === comp.name ? " active-comp" : "");
          compLi.title = `Click to focus ${comp.name} parameters`;

          compLi.addEventListener("click", (e) => {
            e.stopPropagation();
            activeSubComp = activeSubComp === comp.name ? null : comp.name;
            paramTab = "active";
            renderSidebar();
            renderParamSheet(true);
            paramSheet.scrollTop = 0;
          });

          const swatch = document.createElement("span");
          swatch.className = "comp-swatch";
          swatch.style.background = comp.color || "#9fb4d0";

          const cname = document.createElement("span");
          cname.className = "comp-name";
          cname.textContent = comp.name;

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

// --- parameter spreadsheet & live sliders --------------------------------

function postParamPayload(payload) {
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

function activeModuleShort() {
  const item = findItem(current);
  if (!item || !item.module) return null;
  return item.module.split(".").pop();
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

function activeScopeLabel() {
  if (activeSubComp) return activeSubComp;
  if (current) return current.name;
  return activeModuleShort();
}

function renderParamTabs() {
  const pstate = state.params || { modules: {}, custom: [] };
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
    btn.className = "param-tab" + (paramTab === t.id ? " active" : "");
    btn.textContent = t.label;
    btn.addEventListener("click", () => {
      paramTab = t.id;
      renderParamTabs();
      renderParamSheet(true);
    });
    paramTabs.appendChild(btn);
  }

  // Update preset selector
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
  const pstate = state.params || { modules: {}, custom: [] };
  const modules = pstate.modules || {};
  const custom = pstate.custom || [];
  const partScopes = pstate.part_scopes || {};
  const curMod = activeModuleShort();

  // Check if Active tab has a specific part/component scope (e.g. drone_magnet)
  const targetPartName =
    paramTab === "active"
      ? activeSubComp || (current && current.type === "part" ? current.name : null)
      : null;
  const scopedKeyList =
    targetPartName && partScopes[targetPartName]
      ? new Set(partScopes[targetPartName])
      : null;

  let targetShorts = [];
  if (scopedKeyList) {
    targetShorts = Object.keys(modules);
  } else if (paramTab === "all") {
    targetShorts = Object.keys(modules);
  } else if (paramTab === "active") {
    if (curMod && modules[curMod]) {
      targetShorts = [curMod];
    } else {
      targetShorts = Object.keys(modules);
    }
  } else if (modules[paramTab]) {
    targetShorts = [paramTab];
  } else {
    targetShorts = Object.keys(modules);
  }

  const filter = paramFilterText.trim().toLowerCase();
  const sections = [];

  // Custom helper variables section
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

  // Group each module's fields by their section group
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
      byGroup.get(gname).push({ ...f, moduleShort: short, showModuleTag: multiModule });
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

  // Only overwrite expression input if the user isn't actively typing in it
  if (document.activeElement !== exprInput) {
    exprInput.value = field.expr;
  }

  // Update control cell (slider vs bound badge vs error badge)
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
      badge.title = `Bound formula: ${field.expr}` + (field.deps?.length ? `\nDepends on: ${field.deps.join(", ")}` : "");
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

  // Update action button (reset or delete custom)
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

  // 1. Parameter Name + Doc cell
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

  // Prevent mousedown from blurring an active formula input so click-to-insert works!
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
      return;
    }
  });

  const docEl = document.createElement("span");
  docEl.className = "param-doc";
  docEl.textContent = field.doc || "";
  docEl.title = field.doc || "";

  nameCell.append(nameBtn, docEl);

  // 2. Expression / Binding input cell
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

  // 3. Control / Value cell
  const controlCell = document.createElement("div");
  controlCell.className = "control-cell";

  // 4. Action cell
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

function renderParamSheet(forceRebuildDom = false) {
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

// --- errors --------------------------------------------------------------

function showError(text) {
  errorText.textContent = text;
  errorBox.classList.remove("hidden");
}

function hideError() {
  errorBox.classList.add("hidden");
}

document.getElementById("error-close").addEventListener("click", hideError);

// --- state ---------------------------------------------------------------

function applyState(next) {
  state = next;

  const all = [...state.parts, ...(state.assemblies || [])];
  const ok = all.filter((p) => p.status === "ok");
  if (!current || !ok.some((p) => p.name === current.name)) {
    const firstAssembly = (state.assemblies || []).find(
      (p) => p.status === "ok",
    );
    const firstPart = state.parts.find((p) => p.status === "ok");
    current = firstAssembly
      ? { type: "assembly", name: firstAssembly.name }
      : firstPart
        ? { type: "part", name: firstPart.name }
        : null;
  }

  // ?select=<name> pins the view, for screenshots.
  const requested = params.get("select");
  if (requested) {
    const part = state.parts.find((p) => p.name === requested);
    const assembly = (state.assemblies || []).find((p) => p.name === requested);
    if (part && part.status === "ok") {
      current = { type: "part", name: requested };
    } else if (assembly && assembly.status === "ok") {
      current = { type: "assembly", name: requested };
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

  if (current && state.built_at !== lastBuiltAt) {
    lastBuiltAt = state.built_at;
    const item = findItem(current);
    if (item) {
      if (current.type === "part") loadPart(item);
      else loadAssembly(item);
    }
  }
}

function connect() {
  if (params.get("static") === "1") {
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

// --- controls ------------------------------------------------------------

document.getElementById("rebuild").addEventListener("click", () => {
  fetch("/api/rebuild", { method: "POST" });
});

fitBtn.addEventListener("click", () => {
  if (loadedGeometries.length) {
    placeScene(loadedGeometries, true);
  }
});

wireframe.addEventListener("change", () => {
  for (const mesh of loaded) mesh.material.wireframe = wireframe.checked;
});

for (const btn of clipAxisBtns) {
  btn.addEventListener("click", () => {
    const nextAxis = btn.dataset.axis;
    if (clipAxis !== nextAxis) {
      clipAxis = nextAxis;
      clipSlider.value = "0";
    }
    updateClippingPlane();
  });
}

clipFlipBtn.addEventListener("click", () => {
  clipFlip = -clipFlip;
  updateClippingPlane();
});

clipSlider.addEventListener("input", () => {
  updateClippingPlane();
});

// Parameter panel controls
paramCollapseBtn.addEventListener("click", () => {
  paramPanel.classList.add("hidden");
  paramOpenBtn.classList.remove("hidden");
  resize();
});

paramOpenBtn.addEventListener("click", () => {
  paramPanel.classList.remove("hidden");
  paramOpenBtn.classList.add("hidden");
  resize();
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

// --- loop ----------------------------------------------------------------

function resize() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (width === 0 || height === 0) return;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

new ResizeObserver(resize).observe(canvas);
resize();

renderer.setAnimationLoop(() => {
  controls.update();
  renderer.render(scene, camera);
});

connect();
