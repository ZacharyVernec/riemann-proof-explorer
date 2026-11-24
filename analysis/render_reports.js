#!/usr/bin/env node
/**
 * Dual-mode Markdown report renderer:
 *   1. Browser: loaded via <script src="../render_reports.js" data-md="REPORT.md" data-report="dir/REPORT.md"></script>
 *      - For the default Lean version on HTTP(S): fetches sibling .md and re-renders live.
 *      - For any non-default Lean version (file:// or HTTP): loads versions/<vid>/<report>.md.js via RHVersion.
 *   2. Node.js CLI / Git pre-commit hook: `node analysis/render_reports.js [--stage]`
 *      - Regenerates all 8 canonical HTML reports (default version fallback) and per-version *.md.js wrappers.
 */
(function () {
  "use strict";

  const SIMPLE_CSS = `  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6;
    color: #222;
    background: #fff;
    max-width: 1100px;
    margin: 0 auto;
    padding: 24px 20px 60px;
  }
  nav.top-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 1px solid #ddd;
    font-size: 14px;
    color: #555;
  }
  nav.top-nav a {
    color: #0056b3;
    text-decoration: none;
  }
  nav.top-nav a:hover {
    text-decoration: underline;
  }
  h1, h2, h3, h4 {
    color: #111;
    line-height: 1.3;
    margin-top: 1.4em;
    margin-bottom: 0.5em;
  }
  h1 {
    font-size: 1.8em;
    margin-top: 0.4em;
    padding-bottom: 0.3em;
    border-bottom: 1px solid #ddd;
  }
  h2 {
    font-size: 1.4em;
    padding-bottom: 0.2em;
    border-bottom: 1px solid #eee;
  }
  h3 { font-size: 1.15em; }
  h4 { font-size: 1.02em; }
  p, ul, ol, blockquote {
    margin: 0.7em 0;
  }
  ul, ol {
    padding-left: 1.6em;
  }
  li {
    margin: 0.25em 0;
  }
  blockquote {
    margin-left: 0;
    padding: 0.4em 1em;
    border-left: 4px solid #ccc;
    color: #444;
    background: #f9f9f9;
  }
  hr {
    border: 0;
    border-top: 1px solid #ddd;
    margin: 1.8em 0;
  }
  a {
    color: #0056b3;
    text-decoration: none;
  }
  a:hover {
    text-decoration: underline;
  }
  code {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    font-size: 0.9em;
    background: #f4f4f4;
    padding: 0.15em 0.35em;
    border-radius: 3px;
  }
  pre {
    background: #f6f8fa;
    border: 1px solid #e1e4e8;
    border-radius: 4px;
    padding: 12px 14px;
    overflow-x: auto;
    font-size: 0.88em;
    line-height: 1.45;
  }
  pre code {
    background: none;
    padding: 0;
    font-size: inherit;
  }
  .table-wrap {
    overflow-x: auto;
    margin: 1em 0;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    font-size: 0.92em;
  }
  th, td {
    border: 1px solid #ccc;
    padding: 7px 10px;
    vertical-align: top;
    text-align: left;
  }
  th {
    background: #f3f4f6;
    font-weight: 600;
  }
  tr:nth-child(even) td {
    background: #fafafa;
  }
  details {
    margin: 1em 0;
    padding: 0.5em 0.8em;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: #fafafa;
  }
  summary {
    cursor: pointer;
    font-weight: 600;
  }
`;

  function escapeHtml(str, quote) {
    let s = String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    if (quote) {
      s = s.replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
    }
    return s;
  }

  function slugify(text) {
    const clean = text
      .replace(/<[^>]+>/g, "")
      .replace(/[^a-zA-Z0-9\s-]/g, "")
      .trim()
      .toLowerCase();
    return clean.replace(/[\s-]+/g, "-") || "section";
  }

  const FALLBACK_BLOB_BASE =
    "https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/";

  function makeUrlRewriter(urlOpts) {
    const opts = urlOpts || {};
    const srcBlobBase = (opts.sourceBlobBase || "").replace(/\/+$/, "");
    const localSrcPrefix = opts.localSrcDir
      ? "file:///home/ubuntu/riemann_proof/" + String(opts.localSrcDir).replace(/^\/+|\/+$/g, "") + "/"
      : null;
    const LOCAL_PREFIX = "file:///home/ubuntu/riemann_proof/";

    return function rewriteUrl(url) {
      if (url.startsWith(LOCAL_PREFIX + "analysis/")) {
        return "../" + url.slice((LOCAL_PREFIX + "analysis/").length);
      }
      if (localSrcPrefix && url.startsWith(localSrcPrefix) && srcBlobBase) {
        return srcBlobBase + "/" + url.slice(localSrcPrefix.length);
      }
      if (url.startsWith(LOCAL_PREFIX + "lean/src/") && srcBlobBase) {
        return srcBlobBase + "/" + url.slice((LOCAL_PREFIX + "lean/src/").length);
      }
      const mVerSrc = url.match(/^file:\/\/\/home\/ubuntu\/riemann_proof\/lean_versions\/[^/]+\/src\/(.*)$/);
      if (mVerSrc && srcBlobBase) {
        return srcBlobBase + "/" + mVerSrc[1];
      }
      if (url.startsWith(LOCAL_PREFIX)) {
        return FALLBACK_BLOB_BASE + url.slice(LOCAL_PREFIX.length);
      }
      if (
        opts.resolveVersionedAsset &&
        !/^(https?:|file:|mailto:|javascript:|data:|#|\/|\.\.)/i.test(url)
      ) {
        const pathOnly = url.split(/[?#]/)[0];
        if (/\.(json|js|dot|mmd)$/i.test(pathOnly)) {
          const resolved = opts.resolveVersionedAsset(pathOnly);
          if (resolved) {
            return resolved + url.slice(pathOnly.length);
          }
        }
      }
      return url;
    };
  }

  function renderInline(text, rewriteUrl) {
    const tokens = [];

    function saveToken(renderedHtml) {
      const idx = tokens.length;
      tokens.push(renderedHtml);
      return `\x00TOK${idx}\x00`;
    }

    function formatEmphasis(s) {
      s = escapeHtml(s, false);
      s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      s = s.replace(/(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)/g, "<em>$1</em>");
      return s;
    }

    // 1. Code spans `...`
    text = text.replace(/`([^`]+)`/g, (_, inner) =>
      saveToken(`<code>${escapeHtml(inner, false)}</code>`)
    );

    // 1b. Math spans $$...$$ and $...$ (preserve verbatim for KaTeX; avoid italic/bold inside math)
    text = text.replace(/\$\$(.+?)\$\$/g, (m) => saveToken(escapeHtml(m, false)));
    text = text.replace(/\$([^$\n]+?)\$/g, (m) => saveToken(escapeHtml(m, false)));

    // 1c. Images ![alt](url)
    text = text.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (_, altRaw, urlRaw) => {
      const url = rewriteUrl(urlRaw.trim());
      return saveToken(
        `<img src="${escapeHtml(url, true)}" alt="${escapeHtml(altRaw, true)}" style="max-width:100%;height:auto;">`
      );
    });

    // 2. Links [label](url)
    text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, labelRaw, urlRaw) => {
      const url = rewriteUrl(urlRaw.trim());
      const labelRendered = formatEmphasis(labelRaw);
      return saveToken(
        `<a href="${escapeHtml(url, true)}">${labelRendered}</a>`
      );
    });

    // 3. Escape remaining HTML entities and apply bold/italic
    text = formatEmphasis(text);

    // 4. Restore tokens (up to 3 passes so code spans inside link labels expand)
    for (let pass = 0; pass < 3; pass++) {
      if (!text.includes("\x00TOK")) break;
      text = text.replace(/\x00TOK(\d+)\x00/g, (_, idx) => tokens[Number(idx)]);
    }

    return text;
  }

  function splitTableRow(line) {
    let s = line.trim();
    if (s.startsWith("|")) s = s.slice(1);
    if (s.endsWith("|")) s = s.slice(0, -1);

    const cells = [];
    let cur = "";
    let inCode = false;
    for (let i = 0; i < s.length; i++) {
      const ch = s[i];
      if (ch === "`") {
        inCode = !inCode;
        cur += ch;
      } else if (ch === "\\" && i + 1 < s.length && s[i + 1] === "|") {
        cur += "|";
        i++;
      } else if (ch === "|" && !inCode) {
        cells.push(cur.trim());
        cur = "";
      } else {
        cur += ch;
      }
    }
    cells.push(cur.trim());
    return cells;
  }

  function isTableSep(line) {
    const s = line.trim();
    if (!s.startsWith("|")) return false;
    const cells = splitTableRow(s);
    if (cells.length === 0) return false;
    return cells.every((c) => /^:?-{2,}:?$/.test(c.trim()));
  }

  function parseAlignments(sepLine) {
    return splitTableRow(sepLine).map((raw) => {
      const c = raw.trim();
      if (c.startsWith(":") && c.endsWith(":")) return "center";
      if (c.endsWith(":")) return "right";
      return "left";
    });
  }

  function convertMarkdown(mdText, urlOpts) {
    const rewriteUrl = makeUrlRewriter(urlOpts);
    const rInline = (t) => renderInline(t, rewriteUrl);
    const lines = mdText.replace(/\r\n?/g, "\n").split("\n");
    const n = lines.length;
    let i = 0;
    const out = [];
    let title = "Report";
    let foundTitle = false;

    while (i < n) {
      const line = lines[i];
      const stripped = line.trim();

      if (!stripped) {
        i++;
        continue;
      }

      // Raw HTML block tags (<details>, </details>, <summary>...</summary>)
      if (
        stripped === "<details>" ||
        stripped === "</details>" ||
        stripped.startsWith("<summary>")
      ) {
        out.push(stripped);
        i++;
        continue;
      }

      // Fenced code block
      if (stripped.startsWith("```")) {
        const lang = stripped.slice(3).trim();
        i++;
        const codeLines = [];
        while (i < n && !lines[i].trim().startsWith("```")) {
          codeLines.push(lines[i]);
          i++;
        }
        if (i < n) i++;
        const codeEscaped = escapeHtml(codeLines.join("\n"), false);
        const cls = lang ? ` class="language-${escapeHtml(lang, true)}"` : "";
        out.push(`<pre><code${cls}>${codeEscaped}</code></pre>`);
        continue;
      }

      // Horizontal rule
      if (/^-{3,}$/.test(stripped)) {
        out.push("<hr>");
        i++;
        continue;
      }

      // ATX Heading
      const mHead = line.match(/^(#{1,6})\s+(.*)$/);
      if (mHead) {
        const lvl = mHead[1].length;
        const hText = mHead[2].trim();
        if (!foundTitle && lvl === 1) {
          title = hText.replace(/`/g, "");
          foundTitle = true;
        }
        const idAttr = slugify(hText);
        out.push(`<h${lvl} id="${escapeHtml(idAttr, true)}">${rInline(hText)}</h${lvl}>`);
        i++;
        continue;
      }

      // Blockquote
      if (stripped.startsWith(">")) {
        const bqLines = [];
        while (i < n && lines[i].trim().startsWith(">")) {
          bqLines.push(lines[i].trim().replace(/^>\s?/, ""));
          i++;
        }
        out.push(`<blockquote><p>${rInline(bqLines.join(" "))}</p></blockquote>`);
        continue;
      }

      // Table
      if (stripped.startsWith("|") && i + 1 < n && isTableSep(lines[i + 1])) {
        const headers = splitTableRow(lines[i]);
        const aligns = parseAlignments(lines[i + 1]);
        i += 2;
        const rows = [];
        while (i < n && lines[i].trim().startsWith("|")) {
          rows.push(splitTableRow(lines[i]));
          i++;
        }
        const numCols = headers.length;
        const tHtml = ['<div class="table-wrap"><table><thead><tr>'];
        for (let c = 0; c < numCols; c++) {
          const al = c < aligns.length ? aligns[c] : "left";
          const style = al !== "left" ? ` style="text-align:${al}"` : "";
          tHtml.push(`<th${style}>${rInline(headers[c])}</th>`);
        }
        tHtml.push("</tr></thead><tbody>");
        for (const row of rows) {
          tHtml.push("<tr>");
          for (let c = 0; c < numCols; c++) {
            const cellVal = c < row.length ? row[c] : "";
            const al = c < aligns.length ? aligns[c] : "left";
            const style = al !== "left" ? ` style="text-align:${al}"` : "";
            tHtml.push(`<td${style}>${rInline(cellVal)}</td>`);
          }
          tHtml.push("</tr>");
        }
        tHtml.push("</tbody></table></div>");
        out.push(tHtml.join(""));
        continue;
      }

      // List (unordered or ordered, supporting 2-level nesting)
      const mList = line.match(/^(\s*)([-*]|\d+\.)\s+(.+)$/);
      if (mList) {
        const isOrdered = mList[2].endsWith(".");
        const tag = isOrdered ? "ol" : "ul";
        const listHtml = [`<${tag}>`];
        while (i < n) {
          const curr = lines[i];
          if (!curr.trim()) break;
          const mItem = curr.match(/^(\s*)([-*]|\d+\.)\s+(.+)$/);
          if (!mItem) {
            if (curr.startsWith("  ") && listHtml[listHtml.length - 1].endsWith("</li>")) {
              const last = listHtml[listHtml.length - 1];
              listHtml[listHtml.length - 1] =
                last.slice(0, -5) + " " + rInline(curr.trim()) + "</li>";
              i++;
              continue;
            }
            break;
          }
          const indent = mItem[1].length;
          const itemOrdered = mItem[2].endsWith(".");
          if (indent === 0 && itemOrdered !== isOrdered) break;
          let itemText = rInline(mItem[3].trim());
          i++;

          const subItems = [];
          let subTag = "ul";
          while (i < n && lines[i].trim()) {
            const nxt = lines[i];
            const mSub = nxt.match(/^(\s+)([-*]|\d+\.)\s+(.+)$/);
            if (mSub && mSub[1].length > indent) {
              subTag = mSub[2].endsWith(".") ? "ol" : "ul";
              subItems.push(`<li>${rInline(mSub[3].trim())}</li>`);
              i++;
            } else if (nxt.startsWith("   ") && !mSub) {
              if (subItems.length > 0) {
                const lastSub = subItems[subItems.length - 1];
                subItems[subItems.length - 1] =
                  lastSub.slice(0, -5) + " " + rInline(nxt.trim()) + "</li>";
              } else {
                itemText += " " + rInline(nxt.trim());
              }
              i++;
            } else {
              break;
            }
          }
          if (subItems.length > 0) {
            listHtml.push(`<li>${itemText}<${subTag}>${subItems.join("")}</${subTag}></li>`);
          } else {
            listHtml.push(`<li>${itemText}</li>`);
          }
        }
        listHtml.push(`</${tag}>`);
        out.push(listHtml.join(""));
        continue;
      }

      // Paragraph
      const paraLines = [];
      while (i < n) {
        const lCur = lines[i];
        const sCur = lCur.trim();
        if (
          !sCur ||
          sCur.startsWith("#") ||
          sCur.startsWith("```") ||
          sCur.startsWith(">") ||
          sCur === "<details>" ||
          sCur === "</details>" ||
          sCur.startsWith("<summary>") ||
          /^-{3,}$/.test(sCur) ||
          (sCur.startsWith("|") && i + 1 < n && isTableSep(lines[i + 1])) ||
          /^(\s*)([-*]|\d+\.)\s+/.test(lCur)
        ) {
          break;
        }
        paraLines.push(sCur);
        i++;
      }
      if (paraLines.length > 0) {
        out.push(`<p>${rInline(paraLines.join(" "))}</p>`);
      } else {
        i++;
      }
    }

    return { title, bodyHtml: out.join("\n") };
  }

  // ---------------------------------------------------------------------------
  // Mode 1: Browser client-side live renderer
  // ---------------------------------------------------------------------------
  if (typeof window !== "undefined" && typeof document !== "undefined") {
    function renderMath(el) {
      if (!el || typeof window.renderMathInElement !== "function") return false;
      window.renderMathInElement(el, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false },
          { left: "\\(", right: "\\)", display: false },
          { left: "\\[", right: "\\]", display: true },
        ],
        throwOnError: false,
      });
      return true;
    }

    const mainEl = document.querySelector("main");
    const initialStaticHtml = mainEl ? mainEl.innerHTML : "";
    const initialStaticTitle = document.title;
    const scriptEl = document.currentScript;
    const mdHref =
      (scriptEl && scriptEl.getAttribute("data-md")) ||
      window.location.pathname.split("/").pop().replace(/\.html$/i, ".md");
    const reportRelPath = (scriptEl && scriptEl.getAttribute("data-report")) || "";
    const reportDir = reportRelPath && reportRelPath.includes("/")
      ? reportRelPath.split("/").slice(0, -1).join("/")
      : "";

    let currentPanel = null;
    let mathLoadBound = false;

    function ensureMathLoadListener() {
      if (mathLoadBound) return;
      mathLoadBound = true;
      window.addEventListener(
        "load",
        () => {
          if (currentPanel && !currentPanel.dataset.mathRendered) {
            if (renderMath(currentPanel)) {
              currentPanel.dataset.mathRendered = "1";
            }
          }
        },
        { once: true }
      );
    }

    function rewritePanelVersionAssets(panel, verId) {
      if (!window.RHVersion || !reportDir) return;
      // Point relative data/source-graph assets (.json, .js, .dot, .mmd) to versioned storage for all versions
      panel.querySelectorAll("a[href]").forEach((a) => {
        const href = (a.getAttribute("href") || "").trim();
        if (!href || /^(https?:|mailto:|javascript:|data:|#|\/)/i.test(href)) return;
        const pathOnly = href.split(/[?#]/)[0];
        if (/\.(json|js|dot|mmd)$/i.test(pathOnly) && !href.startsWith("..")) {
          a.setAttribute("href", window.RHVersion.versionAssetUrl(reportDir + "/" + href, verId));
        }
      });
      if (verId !== window.RHVersion.defaultVersion.id) {
        // Point relative .svg / .md links inside non-default reports to versioned assets
        panel.querySelectorAll("img[src]").forEach((img) => {
          const src = img.getAttribute("src") || "";
          if (src && !/^(https?:|data:|\/|\.\.)/.test(src)) {
            img.setAttribute("src", window.RHVersion.versionAssetUrl(reportDir + "/" + src, verId));
          }
        });
        panel.querySelectorAll("a[href]").forEach((a) => {
          const href = (a.getAttribute("href") || "").trim();
          if (!href || /^(https?:|mailto:|javascript:|data:|#|\/)/i.test(href)) return;
          const pathOnly = href.split(/[?#]/)[0];
          if (!/\.(svg|md)$/i.test(pathOnly)) return;
          if (href.startsWith("../")) {
            a.setAttribute("href", window.RHVersion.versionAssetUrl(href.slice(3), verId));
          } else {
            a.setAttribute("href", window.RHVersion.versionAssetUrl(reportDir + "/" + href, verId));
          }
        });
      }
    }

    function prepareReport(payload, ver) {
      const panel = document.createElement("div");
      panel.className = "rh-report-panel";
      let title = initialStaticTitle;

      if (payload && typeof payload.preRenderedHtml === "string") {
        title = payload.title || initialStaticTitle;
        panel.innerHTML = payload.preRenderedHtml;
      } else if (payload && typeof payload.markdown === "string") {
        const urlOpts = ver
          ? { sourceBlobBase: ver.source_blob_base, localSrcDir: ver.local_src_dir }
          : {};
        const converted = convertMarkdown(payload.markdown, urlOpts);
        title = converted.title;
        panel.innerHTML = converted.bodyHtml;
      } else {
        panel.innerHTML = initialStaticHtml;
      }

      if (ver) {
        rewritePanelVersionAssets(panel, ver.id);
        if (window.RHVersion) window.RHVersion.rewriteLinks(panel, ver.id);
      }

      if (renderMath(panel)) {
        panel.dataset.mathRendered = "1";
      }
      return { title, panel };
    }

    function applyPreparedReport(entry) {
      document.title = entry.title;
      if (mainEl) {
        mainEl.style.opacity = "";
        if (typeof mainEl.replaceChildren === "function") {
          mainEl.replaceChildren(entry.panel);
        } else {
          mainEl.innerHTML = "";
          mainEl.appendChild(entry.panel);
        }
      }
      currentPanel = entry.panel;
      if (!entry.panel.dataset.mathRendered) {
        if (renderMath(entry.panel)) {
          entry.panel.dataset.mathRendered = "1";
        } else {
          ensureMathLoadListener();
        }
      }
    }

    const rhv = window.RHVersion;
    if (rhv && reportRelPath) {
      rhv.loadDataScript(reportRelPath + ".js", "__REPORT_MD__", applyPreparedReport, {
        customLoad: async (ver) => {
          if (ver.id === rhv.defaultVersion.id) {
            if (mdHref && window.location.protocol !== "file:") {
              try {
                const res = await fetch(mdHref, { cache: "no-store" });
                if (res.ok) {
                  return { markdown: await res.text() };
                }
              } catch (_) {
                // Fall back to static HTML or .md.js wrapper
              }
            }
            return { preRenderedHtml: initialStaticHtml, title: initialStaticTitle };
          }
          return undefined;
        },
        prepare: prepareReport,
        onLoading: () => {
          if (mainEl) mainEl.style.opacity = "0.55";
        },
      });
    } else if (mdHref && window.location.protocol !== "file:") {
      fetch(mdHref, { cache: "no-store" })
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.text();
        })
        .then((mdText) => applyPreparedReport(prepareReport({ markdown: mdText }, null)))
        .catch(() => {
          currentPanel = mainEl;
          if (mainEl && !renderMath(mainEl)) ensureMathLoadListener();
        });
    } else {
      currentPanel = mainEl;
      if (mainEl && !renderMath(mainEl)) ensureMathLoadListener();
    }
    return;
  }

  // ---------------------------------------------------------------------------
  // Mode 2: Node.js CLI & Git pre-commit hook
  // ---------------------------------------------------------------------------
  if (typeof require === "function" && typeof module !== "undefined" && require.main === module) {
    const fs = require("fs");
    const path = require("path");
    const { execSync } = require("child_process");

    const analysisDir = __dirname;
    const repoRoot = path.resolve(analysisDir, "..");

    const versionsPath = path.join(analysisDir, "versions.json");
    const versions = fs.existsSync(versionsPath)
      ? JSON.parse(fs.readFileSync(versionsPath, "utf8"))
      : [];
    const defaultVer = versions.find((v) => v.is_default) || versions[0] || {
      id: "default",
      source_blob_base: FALLBACK_BLOB_BASE + "lean/src/",
      local_src_dir: "lean/src",
    };

    const REPORTS = [
      "blueprint/BLUEPRINT.md",
      "dependency_graph/README.md",
      "interfaces/INTERFACES_REPORT.md",
      "proof_spine/PROOF_SPINE_REPORT.md",
      "size_treemap/SIZE_ANALYSIS.md",
      "published_theorems/PUBLISHED_THEOREMS_INVENTORY.md",
      "full_dag/FULL_DAG.md",
      "codebase_histograms/CODEBASE_HISTOGRAMS.md",
    ];

    const stageMode = process.argv.includes("--stage");
    const generatedPaths = [];

    // 1. Emit per-version .md.js wrappers for offline/cross-version browser switching
    for (const ver of versions) {
      const verDir = path.join(analysisDir, "versions", ver.id);
      if (!fs.existsSync(verDir)) continue;
      for (const relMd of REPORTS) {
        const verMdPath = path.join(verDir, relMd);
        if (!fs.existsSync(verMdPath)) continue;
        const mdText = fs.readFileSync(verMdPath, "utf8");
        const wrapperObj = { version: ver.id, markdown: mdText };
        const safeJs =
          "window.__REPORT_MD__ = " +
          JSON.stringify(wrapperObj).replace(/<\//g, "<\\/") +
          ";\n";
        const jsOutPath = verMdPath + ".js";
        const prevJs = fs.existsSync(jsOutPath) ? fs.readFileSync(jsOutPath, "utf8") : null;
        if (prevJs !== safeJs) {
          fs.writeFileSync(jsOutPath, safeJs, "utf8");
        }
        generatedPaths.push(path.relative(repoRoot, jsOutPath));
      }
    }

    // 2. Render canonical HTML fallback pages (matching default version)
    const defaultUrlOpts = {
      sourceBlobBase: defaultVer.source_blob_base,
      localSrcDir: defaultVer.local_src_dir,
    };

    for (const relMd of REPORTS) {
      const mdPath = path.join(analysisDir, relMd);
      if (!fs.existsSync(mdPath)) continue;

      const reportDir = path.dirname(relMd);
      const urlOpts = {
        ...defaultUrlOpts,
        resolveVersionedAsset(fileRel) {
          const directPath = path.join(analysisDir, reportDir, fileRel);
          if (fs.existsSync(directPath)) return null;
          const verPath = path.join(analysisDir, "versions", defaultVer.id, reportDir, fileRel);
          if (fs.existsSync(verPath)) {
            return "../versions/" + encodeURIComponent(defaultVer.id) + "/" + reportDir + "/" + fileRel;
          }
          return null;
        },
      };

      const mdText = fs.readFileSync(mdPath, "utf8");
      const { title, bodyHtml } = convertMarkdown(mdText, urlOpts);
      const mdName = path.basename(mdPath);
      const htmlPath = mdPath.replace(/\.md$/i, ".html");

      const fullHtml = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${escapeHtml(title, false)}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<style>
${SIMPLE_CSS}</style>
</head>
<body>
<nav class="top-nav">
  <div>
    <a href="../index.html">&larr; Back to Analysis Portal</a> &middot;
    <a href="${escapeHtml(mdName, true)}" data-version-href="${escapeHtml(relMd, true)}">Raw Markdown (${escapeHtml(mdName, false)})</a>
  </div>
  <span data-version-picker></span>
</nav>
<script src="../version_picker.js"></script>
<main>
${bodyHtml}
</main>
<script src="../render_reports.js" data-md="${escapeHtml(mdName, true)}" data-report="${escapeHtml(relMd, true)}"></script>
</body>
</html>
`;

      const prev = fs.existsSync(htmlPath) ? fs.readFileSync(htmlPath, "utf8") : null;
      if (prev !== fullHtml) {
        fs.writeFileSync(htmlPath, fullHtml, "utf8");
      }
      const relFromRepo = path.relative(repoRoot, htmlPath);
      generatedPaths.push(relFromRepo);
      if (!stageMode) {
        console.log(`Generated ${relFromRepo} (${Buffer.byteLength(fullHtml, "utf8").toLocaleString()} bytes)`);
      }
    }

    if (stageMode && generatedPaths.length > 0) {
      const quoted = generatedPaths.map((p) => JSON.stringify(p)).join(" ");
      execSync(`git add ${quoted}`, { cwd: repoRoot, stdio: "inherit" });
    }
  }
})();
