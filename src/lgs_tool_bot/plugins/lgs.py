import base64
import logging

import httpx

from lgs_tool_bot.bot import Bot
from lgs_tool_bot.browser import render_html
from lgs_tool_bot.onebot.models import OneBotEvent

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


async def handle_user_query(bot: Bot, event: OneBotEvent, uid: str):
    if not uid.isdigit():
        await bot.send_msg(event, "用法: /lgs query user <数字ID>")
        return

    url = f"{API_BASE}/user/query/{uid}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Uptime-Kuma"},
            )
            resp.raise_for_status()
            body = resp.json()
    except httpx.RequestError as e:
        logger.error("LGS API error: %s", e)
        await bot.send_msg(event, f"网络错误: {e}")
        return
    except httpx.HTTPStatusError as e:
        await bot.send_msg(event, f"请求失败: HTTP {e.response.status_code}")
        return

    if body.get("code") != 200:
        await bot.send_msg(event, f"查询失败: {body.get('message', '未知错误')}")
        return

    data = body.get("data")
    if not data:
        await bot.send_msg(event, "用户不存在")
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
    await bot.send_msg(event, "\n".join(lines))
    logger.info("LGS user query: %s -> %s", uid, name)


async def handle_user_update(bot: Bot, event: OneBotEvent, uid: str):
    if not uid.isdigit():
        await bot.send_msg(event, "用法: /lgs update user <数字ID>")
        return

    url = f"{API_BASE}/user/{uid}/refresh"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                headers={"User-Agent": "Uptime-Kuma"},
            )
            resp.raise_for_status()
            body = resp.json()
    except httpx.RequestError as e:
        logger.error("LGS API error: %s", e)
        await bot.send_msg(event, f"网络错误: {e}")
        return
    except httpx.HTTPStatusError as e:
        await bot.send_msg(event, f"请求失败: HTTP {e.response.status_code}")
        return

    if body.get("code") != 200:
        await bot.send_msg(event, f"刷新失败: {body.get('message', '未知错误')}")
        return

    task_id = body.get("data", {}).get("taskId")
    if not task_id:
        await bot.send_msg(event, "刷新失败: 未返回 taskId")
        return

    await bot.send_msg(event, f"用户 {uid} 资料刷新任务已派发 (taskId: {task_id})")
    logger.info("LGS user update: %s -> task %s", uid, task_id)


async def handle_article_update(bot: Bot, event: OneBotEvent, article_id: str):
    if not article_id:
        await bot.send_msg(event, "用法: /lgs update article <文章ID>")
        return

    url = f"{API_BASE}/workflow/create/template/article-save-pipeline"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                json={"targetId": article_id},
                headers={"User-Agent": "Uptime-Kuma"},
            )
            resp.raise_for_status()
            body = resp.json()
    except httpx.RequestError as e:
        logger.error("LGS API error: %s", e)
        await bot.send_msg(event, f"网络错误: {e}")
        return
    except httpx.HTTPStatusError as e:
        await bot.send_msg(event, f"请求失败: HTTP {e.response.status_code}")
        return

    if body.get("code") != 200:
        await bot.send_msg(event, f"保存失败: {body.get('message', '未知错误')}")
        return

    data = body.get("data") or {}
    workflow_id = data.get("workflowId") or "(无)"
    task_ids = data.get("taskIds", {}) or {}

    lines = [f"文章 {article_id} 保存工作流已派发", f"工作流: {workflow_id}"]
    for label, key in [("保存", "save"), ("摘要", "summary"), ("审核", "censor"), ("向量化", "embedding")]:
        tid = task_ids.get(key)
        if tid:
            lines.append(f"{label}: {tid}")

    await bot.send_msg(event, "\n".join(lines))
    logger.info("LGS article update: %s -> workflow %s", article_id, workflow_id)


async def handle_paste_update(bot: Bot, event: OneBotEvent, paste_id: str):
    if not paste_id:
        await bot.send_msg(event, "用法: /lgs update paste <剪贴板ID>")
        return

    url = f"{API_BASE}/workflow/create/template/paste-save-pipeline"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                json={"targetId": paste_id},
                headers={"User-Agent": "Uptime-Kuma"},
            )
            resp.raise_for_status()
            body = resp.json()
    except httpx.RequestError as e:
        logger.error("LGS API error: %s", e)
        await bot.send_msg(event, f"网络错误: {e}")
        return
    except httpx.HTTPStatusError as e:
        await bot.send_msg(event, f"请求失败: HTTP {e.response.status_code}")
        return

    if body.get("code") != 200:
        await bot.send_msg(event, f"保存失败: {body.get('message', '未知错误')}")
        return

    data = body.get("data") or {}
    workflow_id = data.get("workflowId") or "(无)"
    task_ids = data.get("taskIds", {}) or {}

    lines = [f"剪贴板 {paste_id} 保存工作流已派发", f"工作流: {workflow_id}"]
    for label, key in [("保存", "save"), ("摘要", "summary"), ("向量化", "embedding"), ("搜索索引", "update-search-index")]:
        tid = task_ids.get(key)
        if tid:
            lines.append(f"{label}: {tid}")

    await bot.send_msg(event, "\n".join(lines))
    logger.info("LGS paste update: %s -> workflow %s", paste_id, workflow_id)


