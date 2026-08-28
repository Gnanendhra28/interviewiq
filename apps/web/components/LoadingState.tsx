import React from 'react';
import { Loader2, Sparkles } from 'lucide-react';

export function LoadingState({ message = 'Loading pipeline metrics...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[300px] w-full p-8">
      <div className="glass-panel p-8 rounded-2xl border border-slate-800 flex flex-col items-center space-y-4 max-w-sm w-full text-center glow-indigo">
        <div className="relative">
          <div className="w-12 h-12 rounded-xl bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center">
            <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
          </div>
          <Sparkles className="w-4 h-4 text-emerald-400 absolute -top-1 -right-1 animate-pulse" />
        </div>
        <div className="space-y-1">
          <h4 className="text-sm font-bold text-white tracking-wide">InterviewIQ Engine</h4>
          <p className="text-xs text-slate-400 font-medium">{message}</p>
        </div>
      </div>
    </div>
  );
}
