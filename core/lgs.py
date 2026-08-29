"""洛谷保存站 (luogu.store) API integration, ported from the original
``lgs_tool_bot.plugins.lgs`` module.

Every ``handle_*`` coroutine is an async generator that yields either a plain
``str`` (to be sent as text) or an :class:`~core.ImageResult` (to be sent as an
image). :func:`dispatch_lgs` reproduces the original command router.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Union

import httpx

from . import ImageResult
from .browser import render_html

logger = logging.getLogger(__name__)

API_BASE = "https://api.luogu.me"

COLOR_MAP = {
    "Gray": "灰",
    "Blue": "蓝",
    "Green": "绿",
    "Orange": "橙",
    "Red": "红",
    "Purple": "紫",
    "Legend": "黑",
}

STATUS_MAP = {0: "等待中", 1: "运行中", 2: "已完成", 3: "失败"}
TASK_STATUS_MAP = {
    "pending": "等待中",
    "running": "运行中",
    "completed": "已完成",
    "failed": "失败",
    "cancelled": "已取消",
}
TYPE_MAP = {
    "save": "保存",
    "llm": "LLM",
    "update": "更新",
    "search": "搜索",
    "read": "读取",
    "rag": "RAG",
}

MAX_MSG_LEN = 1000
MAX_FULL_LEN = 4000
CATEGORY_MAP = {
    1: "个人纪录",
    2: "题解",
    3: "科技·工程",
    4: "算法·理论",
    5: "生活·游记",
    6: "学习·文化课",
    7: "休闲·娱乐",
    8: "闲话",
}

Result = Union[str, ImageResult]


async def _request(url: str, *, method: str = "GET", json_body=None, timeout: float = 15.0) -> dict:
    """Perform an HTTP request against the LGS API and return parsed JSON.

    On transport / HTTP errors, returns a dict containing an ``_error`` key with
    a human-readable Chinese message so the caller can surface it.
    """
    headers = {"User-Agent": "Uptime-Kuma"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method == "POST":
                resp = await client.post(url, headers=headers, json=json_body)
            else:
                resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("LGS API HTTP error for %s: %s", url, e)
        return {"_error": f"请求失败: HTTP {e.response.status_code}"}
    except httpx.RequestError as e:
        logger.error("LGS API network error for %s: %s", url, e)
        return {"_error": f"网络错误: {e}"}


async def handle_user_query(api_base: str, uid: str) -> AsyncGenerator[Result, None]:
    if not uid.isdigit():
        yield "用法: /lgs query user <数字ID>"
        return

    body = await _request(f"{api_base}/user/query/{uid}")
    if "_error" in body:
        yield body["_error"]
        return
    if body.get("code") != 200:
        yield f"查询失败: {body.get('message', '未知错误')}"
        return

    data = body.get("data")
    if not data:
        yield "用户不存在"
        return

    name = data.get("name", "?")
    color = COLOR_MAP.get(data.get("color", ""), data.get("color", "?"))
    ccf_level = data.get("ccfLevel", 0)
    xcpc_level = data.get("xcpcLevel", 0)
    slogan = data.get("slogan") or "(无签名)"

    lines = [
        f"用户: {name}",
        f"颜色: {color}",
        f"CCF 等级: {ccf_level}",
        f"XCPC 等级: {xcpc_level}",
        f"签名: {slogan}",
    ]
    yield "\n".join(lines)
    logger.info("LGS user query: %s -> %s", uid, name)


async def handle_user_update(api_base: str, uid: str) -> AsyncGenerator[Result, None]:
    if not uid.isdigit():
        yield "用法: /lgs update user <数字ID>"
        return

    body = await _request(f"{api_base}/user/{uid}/refresh", method="POST", timeout=30.0)
    if "_error" in body:
        yield body["_error"]
        return
    if body.get("code") != 200:
        yield f"刷新失败: {body.get('message', '未知错误')}"
        return

    task_id = body.get("data", {}).get("taskId")
    if not task_id:
        yield "刷新失败: 未返回 taskId"
        return

    yield f"用户 {uid} 资料刷新任务已派发 (taskId: {task_id})"
    logger.info("LGS user update: %s -> task %s", uid, task_id)


async def handle_article_update(api_base: str, article_id: str) -> AsyncGenerator[Result, None]:
    if not article_id:
        yield "用法: /lgs update article <文章ID>"
        return

    body = await _request(
        f"{api_base}/workflow/create/template/article-save-pipeline",
        method="POST",
        json_body={"targetId": article_id},
        timeout=30.0,
    )
    if "_error" in body:
        yield body["_error"]
        return
    if body.get("code") != 200:
        yield f"保存失败: {body.get('message', '未知错误')}"
        return

    data = body.get("data") or {}
    workflow_id = data.get("workflowId") or "(无)"
    task_ids = data.get("taskIds", {}) or {}

    lines = [f"文章 {article_id} 保存工作流已派发", f"工作流: {workflow_id}"]
    for label, key in [("保存", "save"), ("摘要", "summary"), ("审核", "censor"), ("向量化", "embedding")]:
        tid = task_ids.get(key)
        if tid:
            lines.append(f"{label}: {tid}")

    yield "\n".join(lines)
    logger.info("LGS article update: %s -> workflow %s", article_id, workflow_id)


async def handle_paste_update(api_base: str, paste_id: str) -> AsyncGenerator[Result, None]:
    if not paste_id:
        yield "用法: /lgs update paste <剪贴板ID>"
        return

    body = await _request(
        f"{api_base}/workflow/create/template/paste-save-pipeline",
        method="POST",
        json_body={"targetId": paste_id},
        timeout=30.0,
    )
    if "_error" in body:
        yield body["_error"]
        return
    if body.get("code") != 200:
        yield f"保存失败: {body.get('message', '未知错误')}"
        return

    data = body.get("data") or {}
    workflow_id = data.get("workflowId") or "(无)"
    task_ids = data.get("taskIds", {}) or {}

    lines = [f"剪贴板 {paste_id} 保存工作流已派发", f"工作流: {workflow_id}"]
    for label, key in [
        ("保存", "save"),
        ("摘要", "summary"),
        ("向量化", "embedding"),
        ("搜索索引", "update-search-index"),
    ]:
        tid = task_ids.get(key)
        if tid:
            lines.append(f"{label}: {tid}")

    yield "\n".join(lines)
    logger.info("LGS paste update: %s -> workflow %s", paste_id, workflow_id)


async def handle_task_query(api_base: str, task_id: str) -> AsyncGenerator[Result, None]:
    if not task_id:
        yield "用法: /lgs query task <任务ID>"
        return

    body = await _request(f"{api_base}/task/query/{task_id}")
    if "_error" in body:
        yield body["_error"]
        return
    if body.get("code") != 200:
        yield f"查询失败: {body.get('message', '未知错误')}"
        return

    data = body.get("data")
    if not data:
        yield "任务不存在"
        return

    tid = data.get("id", "?")
    ttype = TYPE_MAP.get(data.get("type", ""), data.get("type", "?"))
    status = STATUS_MAP.get(data.get("status"), f"未知({data.get('status')})")
    info = data.get("info") or "(无信息)"
    created = data.get("createdAt", "?")

    payload = data.get("payload") or {}
    target = payload.get("target", "")
    target_id = payload.get("targetId", "")

    lines = [f"任务: {tid}", f"类型: {ttype}", f"状态: {status}", f"信息: {info}", f"创建: {created}"]
    if target and target_id:
        lines.append(f"目标: {target} {target_id}")

    yield "\n".join(lines)
    logger.info("LGS task query: %s -> status=%s", task_id, data.get("status"))


async def handle_article_query(api_base: str, raw_arg: str, is_admin: bool) -> AsyncGenerator[Result, None]:
    if not raw_arg:
        yield "用法: /lgs query article <文章ID> [--page N] [--full]"
        return

    parts = raw_arg.split()
    article_id = parts[0]
    page = 1
    full = False
    html = False
    for i, p in enumerate(parts):
        if p == "--page" and i + 1 < len(parts) and parts[i + 1].isdigit():
            page = int(parts[i + 1])
        elif p == "--full":
            full = True
        elif p == "--html":
            html = True

    if page < 1:
        page = 1

    if full and not is_admin:
        yield "权限不足：--full 仅限管理员使用"
        return

    body = await _request(f"{api_base}/article/query/{article_id}")
    if "_error" in body:
        yield body["_error"]
        return
    if body.get("code") != 200:
        yield f"查询失败: {body.get('message', '未知错误')}"
        return

    data = body.get("data")
    if not data:
        yield "文章不存在"
        return

    title = data.get("title", "?")
    author = data.get("author", {}) or {}
    author_name = author.get("name", "?")
    category = CATEGORY_MAP.get(data.get("category"), "其它")
    tags = ", ".join(data.get("tags", []) or [])
    upvote = data.get("upvote", 0)
    favor = data.get("favorCount", 0)
    deleted = data.get("deleted", False)
    summary = data.get("summary") or ""
    updated = data.get("updatedAt", "?")[:10]

    content = data.get("content", "").strip()
    if not content:
        content = summary if summary else "(无正文)"

    if html:
        rendered = data.get("renderedContent")
        if not rendered:
            yield "该文章没有渲染内容"
            return
        yield "正在渲染为图片..."
        png = await render_html(rendered)
        yield ImageResult(png)
        logger.info("LGS article html render: %s (%d bytes)", article_id, len(png))
        return

    if full:
        info_lines = [
            f"标题: {title}",
            f"作者: {author_name}",
            f"分类: {category}",
            f"点赞: {upvote}  |  收藏: {favor}",
        ]
        if tags:
            info_lines.append(f"标签: {tags}")
        info_lines.append(f"更新: {updated}")
        if deleted:
            info_lines.append("⚠ 该文章已被删除")
        yield "\n".join(info_lines)

        while content:
            yield content[:MAX_FULL_LEN]
            content = content[MAX_FULL_LEN:]
        logger.info("LGS article full: %s -> %s", article_id, title)
        return

    total_chars = len(content)
    total_pages = max(1, (total_chars + MAX_MSG_LEN - 1) // MAX_MSG_LEN)
    if page > total_pages:
        page = total_pages

    if page == 1:
        info_lines = [
            f"标题: {title}",
            f"作者: {author_name}",
            f"分类: {category}",
            f"点赞: {upvote}  |  收藏: {favor}",
        ]
        if tags:
            info_lines.append(f"标签: {tags}")
        info_lines.append(f"更新: {updated}")
        if deleted:
            info_lines.append("⚠ 该文章已被删除")
        if total_pages > 1:
            info_lines.append(f"--- 第 1/{total_pages} 页 ---")
        yield "\n".join(info_lines)

    start = (page - 1) * MAX_MSG_LEN
    chunk = content[start: start + MAX_MSG_LEN]
    if page < total_pages:
        chunk += f"\n\n--- 第 {page}/{total_pages} 页 ---\n使用 /lgs query article {article_id} --page {page + 1} 获取下一页"
    else:
        chunk += f"\n\n--- 第 {page}/{total_pages} 页 --- 全文完 ---"

    yield chunk
    logger.info("LGS article query: %s -> %s (page %d/%d)", article_id, title, page, total_pages)


async def handle_paste_query(api_base: str, raw_arg: str, is_admin: bool) -> AsyncGenerator[Result, None]:
    if not raw_arg:
        yield "用法: /lgs query paste <剪贴板ID> [--page N] [--full]"
        return

    parts = raw_arg.split()
    paste_id = parts[0]
    page = 1
    full = False
    html = False
    for i, p in enumerate(parts):
        if p == "--page" and i + 1 < len(parts) and parts[i + 1].isdigit():
            page = int(parts[i + 1])
        elif p == "--full":
            full = True
        elif p == "--html":
            html = True

    if page < 1:
        page = 1

    if full and not is_admin:
        yield "权限不足：--full 仅限管理员使用"
        return

    body = await _request(f"{api_base}/paste/query/{paste_id}")
    if "_error" in body:
        yield body["_error"]
        return
    if body.get("code") != 200:
        yield f"查询失败: {body.get('message', '未知错误')}"
        return

    data = body.get("data")
    if not data:
        yield "剪贴板不存在"
        return

    author = data.get("author", {}) or {}
    author_name = author.get("name", "?")
    deleted = data.get("deleted", False)
    updated = data.get("updatedAt", "?")[:10]

    content = data.get("content", "").strip() or "(无内容)"

    if html:
        rendered = data.get("renderedContent")
        if not rendered:
            yield "该剪贴板没有渲染内容"
            return
        yield "正在渲染为图片..."
        png = await render_html(rendered)
        yield ImageResult(png)
        logger.info("LGS paste html render: %s (%d bytes)", paste_id, len(png))
        return

    if full:
        yield f"剪贴板: {paste_id}\n作者: {author_name}\n更新: {updated}" + ("\n⚠ 已删除" if deleted else "")
        while content:
            yield content[:MAX_FULL_LEN]
            content = content[MAX_FULL_LEN:]
        logger.info("LGS paste full: %s", paste_id)
        return

    total_chars = len(content)
    total_pages = max(1, (total_chars + MAX_MSG_LEN - 1) // MAX_MSG_LEN)
    if page > total_pages:
        page = total_pages

    if page == 1:
        info = f"剪贴板: {paste_id}\n作者: {author_name}\n更新: {updated}"
        if deleted:
            info += "\n⚠ 已删除"
        if total_pages > 1:
            info += f"\n--- 第 1/{total_pages} 页 ---"
        yield info

    start = (page - 1) * MAX_MSG_LEN
    chunk = content[start: start + MAX_MSG_LEN]
    if page < total_pages:
        chunk += f"\n\n--- 第 {page}/{total_pages} 页 ---\n使用 /lgs query paste {paste_id} --page {page + 1} 获取下一页"
    else:
        chunk += f"\n\n--- 第 {page}/{total_pages} 页 --- 全文完 ---"

    yield chunk
    logger.info("LGS paste query: %s (page %d/%d)", paste_id, page, total_pages)


async def handle_workflow_query(api_base: str, workflow_id: str) -> AsyncGenerator[Result, None]:
    if not workflow_id:
        yield "用法: /lgs query workflow <工作流ID>"
        return

    body = await _request(f"{api_base}/workflow/query/{workflow_id}", timeout=30.0)
    if "_error" in body:
        yield body["_error"]
        return
    if body.get("code") != 200:
        yield f"查询失败: {body.get('message', '未知错误')}"
        return

    data = body.get("data")
    if not data:
        yield "工作流不存在"
        return

    wf_id = data.get("workflowId") or "(无)"
    wf_status = TASK_STATUS_MAP.get(data.get("status"), data.get("status", "?"))
    lines = [f"工作流: {wf_id}", f"状态: {wf_status}"]

    tasks = data.get("tasks", []) or []
    if tasks:
        done = sum(1 for t in tasks if t.get("status") == "completed")
        lines.append(f"--- {len(tasks)} 个子任务（{done} 完成） ---")
        for t in tasks:
            tname = t.get("taskName") or "?"
            tstatus = TASK_STATUS_MAP.get(t.get("status"), t.get("status", "?"))
            ttype = t.get("type", "")
            lines.append(f"  [{ttype}] {tname}: {tstatus}")

    yield "\n".join(lines)
    logger.info("LGS workflow query: %s (%d tasks)", workflow_id, len(tasks))


async def dispatch_lgs(raw_text: str, is_admin: bool, api_base: str = API_BASE) -> AsyncGenerator[Result, None]:
    """Parse a raw ``/lgs ...`` message and yield reply chunks.

    Mirrors the original standalone-bot command router. ``is_admin`` replaces the
    old permission level check (only ``--full`` requires it).
    """
    text = raw_text.strip()
    if not text:
        return
    # AstrBot may or may not keep the leading "/" in message_str; handle both.
    body = text[1:] if text.startswith("/") else text
    parts = body.split(maxsplit=3)
    if not parts or parts[0].lower() != "lgs":
        return

    sub = parts[1].lower() if len(parts) > 1 else ""
    action = parts[2].lower() if len(parts) > 2 else ""
    arg = parts[3] if len(parts) > 3 else ""

    if sub == "query" and action == "user":
        async for r in handle_user_query(api_base, arg):
            yield r
    elif sub == "update" and action == "user":
        async for r in handle_user_update(api_base, arg):
            yield r
    elif sub == "query" and action == "task":
        async for r in handle_task_query(api_base, arg):
            yield r
    elif sub == "query" and action == "article":
        async for r in handle_article_query(api_base, arg, is_admin):
            yield r
    elif sub == "update" and action == "article":
        async for r in handle_article_update(api_base, arg):
            yield r
    elif sub == "query" and action == "paste":
        async for r in handle_paste_query(api_base, arg, is_admin):
            yield r
    elif sub == "update" and action == "paste":
        async for r in handle_paste_update(api_base, arg):
            yield r
    elif sub == "query" and action == "workflow":
        async for r in handle_workflow_query(api_base, arg):
            yield r
    else:
        yield (
            "用法: /lgs <query|update> <user|article|paste|task|workflow> ...\n"
            "  /lgs query user <ID>\n"
            "  /lgs update user <ID>\n"
            "  /lgs query article <ID> [--page N] [--full]\n"
            "  /lgs update article <ID>\n"
            "  /lgs query paste <ID> [--page N] [--full]\n"
            "  /lgs update paste <ID>\n"
            "  /lgs query task <ID>\n"
            "  /lgs query workflow <ID>"
        )
