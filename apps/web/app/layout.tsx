import React from 'react';
import './globals.css';
import { Providers } from '@/lib/providers';
import { Navbar } from '@/components/Navbar';

export const metadata = {
  title: 'InterviewIQ — AI Adaptive Interview & Recruiter Command Center',
  description: 'Enterprise AI Technical Interview & Recruiter Decision Support Platform',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
        <Providers>
          <Navbar />
          <main className="flex-1 w-full">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
