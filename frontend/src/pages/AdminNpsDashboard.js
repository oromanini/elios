import React, { useEffect, useState } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Skeleton } from '../components/ui/skeleton';
import api from '../services/api';

const statusStyles = {
  completed: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  pending: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  null: 'bg-slate-500/15 text-slate-300 border-slate-500/30'
};

const statusLabels = {
  completed: 'Concluído',
  pending: 'Pendente',
  null: 'Sem registro'
};

const formatDate = (dateValue) => {
  if (!dateValue) return '—';

  const parsed = new Date(dateValue);
  if (Number.isNaN(parsed.getTime())) return '—';

  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short'
  }).format(parsed);
};

const LoadingRows = () => (
  <div className="space-y-2">
    {[...Array(5)].map((_, index) => (
      <div key={`nps-row-skeleton-${index}`} className="grid grid-cols-12 gap-3 items-center rounded-lg border border-gray-800 bg-gray-900 px-4 py-3">
        <Skeleton className="h-4 col-span-4 bg-gray-800" />
        <Skeleton className="h-4 col-span-3 bg-gray-800" />
        <Skeleton className="h-4 col-span-3 bg-gray-800" />
        <Skeleton className="h-9 col-span-2 bg-gray-800" />
      </div>
    ))}
  </div>
);

const AdminNpsDashboard = () => {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [triggeringUserId, setTriggeringUserId] = useState('');

  const loadOverview = async () => {
    setLoading(true);
    try {
      const response = await api.get('/admin/nps-overview');
      setRows(response.data || []);
    } catch (error) {
      toast.error('Não foi possível carregar o painel de NPS.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOverview();
  }, []);

  const handleTrigger = async (userId, fullName) => {
    const confirmed = window.confirm(`Deseja disparar um novo NPS para ${fullName}?`);
    if (!confirmed) return;

    setTriggeringUserId(userId);
    try {
      await api.post(`/nps/trigger/${userId}?force=true`);
      toast.success('NPS disparado com sucesso.');
      loadOverview();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Não foi possível disparar o NPS.');
    } finally {
      setTriggeringUserId('');
    }
  };

  return (
    <Layout>
      <div className="space-y-6" data-testid="admin-nps-dashboard-page">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-white">Gestão de NPS</h1>
          <p className="text-gray-400 mt-1">Acompanhe o último envio de NPS por mentorando e dispare novos ciclos manualmente.</p>
        </div>

        <Card className="border-gray-800 bg-gray-900">
          <CardHeader>
            <CardTitle className="text-white">Visão geral dos mentorandos</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <LoadingRows />
            ) : rows.length === 0 ? (
              <div className="rounded-lg border border-gray-800 bg-gray-950 px-4 py-6 text-center text-gray-300">
                Nenhum mentorando encontrado.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[740px] text-sm">
                  <thead>
                    <tr className="border-b border-gray-800 text-gray-400 text-left">
                      <th className="px-3 py-3 font-medium">Mentorando</th>
                      <th className="px-3 py-3 font-medium">Status último NPS</th>
                      <th className="px-3 py-3 font-medium">Data de envio</th>
                      <th className="px-3 py-3 font-medium">Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((item) => {
                      const status = item.last_nps_status || 'null';
                      const isTriggering = triggeringUserId === item.user_id;

                      return (
                        <tr key={item.user_id} className="border-b border-gray-800/80 text-gray-200">
                          <td className="px-3 py-3">
                            <p className="font-medium text-white">{item.full_name}</p>
                            <p className="text-xs text-gray-500">{item.email}</p>
                          </td>
                          <td className="px-3 py-3">
                            <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${statusStyles[status] || statusStyles.null}`}>
                              {statusLabels[status] || status}
                            </span>
                          </td>
                          <td className="px-3 py-3 text-gray-300">{formatDate(item.last_nps_date)}</td>
                          <td className="px-3 py-3">
                            <Button
                              size="sm"
                              className="bg-indigo-600 hover:bg-indigo-500 text-white"
                              onClick={() => handleTrigger(item.user_id, item.full_name)}
                              disabled={isTriggering}
                            >
                              {isTriggering ? <Loader2 size={16} className="mr-1 animate-spin" /> : <Send size={16} className="mr-1" />}
                              Disparar NPS
                            </Button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default AdminNpsDashboard;
