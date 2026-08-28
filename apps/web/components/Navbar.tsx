'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '../lib/auth-context';
import {
  LayoutDashboard,
  Users,
  Briefcase,
  BookOpen,
  FileCheck,
  ShieldAlert,
  LogOut,
  Building2,
  Bell,
  Network,
  Sparkles,
  User,
} from 'lucide-react';

export function Navbar() {
  const { user, activeOrganization, memberships, switchOrganization, logout } = useAuth();
  const pathname = usePathname();

  if (pathname === '/' || pathname.startsWith('/auth') || pathname.startsWith('/candidate/interview')) {
    return null; // Custom standalone header for public landing, auth, and candidate interview room
  }

  const navItems = [
    { href: '/recruiter/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/recruiter/candidates', label: 'Pipeline', icon: Users },
    { href: '/recruiter/job-roles', label: 'Job Roles', icon: Briefcase },
    { href: '/recruiter/knowledge', label: 'Knowledge RAG', icon: BookOpen },
    { href: '/recruiter/interviews', label: 'Interviews', icon: FileCheck },
    { href: '/recruiter/review-queue', label: 'Review Queue', icon: ShieldAlert, badge: true },
    { href: '/recruiter/notifications', label: 'Alerts', icon: Bell },
    { href: '/recruiter/settings/integrations', label: 'ATS Sync', icon: Network },
  ];

  return (
    <nav className="glass-panel border-b border-slate-800/80 sticky top-0 z-50 shadow-2xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Left Brand & Primary Navigation */}
          <div className="flex items-center space-x-8">
            <Link href="/recruiter/dashboard" className="flex items-center space-x-3 group">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-emerald-400 p-0.5 glow-indigo transition duration-300 group-hover:scale-105">
                <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-indigo-400 group-hover:rotate-12 transition duration-300" />
                </div>
              </div>
              <div className="flex flex-col">
                <span className="font-extrabold text-lg text-white tracking-tight leading-none">
                  Interview<span className="gradient-text">IQ</span>
                </span>
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest leading-tight mt-0.5">
                  Recruiter Command Center
                </span>
              </div>
            </Link>

            {/* Nav Tabs */}
            <div className="hidden lg:flex items-center space-x-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href || (item.href !== '/recruiter/dashboard' && pathname.startsWith(item.href));

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all duration-200 relative ${
                      isActive
                        ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                    }`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`} />
                    <span>{item.label}</span>
                    {item.badge && (
                      <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping absolute top-1.5 right-1.5" />
                    )}
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Right Org Switcher & User Profile */}
          <div className="flex items-center space-x-4">
            {/* Organization Context Switcher */}
            {memberships.length > 0 && (
              <div className="flex items-center space-x-2 bg-slate-900/90 px-3 py-1.5 rounded-lg border border-slate-800 focus-within:border-indigo-500 transition">
                <Building2 className="w-3.5 h-3.5 text-indigo-400" />
                <select
                  aria-label="Select Organization"
                  value={activeOrganization?.id || ''}
                  onChange={(e) => switchOrganization(e.target.value)}
                  className="bg-transparent text-xs font-semibold text-slate-200 focus:outline-none cursor-pointer"
                >
                  {memberships.map((m) => (
                    <option key={m.organization_id} value={m.organization_id} className="bg-slate-900 text-slate-200">
                      {m.organization?.name || `Org ${m.organization_id.substring(0, 8)}`}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* User Profile Info & Logout */}
            {user ? (
              <div className="flex items-center space-x-3 border-l border-slate-800/80 pl-4">
                <div className="flex items-center space-x-2">
                  <div className="w-7 h-7 rounded-full bg-indigo-950 border border-indigo-800 flex items-center justify-center text-indigo-300 font-semibold text-xs">
                    <User className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-xs font-medium text-slate-300 hidden md:inline max-w-[140px] truncate">
                    {user.email}
                  </span>
                </div>
                <button
                  onClick={logout}
                  className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-md transition"
                  title="Sign Out"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <Link
                href="/auth/login"
                className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow-md shadow-indigo-600/30 transition"
              >
                Sign In
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}

