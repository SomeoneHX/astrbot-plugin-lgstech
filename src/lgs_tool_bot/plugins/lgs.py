import logging

import httpx

from lgs_tool_bot.bot import Bot
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


STATUS_MAP = {0: "等待中", 1: "运行中", 2: "已完成", 3: "失败"}
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


async def handler(bot: Bot, event: OneBotEvent):
    text = event.plain_text.strip()
    if not text.startswith("/"):
        return

    parts = text[1:].split(maxsplit=4)
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


def register(bot: Bot):
    bot.register(handler)
