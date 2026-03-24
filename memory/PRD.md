# ELIOS - Sistema de Performance Elite

## Problem Statement
Sistema de gerenciamento de membros para o programa de performance Elite da HUTOO EDUCAÇÃO, com assistente de IA (ELIOS) treinável.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn/UI + Framer Motion
- **Backend**: FastAPI + Motor (MongoDB async)
- **Database**: MongoDB
- **AI**: Provedor configurável (DeepSeek/Groq) via API compatível com OpenAI
- **Email**: Hostinger SMTP

## User Personas
1. **Admin**: Gerencia usuários, perguntas e treina o ELIOS
2. **Membro Elite**: Usuário do programa que usa o sistema para acompanhar metas

## Core Requirements
- [x] Sistema de login com JWT (ADMIN/DEFAULT)
- [x] Formulário step-by-step com 12 perguntas (11 Pilares + Meta Magnus)
- [x] Criação automática de usuário após formulário (inativo até admin aprovar)
- [x] Envio de email com credenciais temporárias
- [x] Dashboard com gráfico radar dos pilares
- [x] Chat com ELIOS (assistente IA)
- [x] Análise em tempo real das respostas do formulário
- [x] CRUD de metas com soft delete e histórico
- [x] Admin: gerenciar usuários (ativar/desativar)
- [x] Admin: editar perguntas do formulário
- [x] Admin: treinar ELIOS (base de conhecimento)

## What's Implemented (Jan 2026)
1. ✅ Login page com autenticação JWT
2. ✅ Formulário step-by-step /form com 14 etapas
3. ✅ Dashboard com gráfico radar dos 12 pilares
4. ✅ Página de Pilares com abas e accordion
5. ✅ Chat com ELIOS (GPT-5.2)
6. ✅ Gerenciamento de Metas (CRUD + histórico)
7. ✅ Admin: Gerenciar Usuários
8. ✅ Admin: Editar Perguntas
9. ✅ Admin: Treinar ELIOS
10. ✅ Envio de email via Hostinger SMTP
11. ✅ Design dark navy com acentos azul elétrico

## Credentials
- **Admin**: admin@hutooeducacao.com / Admin@123

## Prioritized Backlog

### P0 (Critical) - Done
- All core features implemented

### P1 (High Priority)
- [ ] Password reset functionality
- [ ] Email notification when admin activates user
- [ ] Export goals to PDF

### P2 (Medium Priority)
- [ ] Goal reminders/notifications
- [ ] Progress reports (weekly/monthly)
- [ ] Integration with calendar for goal deadlines

### P3 (Low Priority)
- [ ] Mobile app
- [ ] Multi-language support
- [ ] Custom themes

## Next Tasks
1. Fix OpenAI API quota issue (user needs to recharge their API key)
2. Add password reset flow
3. Add email notification when user is activated
4. Implement progress tracking over time
