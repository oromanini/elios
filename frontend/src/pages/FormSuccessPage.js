import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import Logo from '../components/Logo';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { CheckCircle2, Mail, ArrowRight } from 'lucide-react';

const FormSuccessPage = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen login-bg flex items-center justify-center p-4">
      <div className="grid-overlay" />
      
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-md z-10"
      >
        <div className="flex justify-center mb-8">
          <Logo size="md" />
        </div>

        <Card className="glass-card border-white/10">
          <CardContent className="p-8 text-center">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: 'spring' }}
              className="w-20 h-20 mx-auto mb-6 rounded-full bg-green-500/20 flex items-center justify-center"
            >
              <CheckCircle2 className="w-10 h-10 text-green-500" />
            </motion.div>

            <h1 className="text-2xl font-bold text-white mb-4">
              Formulário Enviado com Sucesso!
            </h1>

            <div className="glass rounded-lg p-4 mb-6">
              <div className="flex items-center justify-center gap-3 text-primary mb-2">
                <Mail size={20} />
                <span className="font-medium">Verifique seu Email</span>
              </div>
              <p className="text-slate-400 text-sm">
                Enviamos suas credenciais de acesso para o email informado.
              </p>
            </div>

            <div className="space-y-4 text-left">
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-primary text-sm font-bold">1</span>
                </div>
                <p className="text-slate-300 text-sm">
                  Aguarde a aprovação do administrador para ativar sua conta.
                </p>
              </div>
              
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-primary text-sm font-bold">2</span>
                </div>
                <p className="text-slate-300 text-sm">
                  Você receberá uma notificação quando sua conta estiver ativa.
                </p>
              </div>
              
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-primary text-sm font-bold">3</span>
                </div>
                <p className="text-slate-300 text-sm">
                  Após a aprovação, acesse o sistema com as credenciais enviadas.
                </p>
              </div>
            </div>

            <Button
              onClick={() => navigate('/')}
              className="w-full mt-8 btn-primary"
              data-testid="go-to-login"
            >
              Ir para Login
              <ArrowRight className="ml-2" size={18} />
            </Button>
          </CardContent>
        </Card>

        <p className="text-center text-slate-500 text-sm mt-8">
          HUTOO EDUCAÇÃO © {new Date().getFullYear()} - Programa Elite
        </p>
      </motion.div>
    </div>
  );
};

export default FormSuccessPage;
