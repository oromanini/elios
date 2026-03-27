import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import Logo from '../components/Logo';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { toast } from 'sonner';
import { questionsAPI, formAPI, aiAPI } from '../services/api';
import { 
  ArrowRight, 
  ArrowLeft, 
  CheckCircle2, 
  Sparkles,
  Send,
  Loader2,
  User,
  Mail
} from 'lucide-react';

const PILLAR_ICONS = {
  'ESPIRITUALIDADE': '🙏',
  'CUIDADOS COM A SAÚDE': '💪',
  'EQUILÍBRIO EMOCIONAL': '🧘',
  'LAZER': '🎯',
  'GESTÃO DO TEMPO E ORGANIZAÇÃO': '⏰',
  'DESENVOLVIMENTO INTELECTUAL': '📚',
  'IMAGEM PESSOAL': '✨',
  'FAMÍLIA': '👨‍👩‍👧‍👦',
  'CRESCIMENTO PROFISSIONAL': '📈',
  'FINANÇAS': '💰',
  'NETWORKING E CONTRIBUIÇÃO': '🤝',
  'META MAGNUS': '🎯'
};

const FormPage = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState('');
  const [isUserTyping, setIsUserTyping] = useState(false);
  const [isResponding, setIsResponding] = useState(false);
  const typingTimeoutRef = useRef(null);
  const respondTimeoutRef = useRef(null);
  const previousAiAnalysisRef = useRef('');
  
  // Form data
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [responses, setResponses] = useState({});

  useEffect(() => {
    loadQuestions();
  }, []);

  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
      if (respondTimeoutRef.current) {
        clearTimeout(respondTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!aiAnalysis || aiAnalysis === previousAiAnalysisRef.current) return;

    setIsResponding(true);
    if (respondTimeoutRef.current) {
      clearTimeout(respondTimeoutRef.current);
    }

    respondTimeoutRef.current = setTimeout(() => {
      setIsResponding(false);
    }, 900);

    previousAiAnalysisRef.current = aiAnalysis;
  }, [aiAnalysis]);

  const loadQuestions = async () => {
    try {
      const response = await questionsAPI.getAll();
      setQuestions(response.data);
    } catch (error) {
      toast.error('Erro ao carregar perguntas');
    } finally {
      setLoading(false);
    }
  };

  const totalSteps = questions.length + 2; // Name + Email + Questions
  const progress = ((currentStep + 1) / totalSteps) * 100;

  const handleNext = () => {
    if (currentStep === 0 && !fullName.trim()) {
      toast.error('Por favor, insira seu nome completo');
      return;
    }
    if (currentStep === 1 && !email.trim()) {
      toast.error('Por favor, insira um email válido');
      return;
    }
    if (currentStep >= 2) {
      const question = questions[currentStep - 2];
      if (!responses[question.id]?.trim()) {
        toast.error('Por favor, responda a pergunta antes de continuar');
        return;
      }
    }
    
    setAiAnalysis('');
    setIsUserTyping(false);
    setCurrentStep(prev => prev + 1);
  };

  const handleBack = () => {
    setAiAnalysis('');
    setIsUserTyping(false);
    setCurrentStep(prev => prev - 1);
  };

  const handleResponseChange = (questionId, value) => {
    setResponses(prev => ({
      ...prev,
      [questionId]: value
    }));

    setIsUserTyping(true);
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    typingTimeoutRef.current = setTimeout(() => {
      setIsUserTyping(false);
    }, 1000);
  };

  const analyzeResponse = async () => {
    if (currentStep < 2) return;
    
    const question = questions[currentStep - 2];
    const answer = responses[question.id];
    
    if (!answer || answer.length < 20) return;
    
    setAnalyzing(true);
    try {
      const response = await aiAPI.analyze({
        pillar: question.pillar,
        question: question.description,
        answer: answer
      });
      setAiAnalysis(response.data.analysis);
    } catch (error) {
      console.error('Error analyzing:', error);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const formattedResponses = Object.entries(responses).map(([questionId, answer]) => ({
        question_id: questionId,
        answer: answer
      }));

      await formAPI.submit({
        full_name: fullName,
        email: email,
        responses: formattedResponses
      });

      toast.success('Formulário enviado com sucesso! Verifique seu email.');
      navigate('/form/success');
    } catch (error) {
      const message = error.response?.data?.detail || 'Erro ao enviar formulário';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="spinner" />
      </div>
    );
  }

  const renderStep = () => {
    if (currentStep === 0) {
      return (
        <motion.div
          key="step-name"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          className="space-y-6"
        >
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/20 flex items-center justify-center">
              <User className="w-8 h-8 text-primary" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Vamos começar!</h2>
            <p className="text-slate-400">Qual é o seu nome completo?</p>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="fullName" className="text-slate-400 uppercase text-xs tracking-wide">
              Nome Completo
            </Label>
            <Input
              id="fullName"
              type="text"
              placeholder="Seu nome completo"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="bg-slate-900/50 border-slate-700 text-white placeholder:text-slate-500 h-14 text-lg"
              data-testid="form-name"
            />
          </div>
        </motion.div>
      );
    }

    if (currentStep === 1) {
      return (
        <motion.div
          key="step-email"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          className="space-y-6"
        >
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/20 flex items-center justify-center">
              <Mail className="w-8 h-8 text-primary" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Ótimo, {fullName.split(' ')[0]}!</h2>
            <p className="text-slate-400">Qual é o seu melhor email?</p>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="email" className="text-slate-400 uppercase text-xs tracking-wide">
              Email
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="seu@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="bg-slate-900/50 border-slate-700 text-white placeholder:text-slate-500 h-14 text-lg"
              data-testid="form-email"
            />
            <p className="text-xs text-slate-500">
              Enviaremos suas credenciais de acesso para este email.
            </p>
          </div>
        </motion.div>
      );
    }

    const questionIndex = currentStep - 2;
    const question = questions[questionIndex];

    if (!question) return null;

    return (
      <motion.div
        key={`step-${question.id}`}
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        className="space-y-6"
      >
        <div className="text-center mb-6">
          <span className="text-4xl mb-4 block">{PILLAR_ICONS[question.pillar] || '📋'}</span>
          <div className="inline-block px-4 py-1 rounded-full bg-primary/20 text-primary text-sm font-medium mb-4">
            Pilar {questionIndex + 1} de {questions.length}
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">{question.title}</h2>
        </div>
        
        <div className="space-y-4">
          <p className="text-slate-300 text-center">{question.description}</p>
          
          <Textarea
            placeholder="Descreva detalhadamente sua situação atual e seus objetivos para os próximos 12 meses..."
            value={responses[question.id] || ''}
            onChange={(e) => handleResponseChange(question.id, e.target.value)}
            onBlur={analyzeResponse}
            className="bg-slate-900/50 border-slate-700 text-white placeholder:text-slate-500 min-h-[200px] text-base"
            data-testid={`form-question-${questionIndex}`}
          />

          {/* AI Analysis */}
          {(analyzing || aiAnalysis) && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card rounded-lg p-4 border-l-4 border-primary"
            >
              <div className="flex items-start gap-3">
                <div className={`elios-robot elios-robot--${isResponding ? 'responding' : isUserTyping ? 'thinking' : 'idle'}`} aria-hidden="true">
                  <div className="elios-robot__head">
                    <div className="elios-robot__crest">
                      <span className="elios-robot__arrow" />
                      <span className="elios-robot__arrow" />
                    </div>
                    <div className="elios-robot__eyes">
                      <span className="elios-robot__eye" />
                      <span className="elios-robot__eye" />
                    </div>
                    <span className="elios-robot__led" />
                  </div>
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="w-4 h-4 text-primary" />
                    <p className="text-primary text-sm font-medium">ELIOS Analisa:</p>
                  </div>
                  {analyzing ? (
                    <div className="flex items-center gap-2 text-slate-400">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Analisando sua resposta...</span>
                    </div>
                  ) : (
                    <p className="text-slate-300 text-sm">{aiAnalysis}</p>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </motion.div>
    );
  };

  const isLastStep = currentStep === totalSteps - 1;

  return (
    <div className="min-h-screen login-bg py-8 px-4">
      <div className="grid-overlay" />
      
      <div className="max-w-2xl mx-auto relative z-10">
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <Logo size="md" />
        </div>

        {/* Progress */}
        <div className="mb-8">
          <div className="flex justify-between text-sm text-slate-400 mb-2">
            <span>Progresso</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <Progress value={progress} className="h-2 bg-slate-800" />
          
          {/* Step indicators */}
          <div className="flex justify-between mt-4">
            {Array.from({ length: totalSteps }).map((_, index) => (
              <div
                key={index}
                className={`w-3 h-3 rounded-full transition-all ${
                  index < currentStep
                    ? 'bg-green-500 step-completed'
                    : index === currentStep
                    ? 'bg-primary step-active'
                    : 'bg-slate-700'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Form Card */}
        <Card className="glass-card border-white/10">
          <CardContent className="p-8">
            <AnimatePresence mode="wait">
              {renderStep()}
            </AnimatePresence>

            {/* Navigation Buttons */}
            <div className="flex justify-between mt-8 pt-6 border-t border-white/10">
              <Button
                variant="ghost"
                onClick={handleBack}
                disabled={currentStep === 0}
                className="text-slate-400 hover:text-white"
                data-testid="form-back"
              >
                <ArrowLeft className="mr-2" size={18} />
                Voltar
              </Button>

              {isLastStep ? (
                <Button
                  onClick={handleSubmit}
                  disabled={submitting}
                  className="btn-primary"
                  data-testid="form-submit"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="mr-2 animate-spin" size={18} />
                      Enviando...
                    </>
                  ) : (
                    <>
                      <Send className="mr-2" size={18} />
                      Enviar Formulário
                    </>
                  )}
                </Button>
              ) : (
                <Button
                  onClick={handleNext}
                  className="btn-primary"
                  data-testid="form-next"
                >
                  Próximo
                  <ArrowRight className="ml-2" size={18} />
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default FormPage;
