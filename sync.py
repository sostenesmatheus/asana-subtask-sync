"""
Copia comentarios e anexos de subtarefas para a tarefa principal no Asana.
Roda via GitHub Actions a cada 15 minutos.
"""
import os
import httpx

TOKEN = os.environ["ASANA_TOKEN"]
PROJECT_GID = os.environ.get("PROJECT_GID") or "1211036990943103"
BASE = "https://app.asana.com/api/1.0"
MARKER = "[sync-subtask]"  # incluido em cada comentario copiado para evitar duplicatas


def api(method, path, **kwargs):
    r = httpx.request(
        method,
        f"{BASE}{path}",
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=30,
        **kwargs,
    )
    r.raise_for_status()
    return r.json().get("data", [])


def get_tasks():
    return api("GET", f"/projects/{PROJECT_GID}/tasks", params={"opt_fields": "gid,name"})


def get_subtasks(task_gid):
    return api("GET", f"/tasks/{task_gid}/subtasks", params={"opt_fields": "gid,name,notes"})


def get_stories(task_gid):
    return api("GET", f"/tasks/{task_gid}/stories", params={"opt_fields": "gid,type,text"})


def get_attachments(task_gid):
    return api(
        "GET",
        f"/tasks/{task_gid}/attachments",
        params={"opt_fields": "gid,name,download_url,view_url"},
    )


def post_comment(task_gid, text):
    api("POST", f"/tasks/{task_gid}/stories", json={"data": {"text": text}})


def sync_notes(sub_gid, parent_notes):
    api("PUT", f"/tasks/{sub_gid}", json={"data": {"notes": parent_notes}})


def copy_attachment(task_gid, name, download_url):
    with httpx.Client(timeout=60, follow_redirects=True) as c:
        file_r = c.get(download_url, headers={"Authorization": f"Bearer {TOKEN}"})
        c.post(
            f"{BASE}/attachments",
            headers={"Authorization": f"Bearer {TOKEN}"},
            data={"parent": task_gid},
            files={"file": (name, file_r.content)},
        )


def already_synced(parent_stories, story_gid):
    needle = f"{MARKER}:{story_gid}"
    return any(needle in (s.get("text") or "") for s in parent_stories)


def attachment_exists(parent_attachments, name):
    return any(a.get("name") == name for a in parent_attachments)


def main():
    tasks = get_tasks()
    print(f"{len(tasks)} tarefas no projeto")

    total_comments = 0
    total_attachments = 0

    for task in tasks:
        task_gid = task["gid"]

        subtasks = get_subtasks(task_gid)
        if not subtasks:
            continue

        parent_stories = get_stories(task_gid)
        parent_attachments = get_attachments(task_gid)
        parent_notes = api("GET", f"/tasks/{task_gid}", params={"opt_fields": "notes"}).get("notes") or ""

        for sub in subtasks:
            sub_gid = sub["gid"]
            sub_name = sub.get("name", "subtarefa")

            # --- Descricao ---
            if not sub.get("notes") and parent_notes:
                sync_notes(sub_gid, parent_notes)
                print(f"  descricao copiada para subtarefa '{sub_name}'")

            # --- Comentarios ---
            for story in get_stories(sub_gid):
                if story.get("type") != "comment":
                    continue
                story_gid = story["gid"]
                if already_synced(parent_stories, story_gid):
                    continue

                text = (
                    f"[Comentario de '{sub_name}']\n\n"
                    f"{story['text']}\n\n"
                    f"{MARKER}:{story_gid}"
                )
                post_comment(task_gid, text)
                parent_stories.append({"text": text})
                total_comments += 1
                print(f"  comentario copiado ({story_gid}) da subtarefa '{sub_name}'")

            # --- Anexos ---
            for att in get_attachments(sub_gid):
                att_name = att.get("name", "arquivo")
                download_url = att.get("download_url")
                if not download_url:
                    continue
                if attachment_exists(parent_attachments, att_name):
                    continue

                try:
                    copy_attachment(task_gid, att_name, download_url)
                    post_comment(task_gid, f"[Anexo de '{sub_name}']: {att_name}")
                    parent_attachments.append({"name": att_name})
                    total_attachments += 1
                    print(f"  anexo copiado '{att_name}' da subtarefa '{sub_name}'")
                except Exception as e:
                    view_url = att.get("view_url") or download_url
                    post_comment(
                        task_gid,
                        f"[Anexo de '{sub_name}']: {att_name}\n{view_url}",
                    )
                    print(f"  nao foi possivel copiar '{att_name}', adicionado link: {e}")

    print(f"\nPronto: {total_comments} comentarios, {total_attachments} anexos sincronizados.")


if __name__ == "__main__":
    main()
