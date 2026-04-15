import React from 'react';
import { Button } from './ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from './ui/dialog';
import { PRIVACY_POLICY_EFFECTIVE_DATE } from '../config/privacyPolicy';

const PrivacyPolicyDialog = ({ open, onOpenChange, onAccept }) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] bg-slate-950 border-white/10 text-white overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Política de Privacidade do ELIOS</DialogTitle>
          <DialogDescription>
            Vigente desde {PRIVACY_POLICY_EFFECTIVE_DATE}. Leia os pontos principais abaixo.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 text-sm text-slate-300">
          <section>
            <h3 className="font-semibold text-white mb-1">1) Dados tratados</h3>
            <p>
              Nome, e-mail, data de nascimento, foto de perfil (opcional) e respostas do formulário
              para construção da trilha de acompanhamento.
            </p>
          </section>
          <section>
            <h3 className="font-semibold text-white mb-1">2) Finalidades</h3>
            <p>
              Cadastro, autenticação, personalização da experiência, geração de análises e comunicação
              sobre o serviço.
            </p>
          </section>
          <section>
            <h3 className="font-semibold text-white mb-1">3) Compartilhamento e segurança</h3>
            <p>
              Os dados podem ser processados por operadores contratados para hospedagem, infraestrutura e
              comunicação, com medidas de segurança e confidencialidade.
            </p>
          </section>
          <section>
            <h3 className="font-semibold text-white mb-1">4) Direitos do titular</h3>
            <p>
              Você pode solicitar acesso, correção, anonimização, eliminação e portabilidade dos dados,
              além de revogar consentimentos quando aplicável.
            </p>
          </section>
          <p className="text-slate-400">
            Para ler a versão completa, acesse a página “Política de Privacidade”.
          </p>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="border-white/30 text-white hover:bg-white/10"
          >
            Fechar
          </Button>
          <Button onClick={onAccept} className="btn-primary">
            Li e aceito
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default PrivacyPolicyDialog;
