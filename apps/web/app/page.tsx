import React from 'react';

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 text-center">
      <div className="max-w-3xl space-y-6">
        <div className="inline-block rounded-full bg-sky-500/10 px-4 py-1.5 text-sm font-semibold text-sky-400 border border-sky-500/20">
          InterviewIQ Platform &bull; Modular Monolith Phase 0
        </div>
        <h1 className="text-5xl font-extrabold tracking-tight sm:text-6xl bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
          AI-Powered Adaptive Technical Interviews
        </h1>
        <p className="text-lg text-slate-400 leading-relaxed">
          Production-grade interview platform featuring role-specific grounded RAG, structured Gemini AI evaluation, backend state machine governance, and multi-tenant security.
        </p>
        <div className="flex justify-center gap-4 pt-4">
          <a
            href="http://localhost:8000/api/v1/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg bg-sky-600 px-6 py-3 font-semibold text-white hover:bg-sky-500 transition-colors shadow-lg shadow-sky-600/20"
          >
            Explore API Documentation &rarr;
          </a>
        </div>
      </div>
    </main>
  );
}
