'use client';

import React from 'react';
import Link from 'next/link';
import {
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Zap,
  BrainCircuit,
  FileText,
  Users,
  CheckCircle2,
  Lock,
  BarChart3,
  Terminal,
  Layers,
  Bot,
} from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans overflow-x-hidden selection:bg-indigo-500 selection:text-white">
      {/* Background Ambient Glows */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[500px] bg-gradient-to-b from-indigo-600/20 via-sky-500/10 to-transparent blur-3xl pointer-events-none -z-10" />

      {/* Header / Brand Navbar */}
      <header className="glass-panel border-b border-slate-800/80 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-emerald-400 p-0.5 glow-indigo">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-indigo-400" />
              </div>
            </div>
            <span className="font-extrabold text-xl text-white tracking-tight">
              Interview<span className="gradient-text">IQ</span>
            </span>
          </div>

          <div className="flex items-center space-x-4">
            <a
              href="https://interviewiq-staging-staging-api-q24ci75lba-uc.a.run.app/api/v1/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-semibold text-slate-300 hover:text-white hidden sm:flex items-center space-x-1.5 transition"
            >
              <Terminal className="w-3.5 h-3.5 text-indigo-400" />
              <span>Swagger API Docs</span>
            </a>
            <Link
              href="/auth/login"
              className="text-xs font-semibold text-slate-300 hover:text-white px-3 py-1.5 rounded-lg hover:bg-slate-800 transition"
            >
              Sign In
            </Link>
            <Link
              href="/auth/register"
              className="text-xs font-bold text-white bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 px-4 py-2 rounded-lg shadow-lg shadow-indigo-600/30 transition transform hover:-translate-y-0.5"
            >
              Recruiter Access
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-20 pb-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto text-center flex flex-col items-center">
        <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold mb-8 animate-fade-in">
          <Bot className="w-3.5 h-3.5 text-indigo-400" />
          <span>Autonomous AI Technical Hiring & Decision Intelligence</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold text-white tracking-tight max-w-4xl leading-tight">
          Next-Gen AI <span className="gradient-text">Technical Interviews</span> & Recruiter Intelligence
        </h1>

        <p className="mt-6 text-lg sm:text-xl text-slate-300 max-w-2xl font-normal leading-relaxed">
          Screen resumes, generate adaptive AI coding & system design assessments, detect cheating in real time, and receive instant executive hiring recommendations.
        </p>

        {/* CTA Button Group */}
        <div className="mt-10 flex flex-col sm:flex-row items-center gap-4">
          <Link
            href="/recruiter/dashboard"
            className="w-full sm:w-auto px-8 py-4 bg-gradient-to-r from-indigo-600 via-indigo-500 to-emerald-500 text-white font-bold rounded-xl shadow-xl shadow-indigo-500/25 hover:shadow-indigo-500/40 hover:scale-[1.02] transition duration-200 flex items-center justify-center space-x-2"
          >
            <span>Launch Recruiter Portal</span>
            <ArrowRight className="w-5 h-5" />
          </Link>

          <Link
            href="/auth/register"
            className="w-full sm:w-auto px-8 py-4 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 font-semibold rounded-xl transition flex items-center justify-center space-x-2"
          >
            <span>Create Organization</span>
          </Link>
        </div>

        {/* Platform Stat Highlights */}
        <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-4 w-full max-w-4xl">
          <div className="glass-card p-4 rounded-xl text-center">
            <p className="text-2xl sm:text-3xl font-extrabold text-indigo-400">99.4%</p>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mt-1">Screening Accuracy</p>
          </div>
          <div className="glass-card p-4 rounded-xl text-center">
            <p className="text-2xl sm:text-3xl font-extrabold text-emerald-400">&lt; 15 min</p>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mt-1">Full Evaluation</p>
          </div>
          <div className="glass-card p-4 rounded-xl text-center">
            <p className="text-2xl sm:text-3xl font-extrabold text-sky-400">100%</p>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mt-1">Audit Logged</p>
          </div>
          <div className="glass-card p-4 rounded-xl text-center">
            <p className="text-2xl sm:text-3xl font-extrabold text-amber-400">Zero-Trust</p>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mt-1">Anti-Cheating</p>
          </div>
        </div>
      </section>

      {/* Interactive Workflow Pipeline Section */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full">
        <div className="text-center mb-12">
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            End-to-End Autonomous Hiring Workflow
          </h2>
          <p className="text-sm text-slate-400 mt-2 max-w-xl mx-auto">
            From job spec upload to final recruiter sign-off, InterviewIQ automates candidate evaluation with precision.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="glass-card p-5 rounded-xl space-y-3 relative group hover:border-indigo-500/50 transition">
            <div className="w-10 h-10 rounded-lg bg-indigo-950 border border-indigo-800 flex items-center justify-center text-indigo-400 font-bold">
              1
            </div>
            <h3 className="font-bold text-sm text-white">Job Spec & RAG</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Upload job descriptions and internal engineering knowledge docs into vector storage.
            </p>
          </div>

          <div className="glass-card p-5 rounded-xl space-y-3 relative group hover:border-indigo-500/50 transition">
            <div className="w-10 h-10 rounded-lg bg-indigo-950 border border-indigo-800 flex items-center justify-center text-indigo-400 font-bold">
              2
            </div>
            <h3 className="font-bold text-sm text-white">AI Resume Extraction</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Extract technical skills, experience claims, and role fit automatically from candidate PDFs.
            </p>
          </div>

          <div className="glass-card p-5 rounded-xl space-y-3 relative group hover:border-indigo-500/50 transition">
            <div className="w-10 h-10 rounded-lg bg-indigo-950 border border-indigo-800 flex items-center justify-center text-indigo-400 font-bold">
              3
            </div>
            <h3 className="font-bold text-sm text-white">Adaptive AI Interview</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Conduct dynamic real-time technical interviews tailored to candidate responses.
            </p>
          </div>

          <div className="glass-card p-5 rounded-xl space-y-3 relative group hover:border-indigo-500/50 transition">
            <div className="w-10 h-10 rounded-lg bg-indigo-950 border border-indigo-800 flex items-center justify-center text-indigo-400 font-bold">
              4
            </div>
            <h3 className="font-bold text-sm text-white">Automated Scoring</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Multi-dimensional evaluation across technical depth, problem-solving, and communication.
            </p>
          </div>

          <div className="glass-card p-5 rounded-xl space-y-3 relative group hover:border-indigo-500/50 transition">
            <div className="w-10 h-10 rounded-lg bg-indigo-950 border border-indigo-800 flex items-center justify-center text-indigo-400 font-bold">
              5
            </div>
            <h3 className="font-bold text-sm text-white">Decision Support</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              One-click Hire / Shortlist / Reject decisions backed by full audio transcripts and PDF reports.
            </p>
          </div>
        </div>
      </section>

      {/* Deep Dive Capabilities Grid */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="glass-panel p-6 rounded-2xl space-y-4">
            <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-xl w-fit">
              <BrainCircuit className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-white">Adaptive Interview Engine</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Questions adjust dynamically based on candidate answers, probing deep architecture concepts and code edge cases.
            </p>
          </div>

          <div className="glass-panel p-6 rounded-2xl space-y-4">
            <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-xl w-fit">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-white">Integrity & Anti-Cheating</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Focus monitoring, window switch tracking, and audio pattern validation ensure zero-trust interview authenticity.
            </p>
          </div>

          <div className="glass-panel p-6 rounded-2xl space-y-4">
            <div className="p-3 bg-sky-500/10 text-sky-400 rounded-xl w-fit">
              <FileText className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-white">Executive PDF Reports</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Download complete candidate scorecards, risk flags, and rationale summaries formatted for executive review.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto border-t border-slate-800/80 py-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 space-y-4 sm:space-y-0">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-indigo-400" />
          <span className="font-bold text-slate-300">InterviewIQ Enterprise Platform</span>
          <span>© 2026 All Rights Reserved</span>
        </div>

        <div className="flex items-center space-x-6">
          <a href="https://interviewiq-staging-staging-api-q24ci75lba-uc.a.run.app/health" target="_blank" rel="noopener noreferrer" className="hover:text-slate-300 flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Staging API Healthy</span>
          </a>
          <a href="https://interviewiq-staging-staging-api-q24ci75lba-uc.a.run.app/api/v1/docs" target="_blank" rel="noopener noreferrer" className="hover:text-slate-300">
            OpenAPI Specs
          </a>
        </div>
      </footer>
    </div>
  );
}

