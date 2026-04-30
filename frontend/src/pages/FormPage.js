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
  Mail,
  Camera,
  CalendarDays,
  Phone
} from 'lucide-react';

const NPS_SCORE_OPTIONS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

const PILLAR_ICON_THEMES = {
  'ESPIRITUALIDADE': { bg: '#7C3AED', accent: '#C4B5FD' },
  'CUIDADOS COM A SAÚDE': { bg: '#059669', accent: '#6EE7B7' },
  'EQUILÍBRIO EMOCIONAL': { bg: '#D97706', accent: '#FCD34D' },
  'LAZER': { bg: '#DB2777', accent: '#F9A8D4' },
  'GESTÃO DO TEMPO E ORGANIZAÇÃO': { bg: '#4B5563', accent: '#D1D5DB' },
  'DESENVOLVIMENTO INTELECTUAL': { bg: '#4F46E5', accent: '#A5B4FC' },
  'IMAGEM PESSOAL': { bg: '#0F766E', accent: '#5EEAD4' },
  'FAMÍLIA': { bg: '#BE123C', accent: '#FDA4AF' },
  'CRESCIMENTO PROFISSIONAL': { bg: '#1D4ED8', accent: '#93C5FD' },
  'FINANÇAS': { bg: '#15803D', accent: '#86EFAC' },
  'NETWORKING E CONTRIBUIÇÃO': { bg: '#7E22CE', accent: '#D8B4FE' },
  'META MAGNUS': { bg: '#B45309', accent: '#FDE68A' },
  DEFAULT: { bg: '#334155', accent: '#CBD5E1' }
};

