import logging

import httpx
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

_browser = None
_playwright = None
_cached_css = None

MARKDOWN_CSS_URL = (
    "https://raw.githubusercontent.com/laikit-dev/"
    "luogu-saver/master/packages/frontend/src/styles/markdown.css"
)


async def get_browser():
    global _browser, _playwright
    if _browser is None:
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=True)
    return _browser


async def get_markdown_css() -> str:
    global _cached_css
    if _cached_css is None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(MARKDOWN_CSS_URL)
                resp.raise_for_status()
                _cached_css = resp.text
            logger.info("Markdown CSS fetched (%d bytes)", len(_cached_css))
        except Exception as e:
            logger.warning("Failed to fetch markdown CSS: %s", e)
            _cached_css = ""
    return _cached_css


async def render_html(html_body: str, viewport_width: int = 800) -> bytes:
    css = await get_markdown_css()
    full_html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<style>
body {{ margin: 16px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 14px; line-height: 1.6; color: #333; }}
{css}
</style>
</head>
<body>
{html_body}
</body>
</html>"""
    browser = await get_browser()
    page = await browser.new_page(viewport={"width": viewport_width, "height": 720})
    try:
        await page.set_content(full_html, wait_until="networkidle")
        png = await page.screenshot(full_page=True)
        return png
    finally:
        await page.close()
