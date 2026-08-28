import './globals.css';
import Providers from '@/lib/providers';

export const metadata = {
  title: 'InterviewIQ | AI-Powered Adaptive Technical Interviews',
  description: 'Enterprise production-grade technical interview platform grounded in role-specific knowledge bases and adaptive AI scoring.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased">
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
