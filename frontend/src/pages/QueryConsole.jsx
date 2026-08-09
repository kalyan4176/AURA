import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { CorrelationHeatmap, AnomalyScatter, DynamicAIChart } from '../components/charts/AnalyticsCharts';
import { 
  Bot, Send, Loader2, BarChart3, AlertCircle, ShieldCheck, Download, Copy, Trash2, Sparkles, User
} from 'lucide-react';

function parseInline(str) {
  if (!str) return '';
  const parts = str.split('**');
  return parts.map((part, i) => {
    if (i % 2 === 1) {
      return <strong key={i} className="font-bold text-text-primary">{part}</strong>;
    }
    return part;
  });
}

function renderMarkdown(text) {
  if (!text) return null;
  const lines = text.split('\n');
  return lines.map((line, idx) => {
    let trimmed = line.trim();
    if (!trimmed) return <div key={idx} className="h-2" />;
    
    if (trimmed.startsWith('### ')) {
      return <h3 key={idx} className="text-sm font-bold text-primary mt-3 mb-1">{parseInline(trimmed.substring(4))}</h3>;
    }
    if (trimmed.startsWith('#### ')) {
      return <h4 key={idx} className="text-xs font-bold text-text-primary mt-2 mb-1">{parseInline(trimmed.substring(5))}</h4>;
    }
    
    if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
      return (
        <li key={idx} className="list-disc ml-5 text-xs text-text-secondary mt-0.5">
          {parseInline(trimmed.substring(2))}
        </li>
      );
    }
    
    return <p key={idx} className="text-xs text-text-secondary leading-relaxed mt-1">{parseInline(trimmed)}</p>;
  });
}

