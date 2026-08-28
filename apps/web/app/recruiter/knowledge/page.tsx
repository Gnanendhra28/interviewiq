'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { knowledgeService } from '../../../services/knowledge-service';
import { LoadingState } from '../../../components/LoadingState';
import { ErrorBanner } from '../../../components/ErrorBanner';
import { BookOpen, Plus, Upload, FileText } from 'lucide-react';

export default function KnowledgePage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedKbId, setSelectedKbId] = useState<string | null>(null);
  const [docTitle, setDocTitle] = useState('');
  const [file, setFile] = useState<File | null>(null);

  const { data: bases, isLoading, error } = useQuery({
    queryKey: ['knowledgeBases'],
    queryFn: () => knowledgeService.listBases(),
  });

  const { data: documents } = useQuery({
    queryKey: ['knowledgeDocs', selectedKbId],
    queryFn: () => (selectedKbId ? knowledgeService.listDocuments(selectedKbId) : Promise.resolve([])),
    enabled: !!selectedKbId,
    refetchInterval: 3000, // Safe polling for document ingestion status
  });

  const createKbMutation = useMutation({
    mutationFn: () => knowledgeService.createBase({ name, description }),
    onSuccess: () => {
      setName('');
      setDescription('');
      queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] });
    },
  });

  const uploadDocMutation = useMutation({
    mutationFn: () => {
      if (!selectedKbId || !file || !docTitle) throw new Error('Missing file or title');
      return knowledgeService.uploadDocument(selectedKbId, file, docTitle);
    },
    onSuccess: () => {
      setDocTitle('');
      setFile(null);
      queryClient.invalidateQueries({ queryKey: ['knowledgeDocs', selectedKbId] });
    },
  });

  if (isLoading) return <LoadingState message="Loading knowledge bases..." />;
  if (error) return <ErrorBanner message={(error as Error).message} />;

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="border-b border-slate-800/80 pb-6">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">Knowledge Bases & Grounded RAG Documents</h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">Manage technical domain documentation for grounded interview question generation.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Create KB Form */}
        <div className="glass-panel p-6 rounded-xl border border-slate-800/80 shadow-2xl space-y-4">
          <h2 className="text-base font-bold text-white flex items-center space-x-2">
            <Plus className="w-5 h-5 text-indigo-400" />
            <span>New Knowledge Base</span>
          </h2>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1">Base Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="PostgreSQL Guidelines"
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 text-slate-100 rounded-lg text-xs focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1">Description</label>
              <textarea
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Internal database standards..."
                className="w-full p-2 bg-slate-950 border border-slate-800 text-slate-100 rounded-lg text-xs focus:outline-none focus:border-indigo-500"
              />
            </div>

            <button
              onClick={() => createKbMutation.mutate()}
              disabled={!name || createKbMutation.isPending}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-indigo-600/30 transition disabled:opacity-50"
            >
              Create Knowledge Base
            </button>
          </div>
        </div>

        {/* Knowledge Bases List & Document Upload */}
        <div className="lg:col-span-2 space-y-6">
          <div className="glass-panel p-6 rounded-xl border border-slate-800/80 shadow-2xl space-y-4">
            <h2 className="text-base font-bold text-white flex items-center space-x-2">
              <BookOpen className="w-5 h-5 text-indigo-400" />
              <span>Select Base for Document Upload</span>
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {(bases || []).map((kb) => (
                <div
                  key={kb.id}
                  onClick={() => setSelectedKbId(kb.id)}
                  className={`p-4 rounded-xl border cursor-pointer transition ${
                    selectedKbId === kb.id ? 'border-indigo-500 bg-indigo-600/20 text-indigo-300' : 'border-slate-800 bg-slate-900/90 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  <h3 className="font-bold text-white text-sm">{kb.name}</h3>
                  <p className="text-xs text-slate-400 mt-1">{kb.description || 'No description provided.'}</p>
                </div>
              ))}
            </div>
          </div>

          {selectedKbId && (
            <div className="glass-panel p-6 rounded-xl border border-slate-800/80 shadow-2xl space-y-4">
              <h3 className="font-bold text-white text-sm flex items-center space-x-2">
                <Upload className="w-4 h-4 text-indigo-400" />
                <span>Upload Document to Base</span>
              </h3>

              <div className="space-y-3">
                <input
                  type="text"
                  placeholder="Document Title (e.g. PgBouncer Architecture)"
                  value={docTitle}
                  onChange={(e) => setDocTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 text-slate-100 rounded-lg text-xs focus:outline-none focus:border-indigo-500"
                />

                <input
                  type="file"
                  accept=".pdf,.docx"
                  onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
                  className="text-xs text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-slate-200 hover:file:bg-slate-700 cursor-pointer"
                />

                <button
                  onClick={() => uploadDocMutation.mutate()}
                  disabled={!file || !docTitle || uploadDocMutation.isPending}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-indigo-600/30 transition disabled:opacity-50"
                >
                  Upload & Vectorize Document
                </button>
              </div>

              {/* Ingested Documents Table */}
              <div className="border-t border-slate-800/60 pt-4">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Ingested Documents:</h4>
                <div className="space-y-2">
                  {(documents || []).map((doc) => (
                    <div key={doc.id} className="flex justify-between items-center bg-slate-900/90 border border-slate-800 p-3 rounded-lg text-xs">
                      <div>
                        <span className="font-bold text-white">{doc.title}</span>
                        <span className="block text-slate-400 text-[11px] mt-0.5">{doc.filename}</span>
                      </div>
                      <span
                        className={`px-2.5 py-1 rounded-full text-xs font-bold border ${
                          doc.ingestion_status === 'READY' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                        }`}
                      >
                        {doc.ingestion_status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
