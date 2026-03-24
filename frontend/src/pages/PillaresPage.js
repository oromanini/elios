import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../components/ui/accordion';
import { Button } from '../components/ui/button';
import { formAPI, goalsAPI } from '../services/api';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import {
  Hexagon,
  Target,
  MessageSquare,
  Plus,
  Edit2,
  CheckCircle2,
  Clock
} from 'lucide-react';

const PILLARS = [
  { id: 'ESPIRITUALIDADE', name: 'Espiritualidade', icon: '🙏', color: 'pillar-espiritualidade' },
  { id: 'CUIDADOS COM A SAÚDE', name: 'Saúde', icon: '💪', color: 'pillar-saude' },
  { id: 'EQUILÍBRIO EMOCIONAL', name: 'Emocional', icon: '🧘', color: 'pillar-emocional' },
  { id: 'LAZER', name: 'Lazer', icon: '🎯', color: 'pillar-lazer' },
  { id: 'GESTÃO DO TEMPO E ORGANIZAÇÃO', name: 'Tempo', icon: '⏰', color: 'pillar-tempo' },
  { id: 'DESENVOLVIMENTO INTELECTUAL', name: 'Intelectual', icon: '📚', color: 'pillar-intelectual' },
  { id: 'IMAGEM PESSOAL', name: 'Imagem', icon: '✨', color: 'pillar-imagem' },
  { id: 'FAMÍLIA', name: 'Família', icon: '👨‍👩‍👧‍👦', color: 'pillar-familia' },
  { id: 'CRESCIMENTO PROFISSIONAL', name: 'Profissional', icon: '📈', color: 'pillar-profissional' },
  { id: 'FINANÇAS', name: 'Finanças', icon: '💰', color: 'pillar-financas' },
  { id: 'NETWORKING E CONTRIBUIÇÃO', name: 'Networking', icon: '🤝', color: 'pillar-networking' },
  { id: 'META MAGNUS', name: 'Meta Magnus', icon: '🎯', color: 'pillar-magnus' }
];

