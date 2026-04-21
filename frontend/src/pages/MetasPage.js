import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '../components/ui/alert-dialog';
import { goalsAPI } from '../services/api';
import { toast } from 'sonner';
import {
  Target,
  Plus,
  Edit2,
  Trash2,
  CheckCircle2,
  Clock,
  History,
  X
} from 'lucide-react';

const PILLARS = [
  { id: 'ESPIRITUALIDADE', name: 'Espiritualidade', icon: '🙏' },
  { id: 'CUIDADOS COM A SAÚDE', name: 'Cuidados com a Saúde', icon: '💪' },
  { id: 'EQUILÍBRIO EMOCIONAL', name: 'Equilíbrio Emocional', icon: '🧘' },
  { id: 'LAZER', name: 'Lazer', icon: '🎯' },
  { id: 'GESTÃO DO TEMPO E ORGANIZAÇÃO', name: 'Gestão do Tempo', icon: '⏰' },
  { id: 'DESENVOLVIMENTO INTELECTUAL', name: 'Desenvolvimento Intelectual', icon: '📚' },
  { id: 'IMAGEM PESSOAL', name: 'Imagem Pessoal', icon: '✨' },
  { id: 'FAMÍLIA', name: 'Família', icon: '👨‍👩‍👧‍👦' },
  { id: 'CRESCIMENTO PROFISSIONAL', name: 'Crescimento Profissional', icon: '📈' },
  { id: 'FINANÇAS', name: 'Finanças', icon: '💰' },
  { id: 'NETWORKING E CONTRIBUIÇÃO', name: 'Networking', icon: '🤝' },
  { id: 'META MAGNUS', name: 'Meta Magnus', icon: '🎯' }
];

