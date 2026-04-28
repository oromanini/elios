import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Button } from '../components/ui/button';
import { adminAPI } from '../services/api';
import { toast } from 'sonner';
import { Settings, Save, Loader2 } from 'lucide-react';

const AdminSettingsPage = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadMetadata();
  }, []);

  const loadMetadata = async () => {
    try {
      const response = await adminAPI.getMetadata();
      setItems(response.data);
    } catch (error) {
      toast.error('Erro ao carregar configurações');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (name, value) => {
    setItems((prev) => prev.map((item) => (
      item.name === name ? { ...item, value } : item
    )));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await adminAPI.updateMetadata(items.map(({ name, type, value }) => ({ name, type, value })));
      toast.success('Configurações salvas com sucesso');
      await loadMetadata();
    } catch (error) {
      const detail = error?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Erro ao salvar configurações');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout>
      <div className="space-y-6" data-testid="admin-settings-page">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-white flex items-center gap-3">
            <Settings className="text-white" />
            Configurações
          </h1>
          <p className="text-neutral-400 mt-1">
            Gerencie variáveis não sensíveis usadas pela integração do ELIOS.
          </p>
        </div>

        <Card className="glass-card border-white/10">
          <CardHeader>
            <CardTitle className="text-lg text-white">Metadata da Integração WhatsApp</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {loading ? (
              <div className="flex items-center justify-center h-40">
                <div className="spinner" />
              </div>
            ) : (
              items.map((item) => (
                <div key={item.name} className="space-y-2">
                  <Label className="text-neutral-300">{item.name}</Label>
                  <Input
                    value={item.value || ''}
                    onChange={(event) => handleChange(item.name, event.target.value)}
                    placeholder={`Informe ${item.name}`}
                    className="bg-neutral-900/50 border-neutral-800 text-white"
                  />
                </div>
              ))
            )}

            <div className="pt-4 border-t border-white/10">
              <Button
                onClick={handleSave}
                disabled={loading || saving}
                className="btn-primary w-full sm:w-auto"
                data-testid="save-settings-btn"
              >
                {saving ? (
                  <Loader2 className="mr-2 animate-spin" size={18} />
                ) : (
                  <Save className="mr-2" size={18} />
                )}
                Salvar configurações
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default AdminSettingsPage;