const PillaresPage = () => {
  const navigate = useNavigate();
  const [responses, setResponses] = useState([]);
  const [goals, setGoals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState(PILLARS[0].id);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [responsesRes, goalsRes] = await Promise.all([
        formAPI.getResponses(),
        goalsAPI.getAll()
      ]);
      setResponses(responsesRes.data);
      setGoals(goalsRes.data);
    } catch (error) {
      toast.error('Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  };

  const getPillarResponse = (pillarId) => {
    return responses.find(r => r.question?.pillar === pillarId);
  };

  const getPillarGoals = (pillarId) => {
    return goals.filter(g => g.pillar === pillarId);
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="spinner" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6" data-testid="pillars-page">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-white flex items-center gap-3">
              <Hexagon className="text-primary" />
              11 Pilares + Meta Magnus
            </h1>
            <p className="text-slate-400 mt-1">
              Visualize e gerencie seus objetivos em cada área da vida
            </p>
          </div>
        </div>

        {/* Pillar Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <div className="overflow-x-auto pb-2">
            <TabsList className="inline-flex h-auto p-1 bg-slate-900/50 rounded-lg gap-1 min-w-max">
              {PILLARS.map((pillar) => (
                <TabsTrigger
                  key={pillar.id}
                  value={pillar.id}
                  className="px-3 py-2 text-sm data-[state=active]:bg-primary data-[state=active]:text-primary-foreground rounded-sm whitespace-nowrap"
                  data-testid={`pillar-tab-${pillar.id}`}
                >
                  <span className="mr-2">{pillar.icon}</span>
                  {pillar.name}
                </TabsTrigger>
              ))}
            </TabsList>
          </div>

          {PILLARS.map((pillar) => {
            const response = getPillarResponse(pillar.id);
            const pillarGoals = getPillarGoals(pillar.id);
            
            return (
              <TabsContent key={pillar.id} value={pillar.id} className="mt-6">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Original Response */}
                  <Card className={`glass-card border-white/10 border-l-4 ${pillar.color}`}>
                    <CardHeader>
                      <CardTitle className="text-lg text-white flex items-center justify-between">
                        <span className="flex items-center gap-2">
                          <span className="text-2xl">{pillar.icon}</span>
                          {pillar.name}
                        </span>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => navigate('/chat', { state: { context: pillar.id } })}
                          className="text-primary hover:text-primary/80"
                          data-testid={`chat-about-${pillar.id}`}
                        >
                          <MessageSquare size={16} className="mr-1" />
                          Falar com ELIOS
                        </Button>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div>
                          <p className="text-slate-400 text-sm uppercase tracking-wider mb-2">
                            Resposta do Formulário Inicial
                          </p>
                          {response ? (
                            <p className="text-slate-300 whitespace-pre-wrap">
                              {response.answer}
                            </p>
                          ) : (
                            <p className="text-slate-500 italic">
                              Nenhuma resposta registrada para este pilar.
                            </p>
                          )}
                        </div>

                        {response && (
                          <div className="pt-4 border-t border-white/10">
                            <p className="text-xs text-slate-500">
                              Preenchido em: {new Date(response.created_at).toLocaleDateString('pt-BR')}
                              {response.version > 1 && ` (v${response.version})`}
                            </p>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Goals for this pillar */}
                  <Card className="glass-card border-white/10">
                    <CardHeader>
                      <CardTitle className="text-lg text-white flex items-center justify-between">
                        <span className="flex items-center gap-2">
                          <Target size={20} className="text-primary" />
                          Metas deste Pilar
                        </span>
                        <Button
                          size="sm"
                          onClick={() => navigate('/metas', { state: { pillar: pillar.id } })}
                          className="btn-primary"
                          data-testid={`add-goal-${pillar.id}`}
                        >
                          <Plus size={16} className="mr-1" />
                          Nova Meta
                        </Button>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {pillarGoals.length > 0 ? (
                        <div className="space-y-3">
                          {pillarGoals.map((goal) => (
                            <div
                              key={goal.id}
                              className="glass rounded-lg p-4 goal-card"
                            >
                              <div className="flex items-start justify-between gap-4">
                                <div className="flex-1">
                                  <div className="flex items-center gap-2 mb-1">
                                    {goal.status === 'completed' ? (
                                      <CheckCircle2 size={16} className="text-green-500" />
                                    ) : (
                                      <Clock size={16} className="text-amber-500" />
                                    )}
                                    <h4 className="font-medium text-white">{goal.title}</h4>
                                  </div>
                                  <p className="text-slate-400 text-sm line-clamp-2">
                                    {goal.description}
                                  </p>
                                  {goal.target_date && (
                                    <p className="text-xs text-slate-500 mt-2">
                                      Meta: {new Date(goal.target_date).toLocaleDateString('pt-BR')}
                                    </p>
                                  )}
                                </div>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => navigate('/metas', { state: { editGoal: goal.id } })}
                                  className="text-slate-400 hover:text-white"
                                >
                                  <Edit2 size={14} />
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-center py-8">
                          <Target className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                          <p className="text-slate-500">
                            Nenhuma meta definida para este pilar.
                          </p>
                          <Button
                            variant="link"
                            onClick={() => navigate('/metas', { state: { pillar: pillar.id } })}
                            className="text-primary mt-2"
                          >
                            Criar primeira meta
                          </Button>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>
            );
          })}
        </Tabs>

        {/* All Responses Accordion */}
        <Card className="glass-card border-white/10 mt-8">
          <CardHeader>
            <CardTitle className="text-lg text-white">
              Todas as Respostas do Formulário
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Accordion type="single" collapsible className="space-y-2">
              {PILLARS.map((pillar) => {
                const response = getPillarResponse(pillar.id);
                return (
                  <AccordionItem
                    key={pillar.id}
                    value={pillar.id}
                    className="glass rounded-lg border-none"
                  >
                    <AccordionTrigger className="px-4 py-3 hover:no-underline hover:bg-white/5 rounded-lg">
                      <span className="flex items-center gap-3">
                        <span className="text-xl">{pillar.icon}</span>
                        <span className="text-white">{pillar.name}</span>
                        {response && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-primary/20 text-primary">
                            Preenchido
                          </span>
                        )}
                      </span>
                    </AccordionTrigger>
                    <AccordionContent className="px-4 pb-4">
                      {response ? (
                        <p className="text-slate-300 whitespace-pre-wrap">
                          {response.answer}
                        </p>
                      ) : (
                        <p className="text-slate-500 italic">
                          Sem resposta registrada.
                        </p>
                      )}
                    </AccordionContent>
                  </AccordionItem>
                );
              })}
            </Accordion>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default PillaresPage;
