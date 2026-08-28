'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '../lib/auth-context';
import { LayoutDashboard, Users, Briefcase, BookOpen, FileCheck, ShieldAlert, LogOut, Building2, Bell, Network } from 'lucide-react';

export function Navbar() {
  const { user, activeOrganization, memberships, switchOrganization, logout } = useAuth();
  const pathname = usePathname();

  if (pathname.startsWith('/auth') || pathname.startsWith('/candidate/interview')) {
    return null; // Simplified layout for auth and candidate test pages
  }

  return (
    <nav className="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-8">
            <Link href="/recruiter/dashboard" className="flex items-center space-x-2 font-bold text-xl text-indigo-400">
              <span>InterviewIQ</span>
            </Link>

            <div className="hidden md:flex space-x-3">
              <Link
                href="/recruiter/dashboard"
                className={`flex items-center space-x-1.5 px-3 py-2 rounded-md text-sm font-medium ${
                  pathname === '/recruiter/dashboard' ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                <LayoutDashboard className="w-4 h-4" />
                <span>Dashboard</span>
              </Link>

              <Link
                href="/recruiter/candidates"
                className={`flex items-center space-x-1.5 px-3 py-2 rounded-md text-sm font-medium ${
                  pathname.startsWith('/recruiter/candidates') ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                <Users className="w-4 h-4" />
                <span>Pipeline</span>
              </Link>

              <Link
                href="/recruiter/job-roles"
                className={`flex items-center space-x-1.5 px-3 py-2 rounded-md text-sm font-medium ${
                  pathname === '/recruiter/job-roles' ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                <Briefcase className="w-4 h-4" />
                <span>Job Roles</span>
              </Link>

              <Link
                href="/recruiter/knowledge"
                className={`flex items-center space-x-1.5 px-3 py-2 rounded-md text-sm font-medium ${
                  pathname === '/recruiter/knowledge' ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                <BookOpen className="w-4 h-4" />
                <span>Knowledge</span>
              </Link>

              <Link
                href="/recruiter/interviews"
                className={`flex items-center space-x-1.5 px-3 py-2 rounded-md text-sm font-medium ${
                  pathname === '/recruiter/interviews' ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                <FileCheck className="w-4 h-4" />
                <span>Interviews</span>
              </Link>

              <Link
                href="/recruiter/review-queue"
                className={`flex items-center space-x-1.5 px-3 py-2 rounded-md text-sm font-medium ${
                  pathname === '/recruiter/review-queue' ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                <ShieldAlert className="w-4 h-4 text-amber-400" />
                <span>Queue</span>
              </Link>

              <Link
                href="/recruiter/notifications"
                className={`flex items-center space-x-1.5 px-3 py-2 rounded-md text-sm font-medium ${
                  pathname === '/recruiter/notifications' ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                <Bell className="w-4 h-4" />
                <span>Alerts</span>
              </Link>

              <Link
                href="/recruiter/settings/integrations"
                className={`flex items-center space-x-1.5 px-3 py-2 rounded-md text-sm font-medium ${
                  pathname.startsWith('/recruiter/settings') ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                <Network className="w-4 h-4" />
                <span>ATS</span>
              </Link>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {/* Organization Context Switcher */}
            {memberships.length > 0 && (
              <div className="flex items-center space-x-2 bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700">
                <Building2 className="w-4 h-4 text-indigo-400" />
                <select
                  aria-label="Select Organization"
                  value={activeOrganization?.id || ''}
                  onChange={(e) => switchOrganization(e.target.value)}
                  className="bg-transparent text-sm text-slate-200 focus:outline-none cursor-pointer"
                >
                  {memberships.map((m) => (
                    <option key={m.organization_id} value={m.organization_id} className="bg-slate-900 text-white">
                      {m.organization?.name || m.organization_id.substring(0, 8)}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* User Account & Logout */}
            {user ? (
              <div className="flex items-center space-x-3">
                <span className="text-sm font-medium text-slate-300 hidden sm:inline">{user.email}</span>
                <button
                  onClick={logout}
                  className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-md transition"
                  title="Log out"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <Link href="/auth/login" className="text-sm font-medium text-indigo-400 hover:text-indigo-300">
                Sign In
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
