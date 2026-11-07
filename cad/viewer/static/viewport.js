/**
 * 3D viewport, Three.js scene, STL loader, section clipping plane, and HUD.
 */

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { getCompKey, getCompOpts, selectionKey, urlParams } from "./state.js";

const canvas = document.getElementById("view");
const hud = document.getElementById("hud");
const wireframe = document.getElementById("wireframe");
const fitBtn = document.getElementById("fit");
const clipSliderRow = document.getElementById("clip-slider-row");
const clipSlider = document.getElementById("clip-slider");
const clipVal = document.getElementById("clip-val");
const clipFlipBtn = document.getElementById("clip-flip");
const clipAxisBtns = document.querySelectorAll(".clip-axes .clip-btn");

if (urlParams.get("wireframe") === "1") wireframe.checked = true;

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

const key = new THREE.DirectionalLight(0xffffff, 1.8);
key.position.set(80, -120, 100);
scene.add(key);

const fill = new THREE.DirectionalLight(0x88aaff, 0.6);
fill.position.set(-90, -40, 40);
scene.add(fill);

const rim = new THREE.DirectionalLight(0xffe0c0, 0.9);
rim.position.set(-80, 120, 80);
scene.add(rim);

const grid = new THREE.GridHelper(200, 20, 0x2b3240, 0x1a1f27);
grid.rotation.x = Math.PI / 2;
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
let lastFittedKey = null;
let lastSceneCenter = new THREE.Vector3();
let sceneBounds = new THREE.Box3();
let loadGeneration = 0;

let clipAxis = urlParams.get("clip") || "off";
let clipFlip = urlParams.get("clip_flip") === "1" ? -1 : 1;
const clipPlane = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0);

let onLoadError = () => {};
export function setViewportErrorHandler(fn) {
  onLoadError = fn;
}

export function clearScene() {
  for (const mesh of loaded) {
    group.remove(mesh);
    mesh.geometry.dispose();
    mesh.material.dispose();
  }
  loaded = [];
  loadedGeometries = [];
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

export function placeScene(geometries, resetCamera = false) {
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
    group.position.set(
      -lastSceneCenter.x,
      -lastSceneCenter.y,
      -lastSceneCenter.z,
    );
  }

  updateClippingPlane();
}

export function updateClippingPlane() {
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

export function loadPart(part) {
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
    (err) => onLoadError(`Could not load ${part.name}\n\n${err}`),
  );
}

export function loadAssembly(assembly) {
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
      (err) => onLoadError(`Could not load ${component.name}\n\n${err}`),
    );
  }
}

export function applyCompVisuals(assemblyName, compName) {
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

export function resizeViewport() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (width === 0 || height === 0) return;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

export function initViewport() {
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

  new ResizeObserver(resizeViewport).observe(canvas);
  resizeViewport();

  renderer.setAnimationLoop(() => {
    controls.update();
    renderer.render(scene, camera);
  });
}
