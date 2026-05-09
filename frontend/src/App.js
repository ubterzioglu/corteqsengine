import React, { useState, useEffect, useCallback, createContext, useContext, useRef } from 'react';
import { Routes, Route, Navigate, useNavigate, useLocation, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  House, Database, Graph, ChatCircle, ChartBar, Gear, SignOut, List,
  MagnifyingGlass, Bell, CaretRight, Plus, Plugs, ArrowRight,
  SlackLogo, GithubLogo, GoogleDriveLogo, Envelope, WhatsappLogo,
  Lightning, Users, Folder, Calendar, Tag, X, PaperPlaneTilt, Trash,
  Spinner, CheckCircle, Warning, Clock, ArrowsClockwise
} from '@phosphor-icons/react';
import './App.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// ==================== AUTH CONTEXT ====================
const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    // CRITICAL: Skip if returning from OAuth callback
    if (window.location.hash?.includes('session_id=')) {
      setLoading(false);
      return;
    }
    
    try {
      const response = await fetch(`${API_URL}/api/auth/me`, {
        credentials: 'include'
      });
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      }
    } catch (error) {
      console.log('Not authenticated');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = (userData) => setUser(userData);
  const logout = async () => {
    try {
      await fetch(`${API_URL}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include'
      });
    } catch (error) {
      console.error('Logout error:', error);
    }
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
};

// ==================== AUTH CALLBACK ====================
const AuthCallback = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processAuth = async () => {
      const hash = window.location.hash;
      const sessionId = hash.match(/session_id=([^&]+)/)?.[1];
      
      if (!sessionId) {
        navigate('/login');
        return;
      }

      try {
        const response = await fetch(`${API_URL}/api/auth/session`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ session_id: sessionId })
        });

        if (response.ok) {
          const userData = await response.json();
          login(userData);
          navigate('/dashboard', { replace: true, state: { user: userData } });
        } else {
          navigate('/login');
        }
      } catch (error) {
        console.error('Auth error:', error);
        navigate('/login');
      }
    };

    processAuth();
  }, [navigate, login]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-100">
      <div className="spinner" />
    </div>
  );
};

// ==================== PROTECTED ROUTE ====================
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-100">
        <div className="spinner" />
      </div>
    );
  }

  if (location.state?.user) {
    return children;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

// ==================== LOGIN PAGE ====================
const LoginPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  const handleGoogleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen bg-zinc-100 flex">
      {/* Left Panel - Hero */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden">
        <div 
          className="absolute inset-0 bg-cover bg-center"
          style={{ 
            backgroundImage: 'url(https://images.unsplash.com/photo-1683447551794-1c287cd42675?w=1200)',
            filter: 'grayscale(100%)'
          }}
        />
        <div className="absolute inset-0 bg-primary/90" />
        <div className="relative z-10 flex flex-col justify-center p-16 text-white">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <h1 className="font-display text-5xl font-black tracking-tighter mb-4">
              CorteQS
            </h1>
            <p className="text-xl text-white/80 mb-8">
              Intelligence Engine
            </p>
            <div className="space-y-4 text-white/70">
              <div className="flex items-center gap-3">
                <Database size={20} />
                <span>Unified Corporate Memory</span>
              </div>
              <div className="flex items-center gap-3">
                <Graph size={20} />
                <span>Knowledge Graph Visualization</span>
              </div>
              <div className="flex items-center gap-3">
                <ChatCircle size={20} />
                <span>AI-Powered Q&A</span>
              </div>
              <div className="flex items-center gap-3">
                <ChartBar size={20} />
                <span>Analytics Dashboard</span>
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Right Panel - Login */}
      <div className="flex-1 flex items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="w-full max-w-md"
        >
          <div className="bg-white rounded-md border border-zinc-200 p-8 shadow-sm">
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-12 h-12 bg-primary rounded-md mb-4">
                <Lightning size={24} weight="fill" className="text-white" />
              </div>
              <h2 className="font-display text-2xl font-bold text-zinc-900">
                Welcome Back
              </h2>
              <p className="text-zinc-500 mt-2">
                Sign in to access your corporate intelligence
              </p>
            </div>

            <button
              data-testid="google-login-btn"
              onClick={handleGoogleLogin}
              className="w-full flex items-center justify-center gap-3 bg-white border border-zinc-200 rounded-md px-4 py-3 font-medium text-zinc-900 hover:bg-zinc-50 transition-colors"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continue with Google
            </button>

            <p className="text-xs text-zinc-400 text-center mt-6">
              By signing in, you agree to our Terms of Service and Privacy Policy
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

// ==================== SIDEBAR ====================
const Sidebar = ({ isCollapsed, setIsCollapsed }) => {
  const location = useLocation();
  const { user, logout } = useAuth();

  const navItems = [
    { path: '/dashboard', icon: House, label: 'Dashboard' },
    { path: '/data-sources', icon: Database, label: 'Data Sources' },
    { path: '/knowledge-graph', icon: Graph, label: 'Knowledge Graph' },
    { path: '/ai-chat', icon: ChatCircle, label: 'AI Assistant' },
    { path: '/analytics', icon: ChartBar, label: 'Analytics' },
  ];

  return (
    <aside className={`bg-white border-r border-zinc-200 flex flex-col transition-all duration-300 ${isCollapsed ? 'w-16' : 'w-64'}`}>
      {/* Logo */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-zinc-200">
        {!isCollapsed && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded flex items-center justify-center">
              <Lightning size={18} weight="fill" className="text-white" />
            </div>
            <span className="font-display font-bold text-lg">CorteQS</span>
          </div>
        )}
        <button
          data-testid="sidebar-toggle"
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-2 hover:bg-zinc-100 rounded transition-colors"
        >
          <List size={20} className="text-zinc-600" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              data-testid={`nav-${item.label.toLowerCase().replace(' ', '-')}`}
              className={`flex items-center gap-3 px-4 py-3 mx-2 rounded-md transition-all ${
                isActive 
                  ? 'bg-primary/5 text-primary border-l-2 border-primary' 
                  : 'text-zinc-600 hover:bg-zinc-100'
              }`}
            >
              <item.icon size={20} weight={isActive ? 'fill' : 'regular'} />
              {!isCollapsed && <span className="font-medium">{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* User Section */}
      <div className="border-t border-zinc-200 p-4">
        {!isCollapsed && user && (
          <div className="flex items-center gap-3 mb-3">
            <img 
              src={user.picture || 'https://images.unsplash.com/photo-1718783573640-c5b01c37bf58?w=100'} 
              alt={user.name}
              className="w-10 h-10 rounded-full object-cover"
            />
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm truncate">{user.name}</p>
              <p className="text-xs text-zinc-500 truncate">{user.email}</p>
            </div>
          </div>
        )}
        <button
          data-testid="logout-btn"
          onClick={logout}
          className={`flex items-center gap-3 w-full px-3 py-2 text-zinc-600 hover:bg-zinc-100 rounded-md transition-colors ${isCollapsed ? 'justify-center' : ''}`}
        >
          <SignOut size={20} />
          {!isCollapsed && <span className="text-sm">Sign Out</span>}
        </button>
      </div>
    </aside>
  );
};

// ==================== HEADER ====================
const Header = ({ title }) => {
  const { user } = useAuth();
  
  return (
    <header className="h-16 bg-white/70 backdrop-blur-xl border-b border-zinc-200 sticky top-0 z-50 flex items-center justify-between px-6">
      <h1 className="font-display text-xl font-bold text-zinc-900">{title}</h1>
      
      <div className="flex items-center gap-4">
        <div className="relative">
          <MagnifyingGlass size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
          <input
            data-testid="global-search"
            type="text"
            placeholder="Search..."
            className="pl-10 pr-4 py-2 bg-zinc-100 border border-transparent rounded-md text-sm focus:bg-white focus:border-zinc-200 transition-colors w-64"
          />
        </div>
        
        <button data-testid="notifications-btn" className="p-2 hover:bg-zinc-100 rounded-md transition-colors relative">
          <Bell size={20} className="text-zinc-600" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-accent-red rounded-full" />
        </button>
        
        <img 
          src={user?.picture || 'https://images.unsplash.com/photo-1718783573640-c5b01c37bf58?w=100'} 
          alt={user?.name || 'User'}
          className="w-8 h-8 rounded-full object-cover border-2 border-zinc-200"
        />
      </div>
    </header>
  );
};

// ==================== DASHBOARD PAGE ====================
const DashboardPage = () => {
  const { user } = useAuth();
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const response = await fetch(`${API_URL}/api/analytics/overview`, {
          credentials: 'include'
        });
        if (response.ok) {
          const data = await response.json();
          setAnalytics(data);
        }
      } catch (error) {
        console.error('Error fetching analytics:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  const StatCard = ({ icon: Icon, label, value, color }) => (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white border border-zinc-200 rounded-md p-6 card-hover"
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-1">{label}</p>
          <p className="text-3xl font-display font-black text-zinc-900">{value}</p>
        </div>
        <div className={`w-12 h-12 rounded-md flex items-center justify-center ${color}`}>
          <Icon size={24} weight="fill" className="text-white" />
        </div>
      </div>
    </motion.div>
  );

  return (
    <div data-testid="dashboard-page" className="p-6 sm:p-8">
      {/* Welcome Section */}
      <div className="mb-8">
        <h2 className="font-display text-3xl font-bold text-zinc-900 mb-2">
          Welcome back, {user?.name?.split(' ')[0] || 'User'}
        </h2>
        <p className="text-zinc-500">Here's what's happening with your corporate memory today.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard 
          icon={Graph} 
          label="Knowledge Nodes" 
          value={loading ? '...' : analytics?.statistics?.total_nodes || 0}
          color="bg-primary"
        />
        <StatCard 
          icon={Database} 
          label="Data Sources" 
          value={loading ? '...' : analytics?.statistics?.total_sources || 0}
          color="bg-zinc-800"
        />
        <StatCard 
          icon={Plugs} 
          label="Connected" 
          value={loading ? '...' : analytics?.statistics?.connected_sources || 0}
          color="bg-emerald-500"
        />
        <StatCard 
          icon={ChatCircle} 
          label="AI Messages" 
          value={loading ? '...' : analytics?.statistics?.total_messages || 0}
          color="bg-violet-500"
        />
      </div>

      {/* Quick Actions & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Actions */}
        <div className="bg-white border border-zinc-200 rounded-md p-6">
          <h3 className="font-display text-lg font-bold mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <Link to="/data-sources" data-testid="quick-action-sources" className="flex items-center justify-between p-3 bg-zinc-50 rounded-md hover:bg-zinc-100 transition-colors group">
              <div className="flex items-center gap-3">
                <Database size={20} className="text-primary" />
                <span className="font-medium text-sm">Connect Data Source</span>
              </div>
              <ArrowRight size={16} className="text-zinc-400 group-hover:text-primary transition-colors" />
            </Link>
            <Link to="/knowledge-graph" data-testid="quick-action-graph" className="flex items-center justify-between p-3 bg-zinc-50 rounded-md hover:bg-zinc-100 transition-colors group">
              <div className="flex items-center gap-3">
                <Graph size={20} className="text-primary" />
                <span className="font-medium text-sm">Explore Knowledge</span>
              </div>
              <ArrowRight size={16} className="text-zinc-400 group-hover:text-primary transition-colors" />
            </Link>
            <Link to="/ai-chat" data-testid="quick-action-chat" className="flex items-center justify-between p-3 bg-zinc-50 rounded-md hover:bg-zinc-100 transition-colors group">
              <div className="flex items-center gap-3">
                <ChatCircle size={20} className="text-primary" />
                <span className="font-medium text-sm">Ask AI Assistant</span>
              </div>
              <ArrowRight size={16} className="text-zinc-400 group-hover:text-primary transition-colors" />
            </Link>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="lg:col-span-2 bg-white border border-zinc-200 rounded-md p-6">
          <h3 className="font-display text-lg font-bold mb-4">Recent Activity</h3>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="spinner" />
            </div>
          ) : analytics?.recent_activities?.length > 0 ? (
            <div className="space-y-3">
              {analytics.recent_activities.slice(0, 5).map((activity, idx) => (
                <div key={activity.activity_id || idx} className="flex items-start gap-3 p-3 bg-zinc-50 rounded-md">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <Clock size={16} className="text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-zinc-900">{activity.description}</p>
                    <p className="text-xs text-zinc-500">
                      {new Date(activity.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-zinc-500 py-8">No recent activity</p>
          )}
        </div>
      </div>
    </div>
  );
};

// ==================== DATA SOURCES PAGE ====================
const DataSourcesPage = () => {
  const [sources, setSources] = useState([]);
  const [integrationStatus, setIntegrationStatus] = useState({});
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState({});
  const [showAddModal, setShowAddModal] = useState(false);

  const sourceTypes = [
    { type: 'slack', name: 'Slack', icon: SlackLogo, color: 'bg-purple-500', hasRealIntegration: true },
    { type: 'github', name: 'GitHub', icon: GithubLogo, color: 'bg-zinc-800', hasRealIntegration: true },
    { type: 'gdrive', name: 'Google Drive', icon: GoogleDriveLogo, color: 'bg-yellow-500', hasRealIntegration: true },
    { type: 'email', name: 'Email', icon: Envelope, color: 'bg-blue-500', hasRealIntegration: false },
    { type: 'whatsapp', name: 'WhatsApp', icon: WhatsappLogo, color: 'bg-green-500', hasRealIntegration: false },
  ];

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      // Fetch sources and integration status in parallel
      const [sourcesRes, statusRes] = await Promise.all([
        fetch(`${API_URL}/api/data-sources`, { credentials: 'include' }),
        fetch(`${API_URL}/api/integrations/status`, { credentials: 'include' })
      ]);
      
      if (sourcesRes.ok) {
        setSources(await sourcesRes.json());
      }
      if (statusRes.ok) {
        setIntegrationStatus(await statusRes.json());
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const syncSource = async (sourceType) => {
    setSyncing(prev => ({ ...prev, [sourceType]: true }));
    try {
      const response = await fetch(`${API_URL}/api/integrations/${sourceType}/sync`, {
        method: 'POST',
        credentials: 'include'
      });
      if (response.ok) {
        const result = await response.json();
        alert(`Sync complete! ${JSON.stringify(result.stats)}`);
        fetchData();
      }
    } catch (error) {
      console.error('Error syncing:', error);
    } finally {
      setSyncing(prev => ({ ...prev, [sourceType]: false }));
    }
  };

  const addSource = async (sourceType, name) => {
    try {
      const response = await fetch(`${API_URL}/api/data-sources`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ source_type: sourceType, name })
      });
      if (response.ok) {
        fetchData();
        setShowAddModal(false);
      }
    } catch (error) {
      console.error('Error adding source:', error);
    }
  };

  const toggleConnection = async (sourceId, currentStatus) => {
    const endpoint = currentStatus === 'connected' ? 'disconnect' : 'connect';
    try {
      await fetch(`${API_URL}/api/data-sources/${sourceId}/${endpoint}`, {
        method: 'PUT',
        credentials: 'include'
      });
      fetchData();
    } catch (error) {
      console.error('Error toggling connection:', error);
    }
  };

  const deleteSource = async (sourceId) => {
    try {
      await fetch(`${API_URL}/api/data-sources/${sourceId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      fetchData();
    } catch (error) {
      console.error('Error deleting source:', error);
    }
  };

  const getSourceIcon = (type) => {
    const source = sourceTypes.find(s => s.type === type);
    return source || { icon: Database, color: 'bg-zinc-500' };
  };

  return (
    <div data-testid="data-sources-page" className="p-6 sm:p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="font-display text-3xl font-bold text-zinc-900 mb-2">Data Sources</h2>
          <p className="text-zinc-500">Connect and manage your data integrations</p>
        </div>
        <button
          data-testid="add-source-btn"
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-md font-medium hover:bg-primary-hover transition-colors"
        >
          <Plus size={18} />
          Add Source
        </button>
      </div>

      {/* Real-time Integration Status */}
      <div className="mb-8">
        <h3 className="font-display text-lg font-bold mb-4">Live Integrations</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Slack Integration */}
          <div className="bg-white border border-zinc-200 rounded-md p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-md bg-purple-500 flex items-center justify-center">
                  <SlackLogo size={20} weight="fill" className="text-white" />
                </div>
                <div>
                  <p className="font-medium text-sm">Slack</p>
                  <div className="flex items-center gap-1">
                    <span className={`w-2 h-2 rounded-full ${integrationStatus.slack?.connected ? 'bg-emerald-500' : 'bg-zinc-300'}`} />
                    <span className="text-xs text-zinc-500 truncate max-w-[80px]">
                      {integrationStatus.slack?.connected ? integrationStatus.slack.team : 'Not connected'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
            {integrationStatus.slack?.connected && (
              <button
                data-testid="sync-slack-btn"
                onClick={() => syncSource('slack')}
                disabled={syncing.slack}
                className="w-full flex items-center justify-center gap-2 bg-purple-50 text-purple-700 px-3 py-2 rounded-md text-xs font-medium hover:bg-purple-100 transition-colors disabled:opacity-50"
              >
                {syncing.slack ? <Spinner size={14} className="animate-spin" /> : <ArrowsClockwise size={14} />}
                {syncing.slack ? 'Syncing...' : 'Sync'}
              </button>
            )}
          </div>

          {/* GitHub Integration */}
          <div className="bg-white border border-zinc-200 rounded-md p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-md bg-zinc-800 flex items-center justify-center">
                  <GithubLogo size={20} weight="fill" className="text-white" />
                </div>
                <div>
                  <p className="font-medium text-sm">GitHub</p>
                  <div className="flex items-center gap-1">
                    <span className={`w-2 h-2 rounded-full ${integrationStatus.github?.connected ? 'bg-emerald-500' : 'bg-zinc-300'}`} />
                    <span className="text-xs text-zinc-500 truncate max-w-[80px]">
                      {integrationStatus.github?.connected ? `@${integrationStatus.github.login}` : 'Not connected'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
            {integrationStatus.github?.connected && (
              <button
                data-testid="sync-github-btn"
                onClick={() => syncSource('github')}
                disabled={syncing.github}
                className="w-full flex items-center justify-center gap-2 bg-zinc-100 text-zinc-700 px-3 py-2 rounded-md text-xs font-medium hover:bg-zinc-200 transition-colors disabled:opacity-50"
              >
                {syncing.github ? <Spinner size={14} className="animate-spin" /> : <ArrowsClockwise size={14} />}
                {syncing.github ? 'Syncing...' : 'Sync'}
              </button>
            )}
          </div>

          {/* Google Drive Integration */}
          <div className="bg-white border border-zinc-200 rounded-md p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-md bg-yellow-500 flex items-center justify-center">
                  <GoogleDriveLogo size={20} weight="fill" className="text-white" />
                </div>
                <div>
                  <p className="font-medium text-sm">Google Drive</p>
                  <div className="flex items-center gap-1">
                    <span className={`w-2 h-2 rounded-full ${integrationStatus.gdrive?.connected ? 'bg-emerald-500' : 'bg-zinc-300'}`} />
                    <span className="text-xs text-zinc-500">
                      {integrationStatus.gdrive?.connected ? 'Connected' : 'Not connected'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
            {integrationStatus.gdrive?.connected && (
              <button
                data-testid="sync-gdrive-btn"
                onClick={() => syncSource('gdrive')}
                disabled={syncing.gdrive}
                className="w-full flex items-center justify-center gap-2 bg-yellow-50 text-yellow-700 px-3 py-2 rounded-md text-xs font-medium hover:bg-yellow-100 transition-colors disabled:opacity-50"
              >
                {syncing.gdrive ? <Spinner size={14} className="animate-spin" /> : <ArrowsClockwise size={14} />}
                {syncing.gdrive ? 'Syncing...' : 'Sync'}
              </button>
            )}
          </div>

          {/* Neo4j Status */}
          <div className="bg-white border border-zinc-200 rounded-md p-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-md bg-blue-600 flex items-center justify-center">
                <Graph size={20} weight="fill" className="text-white" />
              </div>
              <div>
                <p className="font-medium text-sm">Neo4j</p>
                <div className="flex items-center gap-1">
                  <span className={`w-2 h-2 rounded-full ${integrationStatus.neo4j?.connected ? 'bg-emerald-500' : 'bg-zinc-300'}`} />
                  <span className="text-xs text-zinc-500">
                    {integrationStatus.neo4j?.connected ? 'Graph DB' : 'Not connected'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Elasticsearch Status */}
          <div className="bg-white border border-zinc-200 rounded-md p-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-md bg-amber-500 flex items-center justify-center">
                <MagnifyingGlass size={20} weight="fill" className="text-white" />
              </div>
              <div>
                <p className="font-medium text-sm">Elasticsearch</p>
                <div className="flex items-center gap-1">
                  <span className={`w-2 h-2 rounded-full ${integrationStatus.elasticsearch?.connected ? 'bg-emerald-500' : 'bg-zinc-300'}`} />
                  <span className="text-xs text-zinc-500">
                    {integrationStatus.elasticsearch?.connected ? 'Search' : 'Not configured'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Available Connectors */}
      <div className="mb-8">
        <h3 className="font-display text-lg font-bold mb-4">Available Connectors</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {sourceTypes.map((source) => (
            <button
              key={source.type}
              data-testid={`connector-${source.type}`}
              onClick={() => {
                const name = prompt(`Enter name for ${source.name} connection:`);
                if (name) addSource(source.type, name);
              }}
              className="bg-white border border-zinc-200 rounded-md p-6 text-center card-hover relative"
            >
              {source.hasRealIntegration && (
                <span className="absolute top-2 right-2 px-1.5 py-0.5 bg-emerald-100 text-emerald-700 text-[10px] font-bold rounded">LIVE</span>
              )}
              <div className={`w-12 h-12 mx-auto mb-3 rounded-md flex items-center justify-center ${source.color}`}>
                <source.icon size={24} weight="fill" className="text-white" />
              </div>
              <p className="font-medium text-sm">{source.name}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Connected Sources */}
      <div>
        <h3 className="font-display text-lg font-bold mb-4">Connected Sources ({sources.length})</h3>
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="spinner" />
          </div>
        ) : sources.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sources.map((source) => {
              const sourceInfo = getSourceIcon(source.source_type);
              return (
                <div
                  key={source.source_id}
                  data-testid={`source-card-${source.source_id}`}
                  className="bg-white border border-zinc-200 rounded-md p-4 card-hover"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-md flex items-center justify-center ${sourceInfo.color}`}>
                        <sourceInfo.icon size={20} weight="fill" className="text-white" />
                      </div>
                      <div>
                        <p className="font-medium">{source.name}</p>
                        <p className="text-xs text-zinc-500">{source.source_type}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => deleteSource(source.source_id)}
                      className="p-1 text-zinc-400 hover:text-accent-red transition-colors"
                    >
                      <Trash size={16} />
                    </button>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${source.status === 'connected' ? 'bg-emerald-500' : 'bg-zinc-300'}`} />
                      <span className="text-xs text-zinc-500 capitalize">{source.status}</span>
                    </div>
                    <button
                      data-testid={`toggle-source-${source.source_id}`}
                      onClick={() => toggleConnection(source.source_id, source.status)}
                      className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                        source.status === 'connected'
                          ? 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'
                          : 'bg-primary text-white hover:bg-primary-hover'
                      }`}
                    >
                      {source.status === 'connected' ? 'Disconnect' : 'Connect'}
                    </button>
                  </div>
                  
                  {source.last_sync && (
                    <p className="text-xs text-zinc-400 mt-3">
                      Last sync: {new Date(source.last_sync).toLocaleString()}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="bg-white border border-zinc-200 rounded-md p-12 text-center">
            <Database size={48} className="mx-auto text-zinc-300 mb-4" />
            <p className="text-zinc-600 font-medium">No data sources connected</p>
            <p className="text-zinc-400 text-sm">Click on a connector above to add your first data source</p>
          </div>
        )}
      </div>
    </div>
  );
};

// ==================== KNOWLEDGE GRAPH PAGE ====================
const KnowledgeGraphPage = () => {
  const [nodes, setNodes] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newNode, setNewNode] = useState({ node_type: 'topic', title: '', content: '' });

  const nodeTypes = [
    { type: 'person', label: 'Person', icon: Users, color: '#002FA7' },
    { type: 'project', label: 'Project', icon: Folder, color: '#10B981' },
    { type: 'document', label: 'Document', icon: Folder, color: '#F59E0B' },
    { type: 'event', label: 'Event', icon: Calendar, color: '#EF4444' },
    { type: 'topic', label: 'Topic', icon: Tag, color: '#8B5CF6' },
  ];

  useEffect(() => {
    fetchGraphData();
  }, []);

  const fetchGraphData = async () => {
    try {
      const response = await fetch(`${API_URL}/api/knowledge/graph`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setNodes(data.nodes);
        
        // Transform for visualization
        const graphNodes = data.nodes.map(n => ({
          id: n.node_id,
          name: n.title,
          type: n.node_type,
          val: 1
        }));
        
        const graphLinks = data.edges.map(e => ({
          source: e.source,
          target: e.target
        }));
        
        setGraphData({ nodes: graphNodes, links: graphLinks });
      }
    } catch (error) {
      console.error('Error fetching graph:', error);
    } finally {
      setLoading(false);
    }
  };

  const createNode = async () => {
    try {
      const response = await fetch(`${API_URL}/api/knowledge/nodes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(newNode)
      });
      if (response.ok) {
        setShowAddModal(false);
        setNewNode({ node_type: 'topic', title: '', content: '' });
        fetchGraphData();
      }
    } catch (error) {
      console.error('Error creating node:', error);
    }
  };

  const getNodeColor = (type) => {
    const nodeType = nodeTypes.find(n => n.type === type);
    return nodeType?.color || '#71717A';
  };

  return (
    <div data-testid="knowledge-graph-page" className="p-6 sm:p-8 h-[calc(100vh-64px)]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="font-display text-3xl font-bold text-zinc-900 mb-2">Knowledge Graph</h2>
          <p className="text-zinc-500">Visualize and explore your corporate knowledge</p>
        </div>
        <button
          data-testid="add-node-btn"
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-md font-medium hover:bg-primary-hover transition-colors"
        >
          <Plus size={18} />
          Add Node
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[calc(100%-100px)]">
        {/* Graph Visualization */}
        <div className="lg:col-span-3 bg-white border border-zinc-200 rounded-md overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="spinner" />
            </div>
          ) : graphData.nodes.length > 0 ? (
            <div className="relative h-full">
              {/* Simple canvas-based visualization */}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="relative w-full h-full p-8">
                  {graphData.nodes.map((node, idx) => {
                    const angle = (2 * Math.PI * idx) / graphData.nodes.length;
                    const radius = Math.min(200, graphData.nodes.length * 20);
                    const x = 50 + 35 * Math.cos(angle);
                    const y = 50 + 35 * Math.sin(angle);
                    
                    return (
                      <motion.div
                        key={node.id}
                        initial={{ opacity: 0, scale: 0 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: idx * 0.05 }}
                        style={{ 
                          position: 'absolute',
                          left: `${x}%`,
                          top: `${y}%`,
                          transform: 'translate(-50%, -50%)'
                        }}
                        onClick={() => setSelectedNode(nodes.find(n => n.node_id === node.id))}
                        className="cursor-pointer group"
                      >
                        <div 
                          className="w-12 h-12 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-lg group-hover:scale-110 transition-transform"
                          style={{ backgroundColor: getNodeColor(node.type) }}
                        >
                          {node.name.charAt(0).toUpperCase()}
                        </div>
                        <p className="absolute top-full mt-1 left-1/2 -translate-x-1/2 text-xs font-medium text-zinc-700 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
                          {node.name}
                        </p>
                      </motion.div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center p-8">
              <Graph size={64} className="text-zinc-300 mb-4" />
              <p className="text-zinc-600 font-medium">No knowledge nodes yet</p>
              <p className="text-zinc-400 text-sm mb-4">Create your first node to start building your knowledge graph</p>
              <button
                onClick={() => setShowAddModal(true)}
                className="flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-md font-medium hover:bg-primary-hover transition-colors"
              >
                <Plus size={18} />
                Create First Node
              </button>
            </div>
          )}
        </div>

        {/* Node List / Details */}
        <div className="bg-white border border-zinc-200 rounded-md p-4 overflow-auto">
          <h3 className="font-display font-bold mb-4">
            {selectedNode ? 'Node Details' : 'All Nodes'}
          </h3>
          
          {selectedNode ? (
            <div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-sm text-primary mb-4 hover:underline"
              >
                ← Back to list
              </button>
              <div className="space-y-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-1">Title</p>
                  <p className="font-medium">{selectedNode.title}</p>
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-1">Type</p>
                  <span 
                    className="inline-block px-2 py-1 rounded text-xs font-medium text-white"
                    style={{ backgroundColor: getNodeColor(selectedNode.node_type) }}
                  >
                    {selectedNode.node_type}
                  </span>
                </div>
                {selectedNode.content && (
                  <div>
                    <p className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-1">Content</p>
                    <p className="text-sm text-zinc-600">{selectedNode.content}</p>
                  </div>
                )}
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-1">Connections</p>
                  <p className="text-sm text-zinc-600">{selectedNode.connections?.length || 0} nodes</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              {/* Node type legend */}
              <div className="flex flex-wrap gap-2 mb-4">
                {nodeTypes.map((type) => (
                  <span 
                    key={type.type}
                    className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs"
                    style={{ backgroundColor: `${type.color}20`, color: type.color }}
                  >
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: type.color }} />
                    {type.label}
                  </span>
                ))}
              </div>
              
              {nodes.map((node) => (
                <button
                  key={node.node_id}
                  onClick={() => setSelectedNode(node)}
                  className="w-full text-left p-3 bg-zinc-50 rounded-md hover:bg-zinc-100 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span 
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: getNodeColor(node.node_type) }}
                    />
                    <div>
                      <p className="font-medium text-sm">{node.title}</p>
                      <p className="text-xs text-zinc-500">{node.node_type}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Add Node Modal */}
      <AnimatePresence>
        {showAddModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setShowAddModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.95 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-white rounded-md w-full max-w-md p-6"
            >
              <div className="flex items-center justify-between mb-6">
                <h3 className="font-display text-xl font-bold">Add Knowledge Node</h3>
                <button onClick={() => setShowAddModal(false)}>
                  <X size={20} className="text-zinc-400 hover:text-zinc-600" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-zinc-700 mb-2 block">Type</label>
                  <select
                    data-testid="node-type-select"
                    value={newNode.node_type}
                    onChange={(e) => setNewNode({ ...newNode, node_type: e.target.value })}
                    className="w-full p-3 border border-zinc-200 rounded-md focus:border-primary focus:ring-1 focus:ring-primary"
                  >
                    {nodeTypes.map((type) => (
                      <option key={type.type} value={type.type}>{type.label}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="text-sm font-medium text-zinc-700 mb-2 block">Title</label>
                  <input
                    data-testid="node-title-input"
                    type="text"
                    value={newNode.title}
                    onChange={(e) => setNewNode({ ...newNode, title: e.target.value })}
                    placeholder="Enter node title..."
                    className="w-full p-3 border border-zinc-200 rounded-md focus:border-primary focus:ring-1 focus:ring-primary"
                  />
                </div>
                
                <div>
                  <label className="text-sm font-medium text-zinc-700 mb-2 block">Content (optional)</label>
                  <textarea
                    data-testid="node-content-input"
                    value={newNode.content}
                    onChange={(e) => setNewNode({ ...newNode, content: e.target.value })}
                    placeholder="Enter node content..."
                    rows={3}
                    className="w-full p-3 border border-zinc-200 rounded-md focus:border-primary focus:ring-1 focus:ring-primary resize-none"
                  />
                </div>

                <button
                  data-testid="create-node-btn"
                  onClick={createNode}
                  disabled={!newNode.title}
                  className="w-full bg-primary text-white py-3 rounded-md font-medium hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Create Node
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// ==================== AI CHAT PAGE ====================
const AIChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchChatHistory();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchChatHistory = async () => {
    try {
      const response = await fetch(`${API_URL}/api/chat/history`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setMessages(data);
      }
    } catch (error) {
      console.error('Error fetching history:', error);
    } finally {
      setHistoryLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    
    const userMessage = input.trim();
    setInput('');
    setLoading(true);

    // Optimistic update
    setMessages(prev => [...prev, { role: 'user', content: userMessage, message_id: 'temp' }]);

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ message: userMessage })
      });

      if (response.ok) {
        const data = await response.json();
        setMessages(prev => {
          const filtered = prev.filter(m => m.message_id !== 'temp');
          return [...filtered, 
            { ...data.user_message, role: 'user' },
            { ...data.assistant_message, role: 'assistant' }
          ];
        });
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => prev.filter(m => m.message_id !== 'temp'));
    } finally {
      setLoading(false);
    }
  };

  const clearHistory = async () => {
    try {
      await fetch(`${API_URL}/api/chat/history`, {
        method: 'DELETE',
        credentials: 'include'
      });
      setMessages([]);
    } catch (error) {
      console.error('Error clearing history:', error);
    }
  };

  return (
    <div data-testid="ai-chat-page" className="p-6 sm:p-8 h-[calc(100vh-64px)] flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="font-display text-3xl font-bold text-zinc-900 mb-2">AI Assistant</h2>
          <p className="text-zinc-500">Ask questions about your corporate knowledge</p>
        </div>
        <button
          data-testid="clear-chat-btn"
          onClick={clearHistory}
          className="flex items-center gap-2 text-zinc-500 hover:text-accent-red transition-colors"
        >
          <Trash size={18} />
          Clear History
        </button>
      </div>

      {/* Chat Container */}
      <div className="flex-1 bg-white border border-zinc-200 rounded-md flex flex-col overflow-hidden">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6">
          {historyLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="spinner" />
            </div>
          ) : messages.length > 0 ? (
            <div className="space-y-4">
              {messages.map((msg, idx) => (
                <motion.div
                  key={msg.message_id || idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[80%] p-4 rounded-md ${
                    msg.role === 'user' 
                      ? 'bg-primary text-white' 
                      : 'bg-zinc-100 text-zinc-900'
                  }`}>
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </motion.div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-zinc-100 p-4 rounded-md">
                    <div className="flex items-center gap-2">
                      <Spinner size={16} className="animate-spin text-primary" />
                      <span className="text-sm text-zinc-500">Thinking...</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <ChatCircle size={64} className="text-zinc-300 mb-4" />
              <p className="text-zinc-600 font-medium mb-2">Start a conversation</p>
              <p className="text-zinc-400 text-sm">Ask me anything about your corporate knowledge</p>
              <div className="flex flex-wrap gap-2 mt-6 justify-center">
                {[
                  'What data sources are connected?',
                  'Show me recent activity',
                  'Summarize my knowledge base'
                ].map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => setInput(suggestion)}
                    className="px-3 py-2 bg-zinc-100 rounded-md text-sm text-zinc-600 hover:bg-zinc-200 transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-zinc-200 p-4">
          <div className="flex gap-3">
            <input
              data-testid="chat-input"
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
              placeholder="Type your message..."
              className="flex-1 p-3 border border-zinc-200 rounded-md focus:border-primary focus:ring-1 focus:ring-primary"
              disabled={loading}
            />
            <button
              data-testid="send-message-btn"
              onClick={sendMessage}
              disabled={!input.trim() || loading}
              className="bg-primary text-white px-6 py-3 rounded-md font-medium hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <PaperPlaneTilt size={20} weight="fill" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ==================== ANALYTICS PAGE ====================
const AnalyticsPage = () => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const response = await fetch(`${API_URL}/api/analytics/overview`, {
          credentials: 'include'
        });
        if (response.ok) {
          const data = await response.json();
          setAnalytics(data);
        }
      } catch (error) {
        console.error('Error fetching analytics:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  if (loading) {
    return (
      <div data-testid="analytics-page" className="flex items-center justify-center h-[calc(100vh-64px)]">
        <div className="spinner" />
      </div>
    );
  }

  const nodeDistribution = analytics?.node_distribution || {};
  const totalNodes = Object.values(nodeDistribution).reduce((a, b) => a + b, 0);

  return (
    <div data-testid="analytics-page" className="p-6 sm:p-8">
      <div className="mb-8">
        <h2 className="font-display text-3xl font-bold text-zinc-900 mb-2">Analytics</h2>
        <p className="text-zinc-500">Insights and metrics about your corporate memory</p>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-white border border-zinc-200 rounded-md p-6">
          <p className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-2">Total Nodes</p>
          <p className="text-4xl font-display font-black text-zinc-900">
            {analytics?.statistics?.total_nodes || 0}
          </p>
        </div>
        <div className="bg-white border border-zinc-200 rounded-md p-6">
          <p className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-2">Data Sources</p>
          <p className="text-4xl font-display font-black text-zinc-900">
            {analytics?.statistics?.total_sources || 0}
          </p>
        </div>
        <div className="bg-white border border-zinc-200 rounded-md p-6">
          <p className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-2">Connected</p>
          <p className="text-4xl font-display font-black text-emerald-500">
            {analytics?.statistics?.connected_sources || 0}
          </p>
        </div>
        <div className="bg-white border border-zinc-200 rounded-md p-6">
          <p className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-2">AI Queries</p>
          <p className="text-4xl font-display font-black text-violet-500">
            {analytics?.statistics?.total_messages || 0}
          </p>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Node Distribution */}
        <div className="bg-white border border-zinc-200 rounded-md p-6">
          <h3 className="font-display text-lg font-bold mb-4">Knowledge Distribution</h3>
          {totalNodes > 0 ? (
            <div className="space-y-4">
              {Object.entries(nodeDistribution).map(([type, count]) => (
                <div key={type}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium capitalize">{type}</span>
                    <span className="text-sm text-zinc-500">{count}</span>
                  </div>
                  <div className="h-2 bg-zinc-100 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-primary rounded-full transition-all"
                      style={{ width: `${(count / totalNodes) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-zinc-500 py-8">No data to display</p>
          )}
        </div>

        {/* Recent Activity */}
        <div className="bg-white border border-zinc-200 rounded-md p-6">
          <h3 className="font-display text-lg font-bold mb-4">Recent Activity</h3>
          {analytics?.recent_activities?.length > 0 ? (
            <div className="space-y-3">
              {analytics.recent_activities.map((activity, idx) => (
                <div key={activity.activity_id || idx} className="flex items-start gap-3 p-3 bg-zinc-50 rounded-md">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <ArrowsClockwise size={16} className="text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-zinc-900 truncate">{activity.description}</p>
                    <p className="text-xs text-zinc-500">
                      {new Date(activity.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-zinc-500 py-8">No recent activity</p>
          )}
        </div>
      </div>
    </div>
  );
};

// ==================== MAIN LAYOUT ====================
const MainLayout = ({ children }) => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const location = useLocation();

  const getPageTitle = () => {
    const paths = {
      '/dashboard': 'Dashboard',
      '/data-sources': 'Data Sources',
      '/knowledge-graph': 'Knowledge Graph',
      '/ai-chat': 'AI Assistant',
      '/analytics': 'Analytics',
    };
    return paths[location.pathname] || 'CorteQS';
  };

  return (
    <div className="flex h-screen bg-zinc-100">
      <Sidebar isCollapsed={sidebarCollapsed} setIsCollapsed={setSidebarCollapsed} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title={getPageTitle()} />
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
};

// ==================== APP ROUTER ====================
const AppRouter = () => {
  const location = useLocation();

  // Check for OAuth callback FIRST (synchronous check)
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <MainLayout><DashboardPage /></MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/data-sources" element={
        <ProtectedRoute>
          <MainLayout><DataSourcesPage /></MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/knowledge-graph" element={
        <ProtectedRoute>
          <MainLayout><KnowledgeGraphPage /></MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/ai-chat" element={
        <ProtectedRoute>
          <MainLayout><AIChatPage /></MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/analytics" element={
        <ProtectedRoute>
          <MainLayout><AnalyticsPage /></MainLayout>
        </ProtectedRoute>
      } />
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
};

// ==================== APP ====================
function App() {
  return (
    <AuthProvider>
      <AppRouter />
    </AuthProvider>
  );
}

export default App;
