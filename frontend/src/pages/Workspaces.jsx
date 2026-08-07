import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { FolderPlus, FileSpreadsheet, HardDrive, Plus, Loader2 } from 'lucide-react';

export function Workspaces({ onSelectDataset }) {
  const queryClient = useQueryClient();
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState(null);
  const [showCreateWorkspace, setShowCreateWorkspace] = useState(false);
  const [wsName, setWsName] = useState('');
  const [wsDesc, setWsDesc] = useState('');
  
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  // Fetch workspaces
  const { data: workspaces = [], isLoading: loadingWorkspaces } = useQuery({
    queryKey: ['workspaces'],
    queryFn: () => api.get('/workspaces'),
  });

  // Fetch datasets for selected workspace
  const { data: datasets = [], isLoading: loadingDatasets } = useQuery({
    queryKey: ['datasets', selectedWorkspaceId],
    queryFn: () => api.get(`/workspaces/${selectedWorkspaceId}/datasets`),
    enabled: !!selectedWorkspaceId,
  });

  // Create workspace mutation
  const createWorkspaceMutation = useMutation({
    mutationFn: (newWs) => api.post(`/workspaces?name=${newWs.name}&description=${newWs.description || ''}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
      setShowCreateWorkspace(false);
      setWsName('');
      setWsDesc('');
    },
  });

  const handleCreateWorkspace = (e) => {
    e.preventDefault();
    if (!wsName.trim()) return;
    createWorkspaceMutation.mutate({ name: wsName, description: wsDesc });
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file || !selectedWorkspaceId) return;

    setUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      await api.post(`/workspaces/${selectedWorkspaceId}/datasets`, formData);
      queryClient.invalidateQueries({ queryKey: ['datasets', selectedWorkspaceId] });
    } catch (err) {
      setUploadError(err.message || 'File upload failed. Ensure format is Parquet, CSV, or Excel.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6 p-6 min-h-[calc(100vh-80px)]">
      
      {/* Workspace Panel */}
      <div className="md:col-span-1 glass-card p-6 flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <h2 className="text-lg font-bold text-text-primary flex items-center gap-2">
            <HardDrive className="text-primary w-5 h-5" /> Workspaces
          </h2>
          <button 
            onClick={() => setShowCreateWorkspace(!showCreateWorkspace)}
            className="p-1.5 rounded-full hover:bg-white/5 text-primary transition-all"
          >
            <Plus className="w-5 h-5" />
          </button>
        </div>

        {showCreateWorkspace && (
          <form onSubmit={handleCreateWorkspace} className="flex flex-col gap-3 p-3 bg-white/5 rounded-lg border border-border">
            <input 
              type="text"
              placeholder="Workspace Name"
              value={wsName}
              onChange={(e) => setWsName(e.target.value)}
              className="bg-black/40 border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary"
              required
            />
            <textarea 
              placeholder="Description"
              value={wsDesc}
              onChange={(e) => setWsDesc(e.target.value)}
              className="bg-black/40 border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary h-16 resize-none"
            />
            <button 
              type="submit"
              disabled={createWorkspaceMutation.isPending}
              className="bg-primary hover:bg-primary-hover text-black font-semibold rounded py-1.5 text-sm transition-all flex items-center justify-center gap-2"
            >
              {createWorkspaceMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />} Create
            </button>
          </form>
        )}

        {loadingWorkspaces ? (
          <div className="flex justify-center py-6"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>
        ) : (
          <div className="flex flex-col gap-2 overflow-y-auto max-h-[60vh]">
            {workspaces.map((ws) => (
              <button
                key={ws.id}
                onClick={() => setSelectedWorkspaceId(ws.id)}
                className={`text-left p-3.5 rounded-lg border transition-all ${
                  selectedWorkspaceId === ws.id 
                    ? 'bg-primary/10 border-primary text-text-primary shadow-lg shadow-primary/5' 
                    : 'border-border bg-white/0 text-text-secondary hover:bg-white/5 hover:text-text-primary'
                }`}
              >
                <div className="font-semibold">{ws.name}</div>
                {ws.description && <div className="text-xs opacity-60 mt-1 truncate">{ws.description}</div>}
              </button>
            ))}
            {workspaces.length === 0 && (
              <div className="text-xs text-text-secondary text-center py-6">No workspaces created yet. Click "+" to start.</div>
            )}
          </div>
        )}
      </div>

      {/* Datasets Panel */}
      <div className="md:col-span-3 glass-card p-6 flex flex-col gap-4">
        {!selectedWorkspaceId ? (
          <div className="flex flex-col items-center justify-center h-full text-text-secondary py-16">
            <FolderPlus className="w-16 h-16 opacity-20 mb-4" />
            <h3 className="text-lg font-bold">No Workspace Selected</h3>
            <p className="text-sm opacity-60">Select or create a workspace on the left to manage datasets.</p>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div>
                <h2 className="text-lg font-bold text-text-primary">Workspace Datasets</h2>
                <p className="text-xs text-text-secondary opacity-60">Ingest files and manage structured profiles here.</p>
              </div>
              
              {/* File Upload Selector */}
              <div>
                <label 
                  className={`px-4 py-2 bg-primary hover:bg-primary-hover text-black font-semibold rounded-lg text-sm cursor-pointer transition-all flex items-center gap-2 ${uploading ? 'opacity-50 pointer-events-none' : ''}`}
                >
                  {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />} 
                  Upload Dataset (CSV/Parquet)
                  <input 
                    type="file" 
                    onChange={handleFileUpload} 
                    accept=".csv,.parquet,.xlsx,.xls,.json"
                    className="hidden" 
                    disabled={uploading}
                  />
                </label>
              </div>
            </div>

            {uploadError && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg p-3 text-sm">
                {uploadError}
              </div>
            )}

            {loadingDatasets ? (
              <div className="flex justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {datasets.map((dataset) => (
                  <div 
                    key={dataset.id} 
                    className="border border-border rounded-xl p-4 bg-white/2 hover:bg-white/5 transition-all flex flex-col justify-between"
                  >
                    <div className="flex items-start gap-3">
                      <div className="p-2 bg-secondary/10 text-secondary rounded-lg">
                        <FileSpreadsheet className="w-6 h-6" />
                      </div>
                      <div className="overflow-hidden">
                        <h4 className="font-semibold text-text-primary truncate">{dataset.name}</h4>
                        <div className="text-xs text-text-secondary mt-0.5 truncate">{dataset.filename}</div>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-2 border-t border-border mt-4 pt-3 text-center text-xs text-text-secondary">
                      <div>
                        <div className="font-bold text-text-primary">{dataset.row_count || '-'}</div>
                        <div className="opacity-60 text-[10px]">Rows</div>
                      </div>
                      <div>
                        <div className="font-bold text-text-primary">{dataset.column_count || '-'}</div>
                        <div className="opacity-60 text-[10px]">Columns</div>
                      </div>
                      <div>
                        <div className="font-bold text-text-primary">
                          {dataset.file_size_bytes ? `${(dataset.file_size_bytes / 1024).toFixed(1)} KB` : '-'}
                        </div>
                        <div className="opacity-60 text-[10px]">Size</div>
                      </div>
                    </div>

                    <button
                      onClick={() => onSelectDataset(dataset.id, dataset.workspace_id)}
                      className="mt-4 w-full bg-white/5 hover:bg-primary hover:text-black border border-border hover:border-primary rounded-lg py-2 text-xs font-semibold text-text-primary transition-all"
                    >
                      Inspect Profile & Dashboard
                    </button>
                  </div>
                ))}
                {datasets.length === 0 && (
                  <div className="col-span-2 text-center text-text-secondary py-16 opacity-60">
                    No datasets uploaded in this workspace. Upload a CSV or Parquet file to begin.
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
export default Workspaces;
