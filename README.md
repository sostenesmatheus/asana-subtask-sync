# Asana Subtask Sync

Sincroniza automaticamente comentarios e anexos de subtarefas para a tarefa principal no Asana.

## Como funciona

1. Um webhook do Asana notifica o servidor quando um comentario ou anexo e adicionado a qualquer tarefa do projeto
2. O servidor verifica se a tarefa tem uma tarefa pai (ou seja, e uma subtarefa)
3. Se sim, o comentario ou anexo e copiado para a tarefa pai automaticamente

## Deploy no Render (recomendado — gratis)

1. Faca fork deste repositorio
2. Acesse [render.com](https://render.com) e crie uma conta gratuita
3. Clique em **New > Web Service** e conecte o repositorio
4. Configure as variaveis de ambiente:

| Variavel | Descricao |
|----------|-----------|
| `ASANA_TOKEN` | Token pessoal da API do Asana |
| `PROJECT_GID` | GID do projeto Asana a monitorar |
| `BASE_URL` | URL publica do servidor (ex: `https://meu-app.onrender.com`) |

5. Clique em **Deploy**

## Registrar o webhook

Apos o deploy, registre o webhook no Asana com uma requisicao POST:

```bash
curl -X POST https://seu-app.onrender.com/setup
```

Ou acesse `https://seu-app.onrender.com/docs` para usar a interface interativa.

## Endpoints

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/` | GET | Health check |
| `/webhook` | POST | Recebe eventos do Asana |
| `/setup` | POST | Registra o webhook no projeto |

## Rodar localmente

```bash
pip install -r requirements.txt
cp .env.example .env
# Edite o .env com seus dados
uvicorn main:app --reload
```
