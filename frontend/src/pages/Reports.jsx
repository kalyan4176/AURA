import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { 
  FileText, Plus, Download, MessageSquare, Sparkles, Send, Loader2, Calendar, FileType 
} from 'lucide-react';

export function Reports({ workspaceId }) {
  const queryClient = useQueryClient();
  const [selectedReportId, setSelectedReportId] = useState(null);
  
  // Create report inputs
  const [showCreate, setShowCreate] = useState(false);
  const [reportName, setReportName] = useState('');
  
  // Collaborative inputs
  const [newComment, setNewComment] = useState('');
  const [cardAnnotationText, setCardAnnotationText] = useState({});
  const [showAnnotationInput, setShowAnnotationInput] = useState({});
  const [aiSummary, setAiSummary] = useState(null);
  const [loadingSummary, setLoadingSummary] = useState(false);

  // Fetch reports in workspace
  const { data: reports = [], isLoading: loadingReports } = useQuery({
    queryKey: ['reports', workspaceId],
    queryFn: () => api.get(`/reports/workspace/${workspaceId}`),
    enabled: !!workspaceId,
  });

  // Fetch detailed report model
  const { data: report, isLoading: loadingReportDetails } = useQuery({
    queryKey: ['report_details', selectedReportId],
    queryFn: () => api.get(`/reports/${selectedReportId}`),
    enabled: !!selectedReportId,
  });

  // Create report mutation
  const createReportMutation = useMutation({
    mutationFn: (name) => {
      // Create a default report layout template with 2 default components (text & chart placeholder)
      const defaultComps = [
        {
          id: 'comp_text_1',
          type: 'text',
          title: 'Executive Objective Brief',
          config: { content: 'This workspace report gathers quality profiles, correlations, and predictive analytics inputs to formulate organizational decision evidence.' },
          annotations: []
        },
        {
          id: 'comp_chart_1',
          type: 'chart',
          title: 'Primary Correlation Matrix',
          config: { chart_type: 'Correlation Heatmap' },
          annotations: ['Observation: Strong correlations found among key financial elements.']
        }
      ];
      const defaultLayout = [
        { i: 'comp_text_1', x: 0, y: 0, w: 12, h: 2 },
        { i: 'comp_chart_1', x: 0, y: 2, w: 12, h: 4 }
      ];
      return api.post('/reports', {
        workspace_id: workspaceId,
        name: name,
        components: defaultComps,
        layout: defaultLayout
      });
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['reports', workspaceId] });
      setSelectedReportId(data.id);
      setShowCreate(false);
      setReportName('');
    }
  });

  // Add annotation mutation
  const addAnnotationMutation = useMutation({
    mutationFn: ({ rId, compId, text }) => api.post(`/reports/${rId}/annotations`, {
      component_id: compId,
      text: text
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['report_details', selectedReportId] });
    }
  });

  // Add comment mutation
  const addCommentMutation = useMutation({
    mutationFn: ({ rId, text }) => api.post(`/reports/${rId}/comments`, { content: text }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['report_details', selectedReportId] });
      setNewComment('');
    }
  });

  const handleCreateReport = (e) => {
    e.preventDefault();
    if (!reportName.trim()) return;
    createReportMutation.mutate(reportName);
  };

  const handleAddAnnotation = (compId) => {
    const text = cardAnnotationText[compId];
    if (!text || !text.trim()) return;

    addAnnotationMutation.mutate({
      rId: selectedReportId,
      compId: compId,
      text: text
    });

    setCardAnnotationText({ ...cardAnnotationText, [compId]: '' });
    setShowAnnotationInput({ ...showAnnotationInput, [compId]: false });
  };

  const handleAddComment = (e) => {
    e.preventDefault();
    if (!newComment.trim()) return;
    addCommentMutation.mutate({ rId: selectedReportId, text: newComment });
  };

  const triggerExport = () => {
    // Navigate browser to download endpoint
    const token = localStorage.getItem('aura_token');
    window.open(`/api/reports/${selectedReportId}/export?token=${token || ''}`, '_blank');
  };

  const fetchAiSummary = async () => {
    setLoadingSummary(true);
    setAiSummary(null);
    try {
      const response = await api.post(`/reports/${selectedReportId}/summary`);
      setAiSummary(response.summary);
    } catch (err) {
      setAiSummary('Failed to compile summary. Check daily budget status.');
    } finally {
      setLoadingSummary(false);
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6 p-6 min-h-[calc(100vh-80px)] max-w-7xl mx-auto">
      
      {/* Reports Listing Sidebar */}
      <div className="md:col-span-1 flex flex-col gap-4">
        
        {/* Reports Index Header */}
        <div className="glass-card p-5 flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <h2 className="text-base font-bold text-text-primary flex items-center gap-2">
              <FileText className="text-secondary w-5 h-5" /> Saved Reports
            </h2>
            <button 
              onClick={() => setShowCreate(!showCreate)}
              className="p-1 rounded-full hover:bg-white/5 text-primary transition-all"
            >
              <Plus className="w-5 h-5" />
            </button>
          </div>

          {showCreate && (
            <form onSubmit={handleCreateReport} className="flex flex-col gap-3 p-3 bg-white/5 rounded-lg border border-border">
              <input 
                type="text"
                value={reportName}
                onChange={(e) => setReportName(e.target.value)}
                placeholder="Report Name"
                className="bg-black/40 border border-border rounded px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-primary"
                required
              />
              <button 
                type="submit"
                disabled={createReportMutation.isPending}
                className="bg-primary hover:bg-primary-hover text-black font-semibold rounded py-1.5 text-xs transition-all flex items-center justify-center gap-2"
              >
                {createReportMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />} Create Report
              </button>
            </form>
          )}

          {loadingReports ? (
            <div className="flex justify-center py-6"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>
          ) : (
            <div className="flex flex-col gap-2 overflow-y-auto max-h-[50vh]">
              {reports.map((rep) => (
                <button
                  key={rep.id}
                  onClick={() => { setSelectedReportId(rep.id); setAiSummary(null); }}
                  className={`text-left p-3.5 rounded-lg border transition-all ${
                    selectedReportId === rep.id 
                      ? 'bg-primary/10 border-primary text-text-primary' 
                      : 'border-border bg-white/0 text-text-secondary hover:bg-white/5'
                  }`}
                >
                  <div className="font-semibold text-xs flex items-center gap-1.5">
                    <FileType className="w-3.5 h-3.5 opacity-70" /> {rep.name}
                  </div>
                  <div className="text-[10px] opacity-60 mt-1 flex items-center gap-1">
                    <Calendar className="w-3 h-3" /> {new Date(rep.created_at).toLocaleDateString()}
                  </div>
                </button>
              ))}
              {reports.length === 0 && (
                <div className="text-xs text-text-secondary text-center py-6">No reports created yet. Click "+" to start.</div>
              )}
            </div>
          )}
        </div>

      </div>

      {/* Main Report Editor Workspace */}
      <div className="md:col-span-3 flex flex-col gap-6">
        
        {!selectedReportId ? (
          <div className="glass-card p-16 flex flex-col items-center justify-center text-text-secondary h-full min-h-[50vh]">
            <FileText className="w-16 h-16 opacity-20 mb-4" />
            <h3 className="text-lg font-bold">No Report Selected</h3>
            <p className="text-sm opacity-60">Create a report or select an existing one to build collaborative briefs.</p>
          </div>
        ) : loadingReportDetails ? (
          <div className="flex items-center justify-center min-h-[50vh]"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
        ) : (
          <>
            {/* Action Headers */}
            <div className="glass-card p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4 border border-border">
              <div>
                <h1 className="text-xl font-bold text-text-primary">{report.name}</h1>
                <p className="text-xs text-text-secondary opacity-60 mt-0.5">Unified Document Model — Real-time Collaboration Brief</p>
              </div>

              <div className="flex gap-2.5">
                <button 
                  onClick={fetchAiSummary}
                  disabled={loadingSummary}
                  className="px-4 py-2 border border-border bg-secondary/15 hover:bg-secondary/25 text-xs font-semibold rounded-lg text-text-primary transition-all flex items-center gap-2"
                >
                  {loadingSummary ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 text-secondary" />} 
                  AI Executive Narration
                </button>

                <button 
                  onClick={triggerExport}
                  className="px-4 py-2 bg-primary hover:bg-primary-hover text-black font-bold rounded-lg text-xs transition-all flex items-center gap-2"
                >
                  <Download className="w-3.5 h-3.5" /> Export Markdown
                </button>
              </div>
            </div>

            {/* AI Executive briefings card if loaded */}
            {aiSummary && (
              <div className="glass-card p-6 border border-secondary/20 bg-secondary/5 flex flex-col gap-3">
                <h3 className="text-xs font-bold text-secondary uppercase tracking-widest flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4" /> AI Executive Briefing
                </h3>
                <p className="text-sm leading-relaxed text-text-primary bg-black/20 p-4 rounded-xl border border-border">
                  {aiSummary}
                </p>
              </div>
            )}

            {/* Component Cards layout */}
            <div className="flex flex-col gap-6">
              {report.components.map((comp) => (
                <div key={comp.id} className="glass-card p-6 flex flex-col gap-4 border border-border/80">
                  <div className="flex items-center justify-between border-b border-border/40 pb-2">
                    <h3 className="text-sm font-bold text-text-primary">{comp.title}</h3>
                    <span className="text-[10px] bg-white/5 border border-border px-2 py-0.5 rounded text-text-secondary uppercase tracking-wider font-semibold">
                      {comp.type}
                    </span>
                  </div>

                  {/* Render component contents */}
                  <div className="bg-black/20 p-4 rounded-xl border border-border/40">
                    {comp.type === 'text' && (
                      <p className="text-sm text-text-primary leading-relaxed">{comp.config.content}</p>
                    )}
                    {comp.type === 'chart' && (
                      <div className="text-xs text-text-secondary italic text-center py-12 border border-dashed border-border rounded-xl">
                        [Interactive Apache ECharts Representation: {comp.config.chart_type}]
                      </div>
                    )}
                    {comp.type === 'table' && (
                      <div className="text-xs text-text-secondary italic text-center py-12 border border-dashed border-border rounded-xl">
                        [Ingested Data Grid View Panel]
                      </div>
                    )}
                  </div>

                  {/* Card Annotations */}
                  <div className="flex flex-col gap-2 pt-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] uppercase font-bold text-text-secondary tracking-widest">Observations & Annotations</span>
                      <button 
                        onClick={() => setShowAnnotationInput({ ...showAnnotationInput, [comp.id]: !showAnnotationInput[comp.id] })}
                        className="text-[10px] text-primary hover:underline"
                      >
                        + Add Observation
                      </button>
                    </div>

                    {showAnnotationInput[comp.id] && (
                      <div className="flex gap-2">
                        <input 
                          type="text" 
                          placeholder="Annotate findings..."
                          value={cardAnnotationText[comp.id] || ''}
                          onChange={(e) => setCardAnnotationText({ ...cardAnnotationText, [comp.id]: e.target.value })}
                          className="flex-1 bg-black/40 border border-border rounded px-3 py-1.5 text-xs text-text-primary focus:outline-none focus:border-primary"
                        />
                        <button 
                          onClick={() => handleAddAnnotation(comp.id)}
                          className="px-3 bg-primary hover:bg-primary-hover text-black text-xs font-bold rounded"
                        >
                          Save
                        </button>
                      </div>
                    )}

                    <div className="flex flex-col gap-1.5 mt-1">
                      {comp.annotations.map((note, nIdx) => (
                        <div key={nIdx} className="text-xs text-text-primary bg-white/2 border border-border/40 p-2.5 rounded-lg italic">
                          - {note}
                        </div>
                      ))}
                      {comp.annotations.length === 0 && (
                        <div className="text-[10px] text-text-secondary opacity-60">No annotations logged yet. Click add to annotate observations.</div>
                      )}
                    </div>
                  </div>

                </div>
              ))}
            </div>

            {/* Collaborative Comment Thread Panel */}
            <div className="glass-card p-6 flex flex-col gap-4 border border-border">
              <h3 className="text-sm font-bold text-text-primary border-b border-border pb-2 flex items-center gap-1.5">
                <MessageSquare className="w-4 h-4 text-primary" /> Workspace Discussion Thread
              </h3>
              
              <div className="flex flex-col gap-3 max-h-[30vh] overflow-y-auto pr-1">
                {report.comments.map((com) => (
                  <div key={com.id} className="p-3 bg-white/2 border border-border/60 rounded-xl text-xs flex flex-col gap-1">
                    <div className="flex items-center justify-between text-[10px] text-text-secondary font-semibold">
                      <span>{com.user_email}</span>
                      <span>{new Date(com.created_at).toLocaleTimeString()}</span>
                    </div>
                    <p className="text-text-primary leading-relaxed">{com.content}</p>
                  </div>
                ))}
                {report.comments.length === 0 && (
                  <div className="text-center py-6 text-xs text-text-secondary opacity-60">No discussion notes logged. Post the first comment below!</div>
                )}
              </div>

              <form onSubmit={handleAddComment} className="flex gap-2 border-t border-border pt-4">
                <input 
                  type="text" 
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Post comment to thread..."
                  className="flex-1 bg-black/40 border border-border rounded-xl px-4 py-2 text-xs text-text-primary focus:outline-none focus:border-primary placeholder-text-secondary/40"
                  required
                />
                <button 
                  type="submit"
                  disabled={addCommentMutation.isPending}
                  className="px-4 bg-primary hover:bg-primary-hover disabled:bg-primary/20 text-black font-bold rounded-xl transition-all"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </form>
            </div>

          </>
        )}
      </div>

    </div>
  );
}
export default Reports;
