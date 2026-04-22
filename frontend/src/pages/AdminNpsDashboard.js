import React, { useEffect, useState } from 'react';
import { Send, Loader2, Eye } from 'lucide-react';
import { toast } from 'sonner';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Skeleton } from '../components/ui/skeleton';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../components/ui/dialog';
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
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [lastNpsDetails, setLastNpsDetails] = useState(null);

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

  const handleOpenDetails = async (userId, fullName) => {
    setSelectedStudent({ userId, fullName });
    setLastNpsDetails(null);
    setDetailsLoading(true);
    setDetailsOpen(true);

    try {
      const response = await api.get(`/nps/history/${userId}`);
      const history = response.data || [];
      setLastNpsDetails(history[0] || null);
    } catch (error) {
      toast.error('Não foi possível carregar os detalhes do último NPS.');
      setLastNpsDetails(null);
    } finally {
      setDetailsLoading(false);
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
                <table className="w-full min-w-[780px] text-sm">
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
                            <div className="flex items-center gap-2">
                              <Button
                                size="icon"
                                variant="outline"
                                className="border-white/20 bg-white/5 text-slate-200 hover:bg-white/10"
                                onClick={() => handleOpenDetails(item.user_id, item.full_name)}
                                aria-label={`Ver detalhes do último NPS de ${item.full_name}`}
                              >
                                <Eye size={16} />
                              </Button>
                              <Button
                                size="sm"
                                className="bg-indigo-600 hover:bg-indigo-500 text-white"
                                onClick={() => handleTrigger(item.user_id, item.full_name)}
                                disabled={isTriggering}
                              >
                                {isTriggering ? <Loader2 size={16} className="mr-1 animate-spin" /> : <Send size={16} className="mr-1" />}
                                Disparar NPS
                              </Button>
                            </div>
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

        <Dialog open={detailsOpen} onOpenChange={setDetailsOpen}>
          <DialogContent className="glass-card border-white/10 sm:max-w-2xl">
            <DialogHeader>
              <DialogTitle className="text-white">
                Último NPS de {selectedStudent?.fullName || 'mentorando'}
              </DialogTitle>
              <DialogDescription className="text-slate-300">
                Pilar, meta e nota atribuída no último check-in.
              </DialogDescription>
            </DialogHeader>

            {detailsLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((item) => (
                  <Skeleton key={`nps-details-skeleton-${item}`} className="h-20 w-full bg-white/10" />
                ))}
              </div>
            ) : !lastNpsDetails ? (
              <div className="rounded-lg border border-white/10 bg-black/20 px-4 py-6 text-center text-slate-300">
                Nenhum NPS encontrado para este mentorando.
              </div>
            ) : (
              <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
                {lastNpsDetails.evaluations?.map((evaluation) => (
                  <div key={evaluation.goal_id} className="rounded-lg border border-white/10 bg-gray-800/50 p-4">
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                      <Badge className="border border-blue-400/30 bg-blue-950/70 text-blue-200">
                        {evaluation.goal_pillar || 'Sem pilar'}
                      </Badge>
                      <span className="rounded-md border border-emerald-400/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-200">
                        Nota: {evaluation.score ?? '—'}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-white">{evaluation.goal_title || 'Meta sem título'}</p>
                    <p className="mt-1 text-xs italic text-slate-300">{evaluation.goal_description || 'Sem descrição informada.'}</p>
                  </div>
                ))}
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default AdminNpsDashboard;
