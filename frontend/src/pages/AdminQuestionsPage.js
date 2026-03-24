import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Switch } from '../components/ui/switch';
import { questionsAPI } from '../services/api';
import { toast } from 'sonner';
import {
  FileText,
  Plus,
  Edit2,
  Trash2,
  GripVertical,
  Eye,
  EyeOff
} from 'lucide-react';

const PILLARS = [
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

const AdminQuestionsPage = () => {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedQuestion, setSelectedQuestion] = useState(null);

  // Form state
  const [formData, setFormData] = useState({
    pillar: '',
    title: '',
    description: '',
    order: 1
  });

  useEffect(() => {
    loadQuestions();
  }, []);

  const loadQuestions = async () => {
    try {
      const response = await questionsAPI.getAllAdmin();
      setQuestions(response.data.sort((a, b) => a.order - b.order));
    } catch (error) {
      toast.error('Erro ao carregar perguntas');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!formData.pillar || !formData.title || !formData.description) {
      toast.error('Preencha todos os campos obrigatórios');
      return;
    }

    try {
      if (selectedQuestion) {
        await questionsAPI.update(selectedQuestion.id, formData);
        toast.success('Pergunta atualizada');
      } else {
        await questionsAPI.create(formData);
        toast.success('Pergunta criada');
      }
      
      loadQuestions();
      handleCloseDialog();
    } catch (error) {
      toast.error('Erro ao salvar pergunta');
    }
  };

  const handleToggleActive = async (question) => {
    try {
      await questionsAPI.update(question.id, { is_active: !question.is_active });
      toast.success(`Pergunta ${question.is_active ? 'desativada' : 'ativada'}`);
      loadQuestions();
    } catch (error) {
      toast.error('Erro ao atualizar pergunta');
    }
  };

  const handleDelete = async (questionId) => {
    try {
      await questionsAPI.delete(questionId);
      toast.success('Pergunta excluída');
      loadQuestions();
    } catch (error) {
      toast.error('Erro ao excluir pergunta');
    }
  };

  const handleEdit = (question) => {
    setSelectedQuestion(question);
    setFormData({
      pillar: question.pillar,
      title: question.title,
      description: question.description,
      order: question.order
    });
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setSelectedQuestion(null);
    setFormData({
      pillar: '',
      title: '',
      description: '',
      order: questions.length + 1
    });
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
      <div className="space-y-6" data-testid="admin-questions-page">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-white flex items-center gap-3">
              <FileText className="text-primary" />
              Gerenciar Perguntas
            </h1>
            <p className="text-slate-400 mt-1">
              Edite as perguntas do formulário de cadastro
            </p>
          </div>
          <Button
            onClick={() => {
              setFormData(prev => ({ ...prev, order: questions.length + 1 }));
              setDialogOpen(true);
            }}
            className="btn-primary"
            data-testid="add-question-btn"
          >
            <Plus className="mr-2" size={18} />
            Nova Pergunta
          </Button>
        </div>

        {/* Questions List */}
        <div className="space-y-3">
          {questions.map((question, index) => (
            <Card
              key={question.id}
              className={`glass-card border-white/10 ${
                !question.is_active ? 'opacity-50' : ''
              }`}
            >
              <CardContent className="p-4">
                <div className="flex items-start gap-4">
                  <div className="flex items-center gap-2 text-slate-500">
                    <GripVertical size={20} />
                    <span className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold">
                      {question.order}
                    </span>
                  </div>

                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="px-2 py-0.5 rounded-full text-xs bg-primary/20 text-primary">
                        {question.pillar}
                      </span>
                      {!question.is_active && (
                        <span className="px-2 py-0.5 rounded-full text-xs bg-red-500/20 text-red-400">
                          Desativada
                        </span>
                      )}
                    </div>
                    <h3 className="text-lg font-semibold text-white mb-1">
                      {question.title}
                    </h3>
                    <p className="text-slate-400 text-sm line-clamp-2">
                      {question.description}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => handleToggleActive(question)}
                      className="h-8 w-8 text-slate-400 hover:text-white"
                      title={question.is_active ? 'Desativar' : 'Ativar'}
                    >
                      {question.is_active ? <Eye size={16} /> : <EyeOff size={16} />}
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => handleEdit(question)}
                      className="h-8 w-8 text-slate-400 hover:text-white"
                      data-testid={`edit-question-${question.id}`}
                    >
                      <Edit2 size={16} />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {questions.length === 0 && (
          <Card className="glass-card border-white/10">
            <CardContent className="p-12 text-center">
              <FileText className="w-16 h-16 text-slate-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">
                Nenhuma pergunta cadastrada
              </h3>
              <p className="text-slate-400 mb-4">
                Crie as perguntas para o formulário de cadastro.
              </p>
              <Button onClick={() => setDialogOpen(true)} className="btn-primary">
                <Plus className="mr-2" size={18} />
                Criar Pergunta
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Create/Edit Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="glass-card border-white/10 sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle className="text-white">
                {selectedQuestion ? 'Editar Pergunta' : 'Nova Pergunta'}
              </DialogTitle>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-slate-400">Pilar *</Label>
                  <Select
                    value={formData.pillar}
                    onValueChange={(value) => setFormData(prev => ({ ...prev, pillar: value }))}
                  >
                    <SelectTrigger className="bg-slate-900/50 border-slate-700 text-white">
                      <SelectValue placeholder="Selecione um pilar" />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-900 border-slate-700 max-h-60">
                      {PILLARS.map(pillar => (
                        <SelectItem key={pillar} value={pillar} className="text-white">
                          {pillar}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label className="text-slate-400">Ordem</Label>
                  <Input
                    type="number"
                    min="1"
                    value={formData.order}
                    onChange={(e) => setFormData(prev => ({ ...prev, order: parseInt(e.target.value) }))}
                    className="bg-slate-900/50 border-slate-700 text-white"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label className="text-slate-400">Título *</Label>
                <Input
                  value={formData.title}
                  onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="Ex: Espiritualidade"
                  className="bg-slate-900/50 border-slate-700 text-white"
                  data-testid="question-title"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-slate-400">Descrição/Pergunta *</Label>
                <Textarea
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Descreva a pergunta que será exibida ao usuário..."
                  className="bg-slate-900/50 border-slate-700 text-white min-h-[120px]"
                  data-testid="question-description"
                />
              </div>
            </div>

            <DialogFooter>
              <Button variant="ghost" onClick={handleCloseDialog} className="text-slate-400">
                Cancelar
              </Button>
              <Button onClick={handleSubmit} className="btn-primary" data-testid="save-question-btn">
                {selectedQuestion ? 'Atualizar' : 'Criar Pergunta'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default AdminQuestionsPage;
