import React from 'react';
import { AlertTriangle } from 'lucide-react';

export function ErrorBanner({ message, code, requestId }: { message: string; code?: string; requestId?: string }) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start space-x-3 text-red-800 my-4">
      <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
      <div>
        <p className="font-semibold text-sm">{message}</p>
        {(code || requestId) && (
          <p className="text-xs text-red-600 mt-1 font-mono">
            {code && <span>Code: {code} </span>}
            {requestId && <span>(Request ID: {requestId})</span>}
          </p>
        )}
      </div>
    </div>
  );
}
