"""HTML -> PNG rendering using Playwright (headless Chromium).

The luogu.store API no longer returns pre-rendered HTML, so the plugin builds
the document itself from the structured article / paste data and styles it with
a self-contained generic CSS (no external CSS downloads).

LaTeX math is rendered with KaTeX, which is bundled locally under ``katex/`` and
embedded inline (CSS + JS + fonts as data URIs) so that no network access is
required at render time.
"""

from __future__ import annotations

import base64
import html
import logging
import os
import re

import markdown
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

_browser = None
_playwright = None

# Self-contained, generic stylesheet used for all in-plugin HTML rendering.
# No external fonts or stylesheets are fetched.
GENERIC_CSS = """\
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 24px;
  background: #ffffff;
  color: #1f2328;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
    "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
  font-size: 15px;
  line-height: 1.7;
}
.container { max-width: 760px; margin: 0 auto; }
.doc-header { border-bottom: 1px solid #e5e7eb; padding-bottom: 14px; margin-bottom: 18px; }
.doc-title { font-size: 24px; font-weight: 700; margin: 0 0 8px; line-height: 1.3; }
.doc-meta { font-size: 13px; color: #6b7280; margin: 0; }
.doc-content { font-size: 15px; }
h1, h2, h3, h4 { line-height: 1.35; margin: 1.4em 0 0.6em; font-weight: 600; }
h1 { font-size: 1.6em; } h2 { font-size: 1.35em; } h3 { font-size: 1.15em; }
p { margin: 0.8em 0; }
a { color: #2563eb; text-decoration: none; }
code {
  background: #f3f4f6; padding: 0.15em 0.4em; border-radius: 4px;
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  font-size: 0.9em;
}
pre {
  background: #f6f8fa; border: 1px solid #e5e7eb; border-radius: 8px;
  padding: 14px 16px; overflow-x: auto;
}
pre code { background: none; padding: 0; font-size: 0.88em; }
blockquote {
  margin: 1em 0; padding: 0.4em 1em; border-left: 4px solid #d1d5db;
  color: #4b5563; background: #f9fafb;
}
ul, ol { padding-left: 1.6em; margin: 0.8em 0; }
li { margin: 0.3em 0; }
hr { border: none; border-top: 1px solid #e5e7eb; margin: 1.6em 0; }
table { border-collapse: collapse; margin: 1em 0; width: 100%; }
th, td { border: 1px solid #e5e7eb; padding: 8px 12px; text-align: left; }
th { background: #f9fafb; font-weight: 600; }
img { max-width: 100%; height: auto; }
.katex-display { margin: 1em 0; overflow-x: auto; overflow-y: hidden; }
"""

_KATEX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "katex")
_FONT_MIME = {
    "woff2": "font/woff2",
    "woff": "font/woff",
    "ttf": "font/ttf",
}


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def _embed_katex_fonts(css: str) -> str:
    """Replace ``url(fonts/...)`` references with inline base64 data URIs."""
    fonts_dir = os.path.join(_KATEX_DIR, "fonts")

    def _replace(m: re.Match) -> str:
        raw = m.group(1).strip().strip('"').strip("'")
        fname = raw.split("/")[-1]
        fpath = os.path.join(fonts_dir, fname)
        if not os.path.exists(fpath):
            return m.group(0)
        ext = fname.rsplit(".", 1)[-1].lower()
        mime = _FONT_MIME.get(ext, "application/octet-stream")
        b64 = base64.b64encode(_read_bytes(fpath)).decode("ascii")
        return f'url("data:{mime};base64,{b64}")'

    return re.sub(r"url\(([^)]*fonts/[^)]+)\)", _replace, css)


# Load KaTeX assets at import time. If anything is missing (e.g. the katex/
# directory was not shipped), we degrade gracefully: math is shown as raw
# $...$ text instead of rendered glyphs, but the rest of the page still works.
try:
    KATEX_CSS = _embed_katex_fonts(_read_text(os.path.join(_KATEX_DIR, "katex.min.css")))
    KATEX_JS = _read_text(os.path.join(_KATEX_DIR, "katex.min.js"))
    KATEX_AUTORENDER_JS = _read_text(os.path.join(_KATEX_DIR, "auto-render.min.js"))
    KATEX_ENABLED = True
except Exception as exc:  # pragma: no cover - depends on bundled assets
    logger.warning("KaTeX assets unavailable, LaTeX rendering disabled: %s", exc)
    KATEX_CSS = KATEX_JS = KATEX_AUTORENDER_JS = ""
    KATEX_ENABLED = False


async def get_browser():
    global _browser, _playwright
    if _browser is None:
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=True)
    return _browser


def md_to_html(md: str) -> str:
    """Convert a markdown string into an HTML fragment."""
    return markdown.markdown(md or "", extensions=["fenced_code", "tables"])


def build_page(
    *, title: str | None = None, meta: str | None = None, body_html: str = ""
) -> str:
    """Assemble a complete, self-contained HTML document for rendering.

    When KaTeX is available, the math stylesheet and rendering scripts are
    embedded inline so that no network access is required during rendering.
    """
    header = ""
    if title or meta:
        parts = []
        if title:
            parts.append(f'<h1 class="doc-title">{html.escape(title)}</h1>')
        if meta:
            parts.append(f'<p class="doc-meta">{html.escape(meta)}</p>')
        header = f'<div class="doc-header">{"".join(parts)}</div>'

    style_block = GENERIC_CSS
    if KATEX_ENABLED:
        style_block += "\n" + KATEX_CSS

    math_scripts = ""
    if KATEX_ENABLED:
        math_scripts = f"""\
<script>{KATEX_JS}</script>
<script>{KATEX_AUTORENDER_JS}</script>
<script>
(function(){{
  function renderMath(){{
    try {{
      renderMathInElement(document.body, {{
        delimiters: [
          {{left: '$$', right: '$$', display: true}},
          {{left: '$', right: '$', display: false}},
          {{left: '\\\\(', right: '\\\\)', display: false}}
        ],
        ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
        throwOnError: false
      }});
    }} catch (e) {{}}
    window.__katexDone = true;
  }}
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', renderMath);
  }} else {{
    renderMath();
  }}
}})();
</script>
"""

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<style>{style_block}</style>
</head>
<body>
<div class="container">
{header}
<div class="doc-content">{body_html}</div>
</div>
{math_scripts}</body>
</html>"""


async def render_html(html_document: str, viewport_width: int = 800) -> bytes:
    browser = await get_browser()
    page = await browser.new_page(viewport={"width": viewport_width, "height": 720})
    try:
        await page.set_content(html_document, wait_until="load")
        # Give KaTeX a moment to finish rendering math (if enabled).
        if KATEX_ENABLED:
            try:
                await page.wait_for_function("window.__katexDone === true", timeout=3000)
            except Exception:
                pass
        png = await page.screenshot(full_page=True)
        return png
    finally:
        await page.close()
