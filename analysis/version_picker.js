/* Shared Lean Repo Version Picker & Cross-Page State Helper */
(function (global) {
  "use strict";

  const STORAGE_KEY = "rh_lean_version";

  /*VERSIONS_MANIFEST_START*/
  const MANIFEST = [
    {
      "id": "community-307cef33",
      "label": "Community simplified (307cef33 · 2026-11-24)",
      "short_label": "307cef33 (2026-11-24)",
      "date": "2026-11-24",
      "repo_name": "leanprover-community/riemann-hypothesis",
      "repo_url": "https://github.com/leanprover-community/riemann-hypothesis",
      "commit": "307cef33f046955ee79dba47e0d828d06496d75f",
      "source_blob_base": "https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/",
      "source_tree_base": "https://github.com/leanprover-community/riemann-hypothesis/tree/307cef33f046955ee79dba47e0d828d06496d75f/src/",
      "is_default": true
    },
    {
      "id": "original-2026-11-20",
      "label": "Original submission (2026-11-20)",
      "short_label": "Original (2026-11-20)",
      "date": "2026-11-20",
      "repo_name": "Original proof (alpo.ge/remark.pdf)",
      "repo_url": "https://github.com/ZacharyVernec/riemann-proof-explorer/tree/main/lean",
      "commit": "original",
      "source_blob_base": "https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/",
      "source_tree_base": "https://github.com/ZacharyVernec/riemann-proof-explorer/tree/main/lean/src/",
      "is_default": false
    }
  ];
  /*VERSIONS_MANIFEST_END*/

  function detectRootPrefix() {
    if (typeof document === "undefined") return "";
    const cs = document.currentScript;
    if (cs && cs.getAttribute) {
      const src = cs.getAttribute("src") || "";
      const idx = src.indexOf("version_picker.js");
      if (idx >= 0) return src.slice(0, idx);
    }
    const subdirs = [
      "/blueprint/",
      "/interfaces/",
      "/proof_spine/",
      "/dependency_graph/",
      "/published_theorems/",
      "/full_dag/",
      "/codebase_histograms/",
      "/size_treemap/",
    ];
    const p = (global.location && global.location.pathname) || "";
    return subdirs.some((d) => p.includes(d)) ? "../" : "";
  }

  function safeStorageGet(key) {
    try {
      return global.localStorage ? global.localStorage.getItem(key) : null;
    } catch (_) {
      return null;
    }
  }

  function safeStorageSet(key, val) {
    try {
      if (global.localStorage) global.localStorage.setItem(key, val);
    } catch (_) {
      // Ignore storage quota / privacy restrictions
    }
  }

  function byId(id) {
    return MANIFEST.find((v) => v.id === id) || null;
  }

  const DEFAULT_VERSION = MANIFEST.find((v) => v.is_default) || MANIFEST[0];

  function getQueryParam(name) {
    try {
      const search = (global.location && global.location.search) || "";
      if (!search) return null;
      const params = new URLSearchParams(search);
      return params.get(name);
    } catch (_) {
      return null;
    }
  }

  function resolveInitialVersion() {
    const qv = getQueryParam("v");
    if (qv && byId(qv)) {
      safeStorageSet(STORAGE_KEY, qv);
      return byId(qv);
    }
    const sv = safeStorageGet(STORAGE_KEY);
    if (sv && byId(sv)) {
      return byId(sv);
    }
    return DEFAULT_VERSION;
  }

  const rootPrefix = detectRootPrefix();
  let current = resolveInitialVersion();
  let isDefault = current.id === DEFAULT_VERSION.id;

  let switchSeq = 0;
  let activeController = null;
  let foregroundLoadingId = null;
  const changeListeners = [];
  const scriptQueues = new Map();

  function encodeRelPath(relPath) {
    return String(relPath || "")
      .replace(/^\/+/, "")
      .split("/")
      .map((seg) => encodeURIComponent(seg))
      .join("/");
  }

  function versionAssetUrl(relPath, versionId) {
    const vid = versionId || current.id;
    const clean = String(relPath || "").replace(/^\/+/, "");
    return rootPrefix + "versions/" + encodeURIComponent(vid) + "/" + clean;
  }

  function sourceUrl(relPath, lineNo, versionId) {
    const ver = versionId ? (byId(versionId) || current) : current;
    const base = String(ver.source_blob_base || "").replace(/\/+$/, "");
    const clean = String(relPath || "").replace(/^\/+/, "");
    const frag = lineNo ? "#L" + String(lineNo) : "";
    if (!base) return encodeRelPath(clean) + frag;
    return base + "/" + encodeRelPath(clean) + frag;
  }

  function treeUrl(relPath, versionId) {
    const ver = versionId ? (byId(versionId) || current) : current;
    const base = String(ver.source_tree_base || ver.repo_url || "").replace(/\/+$/, "");
    const clean = String(relPath || "").replace(/^\/+/, "");
    if (!base) return encodeRelPath(clean);
    return clean ? base + "/" + encodeRelPath(clean) : base;
  }

  function buildUrlWithVersion(href, versionId) {
    if (!href) return href;
    const trimmed = href.trim();
    if (
      !trimmed ||
      trimmed.startsWith("#") ||
      /^(https?:|mailto:|javascript:|data:|blob:|file:)/i.test(trimmed)
    ) {
      return href;
    }
    const hashIdx = trimmed.indexOf("#");
    const hash = hashIdx >= 0 ? trimmed.slice(hashIdx) : "";
    const beforeHash = hashIdx >= 0 ? trimmed.slice(0, hashIdx) : trimmed;
    const qIdx = beforeHash.indexOf("?");
    const basePath = qIdx >= 0 ? beforeHash.slice(0, qIdx) : beforeHash;
    const rawQuery = qIdx >= 0 ? beforeHash.slice(qIdx + 1) : "";

    // Propagate version only across internal HTML pages
    if (!/\.html$/i.test(basePath) && basePath !== "./" && !basePath.endsWith("/")) {
      return href;
    }

    const params = new URLSearchParams(rawQuery);
    if (versionId && versionId !== DEFAULT_VERSION.id) {
      params.set("v", versionId);
    } else {
      params.delete("v");
    }
    const qs = params.toString();
    return basePath + (qs ? "?" + qs : "") + hash;
  }

  function buildNextLocationUrl(versionId) {
    if (!global.location) return "";
    const href = String(global.location.href || "");
    const hashIdx = href.indexOf("#");
    const hash = hashIdx >= 0 ? href.slice(hashIdx) : "";
    const beforeHash = hashIdx >= 0 ? href.slice(0, hashIdx) : href;
    const qIdx = beforeHash.indexOf("?");
    const base = qIdx >= 0 ? beforeHash.slice(0, qIdx) : beforeHash;
    const params = new URLSearchParams(qIdx >= 0 ? beforeHash.slice(qIdx + 1) : "");
    if (versionId && versionId !== DEFAULT_VERSION.id) {
      params.set("v", versionId);
    } else {
      params.delete("v");
    }
    const qs = params.toString();
    return base + (qs ? "?" + qs : "") + hash;
  }

  function isAllPreloaded(ctrl) {
    if (!ctrl) return false;
    return MANIFEST.every((v) => ctrl.loadStates.get(v.id) === "ready");
  }

  function syncPickerUi() {
    if (typeof document === "undefined") return;
    const readyAll = isAllPreloaded(activeController);
    const isBusy = foregroundLoadingId !== null;
    document.querySelectorAll(".rh-vp-select").forEach((sel) => {
      if (sel.value !== current.id) {
        sel.value = current.id;
      }
      sel.title = readyAll ? "All versions loaded — instant switching ready" : "";
    });
    document.querySelectorAll(".rh-vp-status").forEach((st) => {
      if (isBusy) {
        st.textContent = "Loading…";
        st.classList.add("visible");
      } else {
        st.textContent = "";
        st.classList.remove("visible");
      }
    });
  }

  function injectPickerStyles() {
    if (typeof document === "undefined" || !document.head) return;
    if (document.getElementById("rh-version-picker-styles")) return;
    const st = document.createElement("style");
    st.id = "rh-version-picker-styles";
    st.textContent = [
      ".rh-vp-wrap{display:inline-flex;align-items:center;gap:6px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:12.5px;color:#333;}",
      ".rh-vp-label{font-weight:600;color:#555;white-space:nowrap;}",
      ".rh-vp-select{font-family:inherit;font-size:12px;color:#111;background:#fff;border:1px solid #bbb;border-radius:4px;padding:3px 7px;cursor:pointer;max-width:290px;}",
      ".rh-vp-select:hover,.rh-vp-select:focus{border-color:#0056b3;outline:none;}",
      ".rh-vp-status{display:none;font-size:11px;color:#64748b;white-space:nowrap;}",
      ".rh-vp-status.visible{display:inline-block;}",
      ".rh-vp-wrap.rh-vp-compact{font-size:11.5px;gap:4px;}",
      ".rh-vp-wrap.rh-vp-compact .rh-vp-label{font-size:11px;color:#666;}",
      ".rh-vp-wrap.rh-vp-compact .rh-vp-select{font-size:11.5px;padding:2px 6px;border-radius:999px;border-color:#cbd5e1;max-width:210px;}",
      ".rh-vp-wrap.rh-vp-compact .rh-vp-status{font-size:10.5px;}",
    ].join("");
    document.head.appendChild(st);
  }

  function mountPickers(root) {
    if (typeof document === "undefined") return;
    const container = root || document;
    const slots = container.querySelectorAll("[data-version-picker]");
    if (!slots.length) return;
    injectPickerStyles();
    slots.forEach((slot) => {
      const existingSelect = slot.querySelector(".rh-vp-select");
      if (existingSelect) {
        existingSelect.value = current.id;
        return;
      }

      const mode = slot.getAttribute("data-version-picker") || "standard";
      const isCompact = mode === "compact";
      slot.innerHTML = "";

      const wrap = document.createElement("span");
      wrap.className = "rh-vp-wrap" + (isCompact ? " rh-vp-compact" : "");

      const lbl = document.createElement("label");
      lbl.className = "rh-vp-label";
      const selId = "rh-vp-select-" + Math.random().toString(36).slice(2, 8);
      lbl.setAttribute("for", selId);
      lbl.textContent = isCompact ? "Lean version:" : "Lean repo version:";

      const sel = document.createElement("select");
      sel.className = "rh-vp-select";
      sel.id = selId;
      sel.setAttribute("aria-label", "Lean repository version");
      MANIFEST.forEach((v) => {
        const opt = document.createElement("option");
        opt.value = v.id;
        opt.textContent = isCompact ? (v.short_label || v.label) : v.label;
        if (v.id === current.id) opt.selected = true;
        sel.appendChild(opt);
      });
      sel.addEventListener("change", (ev) => {
        selectVersion(ev.target.value);
      });

      const statusEl = document.createElement("span");
      statusEl.className = "rh-vp-status";
      statusEl.setAttribute("aria-live", "polite");

      wrap.appendChild(lbl);
      wrap.appendChild(sel);
      wrap.appendChild(statusEl);
      slot.appendChild(wrap);
    });
    syncPickerUi();
  }

  function rewriteLinks(root, versionId) {
    if (typeof document === "undefined") return;
    const container = root || document;
    const vid = versionId || current.id;

    container.querySelectorAll("a[href]").forEach((a) => {
      if (a.hasAttribute("data-version-ignore")) return;
      const vAsset = a.getAttribute("data-version-href");
      if (vAsset) {
        a.setAttribute("href", versionAssetUrl(vAsset, vid));
        return;
      }
      const orig = a.getAttribute("data-orig-href") || a.getAttribute("href");
      if (!a.hasAttribute("data-orig-href")) {
        a.setAttribute("data-orig-href", orig);
      }
      const rewritten = buildUrlWithVersion(orig, vid);
      if (rewritten !== a.getAttribute("href")) {
        a.setAttribute("href", rewritten);
      }
    });

    container.querySelectorAll("[data-version-src]").forEach((el) => {
      const rel = el.getAttribute("data-version-src");
      if (rel) el.setAttribute("src", versionAssetUrl(rel, vid));
    });
  }

  function pumpScriptQueue(queueKey) {
    const q = scriptQueues.get(queueKey);
    if (!q || q.active || q.items.length === 0) return;

    const item = q.items.shift();
    q.active = true;

    const parent = document.head || document.body || document.documentElement;
    if (!parent) {
      q.active = false;
      item.reject(new Error("Missing document root for script injection: " + item.url));
      pumpScriptQueue(queueKey);
      return;
    }

    try {
      delete global[item.globalVar];
    } catch (_) {
      global[item.globalVar] = undefined;
    }

    const script = document.createElement("script");
    script.src = item.url;
    script.async = false;

    const cleanup = () => {
      script.onload = null;
      script.onerror = null;
      if (script.parentNode) {
        script.parentNode.removeChild(script);
      }
    };

    script.onload = function () {
      const val = global[item.globalVar];
      try {
        delete global[item.globalVar];
      } catch (_) {
        global[item.globalVar] = undefined;
      }
      cleanup();
      q.active = false;
      item.resolve(val);
      pumpScriptQueue(queueKey);
    };

    script.onerror = function () {
      cleanup();
      q.active = false;
      item.reject(
        new Error(
          "Failed to load versioned dataset (" +
            item.url +
            ") for Lean version '" +
            item.version.id +
            "'."
        )
      );
      pumpScriptQueue(queueKey);
    };

    parent.appendChild(script);
  }

  function enqueueScriptLoad(relSubpath, globalVar, version, priority) {
    if (typeof document === "undefined") {
      return Promise.reject(new Error("Document unavailable for script loading."));
    }
    const queueKey = relSubpath + "\0" + globalVar;
    let q = scriptQueues.get(queueKey);
    if (!q) {
      q = { active: false, items: [] };
      scriptQueues.set(queueKey, q);
    }

    const existingIdx = q.items.findIndex((it) => it.version.id === version.id);
    if (existingIdx >= 0) {
      const existing = q.items[existingIdx];
      if (priority && !existing.priority) {
        existing.priority = true;
        q.items.splice(existingIdx, 1);
        const insertIdx = q.items.findIndex((it) => !it.priority);
        if (insertIdx >= 0) q.items.splice(insertIdx, 0, existing);
        else q.items.push(existing);
      }
      return existing.promise;
    }

    const url = versionAssetUrl(relSubpath, version.id);
    let resFn;
    let rejFn;
    const promise = new Promise((resolve, reject) => {
      resFn = resolve;
      rejFn = reject;
    });
    const entry = {
      url,
      version,
      relSubpath,
      globalVar,
      priority: Boolean(priority),
      resolve: resFn,
      reject: rejFn,
      promise,
    };

    if (entry.priority) {
      const insertIdx = q.items.findIndex((it) => !it.priority);
      if (insertIdx >= 0) q.items.splice(insertIdx, 0, entry);
      else q.items.push(entry);
    } else {
      q.items.push(entry);
    }

    pumpScriptQueue(queueKey);
    return promise;
  }

  function promoteQueuedScript(relSubpath, globalVar, versionId) {
    const queueKey = relSubpath + "\0" + globalVar;
    const q = scriptQueues.get(queueKey);
    if (!q) return;
    const idx = q.items.findIndex((it) => it.version.id === versionId);
    if (idx < 0 || q.items[idx].priority) return;
    const [entry] = q.items.splice(idx, 1);
    entry.priority = true;
    const insertIdx = q.items.findIndex((it) => !it.priority);
    if (insertIdx >= 0) q.items.splice(insertIdx, 0, entry);
    else q.items.push(entry);
  }

  function waitNextFrame() {
    if (typeof global.requestAnimationFrame === "function") {
      return new Promise((resolve) => global.requestAnimationFrame(() => resolve()));
    }
    return new Promise((resolve) => setTimeout(resolve, 16));
  }

  function waitForIdle(fallbackDelayMs) {
    const delay = typeof fallbackDelayMs === "number" ? fallbackDelayMs : 150;
    if (typeof global.requestIdleCallback === "function") {
      return new Promise((resolve) => {
        global.requestIdleCallback(() => resolve(), { timeout: 1000 });
      });
    }
    return new Promise((resolve) => setTimeout(resolve, delay));
  }

  function showDefaultLoadError(err) {
    const msg = (err && err.message) ? err.message : String(err);
    console.error(msg);
    if (typeof document === "undefined") return;
    const loadingEl = document.getElementById("loading");
    if (loadingEl) {
      loadingEl.textContent = msg;
      loadingEl.style.color = "#b91c1c";
      loadingEl.style.display = "block";
    } else if (document.body) {
      let banner = document.getElementById("rh-version-error-banner");
      if (!banner) {
        banner = document.createElement("div");
        banner.id = "rh-version-error-banner";
        banner.style.cssText =
          "margin:16px auto;max-width:720px;padding:12px 16px;background:#fef2f2;border:1px solid #fca5a5;color:#991b1b;border-radius:6px;font-family:sans-serif;font-size:13px;";
        document.body.prepend(banner);
      }
      banner.textContent = msg;
    }
  }

  function clearDefaultLoadError() {
    if (typeof document === "undefined") return;
    const banner = document.getElementById("rh-version-error-banner");
    if (banner && banner.parentNode) {
      banner.parentNode.removeChild(banner);
    }
  }

  function ensureVersionLoaded(ctrl, version, opts) {
    const isBackground = Boolean(opts && opts.isBackground);
    if (ctrl.preparedCache.has(version.id)) {
      ctrl.loadStates.set(version.id, "ready");
      return Promise.resolve(ctrl.preparedCache.get(version.id));
    }
    if (ctrl.inFlightPromises.has(version.id)) {
      if (!isBackground) {
        promoteQueuedScript(ctrl.relSubpath, ctrl.globalVar, version.id);
      }
      return ctrl.inFlightPromises.get(version.id);
    }

    ctrl.loadStates.set(version.id, "loading");
    const run = (async () => {
      let raw;
      if (typeof ctrl.options.customLoad === "function") {
        raw = await ctrl.options.customLoad(version, { isBackground });
      }
      if (raw === undefined) {
        raw = await enqueueScriptLoad(ctrl.relSubpath, ctrl.globalVar, version, !isBackground);
      }
      const prepared = typeof ctrl.options.prepare === "function"
        ? await ctrl.options.prepare(raw, version, { isBackground })
        : raw;
      ctrl.preparedCache.set(version.id, prepared);
      ctrl.loadStates.set(version.id, "ready");
      return prepared;
    })();

    const tracked = run.then(
      (val) => {
        ctrl.inFlightPromises.delete(version.id);
        syncPickerUi();
        return val;
      },
      (err) => {
        ctrl.inFlightPromises.delete(version.id);
        ctrl.loadStates.set(version.id, "error");
        syncPickerUi();
        throw err;
      }
    );

    ctrl.inFlightPromises.set(version.id, tracked);
    return tracked;
  }

  async function runBackgroundPreload(ctrl) {
    try {
      await waitNextFrame();
      await waitNextFrame();
      await waitForIdle(150);

      for (const ver of MANIFEST) {
        if (ctrl !== activeController) break;
        if (ctrl.preparedCache.has(ver.id)) continue;

        while (foregroundLoadingId !== null) {
          const inflightFg = ctrl.inFlightPromises.get(foregroundLoadingId);
          if (inflightFg) {
            try {
              await inflightFg;
            } catch (_) {
              // Foreground failure already handled by foreground flow
            }
          } else {
            break;
          }
          await waitForIdle(80);
        }

        if (ctrl.preparedCache.has(ver.id)) continue;
        await waitForIdle(80);
        if (ctrl.preparedCache.has(ver.id)) continue;

        try {
          await ensureVersionLoaded(ctrl, ver, { isBackground: true });
        } catch (err) {
          console.warn("Background preload failed for Lean version '" + ver.id + "':", err);
        }
      }
    } finally {
      syncPickerUi();
      ctrl.resolveAllPreloaded();
    }
  }

  function scheduleBackgroundPreload(ctrl) {
    if (ctrl.preloadStarted) return;
    ctrl.preloadStarted = true;
    runBackgroundPreload(ctrl);
  }

  async function applySwitch(ctrl, targetVer, opts) {
    const isInitial = Boolean(opts && opts.isInitial);
    const mySeq = opts.mySeq;
    const wasCached = ctrl.preparedCache.has(targetVer.id);

    if (!wasCached) {
      foregroundLoadingId = targetVer.id;
      syncPickerUi();
      if (!isInitial && typeof ctrl.options.onLoading === "function") {
        try {
          ctrl.options.onLoading(targetVer);
        } catch (err) {
          console.error("onLoading hook error:", err);
        }
      }
    }

    try {
      const prepared = await ensureVersionLoaded(ctrl, targetVer, { isBackground: false });
      if (foregroundLoadingId === targetVer.id) {
        foregroundLoadingId = null;
        syncPickerUi();
      }
      if (mySeq !== switchSeq || ctrl !== activeController) return;

      clearDefaultLoadError();
      try {
        await ctrl.onReady(prepared, targetVer, { isInitial });
      } catch (err) {
        console.error(
          "Failed initializing viewer from " + versionAssetUrl(ctrl.relSubpath, targetVer.id) + ":",
          err
        );
      }
    } catch (err) {
      if (foregroundLoadingId === targetVer.id) {
        foregroundLoadingId = null;
        syncPickerUi();
      }
      if (mySeq === switchSeq && ctrl === activeController) {
        if (typeof ctrl.options.onError === "function") {
          ctrl.options.onError(err, targetVer);
        } else {
          showDefaultLoadError(err);
        }
      }
    } finally {
      if (isInitial) {
        scheduleBackgroundPreload(ctrl);
      }
    }
  }

  function loadDataScript(relSubpath, globalVar, callback, options) {
    if (typeof document === "undefined") return;
    let resolveAll;
    const allPreloadedPromise = new Promise((resolve) => {
      resolveAll = resolve;
    });
    const loadStates = new Map();
    MANIFEST.forEach((v) => loadStates.set(v.id, "idle"));

    const ctrl = {
      relSubpath,
      globalVar,
      onReady: callback,
      options: options || {},
      preparedCache: new Map(),
      inFlightPromises: new Map(),
      loadStates,
      preloadStarted: false,
      allPreloadedPromise,
      resolveAllPreloaded: resolveAll,
    };
    activeController = ctrl;
    const mySeq = ++switchSeq;
    applySwitch(ctrl, current, { isInitial: true, mySeq });
  }

  function selectVersion(newId, opts) {
    const target = byId(newId);
    if (!target) return Promise.resolve();
    const pushHistory = !opts || opts.pushHistory !== false;

    safeStorageSet(STORAGE_KEY, target.id);
    current = target;
    isDefault = current.id === DEFAULT_VERSION.id;

    if (global.location) {
      const href = String(global.location.href || "");
      const nextUrl = buildNextLocationUrl(target.id);
      if (activeController || changeListeners.length > 0) {
        if (pushHistory && nextUrl && nextUrl !== href && global.history && typeof global.history.pushState === "function") {
          try {
            global.history.pushState({ v: target.id }, "", nextUrl);
          } catch (_) {
            // Ignore history restriction on file:// origins
          }
        }
      } else {
        if (nextUrl === href) {
          global.location.reload();
        } else if (nextUrl) {
          global.location.href = nextUrl;
        }
        return Promise.resolve();
      }
    }

    mountPickers();
    rewriteLinks();

    for (let i = 0; i < changeListeners.length; i++) {
      try {
        changeListeners[i](target);
      } catch (err) {
        console.error("Version change listener error:", err);
      }
    }

    if (activeController) {
      const mySeq = ++switchSeq;
      return applySwitch(activeController, target, { isInitial: false, mySeq });
    }
    return Promise.resolve();
  }

  function onVersionChange(cb) {
    if (typeof cb === "function") {
      changeListeners.push(cb);
    }
  }

  function getLoadState(versionId) {
    if (!activeController) return "idle";
    const id = versionId || current.id;
    return activeController.loadStates.get(id) || "idle";
  }

  function whenAllPreloaded() {
    return activeController ? activeController.allPreloadedPromise : Promise.resolve();
  }

  function onDomReady() {
    mountPickers();
    rewriteLinks();
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", onDomReady);
    } else {
      onDomReady();
    }
    if (typeof global.addEventListener === "function") {
      global.addEventListener("pageshow", () => {
        const qv = getQueryParam("v");
        const sv = safeStorageGet(STORAGE_KEY);
        if (!qv && sv && byId(sv) && sv !== current.id) {
          selectVersion(sv, { pushHistory: false });
          return;
        }
        mountPickers();
        rewriteLinks();
      });
      global.addEventListener("popstate", () => {
        const qv = getQueryParam("v");
        const target = (qv && byId(qv)) ? byId(qv) : DEFAULT_VERSION;
        if (target.id !== current.id) {
          selectVersion(target.id, { pushHistory: false });
        } else {
          mountPickers();
          rewriteLinks();
        }
      });
    }
  }

  const api = {
    versions: MANIFEST,
    defaultVersion: DEFAULT_VERSION,
    rootPrefix: rootPrefix,
    dataUrl: versionAssetUrl,
    versionAssetUrl: versionAssetUrl,
    sourceUrl: sourceUrl,
    treeUrl: treeUrl,
    buildUrlWithVersion: buildUrlWithVersion,
    loadDataScript: loadDataScript,
    mountPickers: mountPickers,
    rewriteLinks: rewriteLinks,
    selectVersion: selectVersion,
    onVersionChange: onVersionChange,
    getLoadState: getLoadState,
    whenAllPreloaded: whenAllPreloaded,
  };
  Object.defineProperty(api, "current", {
    enumerable: true,
    get: function () { return current; },
  });
  Object.defineProperty(api, "isDefault", {
    enumerable: true,
    get: function () { return isDefault; },
  });

  global.RHVersion = api;
})(typeof window !== "undefined" ? window : globalThis);
