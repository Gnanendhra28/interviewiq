import React from 'react';
import { Inbox } from 'lucide-react';

export function EmptyState({
  title = 'No records found',
  description = 'There are no items matching this criteria right now.',
  action,
}: {
  title?: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="glass-card border border-dashed border-slate-800 rounded-2xl p-12 text-center flex flex-col items-center justify-center space-y-4 my-4">
      <div className="w-14 h-14 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400">
        <Inbox className="w-7 h-7 text-indigo-400" />
      </div>
      <div className="space-y-1 max-w-sm">
        <h3 className="text-base font-bold text-white tracking-tight">{title}</h3>
        <p className="text-xs text-slate-400 leading-relaxed">{description}</p>
      </div>
      {action && <div className="pt-2">{action}</div>}
    </div>
  );
}
