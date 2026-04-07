import React, { useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Logo from '../components/Logo';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { toast } from 'sonner';
import { Loader2, ArrowLeft } from 'lucide-react';
import { authAPI } from '../services/api';

const ForgotPasswordPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const tokenFromUrl = searchParams.get('token') || '';
  const isResetMode = useMemo(() => !!tokenFromUrl, [tokenFromUrl]);

  const [email, setEmail] = useState('');
  const [token, setToken] = useState(tokenFromUrl);
  const [newPassword, setNewPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleForgotSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      const response = await authAPI.forgotPassword(email);
      toast.success(response.data?.message || 'Se o email existir, enviaremos as instruções.');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Não foi possível processar sua solicitação.');
    } finally {
      setLoading(false);
    }
  };

  const handleResetSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      const response = await authAPI.resetPassword(token, newPassword);
      toast.success(response.data?.message || 'Senha redefinida com sucesso.');
      navigate('/');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Não foi possível redefinir sua senha.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen login-bg flex items-center justify-center p-4">
      <div className="grid-overlay" />

      <div className="w-full max-w-md z-10 slide-up">
        <div className="flex justify-center mb-8">
          <Logo size="lg" />
        </div>

        <Card className="glass-card border-white/10">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl text-white">
              {isResetMode ? 'Redefinir senha' : 'Esqueci minha senha'}
            </CardTitle>
            <CardDescription className="text-neutral-500">
              {isResetMode
                ? 'Informe o token e crie uma nova senha.'
                : 'Digite seu email para receber as instruções de redefinição.'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isResetMode ? (
              <form onSubmit={handleResetSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="token" className="text-neutral-500 uppercase text-xs tracking-wide">Token</Label>
                  <Input
                    id="token"
                    value={token}
                    onChange={(event) => setToken(event.target.value)}
                    required
                    className="bg-neutral-900/50 border-neutral-800 text-white placeholder:text-neutral-600 h-12"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="new-password" className="text-neutral-500 uppercase text-xs tracking-wide">Nova senha</Label>
                  <Input
                    id="new-password"
                    type="password"
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                    placeholder="mín. 10 caracteres com letras e número"
                    required
                    className="bg-neutral-900/50 border-neutral-800 text-white placeholder:text-neutral-600 h-12"
                  />
                </div>
                <Button type="submit" disabled={loading} className="w-full h-12 btn-primary">
                  {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin text-black" /> : null}
                  Redefinir senha
                </Button>
              </form>
            ) : (
              <form onSubmit={handleForgotSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-neutral-500 uppercase text-xs tracking-wide">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                    className="bg-neutral-900/50 border-neutral-800 text-white placeholder:text-neutral-600 h-12"
                  />
                </div>
                <Button type="submit" disabled={loading} className="w-full h-12 btn-primary">
                  {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin text-black" /> : null}
                  Enviar instruções
                </Button>
              </form>
            )}

            <Button
              variant="ghost"
              className="w-full mt-4 text-neutral-400 hover:text-white"
              onClick={() => navigate('/')}
            >
              <ArrowLeft className="mr-2" size={16} />
              Voltar para o login
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ForgotPasswordPage;
