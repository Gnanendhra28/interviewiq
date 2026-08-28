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
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 min-h-screen flex flex-col font-sans">
        <Providers>
          <Navbar />
          <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
