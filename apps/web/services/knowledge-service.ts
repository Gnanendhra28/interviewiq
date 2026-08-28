import { fetchApi } from '../lib/api-client';
import { KnowledgeBase, KnowledgeDocument } from '../types';

export const knowledgeService = {
  async listBases(): Promise<KnowledgeBase[]> {
    return fetchApi<KnowledgeBase[]>('/knowledge-bases');
  },

  async createBase(data: { name: string; description?: string }): Promise<KnowledgeBase> {
    return fetchApi<KnowledgeBase>('/knowledge-bases', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async listDocuments(knowledge_base_id: string): Promise<KnowledgeDocument[]> {
    return fetchApi<KnowledgeDocument[]>(`/knowledge-bases/${knowledge_base_id}/documents`);
  },

  async uploadDocument(knowledge_base_id: string, file: File, title: string): Promise<KnowledgeDocument> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title);

    return fetchApi<KnowledgeDocument>(`/knowledge-bases/${knowledge_base_id}/documents/upload`, {
      method: 'POST',
      body: formData,
    });
  },
};
