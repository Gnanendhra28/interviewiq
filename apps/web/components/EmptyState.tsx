import React from 'react';
import { Inbox } from 'lucide-react';

export function EmptyState({ title = 'No records found', description = 'There are no items to display right now.' }: { title?: string; description?: string }) {
  return (
    <div className="border border-dashed border-slate-300 rounded-lg p-12 text-center flex flex-col items-center justify-center space-y-2">
      <Inbox className="w-10 h-10 text-slate-400" />
      <h3 className="text-base font-semibold text-slate-700">{title}</h3>
      <p className="text-sm text-slate-500 max-w-sm">{description}</p>
    </div>
  );
}
