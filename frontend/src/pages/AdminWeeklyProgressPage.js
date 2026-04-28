import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import { adminAPI } from '../services/api';
import { Button } from '../components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';

const statusClass = {
  success: 'bg-emerald-600/70',
  failed: 'bg-red-600/70',
  not_sent: 'bg-slate-500/70',
};

export default function AdminWeeklyProgressPage() {
  const navigate = useNavigate();
  const [monitor, setMonitor] = useState({ columns: [], rows: [] });
  const [loading, setLoading] = useState(true);
  const [cycleOpen, setCycleOpen] = useState(false);
  const [cycleData, setCycleData] = useState([]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const response = await adminAPI.getWeeklyProgressMonitor();
        setMonitor(response.data);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const openCycle = async (userId) => {
    const response = await adminAPI.getWeeklyProgressCycle(userId);
    setCycleData(response.data.history || []);
    setCycleOpen(true);
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Monitoramento Semanal de Metas</h1>
          <p className="text-slate-400">Acompanhamento das últimas 4 segundas-feiras.</p>
        </div>

        {loading ? <p className="text-slate-300">Carregando...</p> : (
          <div className="overflow-x-auto rounded-lg border border-white/10">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-900/80 text-slate-200">
                <tr>
                  <th className="px-4 py-3 text-left">Nome do Mentorado</th>
                  {monitor.columns.map((label, idx) => (
                    <th key={label} className="px-4 py-3 text-center">{label || `Semana ${idx + 1}`}</th>
                  ))}
                  <th className="px-4 py-3 text-left">Ações</th>
                </tr>
              </thead>
              <tbody>
                {monitor.rows.map((row) => (
                  <tr key={row.user_id} className="border-t border-white/10">
                    <td className="px-4 py-3 text-white">{row.full_name}</td>
                    {row.weeks.map((week) => (
                      <td key={week.week_start} className="px-4 py-3">
                        <div className={`mx-auto h-6 w-6 rounded ${statusClass[week.status] || statusClass.not_sent}`} />
                      </td>
                    ))}
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <Button size="sm" onClick={() => navigate(`/dashboard/weekly-progress?userId=${row.user_id}`)}>
                          Visualizar como Aluno
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => openCycle(row.user_id)}>
                          Ciclo de 12 Meses
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Dialog open={cycleOpen} onOpenChange={setCycleOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Histórico completo de médias</DialogTitle>
          </DialogHeader>
          <div className="max-h-[60vh] overflow-y-auto space-y-3 pr-2">
            {cycleData.map((entry, idx) => (
              <div key={`${entry.timestamp}-${idx}`} className="rounded border border-white/10 p-3 text-sm">
                <p className="text-slate-200">{new Date(entry.timestamp).toLocaleString('pt-BR')}</p>
                <p className="text-slate-400">Status: {entry.status} | Link enviado: {entry.link_sent ? 'Sim' : 'Não'}</p>
                <pre className="mt-2 text-xs text-slate-300 whitespace-pre-wrap">{JSON.stringify(entry.medias_calculadas, null, 2)}</pre>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}
