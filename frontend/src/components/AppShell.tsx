"use client";

import { useState, useEffect, useCallback } from "react";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import Sidebar from "./Sidebar";
import UpgradeModal from "./UpgradeModal";

const PUBLIC_ROUTES = ["/login", "/register", "/", "/pricing"];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { isAuthenticated, isLoading } = useAuth();

  // Global 402 plan limit modal
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [upgradeMessage, setUpgradeMessage] = useState<string | undefined>();

  const handlePlanLimit = useCallback((e: Event) => {
    const detail = (e as CustomEvent).detail;
    setUpgradeMessage(detail?.message);
    setUpgradeOpen(true);
  }, []);

  useEffect(() => {
    window.addEventListener("hunter:plan-limit", handlePlanLimit);
    return () => window.removeEventListener("hunter:plan-limit", handlePlanLimit);
  }, [handlePlanLimit]);

  const isPublicRoute = PUBLIC_ROUTES.includes(pathname);

  // Public routes (landing, login, register, pricing) — no sidebar, no auth
  if (isPublicRoute) {
    return <>{children}</>;
  }

  // Premium splash screen while checking auth
  if (isLoading) {
    return (
      <>
        <style>{`
          @keyframes splash-bar {
            0%   { width: 0%; }
            20%  { width: 28%; }
            50%  { width: 58%; }
            75%  { width: 80%; }
            92%  { width: 94%; }
            100% { width: 100%; }
          }
          @keyframes splash-logo-in {
            0%   { opacity: 0; transform: translateY(14px) scale(0.90); }
            100% { opacity: 1; transform: translateY(0px)  scale(1); }
          }
          @keyframes splash-bar-track-in {
            0%   { opacity: 0; }
            60%  { opacity: 0; }
            100% { opacity: 1; }
          }
          .splash-bg {
            background: radial-gradient(ellipse at 62% 32%, #1c3160 0%, #0e1e3a 40%, #070e1f 100%);
            position: relative;
            overflow: hidden;
          }
          .splash-bg::before {
            content: '';
            position: absolute;
            inset: 0;
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.035'/%3E%3C/svg%3E");
            background-size: 220px 220px;
            pointer-events: none;
          }
          .splash-logo {
            animation: splash-logo-in 1s cubic-bezier(0.22, 1, 0.36, 1) both;
          }
          .splash-bar-track {
            animation: splash-bar-track-in 1.1s ease both;
          }
          .splash-bar-fill {
            animation: splash-bar 2.8s cubic-bezier(0.4, 0, 0.2, 1) 0.3s forwards;
          }
        `}</style>
        <div className="splash-bg min-h-screen flex flex-col items-center justify-center gap-0">

          {/* Logo */}
          <div className="splash-logo" style={{ marginBottom: 32 }}>
            <img src="/logo.png" style={{ width: 90, opacity: 0.85 }} />
          </div>

          {/* Progress bar — no labels */}
          <div
            className="splash-bar-track"
            style={{ width: 150, height: 1.5, background: 'rgba(255,255,255,0.10)', borderRadius: 2, overflow: 'hidden' }}
          >
            <div
              className="splash-bar-fill"
              style={{ height: '100%', background: 'rgba(255,255,255,0.60)', borderRadius: 2, width: 0 }}
            />
          </div>
        </div>
      </>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    return null;
  }

  // Authenticated layout with sidebar
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-sidebar p-grid-4 overflow-y-auto">
        {children}
      </main>
      <UpgradeModal
        isOpen={upgradeOpen}
        onClose={() => setUpgradeOpen(false)}
        reason="limit_reached"
        message={upgradeMessage}
      />
    </div>
  );
}
