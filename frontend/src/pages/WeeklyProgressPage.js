import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import Layout from '../components/Layout';
import { goalsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

const getCardClass = (average) => {
  if (average === null || average === undefined) return 'border-slate-500/40 bg-slate-700/20';
  if (average >= 7) return 'border-emerald-500/40 bg-emerald-500/10';
  if (average >= 5) return 'border-amber-500/40 bg-amber-500/10';
  return 'border-red-500/40 bg-red-500/10';
};

export default function WeeklyProgressPage() {
  const [searchParams] = useSearchParams();
  const { isAdmin } = useAuth();
  const [data, setData] = useState({ goals: [], full_name: '' });
  const [loading, setLoading] = useState(true);

  const targetUserId = useMemo(() => {
    const queryUser = searchParams.get('userId');
    if (queryUser && isAdmin()) return queryUser;
    return undefined;
  }, [searchParams, isAdmin]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const response = await goalsAPI.getWeeklyProgress(targetUserId ? { user_id: targetUserId } : {});
        setData(response.data);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [targetUserId]);

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Resumo Semanal de Progresso</h1>
          <p className="text-slate-400 mt-1">{data.full_name ? `Mentorado: ${data.full_name}` : 'Suas metas e evolução dos últimos 3 meses.'}</p>
        </div>

        {loading && <p className="text-slate-300">Carregando dados...</p>}

        <div className="grid gap-4 md:grid-cols-2">
          {!loading && data.goals.map((goal) => (
            <div key={goal.goal_id} className={`rounded-lg border p-4 ${getCardClass(goal.average)}`}>
              <div className="mb-3">
                <h2 className="text-lg font-semibold text-white">{goal.goal_title}</h2>
                <p className="text-sm text-slate-300">Pilar: {goal.pillar || 'Não informado'}</p>
                <p className="text-sm text-slate-200 mt-2">Média atual: <strong>{goal.average ?? 'Sem dados'}</strong></p>
              </div>

              <div style={{ width: '100%', height: 220 }}>
                <ResponsiveContainer>
                  <LineChart data={goal.series || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="month" stroke="#94a3b8" />
                    <YAxis domain={[0, 10]} stroke="#94a3b8" />
                    <Tooltip />
                    <Line type="monotone" dataKey="score" stroke="#38bdf8" strokeWidth={2} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Layout>
  );
}
