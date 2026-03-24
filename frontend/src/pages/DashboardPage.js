import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { dashboardAPI, formAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { toast } from 'sonner';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip
} from 'recharts';
import {
  Target,
  CheckCircle2,
  TrendingUp,
  MessageSquare,
  Hexagon,
  ArrowRight
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { useNavigate } from 'react-router-dom';

const DashboardPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [responses, setResponses] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [statsRes, responsesRes] = await Promise.all([
        dashboardAPI.getStats(),
        formAPI.getResponses()
      ]);
      setStats(statsRes.data);
      setResponses(responsesRes.data);
    } catch (error) {
      console.error('Error loading dashboard:', error);
      toast.error('Erro ao carregar dashboard');
    } finally {
      setLoading(false);
    }
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

  const radarData = stats?.radar_data || [];

  return (
    <Layout>
      <div className="space-y-8" data-testid="dashboard">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-white">
              Dashboard
            </h1>
            <p className="text-slate-400 mt-1">
              Bem-vindo de volta, {user?.full_name?.split(' ')[0]}!
            </p>
          </div>
          <Button
            onClick={() => navigate('/chat')}
            className="btn-primary"
            data-testid="chat-btn"
          >
            <MessageSquare className="mr-2" size={18} />
            Conversar com ELIOS
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="glass-card border-white/10 card-hover dashboard-card">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-sm">Total de Metas</p>
                  <p className="text-3xl font-bold text-white mt-1">
                    {stats?.total_goals || 0}
                  </p>
                </div>
                <div className="w-12 h-12 rounded-lg bg-primary/20 flex items-center justify-center">
                  <Target className="text-primary" size={24} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card border-white/10 card-hover dashboard-card">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-sm">Metas Concluídas</p>
                  <p className="text-3xl font-bold text-white mt-1">
                    {stats?.completed_goals || 0}
                  </p>
                </div>
                <div className="w-12 h-12 rounded-lg bg-green-500/20 flex items-center justify-center">
                  <CheckCircle2 className="text-green-500" size={24} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card border-white/10 card-hover dashboard-card">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-sm">Pilares Ativos</p>
                  <p className="text-3xl font-bold text-white mt-1">
                    {Object.keys(stats?.pillars || {}).length}
                  </p>
                </div>
                <div className="w-12 h-12 rounded-lg bg-accent/20 flex items-center justify-center">
                  <Hexagon className="text-accent" size={24} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card border-white/10 card-hover dashboard-card">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-sm">Progresso Geral</p>
                  <p className="text-3xl font-bold text-white mt-1">
                    {stats?.total_goals > 0 
                      ? Math.round((stats.completed_goals / stats.total_goals) * 100)
                      : 0}%
                  </p>
                </div>
                <div className="w-12 h-12 rounded-lg bg-purple-500/20 flex items-center justify-center">
                  <TrendingUp className="text-purple-500" size={24} />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Radar Chart */}
          <Card className="glass-card border-white/10 lg:col-span-8">
            <CardHeader>
              <CardTitle className="text-xl text-white flex items-center gap-2">
                <Hexagon className="text-primary" size={20} />
                Visão dos 11 Pilares + Meta Magnus
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="radar-container">
                <ResponsiveContainer width="100%" height={400}>
                  <RadarChart data={radarData} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
                    <PolarGrid stroke="#334155" />
                    <PolarAngleAxis 
                      dataKey="shortName" 
                      tick={{ fill: '#94a3b8', fontSize: 12 }}
                    />
                    <PolarRadiusAxis 
                      angle={30} 
                      domain={[0, 100]} 
                      tick={{ fill: '#64748b', fontSize: 10 }}
                    />
                    <Radar
                      name="Progresso"
                      dataKey="progress"
                      stroke="#0ea5e9"
                      fill="#0ea5e9"
                      fillOpacity={0.3}
                      strokeWidth={2}
                    />
                    <Tooltip
                      content={({ payload }) => {
                        if (payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                            <div className="glass-card rounded-lg p-3 border border-white/10">
                              <p className="text-white font-medium">{data.pillar}</p>
                              <p className="text-primary">Progresso: {data.progress}%</p>
                              <p className="text-slate-400 text-sm">
                                {data.completed}/{data.goals} metas concluídas
                              </p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <div className="lg:col-span-4 space-y-4">
            <Card className="glass-card border-white/10">
              <CardHeader>
                <CardTitle className="text-lg text-white">Ações Rápidas</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button
                  variant="secondary"
                  className="w-full justify-between bg-slate-800/50 hover:bg-slate-800 border border-white/5"
                  onClick={() => navigate('/pilares')}
                  data-testid="view-pillars-btn"
                >
                  <span className="flex items-center gap-2">
                    <Hexagon size={18} />
                    Ver Pilares
                  </span>
                  <ArrowRight size={18} />
                </Button>
                
                <Button
                  variant="secondary"
                  className="w-full justify-between bg-slate-800/50 hover:bg-slate-800 border border-white/5"
                  onClick={() => navigate('/metas')}
                  data-testid="manage-goals-btn"
                >
                  <span className="flex items-center gap-2">
                    <Target size={18} />
                    Gerenciar Metas
                  </span>
                  <ArrowRight size={18} />
                </Button>
                
                <Button
                  variant="secondary"
                  className="w-full justify-between bg-slate-800/50 hover:bg-slate-800 border border-white/5"
                  onClick={() => navigate('/chat')}
                  data-testid="chat-elios-btn"
                >
                  <span className="flex items-center gap-2">
                    <MessageSquare size={18} />
                    Falar com ELIOS
                  </span>
                  <ArrowRight size={18} />
                </Button>
              </CardContent>
            </Card>

            {/* META MAGNUS Highlight */}
            <Card className="glass-card border-accent/30 neon-glow-gold">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg text-accent flex items-center gap-2">
                  🎯 META MAGNUS
                </CardTitle>
              </CardHeader>
              <CardContent>
                {responses.find(r => r.question?.pillar === 'META MAGNUS') ? (
                  <p className="text-slate-300 text-sm line-clamp-4">
                    {responses.find(r => r.question?.pillar === 'META MAGNUS')?.answer}
                  </p>
                ) : (
                  <p className="text-slate-500 text-sm italic">
                    Nenhuma Meta Magnus definida ainda.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default DashboardPage;
