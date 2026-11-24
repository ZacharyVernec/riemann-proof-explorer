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
  const current = resolveInitialVersion();
  const isDefault = current.id === DEFAULT_VERSION.id;

  function encodeRelPath(relPath) {
    return String(relPath || "")
      .replace(/^\/+/, "")
      .split("/")
      .map((seg) => encodeURIComponent(seg))
      .join("/");
  }

  function versionAssetUrl(relPath) {
    const clean = String(relPath || "").replace(/^\/+/, "");
    return rootPrefix + "versions/" + encodeURIComponent(current.id) + "/" + clean;
  }

  function sourceUrl(relPath, lineNo) {
    const base = String(current.source_blob_base || "").replace(/\/+$/, "");
    const clean = String(relPath || "").replace(/^\/+/, "");
    const frag = lineNo ? "#L" + String(lineNo) : "";
    if (!base) return encodeRelPath(clean) + frag;
    return base + "/" + encodeRelPath(clean) + frag;
  }

  function treeUrl(relPath) {
    const base = String(current.source_tree_base || current.repo_url || "").replace(/\/+$/, "");
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

  function selectVersion(newId) {
    const target = byId(newId);
    if (!target) return;
    safeStorageSet(STORAGE_KEY, target.id);
    if (!global.location) return;
    const href = String(global.location.href || "");
    const hashIdx = href.indexOf("#");
    const hash = hashIdx >= 0 ? href.slice(hashIdx) : "";
    const beforeHash = hashIdx >= 0 ? href.slice(0, hashIdx) : href;
    const qIdx = beforeHash.indexOf("?");
    const base = qIdx >= 0 ? beforeHash.slice(0, qIdx) : beforeHash;
    const params = new URLSearchParams(qIdx >= 0 ? beforeHash.slice(qIdx + 1) : "");
    if (target.id !== DEFAULT_VERSION.id) {
      params.set("v", target.id);
    } else {
      params.delete("v");
    }
    const qs = params.toString();
    const nextUrl = base + (qs ? "?" + qs : "") + hash;
    if (nextUrl === href) {
      global.location.reload();
    } else {
      global.location.href = nextUrl;
    }
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
      ".rh-vp-wrap.rh-vp-compact{font-size:11.5px;gap:4px;}",
      ".rh-vp-wrap.rh-vp-compact .rh-vp-label{font-size:11px;color:#666;}",
      ".rh-vp-wrap.rh-vp-compact .rh-vp-select{font-size:11.5px;padding:2px 6px;border-radius:999px;border-color:#cbd5e1;max-width:210px;}",
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

      wrap.appendChild(lbl);
      wrap.appendChild(sel);
      slot.appendChild(wrap);
    });
  }

  function rewriteLinks(root) {
    if (typeof document === "undefined") return;
    const container = root || document;

    container.querySelectorAll("a[href]").forEach((a) => {
      if (a.hasAttribute("data-version-ignore")) return;
      const vAsset = a.getAttribute("data-version-href");
      if (vAsset) {
        a.setAttribute("href", versionAssetUrl(vAsset));
        return;
      }
      const orig = a.getAttribute("data-orig-href") || a.getAttribute("href");
      if (!a.hasAttribute("data-orig-href")) {
        a.setAttribute("data-orig-href", orig);
      }
      const rewritten = buildUrlWithVersion(orig, current.id);
      if (rewritten !== a.getAttribute("href")) {
        a.setAttribute("href", rewritten);
      }
    });

    container.querySelectorAll("[data-version-src]").forEach((el) => {
      const rel = el.getAttribute("data-version-src");
      if (rel) el.setAttribute("src", versionAssetUrl(rel));
    });
  }

  function loadDataScript(relSubpath, globalVar, callback) {
    if (typeof document === "undefined") return;
    const url = versionAssetUrl(relSubpath);
    const script = document.createElement("script");
    script.src = url;
    script.async = false;
    script.onload = function () {
      try {
        callback(global[globalVar]);
      } catch (err) {
        console.error("Failed initializing viewer from " + url + ":", err);
      }
    };
    script.onerror = function () {
      const msg =
        "Failed to load versioned dataset (" +
        url +
        ") for Lean version '" +
        current.id +
        "'.";
      console.error(msg);
      const loadingEl = document.getElementById("loading");
      if (loadingEl) {
        loadingEl.textContent = msg;
        loadingEl.style.color = "#b91c1c";
      } else if (document.body) {
        const banner = document.createElement("div");
        banner.style.cssText =
          "margin:16px auto;max-width:720px;padding:12px 16px;background:#fef2f2;border:1px solid #fca5a5;color:#991b1b;border-radius:6px;font-family:sans-serif;font-size:13px;";
        banner.textContent = msg;
        document.body.prepend(banner);
      }
    };
    (document.head || document.body || document.documentElement).appendChild(script);
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
          selectVersion(sv);
          return;
        }
        mountPickers();
        rewriteLinks();
      });
    }
  }

  global.RHVersion = {
    versions: MANIFEST,
    defaultVersion: DEFAULT_VERSION,
    current: current,
    isDefault: isDefault,
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
  };
})(typeof window !== "undefined" ? window : globalThis);
