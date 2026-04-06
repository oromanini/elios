import React, { useEffect, useMemo, useState } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { adminAPI } from '../services/api';
import { toast } from 'sonner';
import { CalendarDays, Filter, Search, Users } from 'lucide-react';

const PILLARS_WITH_META_MAGNUS = [
  'ESPIRITUALIDADE',
  'CUIDADOS COM A SAÚDE',
  'EQUILÍBRIO EMOCIONAL',
  'LAZER',
  'GESTÃO DO TEMPO E ORGANIZAÇÃO',
  'DESENVOLVIMENTO INTELECTUAL',
  'IMAGEM PESSOAL',
  'FAMÍLIA',
  'CRESCIMENTO PROFISSIONAL',
  'FINANÇAS',
  'NETWORKING E CONTRIBUIÇÃO',
  'META MAGNUS'
];

const AdminMentoradosPage = () => {
  const [responses, setResponses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    name: '',
    email: '',
    registered_from: '',
    registered_to: ''
  });

  const loadResponses = async (filterValues = filters) => {
    setLoading(true);
    try {
      const params = Object.fromEntries(
        Object.entries(filterValues).filter(([, value]) => value && String(value).trim() !== '')
      );
      const response = await adminAPI.getUsersFormResponses(params);
      setResponses(response.data || []);
    } catch (error) {
      toast.error('Erro ao carregar respostas dos mentorados');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadResponses();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const completedFormsCount = useMemo(
    () => responses.filter((item) => item.form_completed).length,
    [responses]
  );

  const handleFilterChange = (field, value) => {
    setFilters((prev) => ({ ...prev, [field]: value }));
  };

  const handleApplyFilters = () => {
    loadResponses(filters);
  };

  const handleClearFilters = () => {
    const resetFilters = {
      name: '',
      email: '',
      registered_from: '',
      registered_to: ''
    };
    setFilters(resetFilters);
    loadResponses(resetFilters);
  };

  return (
    <Layout>
      <div className="space-y-6" data-testid="admin-mentorados-page">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-white flex items-center gap-3">
            <Users className="text-primary" />
            Respostas dos Mentorados
          </h1>
          <p className="text-slate-400 mt-1">
            Visualize os 11 pilares + Meta Magnus de todos os usuários comuns.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="glass-card border-white/10">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-primary/20 flex items-center justify-center">
                <Users className="text-primary" size={24} />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{responses.length}</p>
                <p className="text-slate-400 text-sm">Mentorados encontrados</p>
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card border-white/10">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-green-500/20 flex items-center justify-center">
                <CalendarDays className="text-green-400" size={24} />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{completedFormsCount}</p>
                <p className="text-slate-400 text-sm">Formulários concluídos</p>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="glass-card border-white/10">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2 text-lg">
              <Filter size={18} className="text-primary" /> Filtros
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
              <div className="relative">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <Input
                  value={filters.name}
                  onChange={(e) => handleFilterChange('name', e.target.value)}
                  placeholder="Filtrar por nome"
                  className="pl-9 bg-slate-900/50 border-slate-700 text-white"
                />
              </div>

              <Input
                value={filters.email}
                onChange={(e) => handleFilterChange('email', e.target.value)}
                placeholder="Filtrar por email"
                className="bg-slate-900/50 border-slate-700 text-white"
              />

              <Input
                type="date"
                value={filters.registered_from}
                onChange={(e) => handleFilterChange('registered_from', e.target.value)}
                className="bg-slate-900/50 border-slate-700 text-white"
              />

              <Input
                type="date"
                value={filters.registered_to}
                onChange={(e) => handleFilterChange('registered_to', e.target.value)}
                className="bg-slate-900/50 border-slate-700 text-white"
              />
            </div>

            <div className="flex flex-wrap gap-2">
              <Button onClick={handleApplyFilters} className="bg-primary hover:bg-primary/90 text-white">
                Aplicar filtros
              </Button>
              <Button variant="outline" onClick={handleClearFilters} className="border-slate-700 text-slate-300">
                Limpar
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          {loading ? (
            <div className="flex items-center justify-center h-56">
              <div className="spinner" />
            </div>
          ) : responses.length === 0 ? (
            <Card className="glass-card border-white/10">
              <CardContent className="p-8 text-center text-slate-400">
                Nenhum mentorado encontrado com os filtros atuais.
              </CardContent>
            </Card>
          ) : (
            responses.map((user) => (
              <Card key={user.user_id} className="glass-card border-white/10">
                <CardHeader>
                  <CardTitle className="text-white text-base md:text-lg">
                    {user.full_name}
                  </CardTitle>
                  <p className="text-sm text-slate-400">
                    {user.email} • Cadastro: {new Date(user.created_at).toLocaleDateString('pt-BR')}
                  </p>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                    {PILLARS_WITH_META_MAGNUS.map((pillar) => (
                      <div key={`${user.user_id}-${pillar}`} className="rounded-lg border border-white/10 bg-slate-900/30 p-3">
                        <p className="text-xs uppercase tracking-wide text-primary font-semibold mb-2">
                          {pillar}
                        </p>
                        <p className="text-sm text-slate-200 whitespace-pre-wrap">
                          {user.responses_by_pillar?.[pillar] || 'Sem resposta enviada.'}
                        </p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>
    </Layout>
  );
};

export default AdminMentoradosPage;
