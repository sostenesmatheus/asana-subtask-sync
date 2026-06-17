# Asana Subtask Sync

Copia automaticamente comentarios e anexos de subtarefas para a tarefa principal no Asana.

Roda via **GitHub Actions** a cada 15 minutos — sem servidor, sem deploy.

## Como funciona

1. O GitHub Actions executa `sync.py` a cada 15 minutos
2. O script percorre todas as tarefas do projeto
3. Para cada subtarefa, verifica se ha comentarios ou anexos novos
4. Copia o que for novo para a tarefa principal (deduplicacao automatica por ID)

## Configuracao

1. Va em **Settings > Secrets and variables > Actions** no repositorio
2. Adicione dois secrets:

| Secret | Valor |
|--------|-------|
| `ASANA_TOKEN` | Seu token pessoal da API do Asana |
| `PROJECT_GID` | GID do projeto Asana a monitorar |

3. Pronto. O sync roda automaticamente a cada 15 minutos.

Para rodar manualmente: **Actions > Asana Subtask Sync > Run workflow**.

## Rodar localmente

```bash
pip install httpx
ASANA_TOKEN=seu_token PROJECT_GID=seu_gid python sync.py
```
