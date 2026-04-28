# ELIOS

Plataforma com:
- **Backend** em FastAPI + MongoDB.
- **Frontend** em React (CRA + CRACO).
- **Agente de IA ELIOS** com suporte a múltiplos provedores (DeepSeek e Groq).

## Estrutura do projeto

- `backend/server.py`: API principal (auth, formulário, metas, admin, chat IA).
- `backend/requirements.txt`: dependências Python.
- `frontend/src`: aplicação React.
- `docker-compose.yml`: stack local com MongoDB + backend + frontend.
- `SECURITY_REVIEW.md`: análise de segurança inicial.

## IA (ELIOS + Groq)

O backend usa Groq como provedor padrão de IA.

Variáveis relevantes:

- `GROQ_API_KEY`
- `GROQ_BASE_URL` (padrão: `https://api.groq.com/openai/v1`)
- `GROQ_MODEL` (padrão: `llama-3.3-70b-versatile`)

> **Importante:** não versionar chaves reais em arquivo. Use `.env` local e secret manager no GCP.

## Subir local com Docker

1. Copie o template de ambiente:

```bash
cp .env.example .env
```

2. Preencha as chaves em `.env`.

3. Inicie os serviços:

```bash
docker compose up --build
```

Serviços:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000/api
- MongoDB: localhost:27017

## Deploy futuro no GCP (diretriz)

- **Cloud Run** para frontend e backend (containers separados).
- **Artifact Registry** para imagens.
- **Secret Manager** para `JWT_SECRET`, `GROQ_API_KEY`, SMTP e demais segredos.
- **MongoDB Atlas** (ou alternativa gerenciada) com IP/VPC restrita.

## Segurança

Consulte `SECURITY_REVIEW.md` para prioridades e plano de mitigação.

## CI de testes e bloqueio de merge

Foi adicionado o workflow GitHub Actions `.github/workflows/tests.yml`, que executa:

```bash
pytest -q tests/test_auth_flow.py
```

em `pull_request` e `push` para `main`.

Para **impedir merge quando teste falhar**, ative no GitHub:

1. `Settings` → `Branches` → `Add branch protection rule`.
2. Selecione a branch `main`.
3. Marque **Require status checks to pass before merging**.
4. Adicione o check obrigatório: **test-backend-auth** (job do workflow de testes).
5. (Opcional, recomendado) marque **Require branches to be up to date before merging**.