const MetasPage = () => {
  const location = useLocation();
  const [goals, setGoals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [historyDialogOpen, setHistoryDialogOpen] = useState(false);
  const [selectedGoal, setSelectedGoal] = useState(null);
  const [goalHistory, setGoalHistory] = useState([]);
  const [filter, setFilter] = useState('all');

  // Form state
  const [formData, setFormData] = useState({
    pillar: '',
    title: '',
    description: '',
    status: 'active'
  });

  useEffect(() => {
    loadGoals();
    
    // Check if we should pre-fill pillar from navigation
    if (location.state?.pillar) {
      setFormData(prev => ({ ...prev, pillar: location.state.pillar }));
      setDialogOpen(true);
    }
  }, [location.state]);

  const loadGoals = async () => {
    try {
      const response = await goalsAPI.getAll();
      setGoals(response.data);
    } catch (error) {
      toast.error('Erro ao carregar metas');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!formData.pillar || !formData.title) {
      toast.error('Preencha os campos obrigatórios');
      return;
    }

    try {
      if (selectedGoal) {
        await goalsAPI.update(selectedGoal.id, formData);
        toast.success('Meta atualizada com sucesso');
      } else {
        await goalsAPI.create(formData);
        toast.success('Meta criada com sucesso');
      }
      
      loadGoals();
      handleCloseDialog();
    } catch (error) {
      toast.error('Erro ao salvar meta');
    }
  };

  const handleDelete = async (goalId) => {
    try {
      await goalsAPI.delete(goalId);
      toast.success('Meta excluída com sucesso');
      loadGoals();
    } catch (error) {
      toast.error('Erro ao excluir meta');
    }
  };

  const handleToggleComplete = async (goal) => {
    try {
      const newStatus = goal.status === 'completed' ? 'active' : 'completed';
      await goalsAPI.update(goal.id, { status: newStatus });
      toast.success(newStatus === 'completed' ? 'Meta concluída!' : 'Meta reativada');
      loadGoals();
    } catch (error) {
      toast.error('Erro ao atualizar meta');
    }
  };

  const handleViewHistory = async (goal) => {
    try {
      const response = await goalsAPI.getHistory(goal.id);
      setGoalHistory(response.data);
      setSelectedGoal(goal);
      setHistoryDialogOpen(true);
    } catch (error) {
      toast.error('Erro ao carregar histórico');
    }
  };

  const handleEdit = (goal) => {
    setSelectedGoal(goal);
    setFormData({
      pillar: goal.pillar,
      title: goal.title,
      description: goal.description,
      status: goal.status
    });
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setSelectedGoal(null);
    setFormData({
      pillar: '',
      title: '',
      description: '',
      status: 'active'
    });
  };

  const filteredGoals = goals.filter(goal => {
    if (filter === 'all') return true;
    if (filter === 'active') return goal.status === 'active';
    if (filter === 'completed') return goal.status === 'completed';
    return goal.pillar === filter;
  });

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
      <div className="space-y-6" data-testid="goals-page">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-white flex items-center gap-3">
              <Target className="text-primary" />
              Gerenciar Metas
            </h1>
            <p className="text-slate-400 mt-1">
              Crie, edite e acompanhe suas metas em cada pilar
            </p>
          </div>
          <Button
            onClick={() => setDialogOpen(true)}
            className="btn-primary"
            data-testid="add-goal-btn"
          >
            <Plus className="mr-2" size={18} />
            Nova Meta
          </Button>
        </div>

        {/* Filters */}
        <Card className="glass-card border-white/10">
          <CardContent className="p-4">
            <div className="flex flex-wrap gap-2">
              <Button
                variant={filter === 'all' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setFilter('all')}
                className={filter === 'all' ? 'bg-primary' : 'text-slate-400'}
              >
                Todas
              </Button>
              <Button
                variant={filter === 'active' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setFilter('active')}
                className={filter === 'active' ? 'bg-primary' : 'text-slate-400'}
              >
                <Clock size={14} className="mr-1" />
                Ativas
              </Button>
              <Button
                variant={filter === 'completed' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setFilter('completed')}
                className={filter === 'completed' ? 'bg-green-600' : 'text-slate-400'}
              >
                <CheckCircle2 size={14} className="mr-1" />
                Concluídas
              </Button>
              <div className="w-px bg-white/10 mx-2" />
              {PILLARS.slice(0, 6).map(pillar => (
                <Button
                  key={pillar.id}
                  variant={filter === pillar.id ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setFilter(pillar.id)}
                  className={filter === pillar.id ? 'bg-primary' : 'text-slate-400'}
                >
                  {pillar.icon}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Goals Grid */}
        {filteredGoals.length === 0 ? (
          <Card className="glass-card border-white/10">
            <CardContent className="p-12 text-center">
              <Target className="w-16 h-16 text-slate-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">
                Nenhuma meta encontrada
              </h3>
              <p className="text-slate-400 mb-4">
                Comece criando sua primeira meta para acompanhar seu progresso.
              </p>
              <Button onClick={() => setDialogOpen(true)} className="btn-primary">
                <Plus className="mr-2" size={18} />
                Criar Meta
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredGoals.map((goal) => {
              const pillar = PILLARS.find(p => p.id === goal.pillar);
              return (
                <Card
                  key={goal.id}
                  className={`glass-card border-white/10 card-hover ${
                    goal.status === 'completed' ? 'opacity-70' : ''
                  }`}
                >
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="text-2xl">{pillar?.icon || '📋'}</span>
                        <span className={`px-2 py-0.5 rounded-full text-xs ${
                          goal.status === 'completed'
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-amber-500/20 text-amber-400'
                        }`}>
                          {goal.status === 'completed' ? 'Concluída' : 'Ativa'}
                        </span>
                      </div>
                      <div className="flex gap-1">
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => handleViewHistory(goal)}
                          className="h-8 w-8 text-slate-400 hover:text-white"
                          data-testid={`history-${goal.id}`}
                        >
                          <History size={14} />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => handleEdit(goal)}
                          className="h-8 w-8 text-slate-400 hover:text-white"
                          data-testid={`edit-${goal.id}`}
                        >
                          <Edit2 size={14} />
                        </Button>
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              size="icon"
                              variant="ghost"
                              className="h-8 w-8 text-slate-400 hover:text-red-400"
                              data-testid={`delete-${goal.id}`}
                            >
                              <Trash2 size={14} />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent className="glass-card border-white/10">
                            <AlertDialogHeader>
                              <AlertDialogTitle className="text-white">Excluir Meta?</AlertDialogTitle>
                              <AlertDialogDescription className="text-slate-400">
                                Esta ação não pode ser desfeita. A meta será movida para o histórico.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel className="bg-slate-800 text-white border-slate-700">
                                Cancelar
                              </AlertDialogCancel>
                              <AlertDialogAction
                                onClick={() => handleDelete(goal.id)}
                                className="bg-red-600 hover:bg-red-700"
                              >
                                Excluir
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </div>

                    <h3 className="font-semibold text-white text-lg mb-2 line-clamp-1">
                      {goal.title}
                    </h3>
                    <p className="text-slate-400 text-sm line-clamp-3 mb-4">
                      {goal.description}
                    </p>

                    <div className="flex items-center justify-between pt-3 border-t border-white/10">
                      {goal.target_date && (
                        <span className="text-xs text-slate-500">
                          Meta: {new Date(goal.target_date).toLocaleDateString('pt-BR')}
                        </span>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleToggleComplete(goal)}
                        className={`ml-auto ${
                          goal.status === 'completed'
                            ? 'text-green-400 hover:text-green-300'
                            : 'text-slate-400 hover:text-green-400'
                        }`}
                      >
                        <CheckCircle2 size={16} className="mr-1" />
                        {goal.status === 'completed' ? 'Concluída' : 'Concluir'}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* Create/Edit Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="glass-card border-white/10 sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle className="text-white">
                {selectedGoal ? 'Editar Meta' : 'Nova Meta'}
              </DialogTitle>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label className="text-slate-400">Pilar *</Label>
                <Select
                  value={formData.pillar}
                  onValueChange={(value) => setFormData(prev => ({ ...prev, pillar: value }))}
                >
                  <SelectTrigger className="bg-slate-900/50 border-slate-700 text-white">
                    <SelectValue placeholder="Selecione um pilar" />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700">
                    {PILLARS.map(pillar => (
                      <SelectItem key={pillar.id} value={pillar.id} className="text-white">
                        {pillar.icon} {pillar.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="text-slate-400">Título *</Label>
                <Input
                  value={formData.title}
                  onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="Ex: Ler 12 livros este ano"
                  className="bg-slate-900/50 border-slate-700 text-white"
                  data-testid="goal-title"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-slate-400">Descrição</Label>
                <Textarea
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Descreva sua meta em detalhes..."
                  className="bg-slate-900/50 border-slate-700 text-white min-h-[100px]"
                  data-testid="goal-description"
                />
              </div>

              <p className="text-xs text-slate-500">
                A data limite é definida automaticamente conforme o ciclo de 12 meses do usuário.
              </p>
            </div>

            <DialogFooter>
              <Button variant="ghost" onClick={handleCloseDialog} className="text-slate-400">
                Cancelar
              </Button>
              <Button onClick={handleSubmit} className="btn-primary" data-testid="save-goal-btn">
                {selectedGoal ? 'Atualizar' : 'Criar Meta'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* History Dialog */}
        <Dialog open={historyDialogOpen} onOpenChange={setHistoryDialogOpen}>
          <DialogContent className="glass-card border-white/10 sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle className="text-white flex items-center gap-2">
                <History size={20} />
                Histórico de Alterações
              </DialogTitle>
            </DialogHeader>
            
            <div className="py-4">
              {selectedGoal && (
                <div className="mb-4 p-3 glass rounded-lg">
                  <p className="text-white font-medium">{selectedGoal.title}</p>
                  <p className="text-slate-400 text-sm">{selectedGoal.pillar}</p>
                </div>
              )}

              {goalHistory.length === 0 ? (
                <p className="text-slate-500 text-center py-8">
                  Nenhuma alteração registrada.
                </p>
              ) : (
                <div className="space-y-3 max-h-64 overflow-y-auto">
                  {goalHistory.map((entry, index) => (
                    <div key={entry.id || index} className="glass rounded-lg p-3">
                      <p className="text-xs text-slate-500 mb-2">
                        {new Date(entry.changed_at).toLocaleString('pt-BR')}
                      </p>
                      {Object.entries(entry.changes || {}).map(([key, value]) => (
                        <div key={key} className="text-sm">
                          <span className="text-slate-400">{key}:</span>{' '}
                          <span className="text-red-400 line-through mr-2">
                            {entry.old_values?.[key] || '-'}
                          </span>
                          <span className="text-green-400">{value}</span>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <DialogFooter>
              <Button variant="ghost" onClick={() => setHistoryDialogOpen(false)}>
                Fechar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default MetasPage;
