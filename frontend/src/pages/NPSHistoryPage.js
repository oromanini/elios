import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Calendar, ClipboardCheck } from 'lucide-react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../components/ui/accordion';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Skeleton } from '../components/ui/skeleton';

const STATUS_LABELS = {
  pending: 'Pendente',
  completed: 'Concluído',
  expired: 'Expirado'
};

const formatDate = (dateString) => {
  if (!dateString) return null;

  const parsedDate = new Date(dateString);
  if (Number.isNaN(parsedDate.getTime())) return null;

  return new Intl.DateTimeFormat('pt-PT').format(parsedDate);
};

const getScoreBadgeClass = (score) => {
  if (score >= 9) {
    return 'bg-emerald-600/20 text-emerald-300 border-emerald-500/40';
  }

  if (score >= 6) {
    return 'bg-amber-500/20 text-amber-200 border-amber-400/40';
  }

  return 'bg-rose-500/20 text-rose-200 border-rose-400/40';
};

const LoadingSkeleton = () => (
  <div className="space-y-3">
    {[1, 2, 3].map((item) => (
      <Card key={item} className="glass-card border-white/10">
        <CardContent className="p-4 space-y-3">
          <div className="flex items-center justify-between gap-4">
            <Skeleton className="h-6 w-40 bg-white/10" />
            <Skeleton className="h-6 w-24 bg-white/10" />
          </div>
          <Skeleton className="h-4 w-full bg-white/10" />
          <Skeleton className="h-4 w-5/6 bg-white/10" />
        </CardContent>
      </Card>
    ))}
  </div>
);

const NPSHistoryPage = () => {
  const { user } = useAuth();
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadHistory = async () => {
      if (!user?.id) {
        setLoading(false);
        return;
      }

      setLoading(true);
      setError('');

      try {
        const response = await api.get(`/nps/history/${user.id}`);
        setRecords(response.data || []);
      } catch (err) {
        setError('Não foi possível carregar o histórico de performance.');
      } finally {
        setLoading(false);
      }
    };

    loadHistory();
  }, [user?.id]);

  const hasRecords = useMemo(() => records.length > 0, [records]);

  return (
    <Layout>
      <div className="space-y-6" data-testid="nps-history-page">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-white">Histórico de Performance</h1>
          <p className="text-slate-400 mt-1">
            Consulte os ciclos de check-in, estado atual e notas atribuídas às suas metas.
          </p>
        </div>

        {loading ? (
          <LoadingSkeleton />
        ) : error ? (
          <Card className="glass-card border-red-500/40">
            <CardContent className="p-4 text-red-200">{error}</CardContent>
          </Card>
        ) : !hasRecords ? (
          <Card className="glass-card border-white/10">
            <CardContent className="p-6 text-slate-300">
              Ainda não existem ciclos de check-in para apresentar.
            </CardContent>
          </Card>
        ) : (
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle className="text-white text-xl">Ciclos de avaliação</CardTitle>
            </CardHeader>
            <CardContent>
              <Accordion type="single" collapsible className="w-full">
                {records.map((record, index) => {
                  const statusLabel = STATUS_LABELS[record.status] || record.status;
                  const fillDate = record.status === 'completed' ? formatDate(record.fill_date) : null;
                  return (
                    <AccordionItem
                      key={record._id}
                      value={record._id}
                      className="border-white/10"
                    >
                      <AccordionTrigger>
                        <div className="w-full pr-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                          <div className="flex items-center gap-2 text-white">
                            <ClipboardCheck size={16} className="text-primary" />
                            <span className="font-semibold">Ciclo {record.cycle ?? index + 1}</span>
                          </div>

                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge className="bg-slate-700/60 text-slate-100 border-slate-500/40">
                              {statusLabel}
                            </Badge>
                            {fillDate && (
                              <Badge className="bg-sky-500/20 text-sky-200 border-sky-400/40">
                                <Calendar size={14} /> {fillDate}
                              </Badge>
                            )}
                          </div>
                        </div>
                      </AccordionTrigger>

                      <AccordionContent>
                        {record.status === 'completed' ? (
                          <div className="space-y-2">
                            {(record.evaluations || []).map((evaluation) => (
                              <div
                                key={evaluation.goal_id || evaluation.goal_title}
                                className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 flex items-center justify-between gap-3"
                              >
                                <p className="text-slate-100 text-sm">{evaluation.goal_title}</p>
                                <Badge className={getScoreBadgeClass(evaluation.score)}>
                                  {evaluation.score}
                                </Badge>
                              </div>
                            ))}
                          </div>
                        ) : record.status === 'pending' ? (
                          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-amber-100 text-sm space-y-3">
                            <p>
                              Check-in disponível. Verifique o seu WhatsApp ou clique aqui para preencher.
                            </p>
                            <Button asChild size="sm">
                              <Link to={`/nps/${record._id}`}>Preencher check-in</Link>
                            </Button>
                          </div>
                        ) : (
                          <div className="rounded-lg border border-slate-600/40 bg-slate-700/20 p-4 text-slate-300 text-sm">
                            Este ciclo expirou e não pode mais ser preenchido.
                          </div>
                        )}
                      </AccordionContent>
                    </AccordionItem>
                  );
                })}
              </Accordion>
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  );
};

export default NPSHistoryPage;
