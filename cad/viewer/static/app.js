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
camera.position.set(90, 70, 110);

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.08;

scene.add(new THREE.HemisphereLight(0xdfe8ff, 0x1a1f28, 1.1));

const key = new THREE.DirectionalLight(0xffffff, 2.0);
key.position.set(80, 120, 90);
scene.add(key);

const fill = new THREE.DirectionalLight(0x88aaff, 0.7);
fill.position.set(-90, 40, -70);
scene.add(fill);

const grid = new THREE.GridHelper(200, 20, 0x2b3240, 0x1a1f27);
grid.material.transparent = true;
grid.material.opacity = 0.7;
scene.add(grid);
scene.add(new THREE.AxesHelper(30));

const group = new THREE.Group();
scene.add(group);

const loader = new STLLoader();
let mesh = null;
let currentName = null;
let lastBuiltAt = 0;
let state = { parts: [], duration_ms: 0, built_at: 0 };

// --- mesh ----------------------------------------------------------------

function fitCamera(geometry) {
  geometry.computeBoundingSphere();
  const radius = geometry.boundingSphere?.radius || 50;
  const distance =
    (radius / Math.sin(THREE.MathUtils.degToRad(camera.fov / 2))) * 1.15;
  const direction = new THREE.Vector3(1, 0.75, 1.2).normalize();
  camera.position.copy(direction.multiplyScalar(distance));
  camera.near = Math.max(0.1, distance / 100);
  camera.far = distance * 20;
  camera.updateProjectionMatrix();
  controls.target.set(0, 0, 0);
  controls.update();
}

function loadPart(name) {
  const part = state.parts.find((p) => p.name === name);
  if (!part || part.status !== "ok") return;

  loader.load(
    `${part.mesh}?t=${Date.now()}`,
    (geometry) => {
      geometry.computeVertexNormals();
      geometry.center();

      if (mesh) {
        group.remove(mesh);
        mesh.geometry.dispose();
        mesh.material.dispose();
      }

      const material = new THREE.MeshStandardMaterial({
        color: 0x9fb4d0,
        metalness: 0.15,
        roughness: 0.55,
        wireframe: wireframe.checked,
      });
      mesh = new THREE.Mesh(geometry, material);
      group.add(mesh);

      fitCamera(geometry);
      updateHud(part);
    },
    undefined,
    (err) => showError(`Could not load ${name}\n\n${err}`),
  );
}

function updateHud(part) {
  const bbox = part.bbox.map((v) => v.toFixed(1)).join(" × ");
  hud.innerHTML = `
    <strong>${part.name}</strong>
    <span>${part.volume_mm3.toLocaleString()} mm³</span>
    <span>${bbox} mm</span>
    <span>${part.triangles.toLocaleString()} tris</span>
    <span>${part.duration_ms.toFixed(0)} ms</span>`;
}

// --- sidebar -------------------------------------------------------------

function renderSidebar() {
  partsList.innerHTML = "";

  for (const part of state.parts) {
    const li = document.createElement("li");
    li.className = "part" + (part.name === currentName ? " active" : "");
    li.dataset.status = part.status;

    const meta =
      part.status === "ok"
        ? `${part.volume_mm3.toLocaleString()} mm³ · ${part.duration_ms.toFixed(0)} ms`
        : "build failed";

    li.innerHTML = `
      <span class="dot"></span>
      <span class="name"></span>
      <span class="meta"></span>`;
    li.querySelector(".name").textContent = part.name;
    li.querySelector(".meta").textContent = meta;

    li.addEventListener("click", () => {
      if (part.status === "ok") {
        currentName = part.name;
        renderSidebar();
        loadPart(part.name);
      } else {
        showError(`${part.name}\n\n${part.error || "build failed"}`);
      }
    });

    partsList.appendChild(li);
  }

  const ok = state.parts.filter((p) => p.status === "ok").length;
  const bad = state.parts.length - ok;
  const when = state.built_at
    ? new Date(state.built_at * 1000).toLocaleTimeString()
    : "—";

  summary.innerHTML =
    `<span class="${bad ? "bad" : "good"}">` +
    `${bad ? `${bad} failed` : "all ok"}</span>` +
    ` · ${ok} part${ok === 1 ? "" : "s"}` +
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

  const ok = state.parts.filter((p) => p.status === "ok");
  if (!ok.some((p) => p.name === currentName)) {
    currentName = ok.length ? ok[0].name : null;
  }

  renderSidebar();

  const errors = state.parts.filter((p) => p.status === "error");
  if (errors.length) {
    showError(errors.map((e) => `${e.name}\n\n${e.error}`).join("\n\n"));
  } else {
    hideError();
  }

  if (currentName && state.built_at !== lastBuiltAt) {
    lastBuiltAt = state.built_at;
    loadPart(currentName);
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
  if (mesh) mesh.material.wireframe = wireframe.checked;
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
