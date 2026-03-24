import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
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
  Lightbulb,
  FileText,
  RotateCcw,
  Save,
  Loader2
} from 'lucide-react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

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

  // System prompt state
  const [systemPrompt, setSystemPrompt] = useState('');
  const [isDefaultPrompt, setIsDefaultPrompt] = useState(true);
  const [promptLoading, setPromptLoading] = useState(false);
  const [savingPrompt, setSavingPrompt] = useState(false);

  useEffect(() => {
    loadKnowledge();
    loadSystemPrompt();
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

  const loadSystemPrompt = async () => {
    setPromptLoading(true);
    try {
      const token = localStorage.getItem('elios_token');
      const response = await axios.get(`${API_URL}/api/admin/ai/prompt`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSystemPrompt(response.data.prompt);
      setIsDefaultPrompt(response.data.is_default);
    } catch (error) {
      toast.error('Erro ao carregar prompt');
    } finally {
      setPromptLoading(false);
    }
  };

  const handleSavePrompt = async () => {
    setSavingPrompt(true);
    try {
      const token = localStorage.getItem('elios_token');
      await axios.put(`${API_URL}/api/admin/ai/prompt`, 
        { prompt: systemPrompt },
        { headers: { Authorization: `Bearer ${token}` }}
      );
      toast.success('Prompt salvo com sucesso!');
      setIsDefaultPrompt(false);
    } catch (error) {
      toast.error('Erro ao salvar prompt');
    } finally {
      setSavingPrompt(false);
    }
  };

  const handleResetPrompt = async () => {
    try {
      const token = localStorage.getItem('elios_token');
      const response = await axios.post(`${API_URL}/api/admin/ai/prompt/reset`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSystemPrompt(response.data.prompt);
      setIsDefaultPrompt(true);
      toast.success('Prompt resetado para o padrão');
    } catch (error) {
      toast.error('Erro ao resetar prompt');
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
            <Brain className="text-white" />
            Treinar ELIOS
          </h1>
          <p className="text-neutral-400 mt-1">
            Configure o comportamento e conhecimento do assistente ELIOS
          </p>
        </div>

        <Tabs defaultValue="prompt" className="w-full">
          <TabsList className="bg-neutral-900/50">
            <TabsTrigger value="prompt" className="data-[state=active]:bg-white data-[state=active]:text-black">
              <FileText size={16} className="mr-2" />
              Script Inicial
            </TabsTrigger>
            <TabsTrigger value="knowledge" className="data-[state=active]:bg-white data-[state=active]:text-black">
              <BookOpen size={16} className="mr-2" />
              Base de Conhecimento
            </TabsTrigger>
          </TabsList>

          {/* System Prompt Tab */}
          <TabsContent value="prompt" className="mt-6">
            <Card className="glass-card border-white/10">
              <CardHeader>
                <CardTitle className="text-lg text-white flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <FileText className="text-white" size={20} />
                    Script Inicial do ELIOS
                  </span>
                  {!isDefaultPrompt && (
                    <span className="text-xs px-2 py-1 rounded-full bg-amber-500/20 text-amber-400">
                      Personalizado
                    </span>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-neutral-400 text-sm">
                  Este é o prompt base que define a personalidade e comportamento do ELIOS. 
                  A cada interação, o sistema injeta automaticamente os dados do usuário (metas, pilares, respostas) abaixo deste script.
                </p>

                {promptLoading ? (
                  <div className="flex items-center justify-center h-64">
                    <div className="spinner" />
                  </div>
                ) : (
                  <Textarea
                    value={systemPrompt}
                    onChange={(e) => setSystemPrompt(e.target.value)}
                    className="bg-neutral-900/50 border-neutral-800 text-white font-mono text-sm min-h-[400px]"
                    placeholder="Digite o prompt do sistema..."
                    data-testid="system-prompt"
                  />
                )}

                <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t border-white/10">
                  <Button
                    onClick={handleSavePrompt}
                    disabled={savingPrompt}
                    className="btn-primary flex-1"
                    data-testid="save-prompt-btn"
                  >
                    {savingPrompt ? (
                      <Loader2 className="mr-2 animate-spin" size={18} />
                    ) : (
                      <Save className="mr-2" size={18} />
                    )}
                    Salvar Prompt
                  </Button>

                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button
                        variant="outline"
                        className="border-neutral-700 text-neutral-400 hover:text-white"
                      >
                        <RotateCcw className="mr-2" size={18} />
                        Resetar para Padrão
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent className="glass-card border-white/10">
                      <AlertDialogHeader>
                        <AlertDialogTitle className="text-white">
                          Resetar Prompt?
                        </AlertDialogTitle>
                        <AlertDialogDescription className="text-neutral-400">
                          Isso substituirá o prompt atual pelo padrão do sistema. Esta ação não pode ser desfeita.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel className="bg-neutral-800 text-white border-neutral-700">
                          Cancelar
                        </AlertDialogCancel>
                        <AlertDialogAction
                          onClick={handleResetPrompt}
                          className="bg-amber-600 hover:bg-amber-700"
                        >
                          Resetar
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>

                {/* Tips */}
                <div className="glass rounded-lg p-4 mt-4">
                  <h4 className="text-white font-medium mb-2 flex items-center gap-2">
                    <Lightbulb size={16} className="text-amber-400" />
                    Dicas para o Script
                  </h4>
                  <ul className="text-neutral-400 text-sm space-y-1">
                    <li>• O sistema injeta automaticamente os dados do usuário após este script</li>
                    <li>• Defina o tom de voz, personalidade e regras de resposta</li>
                    <li>• Mencione os 11 Pilares e como o ELIOS deve tratá-los</li>
                    <li>• Seja específico sobre o formato das respostas esperadas</li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Knowledge Base Tab */}
          <TabsContent value="knowledge" className="mt-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Add Knowledge Form */}
              <Card className="glass-card border-white/10">
                <CardHeader>
                  <CardTitle className="text-lg text-white flex items-center gap-2">
                    <Plus className="text-white" size={20} />
                    Adicionar Conhecimento
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-neutral-400 text-sm">
                    Adicione informações específicas que o ELIOS deve saber sobre o programa Elite, 
                    metodologias ou dicas para os usuários.
                  </p>

                  <div className="space-y-2">
                    <Label className="text-neutral-400">Categoria</Label>
                    <Select
                      value={formData.category}
                      onValueChange={(value) => setFormData(prev => ({ ...prev, category: value }))}
                    >
                      <SelectTrigger className="bg-neutral-900/50 border-neutral-800 text-white">
                        <SelectValue placeholder="Selecione uma categoria" />
                      </SelectTrigger>
                      <SelectContent className="bg-neutral-900 border-neutral-800">
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
                    <Label className="text-neutral-400">Prioridade</Label>
                    <Select
                      value={formData.priority.toString()}
                      onValueChange={(value) => setFormData(prev => ({ ...prev, priority: parseInt(value) }))}
                    >
                      <SelectTrigger className="bg-neutral-900/50 border-neutral-800 text-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-neutral-900 border-neutral-800">
                        <SelectItem value="1" className="text-white">1 - Baixa</SelectItem>
                        <SelectItem value="2" className="text-white">2 - Média</SelectItem>
                        <SelectItem value="3" className="text-white">3 - Alta</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-neutral-400">Conteúdo / Instrução</Label>
                    <Textarea
                      value={formData.content}
                      onChange={(e) => setFormData(prev => ({ ...prev, content: e.target.value }))}
                      placeholder="Ex: Quando um usuário mencionar dificuldades financeiras, sugira começar com um orçamento simples..."
                      className="bg-neutral-900/50 border-neutral-800 text-white min-h-[150px]"
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

              {/* Knowledge List */}
              <Card className="glass-card border-white/10">
                <CardHeader>
                  <CardTitle className="text-lg text-white flex items-center gap-2">
                    <BookOpen className="text-white" size={20} />
                    Conhecimentos ({knowledge.length})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {knowledge.length === 0 ? (
                    <div className="text-center py-8">
                      <Brain className="w-16 h-16 text-neutral-700 mx-auto mb-4" />
                      <p className="text-neutral-500">
                        Nenhum conhecimento adicionado ainda.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-3 max-h-[500px] overflow-y-auto">
                      {knowledge.map((item) => {
                        const CategoryIcon = getCategoryIcon(item.category);
                        return (
                          <div
                            key={item.id}
                            className="glass rounded-lg p-4 flex items-start gap-4"
                          >
                            <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center flex-shrink-0">
                              <CategoryIcon className="text-white" size={20} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-white text-sm font-medium capitalize">
                                  {item.category}
                                </span>
                                <span className={`px-2 py-0.5 rounded-full text-xs ${
                                  item.priority === 3 ? 'bg-red-500/20 text-red-400' :
                                  item.priority === 2 ? 'bg-amber-500/20 text-amber-400' :
                                  'bg-neutral-800 text-neutral-400'
                                }`}>
                                  P{item.priority}
                                </span>
                              </div>
                              <p className="text-neutral-300 text-sm line-clamp-3">{item.content}</p>
                            </div>
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button
                                  size="icon"
                                  variant="ghost"
                                  className="h-8 w-8 text-neutral-500 hover:text-red-400 flex-shrink-0"
                                >
                                  <Trash2 size={16} />
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent className="glass-card border-white/10">
                                <AlertDialogHeader>
                                  <AlertDialogTitle className="text-white">
                                    Remover Conhecimento?
                                  </AlertDialogTitle>
                                  <AlertDialogDescription className="text-neutral-400">
                                    Esta ação não pode ser desfeita.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel className="bg-neutral-800 text-white border-neutral-700">
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
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
};

export default AdminEliosPage;
