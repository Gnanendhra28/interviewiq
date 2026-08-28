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
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Knowledge Bases & Grounded RAG Documents</h1>
        <p className="text-sm text-slate-500 mt-1">Manage technical domain documentation for grounded interview question generation.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Create KB Form */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
            <Plus className="w-5 h-5 text-indigo-600" />
            <span>New Knowledge Base</span>
          </h2>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Base Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="PostgreSQL Guidelines"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Description</label>
              <textarea
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Internal database standards..."
                className="w-full p-2 border border-slate-300 rounded-lg text-sm"
              />
            </div>

            <button
              onClick={() => createKbMutation.mutate()}
              disabled={!name || createKbMutation.isPending}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm rounded-lg transition disabled:opacity-50"
            >
              Create Knowledge Base
            </button>
          </div>
        </div>

        {/* Knowledge Bases List & Document Upload */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <BookOpen className="w-5 h-5 text-indigo-600" />
              <span>Select Base for Document Upload</span>
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {(bases || []).map((kb) => (
                <div
                  key={kb.id}
                  onClick={() => setSelectedKbId(kb.id)}
                  className={`p-4 rounded-xl border cursor-pointer transition ${
                    selectedKbId === kb.id ? 'border-indigo-600 bg-indigo-50/50' : 'border-slate-200 bg-white hover:border-slate-300'
                  }`}
                >
                  <h3 className="font-bold text-slate-900 text-sm">{kb.name}</h3>
                  <p className="text-xs text-slate-500 mt-1">{kb.description || 'No description provided.'}</p>
                </div>
              ))}
            </div>
          </div>

          {selectedKbId && (
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
              <h3 className="font-bold text-slate-900 text-sm flex items-center space-x-2">
                <Upload className="w-4 h-4 text-indigo-600" />
                <span>Upload Document to Base</span>
              </h3>

              <div className="space-y-3">
                <input
                  type="text"
                  placeholder="Document Title (e.g. PgBouncer Architecture)"
                  value={docTitle}
                  onChange={(e) => setDocTitle(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                />

                <input
                  type="file"
                  accept=".pdf,.docx"
                  onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
                  className="text-xs text-slate-500"
                />

                <button
                  onClick={() => uploadDocMutation.mutate()}
                  disabled={!file || !docTitle || uploadDocMutation.isPending}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg transition disabled:opacity-50"
                >
                  Upload & Vectorize Document
                </button>
              </div>

              {/* Ingested Documents Table */}
              <div className="border-t border-slate-100 pt-4">
                <h4 className="text-xs font-semibold uppercase text-slate-500 mb-2">Ingested Documents:</h4>
                <div className="space-y-2">
                  {(documents || []).map((doc) => (
                    <div key={doc.id} className="flex justify-between items-center bg-slate-50 p-3 rounded-lg text-xs">
                      <div>
                        <span className="font-bold text-slate-800">{doc.title}</span>
                        <span className="block text-slate-400">{doc.filename}</span>
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          doc.ingestion_status === 'READY' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
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
