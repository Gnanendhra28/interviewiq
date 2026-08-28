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
      <div className="max-w-xl mx-auto my-16 bg-white p-8 rounded-2xl border border-slate-200 shadow-sm text-center space-y-4">
        <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto">
          <CheckCircle className="w-10 h-10" />
        </div>
        <h1 className="text-2xl font-bold text-slate-900">Interview Completed!</h1>
        <p className="text-sm text-slate-600">
          Thank you for completing your technical interview session. Your responses have been submitted to the recruiting team.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto my-8 space-y-6">
      {/* Top Header */}
      <div className="bg-slate-900 text-white p-5 rounded-xl flex items-center justify-between shadow-sm">
        <div>
          <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">InterviewIQ Candidate UX</span>
          <h1 className="text-lg font-bold">Technical Adaptive Assessment</h1>
        </div>
        <div className="flex items-center space-x-2 text-xs bg-slate-800 px-3 py-1.5 rounded-full text-slate-300">
          <Clock className="w-4 h-4 text-indigo-400" />
          <span>Turn #{progress?.turn_count ?? 1}</span>
        </div>
      </div>

      {statusMsg && <div className="p-3 bg-blue-50 border border-blue-200 text-blue-800 rounded-lg text-xs font-semibold">{statusMsg}</div>}

      {/* Active Question Box */}
      {currentQuestion ? (
        <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm space-y-6">
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-0.5 bg-indigo-50 text-indigo-700 text-xs font-bold rounded-full">
                {currentQuestion.topic}
              </span>
              <span className="text-xs font-semibold uppercase text-slate-400 font-mono">
                Difficulty: {currentQuestion.difficulty}
              </span>
            </div>
            <h2 className="text-xl font-bold text-slate-900 leading-relaxed">{currentQuestion.question_text}</h2>
          </div>

          {/* Candidate Answer Input */}
          <div className="space-y-3 pt-2">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500">Your Technical Response</label>
            <textarea
              rows={8}
              value={answerText}
              onChange={(e) => setAnswerText(e.target.value)}
              placeholder="Provide a clear, detailed technical response..."
              className="w-full p-4 border border-slate-300 rounded-xl text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />

            <button
              onClick={() => submitAnswerMutation.mutate()}
              disabled={!answerText.trim() || submitAnswerMutation.isPending}
              className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl text-sm transition disabled:opacity-50 flex items-center justify-center space-x-2 shadow-sm"
            >
              <Send className="w-4 h-4" />
              <span>{submitAnswerMutation.isPending ? 'Submitting Answer...' : 'Submit Answer'}</span>
            </button>
          </div>
        </div>
      ) : (
        <LoadingState message="Loading next interview question..." />
      )}
    </div>
  );
}
