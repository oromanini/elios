import React, { useState } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Logo from './Logo';
import {
  LayoutDashboard,
  Hexagon,
  MessageSquare,
  Target,
  Users,
  Settings,
  ShieldAlert,
  LogOut,
  Menu,
  X,
  Brain,
  FileText
} from 'lucide-react';
import { Button } from './ui/button';

const Sidebar = () => {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const navItems = [
    { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/pilares', icon: Hexagon, label: 'Pilares' },
    { path: '/metas', icon: Target, label: 'Metas' },
    { path: '/chat', icon: MessageSquare, label: 'ELIOS Chat' },
  ];

  const adminItems = [
    { path: '/admin/usuarios', icon: Users, label: 'Usuários' },
    { path: '/admin/perguntas', icon: FileText, label: 'Perguntas' },
    { path: '/admin/elios', icon: Brain, label: 'Treinar ELIOS' },
  ];

  const NavItem = ({ item }) => {
    const isActive = location.pathname === item.path;
    return (
      <NavLink
        to={item.path}
        onClick={() => setMobileOpen(false)}
        className={`flex items-center gap-3 px-4 py-3 rounded-sm transition-all duration-200 ${
          isActive 
            ? 'sidebar-active bg-primary/10 text-primary' 
            : 'text-slate-400 hover:text-white hover:bg-white/5'
        }`}
        data-testid={`nav-${item.path.replace('/', '')}`}
      >
        <item.icon size={20} strokeWidth={1.5} />
        <span className="font-medium">{item.label}</span>
      </NavLink>
    );
  };

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="p-6 border-b border-white/5">
        <Logo size="md" />
      </div>

      {/* User Info */}
      <div className="p-4 border-b border-white/5">
        <div className="glass-card rounded-lg p-3">
          <p className="text-sm text-slate-400">Bem-vindo,</p>
          <p className="text-white font-semibold truncate">{user?.full_name}</p>
          <span className={`inline-block mt-2 px-2 py-0.5 text-xs rounded-full ${
            isAdmin() ? 'bg-primary/20 text-primary' : 'bg-accent/20 text-accent'
          }`}>
            {user?.role}
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        <p className="text-xs text-slate-500 uppercase tracking-wider px-4 mb-2">Menu</p>
        {navItems.map((item) => (
          <NavItem key={item.path} item={item} />
        ))}

        {isAdmin() && (
          <>
            <div className="my-4 border-t border-white/5" />
            <p className="text-xs text-slate-500 uppercase tracking-wider px-4 mb-2">Administração</p>
            {adminItems.map((item) => (
              <NavItem key={item.path} item={item} />
            ))}
          </>
        )}
      </nav>

      {/* Logout */}
      <div className="p-4 border-t border-white/5">
        <Button
          variant="ghost"
          className="w-full justify-start text-slate-400 hover:text-red-400 hover:bg-red-500/10"
          onClick={handleLogout}
          data-testid="logout-btn"
        >
          <LogOut size={20} className="mr-3" />
          Sair
        </Button>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile menu button */}
      <button
        className="fixed top-4 left-4 z-50 p-2 rounded-lg bg-secondary text-white md:hidden"
        onClick={() => setMobileOpen(!mobileOpen)}
        data-testid="mobile-menu-btn"
      >
        {mobileOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Mobile overlay */}
      <div 
        className={`sidebar-overlay md:hidden ${mobileOpen ? 'open' : ''}`}
        onClick={() => setMobileOpen(false)}
      />

      {/* Sidebar */}
      <aside 
        className={`fixed left-0 top-0 h-full w-64 bg-slate-950/95 border-r border-white/5 backdrop-blur-lg z-50 
          transform transition-transform duration-300 md:translate-x-0
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}
      >
        <SidebarContent />
      </aside>
    </>
  );
};

export default Sidebar;
