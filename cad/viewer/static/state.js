/**
 * Shared viewer state and selection helpers.
 */

export const urlParams = new URLSearchParams(location.search);

export const store = {
  state: {
    parts: [],
    assemblies: [],
    duration_ms: 0,
    built_at: 0,
    params: { modules: {}, custom: [], part_scopes: {}, presets: [] },
  },
  current: null, // { type: "part" | "assembly", name: string }
  activeSubComp: null, // string | null (focused component inside an assembly)
  paramTab: urlParams.get("tab") || "active", // "active" | "all" | <shortModule>
  compState: new Map(), // "<assembly>__<comp>" -> { hidden: bool, ghost: bool }
};

export function selectionKey() {
  return store.current ? `${store.current.type}:${store.current.name}` : null;
}

export function findItem(selection = store.current) {
  if (!selection) return null;
  const list =
    selection.type === "part"
      ? store.state.parts
      : store.state.assemblies || [];
  return list.find((item) => item.name === selection.name) || null;
}

export function isActive(type, name) {
  return (
    store.current &&
    store.current.type === type &&
    store.current.name === name
  );
}

export function activeModuleShort() {
  const item = findItem(store.current);
  if (!item || !item.module) return null;
  return item.module.split(".").pop();
}

export function activeScopeLabel() {
  if (store.activeSubComp) return store.activeSubComp;
  if (store.current) return store.current.name;
  return activeModuleShort();
}

export function getCompKey(assemblyName, compName) {
  return `${assemblyName}__${compName}`;
}

export function getCompOpts(assemblyName, compName) {
  const key = getCompKey(assemblyName, compName);
  if (!store.compState.has(key)) {
    store.compState.set(key, { hidden: false, ghost: false });
  }
  return store.compState.get(key);
}
