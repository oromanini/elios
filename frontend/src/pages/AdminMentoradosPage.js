import React, { useEffect, useMemo, useState } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../components/ui/accordion';
import { adminAPI } from '../services/api';
import { toast } from 'sonner';
import { CalendarDays, Filter, Save, Search, Target, Users } from 'lucide-react';

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
  const [goalDrafts, setGoalDrafts] = useState({});
  const [savingGoals, setSavingGoals] = useState({});
  const [selectedUserId, setSelectedUserId] = useState('');

  const loadResponses = async (filterValues = filters) => {
    setLoading(true);
    try {
      const params = Object.fromEntries(
        Object.entries(filterValues).filter(([, value]) => value && String(value).trim() !== '')
      );
      const response = await adminAPI.getUsersFormResponses(params);
      const loadedResponses = response.data || [];
      setResponses(loadedResponses);
      setSelectedUserId((prevSelected) => {
        if (!loadedResponses.length) return '';
        const hasPreviousSelection = loadedResponses.some((item) => String(item.user_id) === prevSelected);
        return hasPreviousSelection ? prevSelected : String(loadedResponses[0].user_id);
      });
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
  const selectedUser = useMemo(
    () => responses.find((item) => String(item.user_id) === selectedUserId) || null,
    [responses, selectedUserId]
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

  const formatDateForInput = (value) => {
    if (!value) return '';
    return value.slice(0, 10);
  };

  const handleGoalFieldChange = (goalId, field, value) => {
    setGoalDrafts((prev) => ({
      ...prev,
      [goalId]: {
        ...(prev[goalId] || {}),
        [field]: value
      }
    }));
  };

  const handleSaveGoal = async (userId, goal) => {
    const draft = goalDrafts[goal.id];
    if (!draft || Object.keys(draft).length === 0) {
      toast.info('Nenhuma alteração para salvar nesta meta');
      return;
    }

    setSavingGoals((prev) => ({ ...prev, [goal.id]: true }));
    try {
      await adminAPI.updateUserGoal(userId, goal.id, draft);
      toast.success('Meta atualizada com sucesso');
      setGoalDrafts((prev) => {
        const next = { ...prev };
        delete next[goal.id];
        return next;
      });
      loadResponses(filters);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao atualizar meta');
    } finally {
      setSavingGoals((prev) => ({ ...prev, [goal.id]: false }));
    }
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
            <>
              <Card className="glass-card border-white/10">
                <CardHeader>
                  <CardTitle className="text-white text-base md:text-lg">Selecionar mentorado</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <p className="text-sm text-slate-400">
                    Escolha o nome do usuário para visualizar as respostas do formulário e as metas.
                  </p>
                  <select
                    value={selectedUserId}
                    onChange={(e) => setSelectedUserId(e.target.value)}
                    className="h-10 w-full rounded-md border border-slate-700 bg-slate-900/50 px-3 text-sm text-white"
                  >
                    {responses.map((user) => (
                      <option key={user.user_id} value={String(user.user_id)}>
                        {user.full_name} ({user.email})
                      </option>
                    ))}
                  </select>
                </CardContent>
              </Card>

              {selectedUser ? (
                <Card key={selectedUser.user_id} className="glass-card border-white/10">
                  <CardHeader>
                    <CardTitle className="text-white text-base md:text-lg">
                      {selectedUser.full_name}
                    </CardTitle>
                    <p className="text-sm text-slate-400">
                      {selectedUser.email} • Cadastro: {new Date(selectedUser.created_at).toLocaleDateString('pt-BR')}
                    </p>
                  </CardHeader>
                  <CardContent>
                  <Accordion type="single" collapsible className="space-y-3">
                    {PILLARS_WITH_META_MAGNUS.map((pillar) => (
                      <AccordionItem
                        key={`${selectedUser.user_id}-${pillar}`}
                        value={`${selectedUser.user_id}-${pillar}`}
                        className="rounded-lg border border-white/10 bg-slate-900/30 px-3"
                      >
                        <AccordionTrigger className="text-xs uppercase tracking-wide text-primary font-semibold hover:no-underline">
                          {pillar}
                        </AccordionTrigger>
                        <AccordionContent className="space-y-4 pb-4">
                          <div>
                            <p className="text-[11px] uppercase tracking-wide text-slate-400 mb-2">Resposta</p>
                            <p className="text-sm text-slate-200 whitespace-pre-wrap">
                              {selectedUser.responses_by_pillar?.[pillar] || 'Sem resposta enviada.'}
                            </p>
                          </div>

                          <div className="space-y-3">
                            <p className="text-[11px] uppercase tracking-wide text-slate-400 flex items-center gap-2">
                              <Target size={14} className="text-primary" /> Metas do usuário
                            </p>

                            {(selectedUser.goals_by_pillar?.[pillar] || []).length === 0 ? (
                              <p className="text-sm text-slate-400">Nenhuma meta cadastrada neste pilar.</p>
                            ) : (
                              selectedUser.goals_by_pillar[pillar].map((goal) => (
                                <div key={goal.id} className="rounded-md border border-white/10 bg-black/20 p-3 space-y-2">
                                  <Input
                                    value={goalDrafts[goal.id]?.title ?? goal.title}
                                    onChange={(e) => handleGoalFieldChange(goal.id, 'title', e.target.value)}
                                    className="bg-slate-900/50 border-slate-700 text-white"
                                    placeholder="Título da meta"
                                  />
                                  <Textarea
                                    value={goalDrafts[goal.id]?.description ?? goal.description}
                                    onChange={(e) => handleGoalFieldChange(goal.id, 'description', e.target.value)}
                                    className="bg-slate-900/50 border-slate-700 text-white min-h-[96px]"
                                    placeholder="Descrição da meta"
                                  />
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                    <Input
                                      type="date"
                                      value={goalDrafts[goal.id]?.target_date ?? formatDateForInput(goal.target_date)}
                                      onChange={(e) => handleGoalFieldChange(goal.id, 'target_date', e.target.value)}
                                      className="bg-slate-900/50 border-slate-700 text-white"
                                    />
                                    <select
                                      value={goalDrafts[goal.id]?.status ?? goal.status}
                                      onChange={(e) => handleGoalFieldChange(goal.id, 'status', e.target.value)}
                                      className="h-10 rounded-md border border-slate-700 bg-slate-900/50 px-3 text-sm text-white"
                                    >
                                      <option value="active">Ativa</option>
                                      <option value="completed">Concluída</option>
                                    </select>
                                  </div>
                                  <Button
                                    onClick={() => handleSaveGoal(selectedUser.user_id, goal)}
                                    disabled={savingGoals[goal.id]}
                                    className="bg-primary hover:bg-primary/90 text-white"
                                  >
                                    <Save size={15} className="mr-2" />
                                    {savingGoals[goal.id] ? 'Salvando...' : 'Salvar meta'}
                                  </Button>
                                </div>
                              ))
                            )}
                          </div>
                        </AccordionContent>
                      </AccordionItem>
                    ))}
                  </Accordion>
                  </CardContent>
                </Card>
              ) : null}
            </>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default AdminMentoradosPage;
