#!/usr/bin/env node
/**
 * Dual-mode Markdown report renderer:
 *   1. Browser: loaded via <script src="../render_reports.js" data-md="REPORT.md"></script>
 *      Fetches the sibling .md file on page load and re-renders <main> live.
 *   2. Node.js CLI / Git pre-commit hook: `node analysis/render_reports.js`
 *      Regenerates all report HTML files on disk from their source .md files.
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
    let s = str
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

  function renderInline(text) {
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

    const LOCAL_PREFIX = "file:///home/ubuntu/riemann_proof/";
    const GITHUB_BLOB_BASE =
      "https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/";

    function rewriteUrl(url) {
      if (url.startsWith(LOCAL_PREFIX + "analysis/")) {
        return "../" + url.slice((LOCAL_PREFIX + "analysis/").length);
      }
      if (url.startsWith(LOCAL_PREFIX)) {
        return GITHUB_BLOB_BASE + url.slice(LOCAL_PREFIX.length);
      }
      return url;
    }

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

  function convertMarkdown(mdText) {
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

      // Heading
      const mHead = stripped.match(/^(#{1,6})\s+(.+)$/);
      if (mHead) {
        const level = mHead[1].length;
        const rawH = mHead[2].trim();
        if (level === 1 && !foundTitle) {
          title = rawH.replace(/`([^`]+)`/g, "$1");
          foundTitle = true;
        }
        const renderedH = renderInline(rawH);
        const slug = slugify(renderedH);
        out.push(`<h${level} id="${slug}">${renderedH}</h${level}>`);
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
        out.push(`<blockquote><p>${renderInline(bqLines.join(" "))}</p></blockquote>`);
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
          tHtml.push(`<th${style}>${renderInline(headers[c])}</th>`);
        }
        tHtml.push("</tr></thead><tbody>");
        for (const row of rows) {
          tHtml.push("<tr>");
          for (let c = 0; c < numCols; c++) {
            const cellVal = c < row.length ? row[c] : "";
            const al = c < aligns.length ? aligns[c] : "left";
            const style = al !== "left" ? ` style="text-align:${al}"` : "";
            tHtml.push(`<td${style}>${renderInline(cellVal)}</td>`);
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
                last.slice(0, -5) + " " + renderInline(curr.trim()) + "</li>";
              i++;
              continue;
            }
            break;
          }
          const indent = mItem[1].length;
          const itemOrdered = mItem[2].endsWith(".");
          if (indent === 0 && itemOrdered !== isOrdered) break;
          let itemText = renderInline(mItem[3].trim());
          i++;

          const subItems = [];
          let subTag = "ul";
          while (i < n && lines[i].trim()) {
            const nxt = lines[i];
            const mSub = nxt.match(/^(\s+)([-*]|\d+\.)\s+(.+)$/);
            if (mSub && mSub[1].length > indent) {
              subTag = mSub[2].endsWith(".") ? "ol" : "ul";
              subItems.push(`<li>${renderInline(mSub[3].trim())}</li>`);
              i++;
            } else if (nxt.startsWith("   ") && !mSub) {
              if (subItems.length > 0) {
                const lastSub = subItems[subItems.length - 1];
                subItems[subItems.length - 1] =
                  lastSub.slice(0, -5) + " " + renderInline(nxt.trim()) + "</li>";
              } else {
                itemText += " " + renderInline(nxt.trim());
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
        out.push(`<p>${renderInline(paraLines.join(" "))}</p>`);
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
      if (!el || typeof window.renderMathInElement !== "function") return;
      window.renderMathInElement(el, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false },
          { left: "\\(", right: "\\)", display: false },
          { left: "\\[", right: "\\]", display: true },
        ],
        throwOnError: false,
      });
    }

    const mainEl = document.querySelector("main");
    const scriptEl = document.currentScript;
    const mdHref =
      (scriptEl && scriptEl.getAttribute("data-md")) ||
      window.location.pathname.split("/").pop().replace(/\.html$/i, ".md");

    function runMathWhenReady() {
      const target = document.querySelector("main");
      if (typeof window.renderMathInElement === "function") {
        renderMath(target);
      } else {
        window.addEventListener("load", () => renderMath(document.querySelector("main")), {
          once: true,
        });
      }
    }

    if (mdHref && window.location.protocol !== "file:") {
      fetch(mdHref, { cache: "no-store" })
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.text();
        })
        .then((mdText) => {
          const { title, bodyHtml } = convertMarkdown(mdText);
          document.title = title;
          if (mainEl) mainEl.innerHTML = bodyHtml;
          runMathWhenReady();
        })
        .catch(() => {
          // Keep pre-rendered HTML fallback silently if fetch fails
          runMathWhenReady();
        });
    } else {
      runMathWhenReady();
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

    for (const relMd of REPORTS) {
      const mdPath = path.join(analysisDir, relMd);
      if (!fs.existsSync(mdPath)) continue;

      const mdText = fs.readFileSync(mdPath, "utf8");
      const { title, bodyHtml } = convertMarkdown(mdText);
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
  <a href="../index.html">&larr; Back to Analysis Portal</a> &middot;
  <a href="${escapeHtml(mdName, true)}">Raw Markdown (${escapeHtml(mdName, false)})</a>
</nav>
<main>
${bodyHtml}
</main>
<script src="../render_reports.js" data-md="${escapeHtml(mdName, true)}"></script>
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
