import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { DataGrid } from '../components/table/DataGrid';
import { Activity, ShieldAlert, Database, Info, RefreshCw, Loader2 } from 'lucide-react';

export function Dashboard({ datasetId, onBack }) {
  // Fetch dataset metadata & profile
  const { data: dataset, isLoading: loadingMetadata, refetch: refetchMetadata } = useQuery({
    queryKey: ['dataset_profile', datasetId],
    queryFn: () => api.get(`/workspaces/datasets/${datasetId}`),
    enabled: !!datasetId,
  });

  // Fetch dataset rows preview
  const { data: previewData, isLoading: loadingPreview } = useQuery({
    queryKey: ['dataset_preview', datasetId],
    queryFn: () => api.get(`/workspaces/datasets/${datasetId}/preview`),
    enabled: !!datasetId,
  });

  const loading = loadingMetadata || loadingPreview;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] gap-3">
        <Loader2 className="w-10 h-10 animate-spin text-primary" />
        <p className="text-text-secondary text-sm">Loading dataset statistics and profiling schemas...</p>
      </div>
    );
  }

  if (!dataset) return null;

  const qualityReport = dataset.quality_report || { health_score: 100, issues: [], duplicate_rows_count: 0 };
  const schema = dataset.schema_definition || { columns: [], row_count: 0, column_count: 0 };

  // Color mappings for Health Score
  const getHealthColor = (score) => {
    if (score >= 80) return { text: 'text-primary', border: 'border-primary/20', bg: 'bg-primary/5', glow: 'shadow-primary/10' };
    if (score >= 50) return { text: 'text-accent', border: 'border-accent/20', bg: 'bg-accent/5', glow: 'shadow-accent/10' };
    return { text: 'text-red-400', border: 'border-red-500/20', bg: 'bg-red-500/5', glow: 'shadow-red-500/10' };
  };

  const healthStyle = getHealthColor(qualityReport.health_score);

  return (
    <div className="p-6 flex flex-col gap-6 max-w-7xl mx-auto">
      
      {/* Header section */}
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div>
          <button onClick={onBack} className="text-xs text-primary hover:underline mb-1">← Back to Workspace</button>
          <h1 className="text-2xl font-bold text-text-primary flex items-center gap-3">
            <Database className="text-secondary w-6 h-6" /> {dataset.name} Profile Dashboard
          </h1>
          <p className="text-xs text-text-secondary opacity-60 mt-0.5">Ingested: {dataset.filename} ({dataset.file_format.toUpperCase()})</p>
        </div>
        <button 
          onClick={() => refetchMetadata()}
          className="px-3.5 py-1.5 border border-border rounded-lg bg-white/5 text-xs hover:bg-white/10 transition-all flex items-center gap-1.5"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Re-Profile
        </button>
      </div>

      {/* Overview Metric Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        
        {/* Health score metric */}
        <div className={`glass-card p-6 flex items-center justify-between border ${healthStyle.border} ${healthStyle.bg} shadow-lg ${healthStyle.glow}`}>
          <div>
            <div className="text-xs text-text-secondary opacity-80 uppercase tracking-wider font-semibold">Data Quality Score</div>
            <div className={`text-4xl font-extrabold mt-2 ${healthStyle.text}`}>{qualityReport.health_score}%</div>
          </div>
          <Activity className={`w-12 h-12 opacity-35 ${healthStyle.text}`} />
        </div>

        {/* Total rows */}
        <div className="glass-card p-6 flex items-center justify-between">
          <div>
            <div className="text-xs text-text-secondary opacity-80 uppercase tracking-wider font-semibold">Row Count</div>
            <div className="text-3xl font-bold mt-2 text-text-primary">{schema.row_count.toLocaleString()}</div>
          </div>
          <Database className="w-10 h-10 text-secondary opacity-30" />
        </div>

        {/* Columns count */}
        <div className="glass-card p-6 flex items-center justify-between">
          <div>
            <div className="text-xs text-text-secondary opacity-80 uppercase tracking-wider font-semibold">Column Count</div>
            <div className="text-3xl font-bold mt-2 text-text-primary">{schema.column_count}</div>
          </div>
          <Info className="w-10 h-10 text-text-secondary opacity-30" />
        </div>

        {/* Duplicate records */}
        <div className="glass-card p-6 flex items-center justify-between">
          <div>
            <div className="text-xs text-text-secondary opacity-80 uppercase tracking-wider font-semibold">Duplicate Rows</div>
            <div className={`text-3xl font-bold mt-2 ${qualityReport.duplicate_rows_count > 0 ? 'text-accent' : 'text-text-primary'}`}>
              {qualityReport.duplicate_rows_count}
            </div>
          </div>
          <ShieldAlert className={`w-10 h-10 opacity-30 ${qualityReport.duplicate_rows_count > 0 ? 'text-accent' : 'text-text-secondary'}`} />
        </div>

      </div>

      {/* Main dashboard splits */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Columns Schema Grid */}
        <div className="lg:col-span-2 glass-card p-6 flex flex-col gap-4">
          <h3 className="text-base font-bold text-text-primary border-b border-border pb-2 flex items-center gap-2">
            Column Profiles & Inferred Schema
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="text-text-secondary border-b border-border/80 opacity-80">
                  <th className="py-2.5">Name</th>
                  <th className="py-2.5">Type</th>
                  <th className="py-2.5">Null %</th>
                  <th className="py-2.5">Distinct</th>
                  <th className="py-2.5 text-right">Range (Min - Max)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {schema.columns.map((col) => (
                  <tr key={col.name} className="hover:bg-white/2">
                    <td className="py-3 font-semibold text-text-primary">{col.name}</td>
                    <td className="py-3">
                      <span className="bg-secondary/15 text-secondary px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider">
                        {col.data_type}
                      </span>
                    </td>
                    <td className={`py-3 ${col.null_percentage > 10 ? 'text-accent font-semibold' : ''}`}>
                      {col.null_percentage.toFixed(1)}%
                    </td>
                    <td className="py-3">{col.distinct_count}</td>
                    <td className="py-3 text-right opacity-80 font-mono">
                      {col.min_value !== null ? `${col.min_value} to ${col.max_value}` : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Quality Issues Log */}
        <div className="lg:col-span-1 glass-card p-6 flex flex-col gap-4">
          <h3 className="text-base font-bold text-text-primary border-b border-border pb-2 flex items-center gap-2">
            Quality Alerts & Logs
          </h3>
          <div className="flex flex-col gap-3 overflow-y-auto max-h-[45vh] pr-1">
            {qualityReport.issues.map((issue, idx) => (
              <div 
                key={idx} 
                className={`p-3.5 rounded-lg border text-xs flex flex-col gap-2 ${
                  issue.severity === 'high' 
                    ? 'bg-red-500/10 border-red-500/20 text-red-300' 
                    : 'bg-accent/10 border-accent/20 text-amber-300'
                }`}
              >
                <div className="flex items-center justify-between font-semibold uppercase tracking-wider text-[10px]">
                  <span>{issue.issue_type}</span>
                  <span className={`px-1.5 py-0.5 rounded font-bold ${issue.severity === 'high' ? 'bg-red-500/20' : 'bg-accent/20'}`}>
                    {issue.severity}
                  </span>
                </div>
                <p className="opacity-90">{issue.description}</p>
                <div className="border-t border-white/5 pt-2 opacity-70 italic">
                  <b>Advice:</b> {issue.recommendation}
                </div>
              </div>
            ))}
            {qualityReport.issues.length === 0 && (
              <div className="text-center text-text-secondary py-16 opacity-60 text-xs flex flex-col items-center justify-center gap-2">
                <span className="text-primary font-bold text-lg">✓ Healthy</span>
                No missing elements, extreme gaps, or duplicates found.
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Tabular virtual preview grid */}
      <div className="glass-card p-6 flex flex-col gap-4">
        <div>
          <h3 className="text-base font-bold text-text-primary">Data Preview (AG Grid)</h3>
          <p className="text-xs text-text-secondary opacity-60 mt-0.5">Top 100 rows rendered dynamically using DuckDB.</p>
        </div>
        {previewData && (
          <DataGrid 
            columns={previewData.columns} 
            rows={previewData.rows} 
            height="320px" 
          />
        )}
      </div>

    </div>
  );
}
export default Dashboard;
