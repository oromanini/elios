import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '../components/ui/alert-dialog';
import { adminAPI } from '../services/api';
import { toast } from 'sonner';
import {
  Brain,
  Plus,
  Trash2,
  Sparkles,
  BookOpen,
  MessageSquare,
  Target,
  Lightbulb
} from 'lucide-react';

const CATEGORIES = [
  { id: 'comportamento', name: 'Comportamento', icon: MessageSquare },
  { id: 'metodologia', name: 'Metodologia', icon: BookOpen },
  { id: 'motivacao', name: 'Motivação', icon: Sparkles },
  { id: 'estrategia', name: 'Estratégia', icon: Target },
  { id: 'dicas', name: 'Dicas Gerais', icon: Lightbulb }
];

const AdminEliosPage = () => {
  const [knowledge, setKnowledge] = useState([]);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({
    category: '',
    content: '',
    priority: 1
  });

  useEffect(() => {
    loadKnowledge();
  }, []);

  const loadKnowledge = async () => {
    try {
      const response = await adminAPI.getAIKnowledge();
      setKnowledge(response.data);
    } catch (error) {
      toast.error('Erro ao carregar conhecimentos');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!formData.category || !formData.content) {
      toast.error('Preencha todos os campos');
      return;
    }

    try {
      await adminAPI.addAIKnowledge(formData);
      toast.success('Conhecimento adicionado ao ELIOS');
      setFormData({ category: '', content: '', priority: 1 });
      loadKnowledge();
    } catch (error) {
      toast.error('Erro ao adicionar conhecimento');
    }
  };

  const handleDelete = async (id) => {
    try {
      await adminAPI.deleteAIKnowledge(id);
      toast.success('Conhecimento removido');
      loadKnowledge();
    } catch (error) {
      toast.error('Erro ao remover conhecimento');
    }
  };

  const getCategoryIcon = (categoryId) => {
    const category = CATEGORIES.find(c => c.id === categoryId);
    return category?.icon || Brain;
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
      <div className="space-y-6" data-testid="admin-elios-page">
        {/* Header */}
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-white flex items-center gap-3">
            <Brain className="text-primary" />
            Treinar ELIOS
          </h1>
          <p className="text-slate-400 mt-1">
            Adicione conhecimentos e comportamentos ao assistente ELIOS
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Add Knowledge Form */}
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <Plus className="text-primary" size={20} />
                Adicionar Conhecimento
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label className="text-slate-400">Categoria</Label>
                <Select
                  value={formData.category}
                  onValueChange={(value) => setFormData(prev => ({ ...prev, category: value }))}
                >
                  <SelectTrigger className="bg-slate-900/50 border-slate-700 text-white">
                    <SelectValue placeholder="Selecione uma categoria" />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700">
                    {CATEGORIES.map(cat => (
                      <SelectItem key={cat.id} value={cat.id} className="text-white">
                        <span className="flex items-center gap-2">
                          <cat.icon size={16} />
                          {cat.name}
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="text-slate-400">Prioridade</Label>
                <Select
                  value={formData.priority.toString()}
                  onValueChange={(value) => setFormData(prev => ({ ...prev, priority: parseInt(value) }))}
                >
                  <SelectTrigger className="bg-slate-900/50 border-slate-700 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700">
                    <SelectItem value="1" className="text-white">1 - Baixa</SelectItem>
                    <SelectItem value="2" className="text-white">2 - Média</SelectItem>
                    <SelectItem value="3" className="text-white">3 - Alta</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="text-slate-400">Conteúdo / Instrução</Label>
                <Textarea
                  value={formData.content}
                  onChange={(e) => setFormData(prev => ({ ...prev, content: e.target.value }))}
                  placeholder="Ex: Quando um usuário mencionar dificuldades financeiras, sugira começar com um orçamento simples e acompanhamento mensal de gastos..."
                  className="bg-slate-900/50 border-slate-700 text-white min-h-[150px]"
                  data-testid="knowledge-content"
                />
              </div>

              <Button
                onClick={handleSubmit}
                className="w-full btn-primary"
                data-testid="add-knowledge-btn"
              >
                <Plus className="mr-2" size={18} />
                Adicionar ao ELIOS
              </Button>
            </CardContent>
          </Card>

          {/* Tips Card */}
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <Lightbulb className="text-accent" size={20} />
                Dicas de Treinamento
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="glass rounded-lg p-4">
                <h4 className="text-primary font-medium mb-2">Comportamento</h4>
                <p className="text-slate-400 text-sm">
                  Defina como o ELIOS deve responder em situações específicas.
                  Ex: "Seja empático quando o usuário expressar frustração."
                </p>
              </div>

              <div className="glass rounded-lg p-4">
                <h4 className="text-primary font-medium mb-2">Metodologia</h4>
                <p className="text-slate-400 text-sm">
                  Ensine metodologias e frameworks que o ELIOS deve recomendar.
                  Ex: "Use a técnica SMART para definição de metas."
                </p>
              </div>

              <div className="glass rounded-lg p-4">
                <h4 className="text-primary font-medium mb-2">Estratégia</h4>
                <p className="text-slate-400 text-sm">
                  Adicione estratégias específicas para cada pilar.
                  Ex: "Para finanças, sempre comece perguntando sobre o orçamento atual."
                </p>
              </div>

              <div className="glass rounded-lg p-4">
                <h4 className="text-accent font-medium mb-2">Prioridade</h4>
                <p className="text-slate-400 text-sm">
                  Conhecimentos com maior prioridade são mais considerados pelo ELIOS nas respostas.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Knowledge List */}
        <Card className="glass-card border-white/10">
          <CardHeader>
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <BookOpen className="text-primary" size={20} />
              Base de Conhecimento ({knowledge.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {knowledge.length === 0 ? (
              <div className="text-center py-8">
                <Brain className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                <p className="text-slate-500">
                  Nenhum conhecimento adicionado ainda.
                </p>
                <p className="text-slate-600 text-sm">
                  Adicione instruções para personalizar o comportamento do ELIOS.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {knowledge.map((item) => {
                  const CategoryIcon = getCategoryIcon(item.category);
                  return (
                    <div
                      key={item.id}
                      className="glass rounded-lg p-4 flex items-start gap-4"
                    >
                      <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center flex-shrink-0">
                        <CategoryIcon className="text-primary" size={20} />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-primary text-sm font-medium capitalize">
                            {item.category}
                          </span>
                          <span className={`px-2 py-0.5 rounded-full text-xs ${
                            item.priority === 3 ? 'bg-red-500/20 text-red-400' :
                            item.priority === 2 ? 'bg-amber-500/20 text-amber-400' :
                            'bg-slate-700 text-slate-400'
                          }`}>
                            Prioridade {item.priority}
                          </span>
                        </div>
                        <p className="text-slate-300 text-sm">{item.content}</p>
                        <p className="text-slate-600 text-xs mt-2">
                          Adicionado em {new Date(item.created_at).toLocaleDateString('pt-BR')}
                        </p>
                      </div>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-8 w-8 text-slate-400 hover:text-red-400"
                          >
                            <Trash2 size={16} />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent className="glass-card border-white/10">
                          <AlertDialogHeader>
                            <AlertDialogTitle className="text-white">
                              Remover Conhecimento?
                            </AlertDialogTitle>
                            <AlertDialogDescription className="text-slate-400">
                              Esta ação não pode ser desfeita.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel className="bg-slate-800 text-white border-slate-700">
                              Cancelar
                            </AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => handleDelete(item.id)}
                              className="bg-red-600 hover:bg-red-700"
                            >
                              Remover
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default AdminEliosPage;
