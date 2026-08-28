'use client';

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useQuery, useMutation } from '@tanstack/react-query';
import { interviewService } from '../../../../services/interview-service';
import { LoadingState } from '../../../../components/LoadingState';
import { ErrorBanner } from '../../../../components/ErrorBanner';
import { InterviewQuestion } from '../../../../types';
import { Send, CheckCircle, Clock } from 'lucide-react';

export default function CandidateInterviewPage() {
  const params = useParams();
  const interviewId = params.id as string;

  const [currentQuestion, setCurrentQuestion] = useState<InterviewQuestion | null>(null);
  const [answerText, setAnswerText] = useState('');
  const [idempotencyKey, setIdempotencyKey] = useState('');
  const [isCompleted, setIsCompleted] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  // Fetch Interview Progress
  const { data: progress } = useQuery({
    queryKey: ['candidateProgress', interviewId],
    queryFn: () => interviewService.getProgress(interviewId),
    refetchInterval: isCompleted ? false : 3000,
  });

  // Fetch Next Question
  const fetchQuestion = async () => {
    try {
      const q = await interviewService.getNextQuestion(interviewId);
      setCurrentQuestion(q);
      setAnswerText('');
      setIdempotencyKey(`ans_${q.id}_${Math.random().toString(36).substring(2, 8)}`);
    } catch (e: any) {
      if (e.message?.includes('completed') || progress?.is_completed) {
        setIsCompleted(true);
      } else {
        setStatusMsg(e.message || 'Waiting for next question...');
      }
    }
  };

  useEffect(() => {
    fetchQuestion();
  }, [interviewId]);

  // Answer Submission Mutation
  const submitAnswerMutation = useMutation({
    mutationFn: () => {
      if (!currentQuestion || !answerText) throw new Error('Answer required');
      return interviewService.submitAnswer(interviewId, currentQuestion.id, answerText, idempotencyKey);
    },
    onSuccess: () => {
      setStatusMsg('Answer submitted! Preparing next adaptive question...');
      setTimeout(() => {
        setStatusMsg('');
        fetchQuestion();
      }, 2000);
    },
  });

  if (isCompleted || progress?.is_completed) {
    return (
      <div className="max-w-xl mx-auto my-16 glass-panel p-8 rounded-2xl border border-slate-800/80 shadow-2xl text-center space-y-4">
        <div className="w-16 h-16 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full flex items-center justify-center mx-auto shadow-lg">
          <CheckCircle className="w-10 h-10" />
        </div>
        <h1 className="text-2xl font-extrabold text-white">Interview Completed!</h1>
        <p className="text-sm text-slate-300">
          Thank you for completing your technical interview session. Your responses have been submitted to the recruiting team.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto my-8 space-y-6 px-4">
      {/* Top Header */}
      <div className="glass-panel text-white p-5 rounded-xl border border-slate-800/80 flex items-center justify-between shadow-2xl">
        <div>
          <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">InterviewIQ Candidate UX</span>
          <h1 className="text-lg font-extrabold">Technical Adaptive Assessment</h1>
        </div>
        <div className="flex items-center space-x-2 text-xs bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-full text-slate-300">
          <Clock className="w-4 h-4 text-indigo-400" />
          <span>Turn #{progress?.turn_count ?? 1}</span>
        </div>
      </div>

      {statusMsg && <div className="p-3 bg-indigo-500/20 border border-indigo-500/40 text-indigo-300 rounded-lg text-xs font-semibold">{statusMsg}</div>}

      {/* Active Question Box */}
      {currentQuestion ? (
        <div className="glass-panel p-8 rounded-2xl border border-slate-800/80 shadow-2xl space-y-6">
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-0.5 bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-xs font-bold rounded-full">
                {currentQuestion.topic}
              </span>
              <span className="text-xs font-semibold uppercase text-slate-400 font-mono">
                Difficulty: {currentQuestion.difficulty}
              </span>
            </div>
            <h2 className="text-xl font-bold text-white leading-relaxed">{currentQuestion.question_text}</h2>
          </div>

          {/* Candidate Answer Input */}
          <div className="space-y-3 pt-2">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">Your Technical Response</label>
            <textarea
              rows={6}
              value={answerText}
              onChange={(e) => setAnswerText(e.target.value)}
              placeholder="Type your detailed answer or code logic here..."
              className="w-full p-4 bg-slate-950 border border-slate-800 text-slate-100 rounded-xl text-sm focus:outline-none focus:border-indigo-500"
            />

            <button
              onClick={() => submitAnswerMutation.mutate()}
              disabled={!answerText.trim() || submitAnswerMutation.isPending}
              className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-sm transition disabled:opacity-50 flex items-center justify-center space-x-2 shadow-lg shadow-indigo-600/30"
            >
              <Send className="w-4 h-4" />
              <span>{submitAnswerMutation.isPending ? 'Submitting Answer...' : 'Submit Answer'}</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="p-8 text-center text-slate-400 glass-panel rounded-xl">Loading current question...</div>
      )}
    </div>
  );
}
