import { fetchApi } from '../lib/api-client';

export interface PDFExportItem {
  id: string;
  interview_session_id: string;
  interview_report_id: string;
  report_version: number;
  status: string;
  file_size_bytes?: number;
  created_at: string;
}

export const pdfExportService = {
  async requestExport(interview_id: string, report_id: string): Promise<PDFExportItem> {
    return fetchApi<PDFExportItem>(`/interviews/${interview_id}/reports/${report_id}/export`, {
      method: 'POST',
    });
  },

  async listExports(interview_id: string, report_id: string): Promise<PDFExportItem[]> {
    return fetchApi<PDFExportItem[]>(`/interviews/${interview_id}/reports/${report_id}/exports`);
  },

  getDownloadUrl(export_id: string): string {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    return `${baseUrl}/report-exports/${export_id}/download`;
  },
};