STATUS_MAP = {0: "等待中", 1: "运行中", 2: "已完成", 3: "失败"}
TASK_STATUS_MAP = {"pending": "等待中", "running": "运行中", "completed": "已完成", "failed": "失败", "cancelled": "已取消"}
TYPE_MAP = {
    "save": "保存",
    "llm": "LLM",
    "update": "更新",
    "search": "搜索",
    "read": "读取",
    "rag": "RAG",
}


async def handle_task_query(bot: Bot, event: OneBotEvent, task_id: str):
    if not task_id:
        await bot.send_msg(event, "用法: /lgs query task <任务ID>")
        return

    url = f"{API_BASE}/task/query/{task_id}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Uptime-Kuma"},
            )
            resp.raise_for_status()
            body = resp.json()
    except httpx.RequestError as e:
        logger.error("LGS API error: %s", e)
        await bot.send_msg(event, f"网络错误: {e}")
        return
    except httpx.HTTPStatusError as e:
        await bot.send_msg(event, f"请求失败: HTTP {e.response.status_code}")
        return

    if body.get("code") != 200:
        await bot.send_msg(event, f"查询失败: {body.get('message', '未知错误')}")
        return

    data = body.get("data")
    if not data:
        await bot.send_msg(event, "任务不存在")
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

    await bot.send_msg(event, "\n".join(lines))
    logger.info("LGS task query: %s -> status=%s", task_id, data.get("status"))


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


async def handle_article_query(bot: Bot, event: OneBotEvent, raw_arg: str):
    if not raw_arg:
        await bot.send_msg(event, "用法: /lgs query article <文章ID> [--page N] [--full]")
        return

    parts = raw_arg.split()
    article_id = parts[0]
    page = 1
    full = False
    for i, p in enumerate(parts):
        if p == "--page" and i + 1 < len(parts) and parts[i + 1].isdigit():
            page = int(parts[i + 1])
        elif p == "--full":
            full = True
        elif p == "--html":
            html = True

    if page < 1:
        page = 1

    if (full or html) and not await bot.require_permission(event, 1):
        return

    url = f"{API_BASE}/article/query/{article_id}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Uptime-Kuma"},
            )
            resp.raise_for_status()
            body = resp.json()
    except httpx.RequestError as e:
        logger.error("LGS API error: %s", e)
        await bot.send_msg(event, f"网络错误: {e}")
        return
    except httpx.HTTPStatusError as e:
        await bot.send_msg(event, f"请求失败: HTTP {e.response.status_code}")
        return

    if body.get("code") != 200:
        await bot.send_msg(event, f"查询失败: {body.get('message', '未知错误')}")
        return

    data = body.get("data")
    if not data:
        await bot.send_msg(event, "文章不存在")
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
            await bot.send_msg(event, "该文章没有渲染内容")
            return
        await bot.send_msg(event, "正在渲染为图片...")
        png = await render_html(rendered)
        b64 = base64.b64encode(png).decode()
        await bot.send_image(event, f"base64://{b64}")
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
        await bot.send_msg(event, "\n".join(info_lines))

        while content:
            await bot.send_msg(event, content[:MAX_FULL_LEN])
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
        await bot.send_msg(event, "\n".join(info_lines))

    start = (page - 1) * MAX_MSG_LEN
    chunk = content[start: start + MAX_MSG_LEN]
    if page < total_pages:
        chunk += f"\n\n--- 第 {page}/{total_pages} 页 ---\n使用 /lgs query article {article_id} --page {page + 1} 获取下一页"
    else:
        chunk += f"\n\n--- 第 {page}/{total_pages} 页 --- 全文完 ---"

    await bot.send_msg(event, chunk)
    logger.info("LGS article query: %s -> %s (page %d/%d)", article_id, title, page, total_pages)