export function QueryConsole({ datasetId }) {
  const queryClient = useQueryClient();
  const [queryString, setQueryString] = useState('');
  
  // Tab selector: chat, corr, anomalies
  const [activeTab, setActiveTab] = useState('chat');
  const [corrCols, setCorrCols] = useState([]);
  const [anomalyCols, setAnomalyCols] = useState([]);
  const [anomalyAlg, setAnomalyAlg] = useState('isolation_forest');

  // Task execution polling states
  const [pollingTaskId, setPollingTaskId] = useState(null);
  const [taskStatus, setTaskStatus] = useState(null);
  const [taskResult, setTaskResult] = useState(null);
  const [taskError, setTaskError] = useState(null);

  const chatBottomRef = useRef(null);

  // Fetch dataset details & column definitions
  const { data: dataset } = useQuery({
    queryKey: ['dataset_profile', datasetId],
    queryFn: () => api.get(`/workspaces/datasets/${datasetId}`),
    enabled: !!datasetId,
  });

  // Fetch dataset rows preview for accurate anomaly plotting
  const { data: previewData = { rows: [] } } = useQuery({
    queryKey: ['dataset_preview', datasetId],
    queryFn: () => api.get(`/workspaces/datasets/${datasetId}/preview`),
    enabled: !!datasetId,
  });

  // Fetch persistent multi-turn chat message history
  const { data: chatHistory = [], isLoading: isChatLoading } = useQuery({
    queryKey: ['chat_history', datasetId],
    queryFn: () => api.get(`/analytics/chat/${datasetId}`),
    enabled: !!datasetId,
  });

  const columns = dataset?.schema_definition?.columns || [];

  // Query Chat mutation
  const chatMutation = useMutation({
    mutationFn: (q) => api.post('/analytics/query', { dataset_id: datasetId, query: q }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat_history', datasetId] });
      setQueryString('');
    }
  });

  // Clear chat history mutation
  const clearChatMutation = useMutation({
    mutationFn: () => api.delete(`/analytics/chat/${datasetId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat_history', datasetId] });
    }
  });

  const handleChatSubmit = (e) => {
    e.preventDefault();
    if (!queryString.trim() || chatMutation.isPending) return;
    chatMutation.mutate(queryString);
  };

  const handleDownloadResponse = (content, title = 'AURA_Analysis_Report') => {
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `${title}_${Date.now()}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const pollingIntervalRef = useRef(null);

  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (activeTab === 'chat' && chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatHistory, chatMutation.isPending, activeTab]);

  // Poll task execution helper
  const pollTask = async (taskId) => {
    setPollingTaskId(taskId);
    setTaskStatus('PENDING');
    setTaskResult(null);
    setTaskError(null);

    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    pollingIntervalRef.current = setInterval(async () => {
      try {
        const response = await api.get(`/analytics/tasks/${taskId}`);
        setTaskStatus(response.state);
        
        if (response.state === 'SUCCESS') {
          setTaskResult(response.result);
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
          setPollingTaskId(null);
        } else if (response.state === 'FAILURE') {
          setTaskError(response.error || 'Calculation execution failed.');
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
          setPollingTaskId(null);
        }
      } catch (err) {
        setTaskError('Error polling task status.');
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
        setPollingTaskId(null);
      }
    }, 1500);
  };

  // Trigger Celery Task mutations
  const runCorrelation = async () => {
    if (corrCols.length < 2) return;
    try {
      const response = await api.post('/analytics/correlations', {
        dataset_id: datasetId,
        columns: corrCols,
        method: 'pearson'
      });
      pollTask(response.task_id);
    } catch (e) {
      setTaskError(e.message);
    }
  };

  const runAnomaly = async () => {
    if (anomalyCols.length === 0) return;
    try {
      const response = await api.post('/analytics/anomalies', {
        dataset_id: datasetId,
        columns: anomalyCols,
        algorithm: anomalyAlg,
        contamination: 0.05
      });
      pollTask(response.task_id);
    } catch (e) {
      setTaskError(e.message);
    }
  };

  const handleCheckboxChange = (colName, type = 'corr') => {
    const list = type === 'corr' ? corrCols : anomalyCols;
    const setter = type === 'corr' ? setCorrCols : setAnomalyCols;

    if (list.includes(colName)) {
      setter(list.filter(c => c !== colName));
    } else {
      setter([...list, colName]);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 p-6 max-w-7xl mx-auto">
      
      {/* Sidebar Controls */}
      <div className="lg:col-span-1 flex flex-col gap-6">
        
        {/* Navigation Selector */}
        <div className="glass-card p-4 flex flex-col gap-1">
          <button 
            onClick={() => { setActiveTab('chat'); setTaskResult(null); }}
            className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-semibold flex items-center gap-2.5 transition-all ${activeTab === 'chat' ? 'bg-primary text-white' : 'text-text-secondary hover:bg-white/5'}`}
          >
            <Bot className="w-4 h-4" /> AI Narrative Console
          </button>
          
          <div className="border-t border-border/80 my-2 pt-2 text-[10px] uppercase font-bold text-text-secondary tracking-widest pl-3">Deterministic Engines</div>

          <button 
            onClick={() => { setActiveTab('corr'); setTaskResult(null); }}
            className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-semibold flex items-center gap-2.5 transition-all ${activeTab === 'corr' ? 'bg-primary text-white' : 'text-text-secondary hover:bg-white/5'}`}
          >
            <BarChart3 className="w-4 h-4" /> Correlation Matrix
          </button>
          <button 
            onClick={() => { setActiveTab('anomalies'); setTaskResult(null); }}
            className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-semibold flex items-center gap-2.5 transition-all ${activeTab === 'anomalies' ? 'bg-primary text-white' : 'text-text-secondary hover:bg-white/5'}`}
          >
            <AlertCircle className="w-4 h-4" /> Anomaly Detection
          </button>
        </div>

        {/* Privacy Shield Info Badge */}
        <div className="glass-card p-4 flex flex-col gap-2 border border-emerald-500/30 bg-emerald-500/5">
          <div className="flex items-center gap-2 text-emerald-600 font-bold text-xs">
            <ShieldCheck className="w-4 h-4" /> Privacy Shield Active
          </div>
          <p className="text-[11px] text-text-secondary leading-relaxed">
            Raw Parquet dataset rows are stored strictly in your local workspace and are <b>never used to train AI foundation models</b>. Only aggregated metadata or code outputs are ephemerally processed.
          </p>
        </div>

      </div>

      {/* Main calculation workspace */}
      <div className="lg:col-span-3 flex flex-col gap-6">
        
        {/* Main Console Workspace */}
        <div className="glass-card p-6 flex flex-col gap-4">
          
          <div className="flex items-center justify-between border-b border-border pb-3">
            <h2 className="text-base font-bold text-text-primary capitalize flex items-center gap-2">
              {activeTab === 'corr' ? 'Correlation Matrix' : activeTab === 'anomalies' ? 'Anomaly Detection' : 'AI Narrative Console'}
            </h2>

            {activeTab === 'chat' && chatHistory.length > 0 && (
              <button 
                onClick={() => clearChatMutation.mutate()}
                disabled={clearChatMutation.isPending}
                className="text-xs text-red-500 hover:text-red-600 flex items-center gap-1.5 px-2.5 py-1 rounded bg-red-500/10 hover:bg-red-500/20 transition-all font-semibold"
              >
                <Trash2 className="w-3.5 h-3.5" /> Clear Session
              </button>
            )}
          </div>

          {/* AI Narrative Console Interactive Chat Thread */}
          {activeTab === 'chat' && (
            <div className="flex flex-col gap-6">
              
              {/* Chat Thread Container */}
              <div className="flex flex-col gap-4 max-h-[550px] overflow-y-auto pr-2 pt-2">
                {chatHistory.length === 0 && !isChatLoading && (
                  <div className="p-8 text-center flex flex-col items-center justify-center gap-3 border border-dashed border-border rounded-xl bg-white/5">
                    <Sparkles className="w-8 h-8 text-primary/60 animate-pulse" />
                    <h3 className="text-sm font-bold text-text-primary">Start an Interactive Analysis Session</h3>
                    <p className="text-xs text-text-secondary max-w-md">
                      Ask AURA to calculate metrics, explain column behaviors, or request charts like <i>"give me a chart on Amount vs Time"</i>.
                    </p>
                  </div>
                )}

                {chatHistory.map((msg) => (
                  <div key={msg.id} className={`flex flex-col gap-2 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                    
                    {/* Role Header */}
                    <div className="flex items-center gap-1.5 text-[11px] font-bold text-text-secondary uppercase tracking-wider px-1">
                      {msg.role === 'user' ? (
                        <>User <User className="w-3.5 h-3.5 text-secondary" /></>
                      ) : (
                        <><Bot className="w-3.5 h-3.5 text-primary" /> AURA Intelligence</>
                      )}
                    </div>

                    {/* Message Content Bubble */}
                    <div className={`p-4 rounded-2xl max-w-2xl border text-xs leading-relaxed flex flex-col gap-3 ${
                      msg.role === 'user' 
                        ? 'bg-primary text-white border-primary/30 rounded-tr-none' 
                        : 'bg-white/10 text-text-primary border-border rounded-tl-none shadow-sm'
                    }`}>
                      
                      {/* Markdown Narrative */}
                      <div>{msg.role === 'user' ? msg.content : renderMarkdown(msg.content)}</div>

                      {/* SQL Code Block */}
                      {msg.query_executed && (
                        <div className="text-[11px] font-mono text-text-secondary bg-black/40 p-2.5 rounded-lg border border-border mt-1">
                          <b className="text-primary">Executed SQL:</b> {msg.query_executed}
                        </div>
                      )}

                      {/* Interactive AI EChart Component */}
                      {msg.chart_spec && (
                        <div className="bg-white p-3 rounded-xl border border-border mt-2 shadow-inner">
                          <DynamicAIChart spec={msg.chart_spec} />
                        </div>
                      )}

                      {/* Assistant Actions Bar */}
                      {msg.role === 'assistant' && (
                        <div className="flex items-center justify-end gap-2 border-t border-border/40 pt-2.5 mt-1 text-[11px]">
                          <button
                            onClick={() => handleDownloadResponse(msg.content)}
                            className="flex items-center gap-1 text-primary font-bold hover:underline"
                          >
                            <Download className="w-3.5 h-3.5" /> Export Response (.md)
                          </button>
                        </div>
                      )}

                    </div>
                  </div>
                ))}

                {chatMutation.isPending && (
                  <div className="flex items-start gap-2">
                    <Bot className="w-4 h-4 text-primary animate-bounce" />
                    <div className="p-4 rounded-2xl bg-white/10 text-text-secondary border border-border text-xs flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin text-primary" /> AURA is generating narrative insights & executing SQL queries...
                    </div>
                  </div>
                )}

                <div ref={chatBottomRef} />
              </div>

              {/* AI Recommended Chart Chips */}
              <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border/40">
                <span className="text-[11px] font-bold text-text-secondary flex items-center gap-1">
                  <Sparkles className="w-3.5 h-3.5 text-primary" /> Suggested Visualizations:
                </span>
                <button
                  type="button"
                  onClick={() => { setQueryString('bar chart of average Amount by Class'); }}
                  className="px-2.5 py-1 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 rounded-full text-[11px] font-semibold transition-all"
                >
                  📊 Bar: Average Amount by Class
                </button>
                <button
                  type="button"
                  onClick={() => { setQueryString('chart on Amount vs Time'); }}
                  className="px-2.5 py-1 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 rounded-full text-[11px] font-semibold transition-all"
                >
                  📈 Scatter: Amount vs Time
                </button>
                <button
                  type="button"
                  onClick={() => { setQueryString('distribution of Amount'); }}
                  className="px-2.5 py-1 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 rounded-full text-[11px] font-semibold transition-all"
                >
                  📊 Distribution: Amount
                </button>
              </div>

              {/* Chat Input Form */}
              <form onSubmit={handleChatSubmit} className="flex gap-2">
                <input 
                  type="text"
                  value={queryString}
                  onChange={(e) => setQueryString(e.target.value)}
                  placeholder="Ask AURA to query stats, generate a chart (e.g. Amount vs Time), or explain findings..."
                  className="flex-1 bg-white border border-border rounded-xl px-4 py-3 text-xs text-text-primary focus:outline-none focus:border-primary placeholder-text-secondary/60"
                />
                <button 
                  type="submit"
                  disabled={chatMutation.isPending}
                  className="p-3 bg-primary hover:bg-primary-hover disabled:bg-primary/20 text-white rounded-xl transition-all flex items-center justify-center font-bold"
                >
                  {chatMutation.isPending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                </button>
              </form>

            </div>
          )}

          {activeTab === 'corr' && (
            <div className="flex flex-col gap-4">
              <p className="text-xs text-text-secondary opacity-80">Select numeric columns to compute Pearson coefficients:</p>
              <div className="flex flex-wrap gap-4 bg-white/20 p-4 rounded-xl border border-border">
                {columns.filter(c => ['integer', 'float'].includes(c.data_type)).map(c => (
                  <label key={c.name} className="flex items-center gap-2 text-xs text-text-primary cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={corrCols.includes(c.name)}
                      onChange={() => handleCheckboxChange(c.name, 'corr')}
                      className="accent-primary"
                    />
                    {c.name}
                  </label>
                ))}
              </div>
              <button 
                onClick={runCorrelation}
                disabled={corrCols.length < 2 || !!pollingTaskId}
                className="w-fit px-5 py-2.5 bg-primary hover:bg-primary-hover disabled:bg-primary/20 text-white font-bold rounded-xl transition-all text-xs"
              >
                Trigger Correlation Matrix
              </button>
            </div>
          )}

          {activeTab === 'anomalies' && (
            <div className="flex flex-col gap-4">
              <p className="text-xs text-text-secondary opacity-80">Select numeric columns to scan for anomalies:</p>
              <div className="flex flex-wrap gap-4 bg-white/20 p-4 rounded-xl border border-border">
                {columns.filter(c => ['integer', 'float'].includes(c.data_type)).map(c => (
                  <label key={c.name} className="flex items-center gap-2 text-xs text-text-primary cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={anomalyCols.includes(c.name)}
                      onChange={() => handleCheckboxChange(c.name, 'anomaly')}
                      className="accent-primary"
                    />
                    {c.name}
                  </label>
                ))}
              </div>
              <div className="flex flex-col gap-1.5 w-fit">
                <label className="text-xs text-text-secondary font-semibold">Anomaly Detection Algorithm</label>
                <select
                  value={anomalyAlg}
                  onChange={(e) => setAnomalyAlg(e.target.value)}
                  className="bg-white border border-border rounded px-3 py-2 text-xs text-text-primary focus:outline-none"
                >
                  <option value="isolation_forest">Isolation Forest (Spatial Trees)</option>
                  <option value="lof">Local Outlier Factor (Density-based)</option>
                  <option value="one_class_svm">One-Class SVM (Hyperplane fitting)</option>
                </select>
              </div>
              <button 
                onClick={runAnomaly}
                disabled={anomalyCols.length === 0 || !!pollingTaskId}
                className="w-fit px-5 py-2.5 bg-primary hover:bg-primary-hover disabled:bg-primary/20 text-white font-bold rounded-xl transition-all text-xs"
              >
                Scan Outliers (ML Model)
              </button>
            </div>
          )}

        </div>

        {/* Query execution status loader */}
        {pollingTaskId && (
          <div className="glass-card p-6 flex items-center justify-between border border-secondary/10 bg-secondary/2 text-sm text-secondary">
            <span className="flex items-center gap-2">
              <Loader2 className="w-5 h-5 animate-spin" /> Task calculations are currently in progress... (State: <b>{taskStatus}</b>)
            </span>
          </div>
        )}

        {taskError && (
          <div className="glass-card p-6 border border-red-500/20 bg-red-500/10 text-sm text-red-400">
            Error: {taskError}
          </div>
        )}

        {/* Results output section for Deterministic Engines */}
        {taskResult && (
          <div className="glass-card p-6 flex flex-col gap-4">
            <div className="border-b border-border pb-2 text-xs text-text-secondary uppercase tracking-widest font-bold">
              Execution Result Analysis
            </div>

            {activeTab === 'corr' && (
              <div className="flex flex-col gap-4">
                <CorrelationHeatmap columns={taskResult.columns} matrix={taskResult.matrix} />
              </div>
            )}

            {activeTab === 'anomalies' && (
              <div className="flex flex-col gap-4">
                <div className="p-4 bg-white/5 border border-border rounded-xl">
                  <h4 className="text-sm font-bold text-text-primary">Anomaly Summary</h4>
                  <div className="text-xs text-text-secondary mt-1 whitespace-pre-wrap">{taskResult.summary}</div>
                </div>
                <AnomalyScatter 
                  rows={previewData?.rows || []} 
                  columns={anomalyCols} 
                  anomalyIndices={taskResult.anomaly_indices} 
                  plotData={taskResult.plot_data}
                />
              </div>
            )}

          </div>
        )}

      </div>

    </div>
  );
}
export default QueryConsole;
