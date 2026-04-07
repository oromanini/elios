# Security Review (OWASP) - ELIOS

Data da varredura: 2026-04-07
Escopo:
- Backend FastAPI (`backend/server.py`)
- Frontend React (`frontend/src`)
- Infra/deploy (`docker-compose.yml`, `terraform/*`)

## Metodologia (OWASP ASVS + OWASP Top 10)
- Revisão estática de autenticação, autorização, validação de entrada, tratamento de erro e exposição de dados.
- Busca de segredos e configurações inseguras no repositório.
- Revisão de pontos de risco em transporte/armazenamento de tokens no frontend.

## Achados e status

### 1) Autenticação e sessão (A07 / V2)

**Antes da correção**
- JWT sem expiração explícita.
- Fallback inseguro de `JWT_SECRET` possível em produção.
- Sem proteção contra brute force em `/api/auth/login`.

**Correções aplicadas**
- Token JWT com `iat` e `exp` (configurável via `JWT_EXP_HOURS`, padrão 12h).
- Bloqueio de inicialização em produção quando `JWT_SECRET` está no valor padrão.
- Rate limiting em memória por email+IP no login (`MAX_LOGIN_ATTEMPTS` e `LOGIN_WINDOW_MINUTES`).

### 2) Credenciais e senhas (A02/A07 / V2)

**Antes da correção**
- Senhas com baixa complexidade podiam ser aceitas em alguns fluxos.

**Correções aplicadas**
- Política mínima: 10+ caracteres, maiúscula, minúscula e número.
- Validação aplicada em:
  - cadastro público com senha explícita,
  - troca de senha,
  - criação de admin.
- Fluxo de **esqueci minha senha** com token de uso único e expiração (`/api/auth/forgot-password` e `/api/auth/reset-password`).

### 3) Exposição de superfícies de setup (A01 / V4)

**Antes da correção**
- Endpoints `/api/init/admin` e `/api/init/questions` podiam ser usados indevidamente em produção.

**Correções aplicadas**
- Em produção, endpoints de inicialização exigem `INIT_SETUP_TOKEN`; sem token configurado, ficam desativados.

### 4) Vazamento de informação em erros (A09 / V10)

**Antes da correção**
- Erros de integração com IA podiam retornar detalhes internos ao usuário.

**Correções aplicadas**
- Mensagens externas padronizadas e seguras.
- Detalhes técnicos mantidos apenas em log do servidor.

## Riscos ainda abertos (não corrigidos neste patch)

1. **Token em `localStorage` no frontend**
   - Risco: em caso de XSS, um invasor pode ler o token.
   - Recomendação: migrar para cookie `HttpOnly` + `Secure` + `SameSite`.

2. **Arquivos de estado Terraform no repositório**
   - `terraform.tfstate` e backups estão versionados.
   - Risco: estado pode conter metadados e, dependendo dos recursos, segredos.
   - Recomendação: remover do git, rotacionar credenciais e usar backend remoto seguro (S3/GCS/TF Cloud + criptografia + locking).

3. **Rate limiting em memória**
   - Em ambiente multi-instância não é compartilhado.
   - Recomendação: mover para Redis (chaves por IP, email e rota), com observabilidade.

4. **CORS permissivo por padrão em algumas implantações**
   - Recomendação: definir `CORS_ORIGINS` explicitamente por ambiente e sem wildcard em produção.

## Checklist rápido (produção)
- [ ] `JWT_SECRET` forte, único e rotacionado.
- [ ] `INIT_SETUP_TOKEN` definido ou endpoints `/init/*` desabilitados por gateway.
- [ ] `CORS_ORIGINS` explícito (sem `*`).
- [ ] Redis para rate limiting distribuído.
- [ ] Cookies `HttpOnly` para sessão no frontend.
- [ ] Terraform state fora do git e com criptografia.
