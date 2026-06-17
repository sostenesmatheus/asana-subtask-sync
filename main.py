import os
import httpx
from fastapi import FastAPI, Request, Response, Header
from fastapi.responses import JSONResponse

app = FastAPI(title="Asana Subtask Sync")

ASANA_TOKEN = os.environ.get("ASANA_TOKEN", "")
PROJECT_GID = os.environ.get("PROJECT_GID", "")
BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")
ASANA_BASE = "https://app.asana.com/api/1.0"


def _headers():
    return {"Authorization": f"Bearer {ASANA_TOKEN}", "Accept": "application/json"}


async def get_task_parent(task_gid: str):
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"{ASANA_BASE}/tasks/{task_gid}",
            headers=_headers(),
            params={"opt_fields": "gid,name,parent.gid,parent.name"},
        )
        data = r.json().get("data", {})
        parent = data.get("parent")
        return (parent.get("gid") if parent else None), data.get("name", "")


async def get_story(story_gid: str):
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"{ASANA_BASE}/stories/{story_gid}",
            headers=_headers(),
            params={"opt_fields": "gid,text,type"},
        )
        return r.json().get("data")


async def post_comment(task_gid: str, text: str):
    async with httpx.AsyncClient(timeout=15) as c:
        await c.post(
            f"{ASANA_BASE}/tasks/{task_gid}/stories",
            headers={**_headers(), "Content-Type": "application/json"},
            json={"data": {"text": text}},
        )


async def get_attachment(att_gid: str):
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"{ASANA_BASE}/attachments/{att_gid}",
            headers=_headers(),
            params={"opt_fields": "gid,name,download_url,view_url,host"},
        )
        return r.json().get("data")


async def copy_attachment(task_gid: str, name: str, download_url: str):
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as c:
        file_r = await c.get(download_url, headers=_headers())
        await c.post(
            f"{ASANA_BASE}/attachments",
            headers={"Authorization": f"Bearer {ASANA_TOKEN}"},
            data={"parent": task_gid},
            files={"file": (name, file_r.content)},
        )


@app.post("/webhook")
async def webhook(
    request: Request,
    x_hook_secret: str = Header(default=None, alias="X-Hook-Secret"),
):
    # Handshake inicial do Asana
    if x_hook_secret:
        return Response(status_code=200, headers={"X-Hook-Secret": x_hook_secret})

    payload = await request.json()

    for event in payload.get("events", []):
        resource_type = event.get("resource", {}).get("resource_type")
        action = event.get("action")
        resource_gid = event.get("resource", {}).get("gid")
        task_gid = event.get("parent", {}).get("gid")

        if action != "added" or not task_gid:
            continue

        # Verifica se a tarefa é uma subtarefa (tem pai)
        parent_gid, subtask_name = await get_task_parent(task_gid)
        if not parent_gid:
            continue

        # Comentario adicionado na subtarefa -> copiar para tarefa pai
        if resource_type == "story":
            story = await get_story(resource_gid)
            if story and story.get("type") == "comment" and story.get("text"):
                text = f"[Comentario da subtarefa '{subtask_name}']\n\n{story['text']}"
                await post_comment(parent_gid, text)

        # Anexo adicionado na subtarefa -> copiar para tarefa pai
        elif resource_type == "attachment":
            att = await get_attachment(resource_gid)
            if not att:
                continue
            att_name = att.get("name", "arquivo")
            download_url = att.get("download_url")
            if download_url:
                try:
                    await copy_attachment(parent_gid, att_name, download_url)
                    await post_comment(
                        parent_gid,
                        f"[Anexo da subtarefa '{subtask_name}']: {att_name}",
                    )
                except Exception:
                    view_url = att.get("view_url") or download_url
                    await post_comment(
                        parent_gid,
                        f"[Anexo da subtarefa '{subtask_name}']: {att_name}\n{view_url}",
                    )

    return JSONResponse({"ok": True})


@app.post("/setup")
async def setup():
    """Registra o webhook no projeto Asana."""
    if not PROJECT_GID or not BASE_URL:
        return JSONResponse(
            {"error": "Defina as variaveis PROJECT_GID e BASE_URL"}, status_code=400
        )
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(
            f"{ASANA_BASE}/webhooks",
            headers={**_headers(), "Content-Type": "application/json"},
            json={
                "data": {
                    "resource": PROJECT_GID,
                    "target": f"{BASE_URL}/webhook",
                    "filters": [
                        {"resource_type": "story", "action": "added"},
                        {"resource_type": "attachment", "action": "added"},
                    ],
                }
            },
        )
        return r.json()


@app.get("/")
async def health():
    return {"status": "ok", "service": "asana-subtask-sync"}
