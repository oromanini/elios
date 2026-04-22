import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { CalendarDays, TrendingUp } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from 'recharts';
import { toast } from 'sonner';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Skeleton } from '../components/ui/skeleton';
import api from '../services/api';

const formatDate = (dateValue) => {
  if (!dateValue) return '—';
  const parsed = new Date(dateValue);
  if (Number.isNaN(parsed.getTime())) return '—';
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium' }).format(parsed);
};

const HistoryLoading = () => (
  <div className="space-y-3">
    {[...Array(4)].map((_, index) => (
      <Card key={`nps-history-skeleton-${index}`} className="border-gray-800 bg-gray-900">
        <CardContent className="space-y-3 p-5">
          <Skeleton className="h-6 w-40 bg-gray-800" />
          <Skeleton className="h-4 w-48 bg-gray-800" />
          <Skeleton className="h-10 w-36 bg-gray-800" />
        </CardContent>
      </Card>
    ))}
  </div>
);

const NpsHistory = () => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadHistory = async () => {
      setLoading(true);
      try {
        const response = await api.get('/nps/history');
        setHistory(response.data || []);
      } catch (error) {
        toast.error('Não foi possível carregar o histórico de NPS.');
      } finally {
        setLoading(false);
      }
    };

    loadHistory();
  }, []);

  const chartData = useMemo(
    () => history
      .slice()
      .sort((a, b) => Number(a.cycle || 0) - Number(b.cycle || 0))
      .map((item) => ({
        cycle: Number(item.cycle || 0),
        score: typeof item.average_score === 'number' ? item.average_score : null,
      })),
    [history]
  );

  return (
    <Layout>
      <div className="space-y-6" data-testid="nps-history-page-v2">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-white">Histórico de NPS</h1>
          <p className="text-gray-400 mt-1">Acompanhe sua evolução ao longo dos 12 ciclos de acompanhamento.</p>
        </div>

        {loading ? (
          <HistoryLoading />
        ) : history.length === 0 ? (
          <Card className="border-gray-800 bg-gray-900">
            <CardContent className="p-6 text-gray-300">Nenhum ciclo de NPS disponível até o momento.</CardContent>
          </Card>
        ) : (
          <>
            {chartData.length > 0 && (
              <Card className="border-gray-800 bg-gray-900">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <TrendingUp size={18} className="text-indigo-400" /> Evolução da média
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis
                          dataKey="cycle"
                          stroke="#9CA3AF"
                          tickLine={false}
                          tickFormatter={(value) => `C${value}`}
                        />
                        <YAxis domain={[0, 10]} stroke="#9CA3AF" tickLine={false} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                          labelStyle={{ color: '#E5E7EB' }}
                        />
                        <Line type="monotone" dataKey="score" stroke="#818CF8" strokeWidth={3} dot={{ fill: '#A5B4FC' }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="space-y-3">
              {history.map((item) => (
                <Card key={`${item.id || item.cycle}-${item.send_date}`} className="border-gray-800 bg-gray-900">
                  <CardContent className="p-5 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div className="space-y-2">
                      <h2 className="text-lg font-semibold text-white">Ciclo {item.cycle} de 12</h2>
                      <p className="text-sm text-gray-400 inline-flex items-center gap-2">
                        <CalendarDays size={14} /> Preenchimento: {formatDate(item.fill_date)}
                      </p>
                    </div>

                    {item.status === 'completed' ? (
                      <div className="text-right">
                        <p className="text-xs text-gray-400">Média de score</p>
                        <p className="text-3xl font-bold text-emerald-300">{Number(item.average_score || 0).toFixed(1)}<span className="text-lg text-gray-400">/10</span></p>
                      </div>
                    ) : (
                      <Button asChild className="bg-indigo-600 hover:bg-indigo-500 text-white">
                        <Link to={`/nps/${item.id}`}>Preencher Agora</Link>
                      </Button>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </>
        )}
      </div>
    </Layout>
  );
};

export default NpsHistory;
