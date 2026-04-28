import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Switch } from '../components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '../components/ui/alert-dialog';
import { adminAPI } from '../services/api';
import { toast } from 'sonner';
import { getBackendBaseUrl } from '../config/apiBaseUrl';
import {
  Users,
  Search,
  Edit2,
  Trash2,
  UserCheck,
  UserX,
  Shield,
  User,
  Camera,
  UserPlus
} from 'lucide-react';

const applyPhoneMask = (value) => {
  const digits = value.replace(/\D/g, '').slice(0, 11);

  if (digits.length <= 2) return digits;
  if (digits.length <= 6) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
  if (digits.length <= 10) return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
  return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
};

const AdminUsersPage = () => {
  const backendBaseUrl = getBackendBaseUrl();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRole, setFilterRole] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [newAdminData, setNewAdminData] = useState({
    full_name: '',
    email: '',
    password: ''
  });
  const [editData, setEditData] = useState({
    full_name: '',
    email: '',
    whatsapp: ''
  });
  const [editPhotoFile, setEditPhotoFile] = useState(null);
  const [editPhotoPreview, setEditPhotoPreview] = useState(null);
  const [whatsappDialogOpen, setWhatsappDialogOpen] = useState(false);
  const [whatsappTargetUser, setWhatsappTargetUser] = useState(null);
  const [whatsappBio, setWhatsappBio] = useState('');
  const [isSubmittingWhatsapp, setIsSubmittingWhatsapp] = useState(false);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const response = await adminAPI.getUsers();
      setUsers(response.data);
    } catch (error) {
      toast.error('Erro ao carregar usuários');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActive = async (user) => {
    try {
      await adminAPI.updateUser(user.id, { is_active: !user.is_active });
      toast.success(`Usuário ${user.is_active ? 'desativado' : 'ativado'} com sucesso`);
      loadUsers();
    } catch (error) {
      toast.error('Erro ao atualizar usuário');
    }
  };

  const handleUpdateRole = async (user, newRole) => {
    try {
      await adminAPI.updateUser(user.id, { role: newRole });
      toast.success('Permissão atualizada');
      loadUsers();
    } catch (error) {
      toast.error('Erro ao atualizar permissão');
    }
  };

  const handleDeleteUser = async (userId) => {
    try {
      await adminAPI.deleteUser(userId);
      toast.success('Usuário excluído');
      loadUsers();
    } catch (error) {
      toast.error('Erro ao excluir usuário');
    }
  };

  const handleOpenEditDialog = (user) => {
    const currentPhotoUrl = user.profile_photo_url
      ? (user.profile_photo_url.startsWith('http') ? user.profile_photo_url : `${backendBaseUrl}${user.profile_photo_url}`)
      : null;

    setSelectedUser(user);
    setEditData({
      full_name: user.full_name,
      email: user.email,
      whatsapp: user.whatsapp || ''
    });
    setEditPhotoFile(null);
    setEditPhotoPreview(currentPhotoUrl);
    setEditDialogOpen(true);
  };

  const handlePhotoSelection = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error('Selecione apenas arquivos de imagem');
      return;
    }

    setEditPhotoFile(file);
    setEditPhotoPreview(URL.createObjectURL(file));
  };

  const handleCreateAdmin = async () => {
    try {
      await adminAPI.createUser({
        ...newAdminData,
        role: 'ADMIN',
        is_active: true
      });
      toast.success('Novo admin criado com sucesso');
      setCreateDialogOpen(false);
      setNewAdminData({ full_name: '', email: '', password: '' });
      loadUsers();
    } catch (error) {
      const detail = error?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Erro ao criar admin');
    }
  };

  const handleOpenWhatsappDialog = (user) => {
    setWhatsappTargetUser(user);
    setWhatsappBio('');
    setWhatsappDialogOpen(true);
  };

  const handleAddUserToWhatsappGroup = async () => {
    if (!whatsappTargetUser || !whatsappBio.trim()) return;

    try {
      setIsSubmittingWhatsapp(true);
      await adminAPI.addUserToWhatsappGroup(whatsappTargetUser.id, {
        biography: whatsappBio.trim()
      });
      toast.success('Usuário adicionado ao grupo com sucesso');
      setWhatsappDialogOpen(false);
      setWhatsappTargetUser(null);
      setWhatsappBio('');
      loadUsers();
    } catch (error) {
      const detail = error?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Erro ao adicionar usuário no grupo');
    } finally {
      setIsSubmittingWhatsapp(false);
    }
  };

  const handleSaveUserEdits = async () => {
    if (!selectedUser) return;

    try {
      const hasProfileChanged = (
        editData.full_name !== selectedUser.full_name ||
        editData.email !== selectedUser.email ||
        editData.whatsapp !== (selectedUser.whatsapp || '')
      );

      if (!hasProfileChanged && !editPhotoFile) {
        toast.error('Nenhuma alteração para salvar');
        return;
      }

      if (hasProfileChanged) {
        await adminAPI.updateUser(selectedUser.id, editData);
      }

      if (editPhotoFile) {
        const formData = new FormData();
        formData.append('profile_photo', editPhotoFile);
        await adminAPI.uploadUserPhoto(selectedUser.id, formData);
      }

      toast.success('Usuário atualizado com sucesso');
      setEditDialogOpen(false);
      setSelectedUser(null);
      setEditPhotoFile(null);
      setEditPhotoPreview(null);
      loadUsers();
    } catch (error) {
      const detail = error?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Erro ao atualizar usuário');
    }
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          user.email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = filterRole === 'all' || user.role === filterRole;
    const matchesStatus = filterStatus === 'all' || 
                          (filterStatus === 'active' && user.is_active) ||
                          (filterStatus === 'inactive' && !user.is_active);
    
    return matchesSearch && matchesRole && matchesStatus;
  });

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="spinner" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6" data-testid="admin-users-page">
        {/* Header */}
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-white flex items-center gap-3">
            <Users className="text-primary" />
            Gerenciar Usuários
          </h1>
          <p className="text-slate-400 mt-1">
            Administre os usuários do sistema ELIOS
          </p>
        </div>
        <div className="flex justify-end">
          <Button
            onClick={() => setCreateDialogOpen(true)}
            className="bg-primary text-primary-foreground"
            data-testid="open-create-admin-dialog"
          >
            Adicionar Admin
          </Button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="glass-card border-white/10">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-primary/20 flex items-center justify-center">
                <Users className="text-primary" size={24} />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{users.length}</p>
                <p className="text-slate-400 text-sm">Total</p>
              </div>
            </CardContent>
          </Card>
          
          <Card className="glass-card border-white/10">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-green-500/20 flex items-center justify-center">
                <UserCheck className="text-green-500" size={24} />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">
                  {users.filter(u => u.is_active).length}
                </p>
                <p className="text-slate-400 text-sm">Ativos</p>
              </div>
            </CardContent>
          </Card>
          
          <Card className="glass-card border-white/10">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-amber-500/20 flex items-center justify-center">
                <UserX className="text-amber-500" size={24} />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">
                  {users.filter(u => !u.is_active).length}
                </p>
                <p className="text-slate-400 text-sm">Pendentes</p>
              </div>
            </CardContent>
          </Card>
          
          <Card className="glass-card border-white/10">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-purple-500/20 flex items-center justify-center">
                <Shield className="text-purple-500" size={24} />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">
                  {users.filter(u => u.role === 'ADMIN').length}
                </p>
                <p className="text-slate-400 text-sm">Admins</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="glass-card border-white/10">
          <CardContent className="p-4">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                <Input
                  placeholder="Buscar por nome ou email..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 bg-slate-900/50 border-slate-700 text-white"
                  data-testid="search-users"
                />
              </div>
              
              <Select value={filterRole} onValueChange={setFilterRole}>
                <SelectTrigger className="w-full md:w-40 bg-slate-900/50 border-slate-700 text-white">
                  <SelectValue placeholder="Permissão" />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-slate-700">
                  <SelectItem value="all" className="text-white">Todas</SelectItem>
                  <SelectItem value="ADMIN" className="text-white">Admin</SelectItem>
                  <SelectItem value="DEFAULT" className="text-white">Padrão</SelectItem>
                </SelectContent>
              </Select>
              
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="w-full md:w-40 bg-slate-900/50 border-slate-700 text-white">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-slate-700">
                  <SelectItem value="all" className="text-white">Todos</SelectItem>
                  <SelectItem value="active" className="text-white">Ativos</SelectItem>
                  <SelectItem value="inactive" className="text-white">Inativos</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Users Table */}
        <Card className="glass-card border-white/10 overflow-hidden">
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table className="admin-table">
                <TableHeader>
                  <TableRow className="border-white/5 hover:bg-transparent">
                    <TableHead className="text-slate-400">Usuário</TableHead>
                    <TableHead className="text-slate-400">Email</TableHead>
                    <TableHead className="text-slate-400">Permissão</TableHead>
                    <TableHead className="text-slate-400">Status</TableHead>
                    <TableHead className="text-slate-400">Formulário</TableHead>
                    <TableHead className="text-slate-400">Cadastro</TableHead>
                    <TableHead className="text-slate-400 text-right">Ações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredUsers.map((user) => (
                    <TableRow key={user.id} className="border-white/5">
                      <TableCell className="font-medium text-white">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center">
                            {user.profile_photo_url ? (
                              <img
                                src={user.profile_photo_url.startsWith('http') ? user.profile_photo_url : `${backendBaseUrl}${user.profile_photo_url}`}
                                alt={`Foto de ${user.full_name}`}
                                className="w-10 h-10 rounded-full object-cover"
                              />
                            ) : user.role === 'ADMIN' ? (
                              <Shield size={18} className="text-primary" />
                            ) : (
                              <User size={18} className="text-slate-400" />
                            )}
                          </div>
                          {user.full_name}
                        </div>
                      </TableCell>
                      <TableCell className="text-slate-400">{user.email}</TableCell>
                      <TableCell>
                        <Select
                          value={user.role}
                          onValueChange={(value) => handleUpdateRole(user, value)}
                        >
                          <SelectTrigger className="w-28 h-8 bg-slate-800/50 border-slate-700 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-slate-900 border-slate-700">
                            <SelectItem value="DEFAULT" className="text-white">Padrão</SelectItem>
                            <SelectItem value="ADMIN" className="text-white">Admin</SelectItem>
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={user.is_active}
                            onCheckedChange={() => handleToggleActive(user)}
                            data-testid={`toggle-${user.id}`}
                          />
                          <span className={`text-xs ${
                            user.is_active ? 'text-green-400' : 'text-amber-400'
                          }`}>
                            {user.is_active ? 'Ativo' : 'Inativo'}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          user.form_completed
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-slate-700 text-slate-400'
                        }`}>
                          {user.form_completed ? 'Preenchido' : 'Pendente'}
                        </span>
                      </TableCell>
                      <TableCell className="text-slate-500 text-sm">
                        {new Date(user.created_at).toLocaleDateString('pt-BR')}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-8 w-8 text-slate-400 hover:text-green-400 disabled:text-slate-600"
                            data-testid={`add-whatsapp-group-${user.id}`}
                            disabled={!user.whatsapp || user.whatsapp_in_elios_group}
                            title={
                              user.whatsapp_in_elios_group
                                ? 'Usuário já está no grupo do WhatsApp'
                                : (!user.whatsapp ? 'Usuário sem WhatsApp cadastrado' : 'Adicionar ao grupo do WhatsApp')
                            }
                            onClick={() => handleOpenWhatsappDialog(user)}
                          >
                            <UserPlus size={16} />
                          </Button>
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-8 w-8 text-slate-400 hover:text-primary"
                            data-testid={`edit-user-${user.id}`}
                            onClick={() => handleOpenEditDialog(user)}
                          >
                            <Edit2 size={16} />
                          </Button>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-8 w-8 text-slate-400 hover:text-red-400"
                                data-testid={`delete-user-${user.id}`}
                              >
                                <Trash2 size={16} />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent className="glass-card border-white/10">
                              <AlertDialogHeader>
                                <AlertDialogTitle className="text-white">
                                  Excluir Usuário?
                                </AlertDialogTitle>
                                <AlertDialogDescription className="text-slate-400">
                                  Esta ação não pode ser desfeita. Todos os dados do usuário serão perdidos.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel className="bg-slate-800 text-white border-slate-700">
                                  Cancelar
                                </AlertDialogCancel>
                                <AlertDialogAction
                                  onClick={() => handleDeleteUser(user.id)}
                                  className="bg-red-600 hover:bg-red-700"
                                >
                                  Excluir
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {filteredUsers.length === 0 && (
              <div className="text-center py-12">
                <Users className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-500">Nenhum usuário encontrado</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogContent className="glass-card border-white/10">
            <DialogHeader>
              <DialogTitle className="text-white">Criar novo admin</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <Input
                placeholder="Nome completo"
                value={newAdminData.full_name}
                onChange={(event) => setNewAdminData((prev) => ({ ...prev, full_name: event.target.value }))}
                className="bg-slate-900/50 border-slate-700 text-white"
              />
              <Input
                type="email"
                placeholder="Email"
                value={newAdminData.email}
                onChange={(event) => setNewAdminData((prev) => ({ ...prev, email: event.target.value }))}
                className="bg-slate-900/50 border-slate-700 text-white"
              />
              <Input
                type="password"
                placeholder="Senha inicial"
                value={newAdminData.password}
                onChange={(event) => setNewAdminData((prev) => ({ ...prev, password: event.target.value }))}
                className="bg-slate-900/50 border-slate-700 text-white"
              />
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setCreateDialogOpen(false)}
                className="border-slate-700 text-white"
              >
                Cancelar
              </Button>
              <Button
                onClick={handleCreateAdmin}
                disabled={!newAdminData.full_name || !newAdminData.email || !newAdminData.password}
              >
                Criar Admin
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
          <DialogContent className="glass-card border-white/10">
            <DialogHeader>
              <DialogTitle className="text-white">Editar usuário</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <div className="rounded-lg border border-slate-700 bg-slate-900/40 p-4">
                <p className="text-sm text-slate-300 mb-3">Foto de perfil</p>
                <div className="flex items-center gap-4">
                  <div className="h-20 w-20 rounded-full bg-slate-800 flex items-center justify-center overflow-hidden border border-slate-700">
                    {editPhotoPreview ? (
                      <img
                        src={editPhotoPreview}
                        alt={`Foto de ${editData.full_name || selectedUser?.full_name || 'usuário'}`}
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <User className="text-slate-500" size={28} />
                    )}
                  </div>
                  <div className="space-y-2">
                    <label className="inline-flex items-center gap-2 text-sm text-white bg-slate-800 px-3 py-2 rounded-md border border-slate-700 cursor-pointer hover:bg-slate-700 transition-colors">
                      <Camera size={16} />
                      <span>{selectedUser?.profile_photo_url ? 'Trocar foto' : 'Enviar foto'}</span>
                      <input
                        type="file"
                        accept="image/png,image/jpeg,image/jpg"
                        className="hidden"
                        onChange={handlePhotoSelection}
                      />
                    </label>
                    <p className="text-xs text-slate-500">Formatos: JPG ou PNG (máx. 5MB)</p>
                  </div>
                </div>
              </div>
              <Input
                placeholder="Nome completo"
                value={editData.full_name}
                onChange={(event) => setEditData((prev) => ({ ...prev, full_name: event.target.value }))}
                className="bg-slate-900/50 border-slate-700 text-white"
              />
              <Input
                type="email"
                placeholder="Email"
                value={editData.email}
                onChange={(event) => setEditData((prev) => ({ ...prev, email: event.target.value }))}
                className="bg-slate-900/50 border-slate-700 text-white"
              />
              <Input
                type="tel"
                placeholder="WhatsApp"
                value={editData.whatsapp}
                onChange={(event) =>
                  setEditData((prev) => ({ ...prev, whatsapp: applyPhoneMask(event.target.value) }))
                }
                className="bg-slate-900/50 border-slate-700 text-white"
              />
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setEditDialogOpen(false)}
                className="border-slate-700 text-white"
              >
                Cancelar
              </Button>
              <Button
                onClick={handleSaveUserEdits}
                disabled={!editData.full_name || !editData.email}
              >
                Salvar alterações
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <Dialog open={whatsappDialogOpen} onOpenChange={setWhatsappDialogOpen}>
          <DialogContent className="glass-card border-white/10">
            <DialogHeader>
              <DialogTitle className="text-white">Adicionar usuário ao grupo do WhatsApp</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <p className="text-sm text-slate-300">
                Usuário: <span className="font-semibold text-white">{whatsappTargetUser?.full_name || '-'}</span>
              </p>
              <Input
                readOnly
                value={whatsappTargetUser?.whatsapp || ''}
                className="bg-slate-900/50 border-slate-700 text-white"
              />
              <textarea
                value={whatsappBio}
                onChange={(event) => setWhatsappBio(event.target.value)}
                placeholder="Escreva uma breve biografia para apresentar o usuário no grupo..."
                className="min-h-[120px] w-full rounded-md border border-slate-700 bg-slate-900/50 p-3 text-sm text-white placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
              />
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setWhatsappDialogOpen(false)}
                className="border-slate-700 text-white"
                disabled={isSubmittingWhatsapp}
              >
                Cancelar
              </Button>
              <Button
                onClick={handleAddUserToWhatsappGroup}
                disabled={!whatsappBio.trim() || isSubmittingWhatsapp}
              >
                {isSubmittingWhatsapp ? 'Enviando...' : 'Adicionar ao grupo'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default AdminUsersPage;
