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

// --- scene ---------------------------------------------------------------

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x0e1116);

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
let current = null;
let lastBuiltAt = 0;
let loadGeneration = 0;
let state = { parts: [], assemblies: [], duration_ms: 0, built_at: 0 };

// --- scene management ----------------------------------------------------

function clearScene() {
  for (const mesh of loaded) {
    group.remove(mesh);
    mesh.geometry.dispose();
    mesh.material.dispose();
  }
  loaded = [];
  group.position.set(0, 0, 0);
}

function makeMaterial(color) {
  return new THREE.MeshStandardMaterial({
    color: new THREE.Color(color || "#9fb4d0"),
    metalness: 0.15,
    roughness: 0.55,
    wireframe: wireframe.checked,
  });
}

function addMesh(geometry, color) {
  geometry.computeVertexNormals();
  const mesh = new THREE.Mesh(geometry, makeMaterial(color));
  group.add(mesh);
  loaded.push(mesh);
  return mesh;
}

function fitScene(geometries) {
  const box = new THREE.Box3();
  for (const geometry of geometries) {
    geometry.computeBoundingBox();
    box.union(geometry.boundingBox);
  }
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const radius = Math.max(size.length() / 2, 1);

  // Centre the whole scene, not each component.
  group.position.set(-center.x, -center.y, -center.z);
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
}

// --- loading -------------------------------------------------------------

function loadPart(part) {
  const generation = ++loadGeneration;
  clearScene();
  loader.load(
    `${part.mesh}?t=${Date.now()}`,
    (geometry) => {
      if (generation !== loadGeneration) return;
      addMesh(geometry, part.color);
      fitScene([geometry]);
      updateHud(part);
    },
    undefined,
    (err) => showError(`Could not load ${part.name}\n\n${err}`),
  );
}

function loadAssembly(assembly) {
  const generation = ++loadGeneration;
  clearScene();
  const geometries = [];
  const components = assembly.components.filter((c) => c.status === "ok");
  if (!components.length) return;

  let pending = components.length;
  for (const component of components) {
    loader.load(
      `${component.mesh}?t=${Date.now()}`,
      (geometry) => {
        if (generation !== loadGeneration) return;
        addMesh(geometry, component.color);
        geometries.push(geometry);
        if (--pending === 0) {
          fitScene(geometries);
          updateHud(assembly);
        }
      },
      undefined,
      (err) => showError(`Could not load ${component.name}\n\n${err}`),
    );
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
      const li = document.createElement("li");
      li.className = "part" + (isActive(type, item.name) ? " active" : "");
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
        renderSidebar();
        if (type === "part") loadPart(item);
        else loadAssembly(item);
      });

      partsList.appendChild(li);
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

  renderSidebar();

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

wireframe.addEventListener("change", () => {
  for (const mesh of loaded) mesh.material.wireframe = wireframe.checked;
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