async def handle_paste_query(bot: Bot, event: OneBotEvent, raw_arg: str):
    if not raw_arg:
        await bot.send_msg(event, "用法: /lgs query paste <剪贴板ID> [--page N] [--full]")
        return

    parts = raw_arg.split()
    paste_id = parts[0]
    page = 1
    full = False
    for i, p in enumerate(parts):
        if p == "--page" and i + 1 < len(parts) and parts[i + 1].isdigit():
            page = int(parts[i + 1])
        elif p == "--full":
            full = True
        elif p == "--html":
            html = True

    if page < 1:
        page = 1

    if (full or html) and not await bot.require_permission(event, 1):
        return

    url = f"{API_BASE}/paste/query/{paste_id}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Uptime-Kuma"},
            )
            resp.raise_for_status()
            body = resp.json()
    except httpx.RequestError as e:
        logger.error("LGS API error: %s", e)
        await bot.send_msg(event, f"网络错误: {e}")
        return
    except httpx.HTTPStatusError as e:
        await bot.send_msg(event, f"请求失败: HTTP {e.response.status_code}")
        return

    if body.get("code") != 200:
        await bot.send_msg(event, f"查询失败: {body.get('message', '未知错误')}")
        return

    data = body.get("data")
    if not data:
        await bot.send_msg(event, "剪贴板不存在")
        return

    author = data.get("author", {}) or {}
    author_name = author.get("name", "?")
    deleted = data.get("deleted", False)
    updated = data.get("updatedAt", "?")[:10]

    content = data.get("content", "").strip() or "(无内容)"

    if html:
        rendered = data.get("renderedContent")
        if not rendered:
            await bot.send_msg(event, "该剪贴板没有渲染内容")
            return
        await bot.send_msg(event, "正在渲染为图片...")
        png = await render_html(rendered)
        b64 = base64.b64encode(png).decode()
        await bot.send_image(event, f"base64://{b64}")
        logger.info("LGS paste html render: %s (%d bytes)", paste_id, len(png))
        return

    if full:
        await bot.send_msg(event, f"剪贴板: {paste_id}\n作者: {author_name}\n更新: {updated}" + ("\n⚠ 已删除" if deleted else ""))
        while content:
            await bot.send_msg(event, content[:MAX_FULL_LEN])
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
        await bot.send_msg(event, info)

    start = (page - 1) * MAX_MSG_LEN
    chunk = content[start: start + MAX_MSG_LEN]
    if page < total_pages:
        chunk += f"\n\n--- 第 {page}/{total_pages} 页 ---\n使用 /lgs query paste {paste_id} --page {page + 1} 获取下一页"
    else:
        chunk += f"\n\n--- 第 {page}/{total_pages} 页 --- 全文完 ---"

    await bot.send_msg(event, chunk)
    logger.info("LGS paste query: %s (page %d/%d)", paste_id, page, total_pages)


async def handle_workflow_query(bot: Bot, event: OneBotEvent, workflow_id: str):
    if not workflow_id:
        await bot.send_msg(event, "用法: /lgs query workflow <工作流ID>")
        return

    url = f"{API_BASE}/workflow/query/{workflow_id}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Uptime-Kuma"},
            )
            resp.raise_for_status()
            body = resp.json()
    except httpx.RequestError as e:
        logger.error("LGS API error: %s", e)
        await bot.send_msg(event, f"网络错误: {e}")
        return
    except httpx.HTTPStatusError as e:
        await bot.send_msg(event, f"请求失败: HTTP {e.response.status_code}")
        return

    if body.get("code") != 200:
        await bot.send_msg(event, f"查询失败: {body.get('message', '未知错误')}")
        return

    data = body.get("data")
    if not data:
        await bot.send_msg(event, "工作流不存在")
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

    await bot.send_msg(event, "\n".join(lines))
    logger.info("LGS workflow query: %s (%d tasks)", workflow_id, len(tasks))


async def handler(bot: Bot, event: OneBotEvent):
    text = event.plain_text.strip()
    if not text.startswith("/"):
        return

    parts = text[1:].split(maxsplit=3)
    if len(parts) < 1 or parts[0].lower() != "lgs":
        return

    sub = parts[1].lower() if len(parts) > 1 else ""
    action = parts[2].lower() if len(parts) > 2 else ""
    arg = parts[3] if len(parts) > 3 else ""

    if sub == "query" and action == "user":
        await handle_user_query(bot, event, arg)
    elif sub == "update" and action == "user":
        await handle_user_update(bot, event, arg)
    elif sub == "query" and action == "task":
        await handle_task_query(bot, event, arg)
    elif sub == "query" and action == "article":
        await handle_article_query(bot, event, arg)
    elif sub == "update" and action == "article":
        await handle_article_update(bot, event, arg)
    elif sub == "query" and action == "paste":
        await handle_paste_query(bot, event, arg)
    elif sub == "update" and action == "paste":
        await handle_paste_update(bot, event, arg)
    elif sub == "query" and action == "workflow":
        await handle_workflow_query(bot, event, arg)


def register(bot: Bot):
    bot.register(handler)
