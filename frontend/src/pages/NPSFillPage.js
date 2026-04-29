import React, { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Loader2, CheckCircle2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Skeleton } from '../components/ui/skeleton';
import { Badge } from '../components/ui/badge';
import api from '../services/api';
import { toast } from 'sonner';

const SCORE_OPTIONS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

const NPSFillPage = () => {
  const { npsId } = useParams();

  const [record, setRecord] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [scores, setScores] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    const loadNps = async () => {
      if (!npsId) {
        setError('Link de check-in inválido.');
        setLoading(false);
        return;
      }

      setLoading(true);
      setError('');

      try {
        const response = await api.get(`/nps/link/${npsId}`);
        const npsRecord = response.data;
        const pendingEvaluations = (npsRecord.evaluations || []).filter((evaluation) => !evaluation.is_completed);

        if (npsRecord.status === 'completed' || pendingEvaluations.length === 0) {
          setError('Este check-in já foi concluído e não está mais disponível para preenchimento.');
          setRecord(null);
          return;
        }

        setRecord({
          ...npsRecord,
          evaluations: pendingEvaluations,
        });
      } catch (err) {
        const fallbackMessage = 'Não foi possível carregar este check-in. Verifique se o link existe ou se já foi concluído.';
        setError(err?.response?.data?.detail || fallbackMessage);
      } finally {
        setLoading(false);
      }
    };

    loadNps();
  }, [npsId]);

  const pendingEvaluations = useMemo(() => record?.evaluations || [], [record]);

  const handleScoreChange = (goalId, score) => {
    setScores((prev) => ({
      ...prev,
      [goalId]: score,
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (pendingEvaluations.some((evaluation) => !scores[evaluation.goal_id])) {
      setError('Para concluir o check-in, atribua uma nota para todas as metas exibidas.');
      return;
    }

    setSubmitting(true);
    setError('');

    const payload = {
      evaluations: pendingEvaluations.map((evaluation) => ({
        goal_id: evaluation.goal_id,
        score: scores[evaluation.goal_id],
      })),
    };

    try {
      await api.post(`/nps/submit/${npsId}`, payload);
      setSubmitted(true);
    } catch (err) {
      const fallbackMessage = 'Não foi possível enviar sua avaliação agora. Tente novamente em alguns instantes.';
      toast.error(err?.response?.data?.detail || fallbackMessage);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen login-bg flex items-center justify-center p-4">
        <div className="grid-overlay" />
        <Card className="w-full max-w-4xl glass-card border-white/10 z-10">
          <CardHeader>
            <Skeleton className="h-8 w-72 bg-white/10" />
            <Skeleton className="h-5 w-96 bg-white/10" />
          </CardHeader>
          <CardContent className="space-y-6">
            {[1, 2, 3].map((item) => (
              <div key={item} className="space-y-4 rounded-lg border border-white/10 p-4">
                <Skeleton className="h-5 w-2/3 bg-white/10" />
                <div className="grid grid-cols-5 md:grid-cols-10 gap-2">
                  {SCORE_OPTIONS.map((score) => (
                    <Skeleton key={score} className="h-10 w-full bg-white/10" />
                  ))}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen login-bg flex items-center justify-center p-4">
      <div className="grid-overlay" />

      <Card className="w-full max-w-4xl glass-card border-white/10 z-10">
        <CardHeader>
          <CardTitle className="text-white text-2xl md:text-3xl">Check-in de Performance Mensal</CardTitle>
          <CardDescription className="text-slate-300">
            Avalie cada meta ativa com uma nota de 1 a 10 para registar sua evolução.
          </CardDescription>
        </CardHeader>

        <CardContent>
          {submitted ? (
            <div className="rounded-xl border border-emerald-400/30 bg-emerald-400/10 p-8 text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-400/20">
                <CheckCircle2 className="h-8 w-8 text-emerald-300" />
              </div>
              <h2 className="text-2xl font-semibold text-white mb-2">Check-in concluído com sucesso</h2>
              <p className="text-slate-200">A sua evolução foi registada!</p>
            </div>
          ) : error ? (
            <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-4 text-red-200">
              {error}
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6">
              {pendingEvaluations.map((evaluation) => (
                <div key={evaluation.goal_id} className="rounded-lg border border-white/10 bg-black/20 p-4 md:p-5">
                  <div className="mb-4 space-y-2">
                    {evaluation.goal_pillar ? (
                      <Badge variant="secondary" className="w-fit border border-blue-400/30 bg-blue-900/80 text-blue-200">
                        {evaluation.goal_pillar}
                      </Badge>
                    ) : null}
                    <p className="text-white font-semibold">{evaluation.goal_title}</p>
                    {evaluation.goal_description ? (
                      <p className="text-sm text-slate-300">{evaluation.goal_description}</p>
                    ) : null}
                  </div>

                  <div className="grid grid-cols-5 md:grid-cols-10 gap-2">
                    {SCORE_OPTIONS.map((score) => {
                      const isSelected = scores[evaluation.goal_id] === score;
                      return (
                        <Button
                          key={score}
                          type="button"
                          variant={isSelected ? 'default' : 'outline'}
                          onClick={() => handleScoreChange(evaluation.goal_id, score)}
                          className={`h-11 ${isSelected ? 'bg-primary text-primary-foreground' : 'border-white/20 text-slate-200 hover:bg-white/10'}`}
                          aria-label={`Nota ${score} para ${evaluation.goal_title}`}
                        >
                          {score}
                        </Button>
                      );
                    })}
                  </div>
                </div>
              ))}

              <div className="flex justify-end pt-2">
                <Button type="submit" className="min-w-48" disabled={submitting}>
                  {submitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Enviando...
                    </>
                  ) : (
                    'Concluir Check-in'
                  )}
                </Button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default NPSFillPage;