const PillarStepIcon = ({ pillar }) => {
  const theme = PILLAR_ICON_THEMES[pillar] || PILLAR_ICON_THEMES.DEFAULT;
  const commonStroke = {
    stroke: theme.accent,
    strokeWidth: 1.8,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    fill: 'none'
  };

  const iconsByPillar = {
    'ESPIRITUALIDADE': (
      <>
        <path {...commonStroke} d="M20 17c2.4-2.8 2.3-6.6 0-8.9-2.3 2.3-2.4 6.1 0 8.9Z" />
        <path {...commonStroke} d="M12 17c-2.4-2.8-2.3-6.6 0-8.9 2.3 2.3 2.4 6.1 0 8.9Z" />
        <path {...commonStroke} d="M16 18v8" />
      </>
    ),
    'CUIDADOS COM A SAÚDE': (
      <>
        <path {...commonStroke} d="M16 25V9" />
        <path {...commonStroke} d="M8 17h16" />
        <circle cx="16" cy="17" r="8.5" {...commonStroke} />
      </>
    ),
    'EQUILÍBRIO EMOCIONAL': (
      <>
        <path {...commonStroke} d="M16 26c4.3-2.5 7-6.2 7-9.8A4.3 4.3 0 0 0 16 13a4.3 4.3 0 0 0-7 3.2c0 3.6 2.7 7.3 7 9.8Z" />
        <path {...commonStroke} d="M16 10v3" />
      </>
    ),
    'LAZER': (
      <>
        <circle cx="16" cy="16" r="9" {...commonStroke} />
        <path {...commonStroke} d="m16 9 2.1 4.2 4.6.7-3.3 3.3.8 4.6-4.2-2.2-4.2 2.2.8-4.6-3.3-3.3 4.6-.7Z" />
      </>
    ),
    'GESTÃO DO TEMPO E ORGANIZAÇÃO': (
      <>
        <circle cx="16" cy="16" r="9" {...commonStroke} />
        <path {...commonStroke} d="M16 16V11.5" />
        <path {...commonStroke} d="m16 16 3.5 2" />
      </>
    ),
    'DESENVOLVIMENTO INTELECTUAL': (
      <>
        <path {...commonStroke} d="M8.5 11.5c2.3-1.6 4.9-1.6 7.5 0v10c-2.6-1.6-5.2-1.6-7.5 0Z" />
        <path {...commonStroke} d="M23.5 11.5c-2.3-1.6-4.9-1.6-7.5 0v10c2.6-1.6 5.2-1.6 7.5 0Z" />
      </>
    ),
    'IMAGEM PESSOAL': (
      <>
        <circle cx="16" cy="13.5" r="3.5" {...commonStroke} />
        <path {...commonStroke} d="M10.5 24c1.3-2.8 3.2-4.2 5.5-4.2s4.2 1.4 5.5 4.2" />
        <rect x="7.5" y="7.5" width="17" height="17" rx="4" {...commonStroke} />
      </>
    ),
    'FAMÍLIA': (
      <>
        <circle cx="12" cy="14" r="2.5" {...commonStroke} />
        <circle cx="20" cy="14" r="2.5" {...commonStroke} />
        <path {...commonStroke} d="M8.5 23c.8-2.7 2.2-4 3.5-4s2.7 1.3 3.5 4" />
        <path {...commonStroke} d="M16.5 23c.8-2.7 2.2-4 3.5-4s2.7 1.3 3.5 4" />
      </>
    ),
    'CRESCIMENTO PROFISSIONAL': (
      <>
        <path {...commonStroke} d="M10 22V16" />
        <path {...commonStroke} d="M16 22V12" />
        <path {...commonStroke} d="M22 22V9" />
        <path {...commonStroke} d="m9 10 4 2 4-3 5 1" />
      </>
    ),
    'FINANÇAS': (
      <>
        <path {...commonStroke} d="M16 8v16" />
        <path {...commonStroke} d="M20.2 11.4c-.8-1.2-2.4-2-4.2-2-2.4 0-4.3 1.4-4.3 3.3 0 4.8 8.6 2.1 8.6 6 0 1.9-1.9 3.3-4.3 3.3-1.9 0-3.4-.8-4.3-2" />
      </>
    ),
    'NETWORKING E CONTRIBUIÇÃO': (
      <>
        <circle cx="9.5" cy="12" r="2" {...commonStroke} />
        <circle cx="22.5" cy="12" r="2" {...commonStroke} />
        <circle cx="16" cy="22" r="2" {...commonStroke} />
        <path {...commonStroke} d="m11.2 13.2 3.2 6.8" />
        <path {...commonStroke} d="m20.8 13.2-3.2 6.8" />
        <path {...commonStroke} d="M11.5 12h9" />
      </>
    ),
    'META MAGNUS': (
      <>
        <circle cx="16" cy="16" r="8.5" {...commonStroke} />
        <circle cx="16" cy="16" r="4.5" {...commonStroke} />
        <circle cx="16" cy="16" r="1.8" fill={theme.accent} />
      </>
    ),
    DEFAULT: <rect x="9" y="9" width="14" height="14" rx="2.5" {...commonStroke} />
  };

  return (
    <div
      className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center shadow-lg"
      style={{ background: `radial-gradient(circle at 30% 30%, ${theme.accent}33, ${theme.bg})` }}
    >
      <svg viewBox="0 0 32 32" className="w-10 h-10" role="img" aria-label={`Ícone do pilar ${pillar}`}>
        {iconsByPillar[pillar] || iconsByPillar.DEFAULT}
      </svg>
    </div>
  );
};

const MIN_QUESTION_ANSWER_LENGTH = 50;

const applyPhoneMask = (value) => {
  const digits = value.replace(/\D/g, '').slice(0, 11);

  if (digits.length <= 2) return digits;
  if (digits.length <= 6) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
  if (digits.length <= 10) return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
  return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
};

