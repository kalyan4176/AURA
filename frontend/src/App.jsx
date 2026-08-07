import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuth } from './hooks/useAuth';
import { Workspaces } from './pages/Workspaces';
import { Dashboard } from './pages/Dashboard';
import { QueryConsole } from './pages/QueryConsole';
import { Reports } from './pages/Reports';
import { Diagnostics } from './pages/Diagnostics';
import { Bot, LogOut, LayoutGrid, Terminal, Activity, LogIn, Loader2, FileText, Settings } from 'lucide-react';

const queryClient = new QueryClient();

function MainAppContent() {
  const { user, isAuthenticated, isLoading, login, register, logout } = useAuth();
  
  const [activeWorkspaceId, setActiveWorkspaceId] = useState(null);
  const [activeDatasetId, setActiveDatasetId] = useState(null);
  const [subView, setSubView] = useState('dashboard'); // dashboard, query, reports, diagnostics
  
  // Auth Form local states
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState(null);

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthError(null);
    try {
      if (isRegisterMode) {
        await register({ email, password, role: 'analyst' });
        setIsRegisterMode(false);
        alert('Registration successful! Please login.');
      } else {
        await login({ email, password });
      }
      setEmail('');
      setPassword('');
    } catch (err) {
      setAuthError(err.message || 'Authentication failed.');
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-3">
        <Loader2 className="w-10 h-10 animate-spin text-primary" />
        <p className="text-text-secondary text-sm">Synchronizing user credentials context...</p>
      </div>
    );
  }

  // Render auth screens if not logged in
  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen p-6 bg-background relative overflow-hidden">
        
        {/* Glow vector decorations */}
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-primary/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-secondary/10 rounded-full blur-[120px]" />

        <div className="w-full max-w-md glass-card p-8 flex flex-col gap-6 z-10">
          <div className="text-center">
            <h1 className="text-3xl font-black text-gradient tracking-tight">AURA</h1>
            <p className="text-xs text-text-secondary opacity-70 mt-1 uppercase tracking-widest font-semibold">Autonomous Unified Reasoning Analytics</p>
          </div>

          <form onSubmit={handleAuthSubmit} className="flex flex-col gap-4">
            <h2 className="text-lg font-bold text-text-primary text-center">
              {isRegisterMode ? 'Register Analyst Account' : 'Sign In to Platform'}
            </h2>
            
            {authError && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg p-3 text-xs">
                {authError}
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-text-secondary">Email Address</label>
              <input 
                type="email" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="analyst@aura.ai"
                className="bg-black/40 border border-border rounded-xl px-4 py-2.5 text-sm text-text-primary focus:outline-none focus:border-primary placeholder-text-secondary/40"
                required
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-text-secondary">Password</label>
              <input 
                type="password" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="bg-black/40 border border-border rounded-xl px-4 py-2.5 text-sm text-text-primary focus:outline-none focus:border-primary placeholder-text-secondary/40"
                required
              />
            </div>

            <button 
              type="submit"
              className="mt-2 w-full bg-primary hover:bg-primary-hover text-black font-extrabold rounded-xl py-3 text-sm transition-all flex items-center justify-center gap-2"
            >
              <LogIn className="w-4 h-4" /> {isRegisterMode ? 'Register' : 'Authenticate'}
            </button>
          </form>

          <div className="text-center text-xs text-text-secondary">
            {isRegisterMode ? (
              <p>Already registered? <button onClick={() => setIsRegisterMode(false)} className="text-primary hover:underline font-semibold">Sign In</button></p>
            ) : (
              <p>Need a workspace account? <button onClick={() => setIsRegisterMode(true)} className="text-primary hover:underline font-semibold">Register Here</button></p>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-text-primary">
      
      {/* Navigation Headers */}
      <nav className="glass-nav sticky top-0 z-50 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xl font-black text-gradient tracking-tight">AURA</span>
          <span className="bg-white/5 border border-border rounded px-2 py-0.5 text-[10px] text-text-secondary uppercase tracking-widest font-bold">Portal v1</span>
        </div>

        {isAuthenticated && (
          <div className="flex items-center gap-4">
            
            {/* View navigation switches */}
            {activeWorkspaceId && (
              <div className="flex border border-border rounded-lg overflow-hidden bg-white/2">
                <button 
                  onClick={() => { setActiveDatasetId(null); setSubView('reports'); }}
                  className={`px-3 py-1.5 text-xs font-semibold flex items-center gap-1.5 transition-all ${subView === 'reports' && !activeDatasetId ? 'bg-primary text-black' : 'text-text-secondary hover:bg-white/5'}`}
                >
                  <FileText className="w-3.5 h-3.5" /> Workspace Reports
                </button>
                
                {activeDatasetId && (
                  <>
                    <button 
                      onClick={() => setSubView('dashboard')}
                      className={`px-3 py-1.5 text-xs font-semibold flex items-center gap-1.5 transition-all border-l border-border ${subView === 'dashboard' ? 'bg-primary text-black' : 'text-text-secondary hover:bg-white/5'}`}
                    >
                      <Activity className="w-3.5 h-3.5" /> Profiler
                    </button>
                    <button 
                      onClick={() => setSubView('query')}
                      className={`px-3 py-1.5 text-xs font-semibold flex items-center gap-1.5 transition-all border-l border-border ${subView === 'query' ? 'bg-primary text-black' : 'text-text-secondary hover:bg-white/5'}`}
                    >
                      <Terminal className="w-3.5 h-3.5" /> Query Console
                    </button>
                  </>
                )}
              </div>
            )}

            <button 
              onClick={() => { setActiveDatasetId(null); setActiveWorkspaceId(null); setSubView('diagnostics'); }}
              className={`px-3.5 py-1.5 border border-border rounded-lg text-xs transition-all flex items-center gap-1.5 ${subView === 'diagnostics' ? 'bg-primary text-black border-primary' : 'bg-white/5 text-text-secondary hover:bg-white/10'}`}
            >
              <Activity className="w-4 h-4" /> System Health
            </button>

            <button 
              onClick={() => { setActiveDatasetId(null); setActiveWorkspaceId(null); setSubView('dashboard'); }}
              className="px-3.5 py-1.5 border border-border rounded-lg bg-white/5 text-xs hover:bg-white/10 transition-all flex items-center gap-1.5 text-text-secondary"
            >
              <LayoutGrid className="w-4 h-4" /> Workspaces
            </button>

            <div className="flex items-center gap-2 border-l border-border pl-4">
              <span className="text-xs text-text-secondary truncate max-w-[120px]">{user.email}</span>
              <button 
                onClick={logout}
                className="p-1.5 text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </nav>

      {/* View routing router */}
      <main className="min-h-[calc(100vh-80px)]">
        {subView === 'diagnostics' ? (
          <Diagnostics />
        ) : !activeWorkspaceId ? (
          <Workspaces onSelectDataset={(dId, wsId) => { setActiveDatasetId(dId); setActiveWorkspaceId(wsId); setSubView('dashboard'); }} />
        ) : subView === 'reports' ? (
          <Reports workspaceId={activeWorkspaceId} />
        ) : subView === 'dashboard' ? (
          <Dashboard datasetId={activeDatasetId} onBack={() => setActiveDatasetId(null)} />
        ) : (
          <QueryConsole datasetId={activeDatasetId} />
        )}
      </main>
    </div>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MainAppContent />
    </QueryClientProvider>
  );
}
export default App;
