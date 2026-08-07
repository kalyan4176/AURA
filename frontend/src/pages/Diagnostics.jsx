import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { 
  Activity, Cpu, HardDrive, Zap, HelpCircle, Bell, BellRing, Check, RefreshCw, Loader2 
} from 'lucide-react';

export function Diagnostics() {
  const queryClient = useQueryClient();
  const [autoPoll, setAutoPoll] = useState(true);

  // Poll system diagnostics
  const { data: stats, isLoading: loadingStats, refetch: refetchStats } = useQuery({
    queryKey: ['system_diagnostics'],
    queryFn: () => api.get('/system/diagnostics'),
    refetchInterval: autoPoll ? 4000 : false,
  });

  // Poll unread notifications
  const { data: notifications = [], refetch: refetchNotifs } = useQuery({
    queryKey: ['notifications_list'],
    queryFn: () => api.get('/notifications'),
    refetchInterval: autoPoll ? 5000 : false,
  });

  // Dismiss notification mutation
  const dismissNotifMutation = useMutation({
    mutationFn: (id) => api.post(`/notifications/${id}/read`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications_list'] });
    }
  });

  const getAlertColor = (type) => {
    if (type === 'error') return 'border-red-500/20 bg-red-500/5 text-red-400';
    if (type === 'warning') return 'border-accent/20 bg-accent/5 text-amber-400';
    return 'border-primary/20 bg-primary/5 text-primary';
  };

  return (
    <div className="p-6 flex flex-col gap-6 max-w-7xl mx-auto">
      
      {/* Header Panel */}
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary flex items-center gap-3">
            <Activity className="text-primary w-6 h-6" /> System Diagnostics & Health Monitor
          </h1>
          <p className="text-xs text-text-secondary opacity-60 mt-0.5">Real-time telemetry records tracking host metrics, cache efficiencies, and ingestion alerts.</p>
        </div>
        
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-text-secondary cursor-pointer">
            <input 
              type="checkbox" 
              checked={autoPoll} 
              onChange={() => setAutoPoll(!autoPoll)}
              className="accent-primary"
            />
            Auto-refresh (4s)
          </label>
          <button 
            onClick={() => { refetchStats(); refetchNotifs(); }}
            className="p-2 border border-border rounded-lg bg-white/5 text-xs hover:bg-white/10 transition-all text-text-secondary"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {loadingStats ? (
        <div className="flex flex-col items-center justify-center py-24 gap-3">
          <Loader2 className="w-10 h-10 animate-spin text-primary" />
          <p className="text-text-secondary text-sm">Gathering system health parameters...</p>
        </div>
      ) : (
        stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            
            {/* CPU Metric Card */}
            <div className="glass-card p-6 flex items-center justify-between border border-border/80">
              <div>
                <div className="text-xs text-text-secondary opacity-85 uppercase tracking-wider font-semibold">CPU Utilization</div>
                <div className="text-3xl font-extrabold mt-2 text-text-primary">
                  {stats.system.cpu_utilization_percent.toFixed(1)}%
                </div>
                <div className="w-32 bg-white/10 rounded-full h-1 mt-2 overflow-hidden">
                  <div className="bg-primary h-1" style={{ width: `${stats.system.cpu_utilization_percent}%` }} />
                </div>
              </div>
              <Cpu className="w-10 h-10 text-primary opacity-30" />
            </div>

            {/* Memory Card */}
            <div className="glass-card p-6 flex items-center justify-between border border-border/80">
              <div>
                <div className="text-xs text-text-secondary opacity-85 uppercase tracking-wider font-semibold">Memory Usage</div>
                <div className="text-3xl font-extrabold mt-2 text-text-primary">
                  {stats.system.memory_utilization_percent.toFixed(1)}%
                </div>
                <div className="w-32 bg-white/10 rounded-full h-1 mt-2 overflow-hidden">
                  <div className="bg-secondary h-1" style={{ width: `${stats.system.memory_utilization_percent}%` }} />
                </div>
              </div>
              <HardDrive className="w-10 h-10 text-secondary opacity-30" />
            </div>

            {/* Response Latency */}
            <div className="glass-card p-6 flex items-center justify-between border border-border/80">
              <div>
                <div className="text-xs text-text-secondary opacity-85 uppercase tracking-wider font-semibold">Avg API Latency</div>
                <div className="text-3xl font-extrabold mt-2 text-text-primary">
                  {stats.api.average_response_latency_seconds.toFixed(4)}s
                </div>
                <p className="text-[10px] text-text-secondary opacity-60 mt-2">Total calls logged: {stats.api.total_requests}</p>
              </div>
              <Zap className="w-10 h-10 text-accent opacity-30" />
            </div>

            {/* Cache Hits */}
            <div className="glass-card p-6 flex items-center justify-between border border-border/80">
              <div>
                <div className="text-xs text-text-secondary opacity-85 uppercase tracking-wider font-semibold">Cache Hit Ratio</div>
                <div className="text-3xl font-extrabold mt-2 text-text-primary">
                  {(stats.cache.hit_ratio * 100).toFixed(1)}%
                </div>
                <p className="text-[10px] text-text-secondary opacity-60 mt-2">
                  Hits: {stats.cache.hit_count} / Misses: {stats.cache.miss_count}
                </p>
              </div>
              <HelpCircle className="w-10 h-10 text-text-secondary opacity-30" />
            </div>

          </div>
        )
      )}

      {/* Main Splits: Alert Feed & Details list */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Alert Notifications Feed */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          <div className="glass-card p-6 flex flex-col gap-4">
            <h3 className="text-base font-bold text-text-primary border-b border-border pb-2 flex items-center gap-2">
              {notifications.length > 0 ? (
                <BellRing className="text-accent animate-bounce w-5 h-5" />
              ) : (
                <Bell className="text-text-secondary w-5 h-5" />
              )}
              Active Quality Warnings & Ingestion Alerts
            </h3>
            
            <div className="flex flex-col gap-3.5 max-h-[50vh] overflow-y-auto pr-1">
              {notifications.map((notif) => (
                <div 
                  key={notif.id} 
                  className={`p-4 border rounded-xl flex items-start justify-between gap-4 text-xs transition-all ${getAlertColor(notif.type)}`}
                >
                  <div>
                    <div className="font-bold uppercase tracking-wider text-[10px] opacity-75 mb-1">{notif.type} alert</div>
                    <p className="leading-relaxed font-medium opacity-90">{notif.message}</p>
                    <span className="text-[10px] text-text-secondary opacity-50 block mt-2">
                      Logged: {new Date(notif.created_at).toLocaleString()}
                    </span>
                  </div>
                  <button 
                    onClick={() => dismissNotifMutation.mutate(notif.id)}
                    className="p-1 rounded-full bg-white/5 hover:bg-white/10 text-text-primary border border-white/5 transition-all"
                    title="Dismiss alert"
                  >
                    <Check className="w-4 h-4" />
                  </button>
                </div>
              ))}
              {notifications.length === 0 && (
                <div className="text-center py-20 text-xs text-text-secondary opacity-60 flex flex-col items-center justify-center gap-2">
                  <Check className="w-8 h-8 text-primary opacity-60 border border-primary/20 p-1.5 rounded-full" />
                  No quality alerts or execution failures. All systems operate nominal.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Engine Diagnostics details */}
        <div className="lg:col-span-1 flex flex-col gap-6">
          <div className="glass-card p-6 flex flex-col gap-4">
            <h3 className="text-base font-bold text-text-primary border-b border-border pb-2">Active Services Registry</h3>
            <div className="flex flex-col gap-3 text-xs">
              <div className="flex items-center justify-between py-2 border-b border-border/40">
                <span className="text-text-secondary">Uvicorn API Core</span>
                <span className="text-primary font-bold">● ONLINE</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-border/40">
                <span className="text-text-secondary">Celery Analytics Queue</span>
                <span className="text-primary font-bold">● ONLINE</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-border/40">
                <span className="text-text-secondary">Redis Semantic Cache</span>
                <span className="text-primary font-bold">● ONLINE</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-text-secondary">Postgres Metadata Database</span>
                <span className="text-primary font-bold">● ONLINE</span>
              </div>
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}
export default Diagnostics;
