import React from 'react';
import { Link } from 'react-router-dom';
import Logo from '../components/Logo';
import { PRIVACY_POLICY_EFFECTIVE_DATE, PRIVACY_POLICY_VERSION } from '../config/privacyPolicy';

const PrivacyPolicyPage = () => {
  return (
    <div className="min-h-screen login-bg py-8 px-4">
      <div className="grid-overlay" />
      <div className="max-w-4xl mx-auto relative z-10">
        <div className="flex justify-center mb-8">
          <Logo size="md" />
        </div>

        <article className="glass-card border border-white/10 rounded-xl p-6 md:p-8 text-slate-200 space-y-6">
          <header className="space-y-2">
            <h1 className="text-3xl font-bold text-white">Política de Privacidade — ELIOS</h1>
            <p className="text-slate-400">
              Versão {PRIVACY_POLICY_VERSION} • Vigência: {PRIVACY_POLICY_EFFECTIVE_DATE}
            </p>
          </header>

          <section className="space-y-2">
            <h2 className="text-xl font-semibold text-white">1. Quem somos</h2>
            <p>
              Esta política descreve como a plataforma ELIOS, da HUTOO EDUCAÇÃO, realiza o tratamento de dados
              pessoais em conformidade com a Lei Geral de Proteção de Dados (LGPD).
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-xl font-semibold text-white">2. Dados que coletamos</h2>
            <ul className="list-disc pl-6 space-y-1">
              <li>Dados cadastrais: nome completo, e-mail e data de nascimento.</li>
              <li>Dados opcionais: foto de perfil enviada pelo usuário.</li>
              <li>Dados de conteúdo: respostas do formulário e metas detectadas.</li>
              <li>Dados técnicos: registros de acesso e segurança da aplicação.</li>
            </ul>
          </section>

          <section className="space-y-2">
            <h2 className="text-xl font-semibold text-white">3. Finalidades de uso</h2>
            <ul className="list-disc pl-6 space-y-1">
              <li>Executar cadastro e autenticação.</li>
              <li>Permitir análises e personalização da jornada do usuário.</li>
              <li>Manter comunicação operacional sobre o serviço.</li>
              <li>Cumprir obrigações legais e proteger a plataforma contra uso indevido.</li>
            </ul>
          </section>

          <section className="space-y-2">
            <h2 className="text-xl font-semibold text-white">4. Bases legais</h2>
            <p>
              Tratamos dados com base em execução de contrato, legítimo interesse, cumprimento de obrigação legal e,
              quando necessário, consentimento específico do titular.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-xl font-semibold text-white">5. Compartilhamento</h2>
            <p>
              Os dados podem ser compartilhados com operadores essenciais para funcionamento do serviço (infraestrutura,
              comunicação e suporte), sempre sob obrigações de confidencialidade e segurança.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-xl font-semibold text-white">6. Retenção e descarte</h2>
            <p>
              Os dados são mantidos pelo tempo necessário às finalidades desta política e obrigações legais, com
              descarte seguro ou anonimização quando aplicável.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-xl font-semibold text-white">7. Direitos do titular</h2>
            <p>
              Você pode solicitar confirmação de tratamento, acesso, correção, anonimização, eliminação e portabilidade
              de dados, além de revogação de consentimento quando aplicável.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-xl font-semibold text-white">8. Atualizações desta política</h2>
            <p>
              Podemos atualizar esta política periodicamente. Quando houver mudanças relevantes, a nova versão será
              disponibilizada nesta página.
            </p>
          </section>

          <footer className="pt-4 border-t border-white/10">
            <Link to="/" className="text-primary hover:underline">
              Voltar para o login
            </Link>
          </footer>
        </article>
      </div>
    </div>
  );
};

export default PrivacyPolicyPage;
