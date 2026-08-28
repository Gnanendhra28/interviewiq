import React from 'react';
import { AlertCircle } from 'lucide-react';

export function ErrorBanner({ message, code, requestId }: { message: string; code?: string; requestId?: string }) {
  return (
    <div className="bg-rose-950/40 border border-rose-800/60 rounded-xl p-4 flex items-start space-x-3 text-rose-200 my-4 shadow-lg backdrop-blur-sm">
      <div className="p-1.5 bg-rose-900/50 rounded-lg text-rose-400 flex-shrink-0 mt-0.5">
        <AlertCircle className="w-5 h-5" />
      </div>
      <div className="space-y-1">
        <h4 className="font-bold text-sm text-rose-100">{message}</h4>
        {(code || requestId) && (
          <p className="text-xs text-rose-300/80 font-mono tracking-tight">
            {code && <span>[Error Code: {code}] </span>}
            {requestId && <span>(Req: {requestId})</span>}
          </p>
        )}
      </div>
    </div>
  );
}
