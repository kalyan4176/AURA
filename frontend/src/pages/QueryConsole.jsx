import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { CorrelationHeatmap, AnomalyScatter, ForecastAreaLine } from '../components/charts/AnalyticsCharts';
import { 
  Bot, Send, DollarSign, Loader2, PlayCircle, BarChart3, AlertCircle, TrendingUp
} from 'lucide-react';

export function QueryConsole({ datasetId }) {
  const queryClient = useQueryClient();
  const [queryString, setQueryString] = useState('');
  
  // Custom manual calculation fields
  const [activeTab, setActiveTab] = useState('chat'); // chat, stats, anomalies, forecast
  const [corrCols, setCorrCols] = useState([]);
  const [statTest, setStatTest] = useState('t_test');
  const [statGroup, setStatGroup] = useState('');
  const [statValue, setStatValue] = useState('');
  const [anomalyCols, setAnomalyCols] = useState([]);
  const [forecastTime, setForecastTime] = useState('');
  const [forecastVal, setForecastVal] = useState('');

  // Task execution polling states
  const [pollingTaskId, setPollingTaskId] = useState(null);
  const [taskStatus, setTaskStatus] = useState(null);
  const [taskResult, setTaskResult] = useState(null);
  const [taskError, setTaskError] = useState(null);

  // Fetch dataset to get column configurations
  const { data: dataset } = useQuery({
    queryKey: ['dataset_profile', datasetId],
    queryFn: () => api.get(`/workspaces/datasets/${datasetId}`),
    enabled: !!datasetId,
  });

  const columns = dataset?.schema_definition?.columns || [];

  // Fetch daily spend limits
  const { data: budget = { daily_spend_usd: 0, daily_limit_usd: 10, remaining_budget_usd: 10 }, refetch: refetchBudget } = useQuery({
    queryKey: ['budget_spend'],
    queryFn: () => api.get('/analytics/budget/spend'),
  });

  // Query Chat mutation (routes directly to AI Budget Manager)
  const chatMutation = useMutation({
    mutationFn: (q) => api.post('/analytics/query', { dataset_id: datasetId, query: q }),
    onSuccess: (data) => {
      refetchBudget();
    }
  });

  const handleChatSubmit = (e) => {
    e.preventDefault();
    if (!queryString.trim()) return;
    chatMutation.mutate(queryString);
  };

  // Poll task execution helper
  const pollTask = async (taskId) => {
    setPollingTaskId(taskId);
    setTaskStatus('PENDING');
    setTaskResult(null);
    setTaskError(null);

    const interval = setInterval(async () => {
      try {
        const response = await api.get(`/analytics/tasks/${taskId}`);
        setTaskStatus(response.state);
        
        if (response.state === 'SUCCESS') {
          setTaskResult(response.result);
          clearInterval(interval);
          setPollingTaskId(null);
          refetchBudget();
        } else if (response.state === 'FAILURE') {
          setTaskError(response.error || 'Calculation execution failed.');
          clearInterval(interval);
          setPollingTaskId(null);
        }
      } catch (err) {
        setTaskError('Error polling task status.');
        clearInterval(interval);
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

  const runStatisticalTest = async () => {
    if (!statGroup || !statValue) return;
    try {
      const response = await api.post('/analytics/statistics-test', {
        dataset_id: datasetId,
        test_type: statTest,
        group_col: statGroup,
        value_col: statValue
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
        algorithm: 'isolation_forest',
        contamination: 0.05
      });
      pollTask(response.task_id);
    } catch (e) {
      setTaskError(e.message);
    }
  };

  const runForecast = async () => {
    if (!forecastTime || !forecastVal) return;
    try {
      const response = await api.post('/analytics/forecast', {
        dataset_id: datasetId,
        time_col: forecastTime,
        value_col: forecastVal,
        steps: 6
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
        
        {/* Daily budget stats */}
        <div className="glass-card p-5 border border-primary/10 bg-primary/2">
          <div className="flex items-center gap-2 text-xs font-bold text-primary uppercase tracking-wider">
            <DollarSign className="w-4 h-4" /> AI Budget Manager
          </div>
          <div className="flex items-baseline gap-1 mt-3">
            <span className="text-2xl font-black text-text-primary">${budget.daily_spend_usd.toFixed(4)}</span>
            <span className="text-xs text-text-secondary">/ ${budget.daily_limit_usd.toFixed(2)} spent</span>
          </div>

          {/* Budget progress bar */}
          <div className="w-full bg-white/10 rounded-full h-1.5 mt-3 overflow-hidden">
            <div 
              className="bg-primary h-1.5 transition-all duration-500" 
              style={{ width: `${(budget.daily_spend_usd / budget.daily_limit_usd) * 100}%` }}
            />
          </div>
        </div>

        {/* Navigation Selector */}
        <div className="glass-card p-4 flex flex-col gap-1">
          <button 
            onClick={() => { setActiveTab('chat'); setTaskResult(null); }}
            className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-semibold flex items-center gap-2.5 transition-all ${activeTab === 'chat' ? 'bg-primary text-black' : 'text-text-secondary hover:bg-white/5'}`}
          >
            <Bot className="w-4 h-4" /> AI Narrative Console
          </button>
          
          <div className="border-t border-border/80 my-2 pt-2 text-[10px] uppercase font-bold text-text-secondary tracking-widest pl-3">Deterministic Engines</div>

          <button 
            onClick={() => { setActiveTab('corr'); setTaskResult(null); }}
            className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-semibold flex items-center gap-2.5 transition-all ${activeTab === 'corr' ? 'bg-primary text-black' : 'text-text-secondary hover:bg-white/5'}`}
          >
            <BarChart3 className="w-4 h-4" /> Correlation Matrix
          </button>
          <button 
            onClick={() => { setActiveTab('stats'); setTaskResult(null); }}
            className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-semibold flex items-center gap-2.5 transition-all ${activeTab === 'stats' ? 'bg-primary text-black' : 'text-text-secondary hover:bg-white/5'}`}
          >
            <PlayCircle className="w-4 h-4" /> Hypothesis Tests
          </button>
          <button 
            onClick={() => { setActiveTab('anomalies'); setTaskResult(null); }}
            className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-semibold flex items-center gap-2.5 transition-all ${activeTab === 'anomalies' ? 'bg-primary text-black' : 'text-text-secondary hover:bg-white/5'}`}
          >
            <AlertCircle className="w-4 h-4" /> Anomaly Detection
          </button>
          <button 
            onClick={() => { setActiveTab('forecast'); setTaskResult(null); }}
            className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-semibold flex items-center gap-2.5 transition-all ${activeTab === 'forecast' ? 'bg-primary text-black' : 'text-text-secondary hover:bg-white/5'}`}
          >
            <TrendingUp className="w-4 h-4" /> Time-Series Forecast
          </button>
        </div>

      </div>

      {/* Main calculation workspace */}
      <div className="lg:col-span-3 flex flex-col gap-6">
        
        {/* Input parameters card */}
        <div className="glass-card p-6 flex flex-col gap-4">
          <h2 className="text-base font-bold text-text-primary border-b border-border pb-2 capitalize">
            {activeTab} Console
          </h2>

          {activeTab === 'chat' && (
            <form onSubmit={handleChatSubmit} className="flex gap-2">
              <input 
                type="text"
                value={queryString}
                onChange={(e) => setQueryString(e.target.value)}
                placeholder="Ask AURA to query stats, calculate averages, explain trends..."
                className="flex-1 bg-black/40 border border-border rounded-xl px-4 py-3 text-sm text-text-primary focus:outline-none focus:border-primary placeholder-text-secondary/60"
              />
              <button 
                type="submit"
                disabled={chatMutation.isPending}
                className="px-5 bg-primary hover:bg-primary-hover disabled:bg-primary/20 text-black font-bold rounded-xl flex items-center justify-center transition-all"
              >
                {chatMutation.isPending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-4 h-4" />}
              </button>
            </form>
          )}

          {activeTab === 'corr' && (
            <div className="flex flex-col gap-4">
              <p className="text-xs text-text-secondary opacity-80">Select numeric columns to compute correlations:</p>
              <div className="flex flex-wrap gap-4 bg-black/20 p-4 rounded-xl border border-border">
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
                className="w-fit px-5 py-2.5 bg-primary hover:bg-primary-hover disabled:bg-primary/20 text-black font-bold rounded-xl transition-all"
              >
                Trigger Correlation Matrix
              </button>
            </div>
          )}

          {activeTab === 'stats' && (
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs text-text-secondary">Hypothesis Test Type</label>
                  <select 
                    value={statTest} 
                    onChange={(e) => setStatTest(e.target.value)}
                    className="bg-black/40 border border-border rounded px-3 py-2 text-xs text-text-primary focus:outline-none"
                  >
                    <option value="t_test">Welch's 2-Sample T-Test</option>
                    <option value="anova">One-way ANOVA (F-Test)</option>
                    <option value="mann_whitney">Mann-Whitney U Test</option>
                  </select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs text-text-secondary">Group Column (Categorical)</label>
                  <select 
                    value={statGroup} 
                    onChange={(e) => setStatGroup(e.target.value)}
                    className="bg-black/40 border border-border rounded px-3 py-2 text-xs text-text-primary focus:outline-none"
                  >
                    <option value="">-- Choose column --</option>
                    {columns.filter(c => ['string', 'boolean'].includes(c.data_type)).map(c => (
                      <option key={c.name} value={c.name}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs text-text-secondary">Value Column (Numeric)</label>
                  <select 
                    value={statValue} 
                    onChange={(e) => setStatValue(e.target.value)}
                    className="bg-black/40 border border-border rounded px-3 py-2 text-xs text-text-primary focus:outline-none"
                  >
                    <option value="">-- Choose column --</option>
                    {columns.filter(c => ['integer', 'float'].includes(c.data_type)).map(c => (
                      <option key={c.name} value={c.name}>{c.name}</option>
                    ))}
                  </select>
                </div>
              </div>
              <button 
                onClick={runStatisticalTest}
                disabled={!statGroup || !statValue || !!pollingTaskId}
                className="w-fit px-5 py-2.5 bg-primary hover:bg-primary-hover disabled:bg-primary/20 text-black font-bold rounded-xl transition-all"
              >
                Execute Hypothesis Test
              </button>
            </div>
          )}

          {activeTab === 'anomalies' && (
            <div className="flex flex-col gap-4">
              <p className="text-xs text-text-secondary opacity-80">Select numeric columns to scan for anomalies:</p>
              <div className="flex flex-wrap gap-4 bg-black/20 p-4 rounded-xl border border-border">
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
              <button 
                onClick={runAnomaly}
                disabled={anomalyCols.length === 0 || !!pollingTaskId}
                className="w-fit px-5 py-2.5 bg-primary hover:bg-primary-hover disabled:bg-primary/20 text-black font-bold rounded-xl transition-all"
              >
                Scan Outliers (Isolation Forest)
              </button>
            </div>
          )}

          {activeTab === 'forecast' && (
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs text-text-secondary">Time / Horizon Column</label>
                  <select 
                    value={forecastTime} 
                    onChange={(e) => setForecastTime(e.target.value)}
                    className="bg-black/40 border border-border rounded px-3 py-2 text-xs text-text-primary focus:outline-none"
                  >
                    <option value="">-- Choose column --</option>
                    {columns.map(c => (
                      <option key={c.name} value={c.name}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs text-text-secondary">Value Column (Numeric)</label>
                  <select 
                    value={forecastVal} 
                    onChange={(e) => setForecastVal(e.target.value)}
                    className="bg-black/40 border border-border rounded px-3 py-2 text-xs text-text-primary focus:outline-none"
                  >
                    <option value="">-- Choose column --</option>
                    {columns.filter(c => ['integer', 'float'].includes(c.data_type)).map(c => (
                      <option key={c.name} value={c.name}>{c.name}</option>
                    ))}
                  </select>
                </div>
              </div>
              <button 
                onClick={runForecast}
                disabled={!forecastTime || !forecastVal || !!pollingTaskId}
                className="w-fit px-5 py-2.5 bg-primary hover:bg-primary-hover disabled:bg-primary/20 text-black font-bold rounded-xl transition-all"
              >
                Calculate Time-Series Forecasts
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

        {/* Results output section */}
        {chatMutation.data && activeTab === 'chat' && (
          <div className="glass-card p-6 flex flex-col gap-4">
            <div className="flex items-center gap-2 border-b border-border pb-2 text-xs text-text-secondary uppercase tracking-widest font-bold">
              <Bot className="w-4 h-4 text-primary" /> AURA Decision Narrative
            </div>
            
            <div className="p-4 bg-white/5 rounded-xl border border-border text-sm leading-relaxed text-text-primary">
              {chatMutation.data.response || chatMutation.data.explanation}
            </div>

            {chatMutation.data.source === 'deterministic_sql' && chatMutation.data.data?.query_executed && (
              <div className="text-xs font-mono text-text-secondary bg-black/40 p-3 rounded-lg border border-border">
                <b>Execution SQL Query:</b> {chatMutation.data.data.query_executed}
              </div>
            )}
          </div>
        )}

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

            {activeTab === 'stats' && (
              <div className="flex flex-col gap-4">
                <div className="p-4 bg-white/5 border border-border rounded-xl">
                  <h4 className="text-sm font-bold text-text-primary">{taskResult.test_name}</h4>
                  <div className="grid grid-cols-2 gap-4 mt-3 text-xs text-text-secondary">
                    <div>Statistic: <b className="text-text-primary">{taskResult.statistic.toFixed(4)}</b></div>
                    <div>P-Value: <b className="text-text-primary">{taskResult.p_value.toFixed(5)}</b></div>
                  </div>
                  <div className="mt-3 text-xs font-semibold text-primary">
                    Significant: {taskResult.is_significant ? 'Yes (Confidence Interval >95%)' : 'No'}
                  </div>
                </div>
                <div className="text-sm p-4 bg-white/5 border border-border rounded-xl">
                  {taskResult.business_explanation}
                </div>
              </div>
            )}

            {activeTab === 'anomalies' && (
              <div className="flex flex-col gap-4">
                <div className="p-4 bg-white/5 border border-border rounded-xl">
                  <h4 className="text-sm font-bold text-text-primary">Anomaly Summary</h4>
                  <p className="text-xs text-text-secondary mt-1">{taskResult.summary}</p>
                </div>
                {/* Visual scatter (mocking original rows preview to chart points) */}
                <AnomalyScatter 
                  rows={dataset?.quality_report?.total_rows ? Array.from({length: dataset.quality_report.total_rows}, (_, i) => ({
                    [anomalyCols[0]]: Math.random() * 100, // mock fallback
                    [anomalyCols[1] || anomalyCols[0]]: Math.random() * 100
                  })) : []} 
                  columns={anomalyCols} 
                  anomalyIndices={taskResult.anomaly_indices} 
                />
              </div>
            )}

            {activeTab === 'forecast' && (
              <div className="flex flex-col gap-4">
                <div className="p-4 bg-white/5 border border-border rounded-xl">
                  <h4 className="text-sm font-bold text-text-primary">Projections Model</h4>
                  <p className="text-xs text-text-secondary mt-1">{taskResult.model_details}</p>
                </div>
                <ForecastAreaLine 
                  timeline={taskResult.timeline} 
                  historicalValues={taskResult.historical_values} 
                  forecastTimeline={taskResult.forecast_timeline} 
                  forecastValues={taskResult.forecast_values} 
                  lowerBounds={taskResult.lower_confidence_bounds} 
                  upperBounds={taskResult.upper_confidence_bounds} 
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