const FormPage = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [questionAnalyses, setQuestionAnalyses] = useState({});
  const profilePhotoInputRef = useRef(null);
  
  // Form data
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [profilePhoto, setProfilePhoto] = useState(null);
  const [profilePhotoPreview, setProfilePhotoPreview] = useState('');
  const [whatsapp, setWhatsapp] = useState('');
  const [birthDate, setBirthDate] = useState('');
  const [responses, setResponses] = useState({});
  const [ratings, setRatings] = useState({});

  useEffect(() => {
    loadQuestions();
  }, []);

  useEffect(() => {
    if (!profilePhoto) {
      setProfilePhotoPreview('');
      return undefined;
    }

    const previewUrl = URL.createObjectURL(profilePhoto);
    setProfilePhotoPreview(previewUrl);

    return () => {
      URL.revokeObjectURL(previewUrl);
    };
  }, [profilePhoto]);

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

  const totalSteps = questions.length + 5; // Name + Email + Photo + WhatsApp + Birth date + Questions
  const progress = ((currentStep + 1) / totalSteps) * 100;

  const handleNext = async () => {
    if (currentStep === 0 && !fullName.trim()) {
      toast.error('Por favor, insira seu nome completo');
      return;
    }
    if (currentStep === 1 && !email.trim()) {
      toast.error('Por favor, insira um email válido');
      return;
    }
    if (currentStep === 3 && whatsapp.replace(/\D/g, '').length < 10) {
      toast.error('Por favor, informe um WhatsApp válido');
      return;
    }
    if (currentStep === 4 && !birthDate) {
      toast.error('Por favor, informe sua data de nascimento');
      return;
    }
    if (currentStep >= 5) {
      const question = questions[currentStep - 5];
      const answer = responses[question.id]?.trim() || '';
      const rating = ratings[question.id];
      if (answer.length < MIN_QUESTION_ANSWER_LENGTH) {
        toast.error(`Por favor, escreva pelo menos ${MIN_QUESTION_ANSWER_LENGTH} caracteres para continuar`);
        return;
      }
      if (question.id !== 'ca7e651a-a3a7-41f0-b38f-81f5bcc0b699' && (rating === undefined || rating === null)) {
        toast.error('Por favor, selecione uma nota de 0 a 10 para este pilar antes de continuar.');
        return;
      }

      const existingAnalysis = questionAnalyses[question.id];
      const shouldReanalyze = !existingAnalysis || existingAnalysis.answer !== answer;

      if (shouldReanalyze) {
        setAnalyzing(true);
        try {
          const analysisResponse = await aiAPI.analyze({
            pillar: question.pillar,
            question: question.description,
            answer
          });

          const analysis = {
            ...analysisResponse.data,
            answer
          };
          setQuestionAnalyses((prev) => ({ ...prev, [question.id]: analysis }));
          setAiAnalysis(analysis);

          if (!analysis.can_proceed) {
            toast.error('Revise a resposta: ela precisa estar satisfatória e conter ao menos uma meta detectável.');
          } else {
            toast.success('Resposta aprovada pelo ELIOS. Clique em "Próximo" novamente para continuar.');
          }
        } catch (error) {
          toast.error('Não foi possível analisar a resposta agora. Tente novamente.');
        } finally {
          setAnalyzing(false);
        }
        return;
      }

      if (!existingAnalysis.can_proceed) {
        setAiAnalysis(existingAnalysis);
        toast.error('Ainda não é possível avançar: melhore a resposta e inclua uma meta detectável.');
        return;
      }
    }
    
    setAiAnalysis(null);
    setCurrentStep(prev => prev + 1);
  };

  const handleBack = () => {
    setAiAnalysis(null);
    setCurrentStep(prev => prev - 1);
  };

  const handleResponseChange = (questionId, value) => {
    setResponses(prev => ({
      ...prev,
      [questionId]: value
    }));
    setAiAnalysis(null);
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const formattedResponses = Object.entries(responses).map(([questionId, answer]) => ({
        question_id: questionId,
        answer: answer,
        rating: ratings[questionId] ?? null
      }));

      const formData = new FormData();
      formData.append('full_name', fullName);
      formData.append('email', email);
      formData.append('whatsapp', whatsapp);
      formData.append('date_of_birth', birthDate);
      formData.append('responses', JSON.stringify(formattedResponses));
      const detectedGoals = Object.entries(questionAnalyses).flatMap(([questionId, analysis]) =>
        (analysis.detected_goals || []).map((goal) => ({
          question_id: questionId,
          pillar: goal.pillar,
          title: goal.title,
          description: goal.description
        }))
      );
      formData.append('detected_goals', JSON.stringify(detectedGoals));
      if (profilePhoto) {
        formData.append('profile_photo', profilePhoto);
      }

      await formAPI.submit(formData);

      toast.success('Formulário enviado com sucesso! Verifique seu email.');
      navigate('/form/success');
    } catch (error) {
      const message = error.response?.data?.detail || 'Erro ao enviar formulário';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handlePhotoSelect = (file) => {
    if (!file) {
      setProfilePhoto(null);
      return;
    }

    if (!['image/jpeg', 'image/png'].includes(file.type)) {
      toast.error('Formato inválido. Use apenas JPEG ou PNG.');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      toast.error('A foto deve ter no máximo 5MB.');
      return;
    }

    setProfilePhoto(file);
  };

  const handleRatingChange = (questionId, value) => {
    setRatings((prev) => ({
      ...prev,
      [questionId]: Number(value)
    }));
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

    if (currentStep === 2) {
      return (
        <motion.div
          key="step-photo"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          className="space-y-6"
        >
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/20 flex items-center justify-center">
              <Camera className="w-8 h-8 text-primary" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Foto de Perfil</h2>
            <p className="text-slate-400">Envie sua foto (opcional) para personalizar seu perfil.</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="profilePhoto" className="text-slate-400 uppercase text-xs tracking-wide">
              Upload de foto (JPEG/PNG, até 5MB)
            </Label>
            <input
              id="profilePhoto"
              ref={profilePhotoInputRef}
              type="file"
              accept="image/jpeg,image/png"
              onChange={(e) => handlePhotoSelect(e.target.files?.[0] || null)}
              className="hidden"
              data-testid="form-photo"
            />
            <button
              type="button"
              onClick={() => profilePhotoInputRef.current?.click()}
              className="w-full group rounded-2xl border border-slate-700/80 bg-gradient-to-br from-slate-900/80 via-slate-900/60 to-slate-950/90 p-5 text-left transition-all hover:border-primary/50 hover:shadow-[0_0_0_1px_rgba(56,189,248,0.2)]"
            >
              <div className="flex items-start gap-4">
                {profilePhotoPreview ? (
                  <img
                    src={profilePhotoPreview}
                    alt="Prévia da foto de perfil"
                    className="w-16 h-16 rounded-xl object-cover border border-primary/40 shadow-lg shadow-primary/10"
                  />
                ) : (
                  <div className="w-16 h-16 rounded-xl border border-dashed border-slate-600 bg-slate-800/60 flex items-center justify-center">
                    <Camera className="w-7 h-7 text-slate-400 group-hover:text-primary transition-colors" />
                  </div>
                )}

                <div className="flex-1 min-w-0">
                  <p className="text-white font-semibold text-base mb-1">
                    {profilePhoto ? 'Foto selecionada com sucesso' : 'Escolher foto de perfil'}
                  </p>
                  <p className="text-slate-400 text-sm mb-2">
                    {profilePhoto
                      ? profilePhoto.name
                      : 'Clique aqui para enviar uma imagem com boa iluminação.'}
                  </p>
                  <div className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800/80 px-3 py-1 text-xs text-slate-300">
                    {profilePhoto ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <Camera className="w-3.5 h-3.5 text-primary" />}
                    {profilePhoto ? 'Pronto para envio' : 'JPEG/PNG • até 5MB'}
                  </div>
                </div>
              </div>
            </button>
            <p className="text-xs text-slate-500">
              A imagem será otimizada automaticamente para avatar.
            </p>
          </div>
        </motion.div>
      );
    }

    if (currentStep === 3) {
      return (
        <motion.div
          key="step-whatsapp"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          className="space-y-6"
        >
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/20 flex items-center justify-center">
              <Phone className="w-8 h-8 text-primary" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Seu WhatsApp</h2>
            <p className="text-slate-400">Qual número devemos usar para falar com você?</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="whatsapp" className="text-slate-400 uppercase text-xs tracking-wide">
              WhatsApp
            </Label>
            <Input
              id="whatsapp"
              type="tel"
              placeholder="(11) 99999-9999"
              value={whatsapp}
              onChange={(e) => setWhatsapp(applyPhoneMask(e.target.value))}
              className="bg-slate-900/50 border-slate-700 text-white placeholder:text-slate-500 h-14 text-lg"
              data-testid="form-whatsapp"
            />
          </div>
        </motion.div>
      );
    }

    if (currentStep === 4) {
      return (
        <motion.div
          key="step-birthdate"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          className="space-y-6"
        >
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/20 flex items-center justify-center">
              <CalendarDays className="w-8 h-8 text-primary" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Data de Nascimento</h2>
            <p className="text-slate-400">Precisamos dessa informação para futuras análises.</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="birthDate" className="text-slate-400 uppercase text-xs tracking-wide">
              Data de Nascimento
            </Label>
            <Input
              id="birthDate"
              type="date"
              value={birthDate}
              onChange={(e) => setBirthDate(e.target.value)}
              className="bg-slate-900/50 border-slate-700 text-white h-14 text-lg"
              data-testid="form-birthdate"
            />
          </div>
        </motion.div>
      );
    }

    const questionIndex = currentStep - 5;
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
          <PillarStepIcon pillar={question.pillar} />
          <div className="inline-block px-4 py-1 rounded-full bg-primary/20 text-primary text-sm font-medium mb-4">
            Pilar {questionIndex + 1} de {questions.length}
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">{question.title}</h2>
        </div>
        
        <div className="space-y-4">
          <p className="text-slate-300 text-center">{question.description}</p>

          {question.id !== 'ca7e651a-a3a7-41f0-b38f-81f5bcc0b699' && (
            <div className="space-y-3 rounded-xl border border-slate-700 bg-slate-900/40 p-4">
              <div className="flex items-center justify-between gap-3">
                <Label className="text-slate-200 text-sm">
                  NPS deste pilar (de 0 a 10)
                </Label>
                <span className="text-primary font-bold text-lg">
                  {ratings[question.id] ?? '-'}
                </span>
              </div>
              <div className="grid grid-cols-6 md:grid-cols-11 gap-2">
                {NPS_SCORE_OPTIONS.map((score) => {
                  const isSelected = ratings[question.id] === score;
                  return (
                    <Button
                      key={score}
                      type="button"
                      variant={isSelected ? 'default' : 'outline'}
                      onClick={() => handleRatingChange(question.id, score)}
                      className={`h-11 ${isSelected ? 'bg-primary text-primary-foreground' : 'border-white/20 text-slate-200 hover:bg-white/10'}`}
                      data-testid={`form-rating-${questionIndex}-${score}`}
                      aria-label={`Nota ${score} para ${question.title}`}
                    >
                      {score}
                    </Button>
                  );
                })}
              </div>
            </div>
          )}
          
          <Textarea
            placeholder="Descreva detalhadamente sua situação atual e seus objetivos para os próximos 12 meses..."
            value={responses[question.id] || ''}
            onChange={(e) => handleResponseChange(question.id, e.target.value)}
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
              <div className="flex items-start gap-2 sm:gap-3">
                <img
                  src="/images/elios.gif"
                  alt="ELIOS"
                  className="w-20 h-20 sm:w-20 sm:h-20 rounded-md object-cover shrink-0"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="w-4 h-4 text-amber-300 shrink-0" />
                    <p className="text-amber-300 text-sm font-medium">ELIOS Analisa:</p>
                  </div>
                  {analyzing ? (
                    <div className="flex items-center gap-2 text-slate-400">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Analisando sua resposta ao clicar em Próximo...</span>
                    </div>
                  ) : (
                    <div className="space-y-3 text-sm">
                      <p className="text-slate-200">
                        <span className="text-amber-300 font-medium">a. Feedback:</span>{' '}
                        {aiAnalysis?.feedback}
                      </p>
                      <div>
                        <p className="text-amber-300 font-medium">b. Objetivos:</p>
                        <ul className="list-disc pl-5 text-slate-300 space-y-1 mt-1">
                          {(aiAnalysis?.objectives || []).map((objective, idx) => (
                            <li key={`${objective}-${idx}`}>{objective}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
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
                  disabled={analyzing}
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
