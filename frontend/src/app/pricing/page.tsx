"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  Crosshair, ChevronRight, Lock, Shield, FileCheck,
  LayoutDashboard,
} from "lucide-react";

const PRICING_TABS = ["annual_prepaid", "annual_contract", "quarterly"] as const;
type BillingTab = (typeof PRICING_TABS)[number];

const TAB_LABELS: Record<BillingTab, string> = {
  annual_prepaid: "Annual Prepaid 20% OFF",
  annual_contract: "Annual Contract",
  quarterly: "Quarterly Bill",
};

const PRICES: Record<BillingTab, { monthly: number; note: string }> = {
  annual_prepaid: { monthly: 279, note: "Billed $3,348/year" },
  annual_contract: { monthly: 349, note: "Billed monthly, 12-month commitment" },
  quarterly: { monthly: 349, note: "Billed $1,047 every 3 months" },
};

const GROWTH_FEATURES = [
  "Unlimited Discovery Credits",
  "10k Researched Accounts/mo",
  "Advanced Predictive Scoring",
  "Custom CRM Integration",
  "Dedicated Success Manager",
];

const ENTERPRISE_FEATURES = [
  "Volume Discounts",
  "Custom Workflows",
  "On-Premise Deployment Options",
  "Dedicated Account Manager",
  "SLA & Priority Support",
];

export default function PricingPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const [billingTab, setBillingTab] = useState<BillingTab>("annual_prepaid");

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="min-h-screen bg-[#0D0D0D] text-white">
      {/* ── Navbar ──────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0D0D0D]/90 backdrop-blur-md border-b border-[#1A1A1A]">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Crosshair size={24} className="text-primary" />
            <span className="font-display text-xl font-bold tracking-tight">
              HUNTER<span className="text-primary">.OS</span>
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-8 text-sm text-[#9E9E9E]">
            <Link href="/#ares" className="hover:text-white transition-colors">Workflow</Link>
            <Link href="/pricing" className="text-white">Pricing</Link>
          </div>

          <div className="flex items-center gap-3">
            {isAuthenticated && (
              <button
                onClick={() => router.push("/dashboard")}
                className="text-sm text-[#9E9E9E] hover:text-white flex items-center gap-1 transition-colors"
              >
                <LayoutDashboard size={16} />
                Dashboard
              </button>
            )}
            <button
              onClick={() => router.push("/register")}
              className="bg-primary hover:bg-primary-hover text-white px-5 py-2 rounded-sm text-sm font-medium transition-colors"
            >
              Request Demo
            </button>
          </div>
        </div>
      </nav>

      {/* ── Main Content ────────────────────────────────── */}
      <section className="pt-32 pb-24 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="font-display text-4xl md:text-5xl font-bold tracking-tight mb-4">
              Transparent Pricing
            </h1>
            <p className="text-[#9E9E9E] text-lg">
              Scale your autonomous sales engine predictably.
            </p>
          </div>

          {/* Billing Tabs */}
          <div className="flex items-center justify-center gap-1 mb-10 bg-[#1A1A1A] rounded-sm p-1 max-w-fit mx-auto">
            {PRICING_TABS.map((tab) => (
              <button
                key={tab}
                onClick={() => setBillingTab(tab)}
                className={`px-4 py-2 rounded-sm text-sm font-medium transition-all ${
                  billingTab === tab
                    ? "bg-primary text-white"
                    : "text-[#9E9E9E] hover:text-white"
                }`}
              >
                {TAB_LABELS[tab]}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
            {/* Growth Plan */}
            <div className="rounded-lg border border-[#2A2A2A] bg-[#111] p-8">
              <div className="mb-6">
                <p className="text-label uppercase tracking-widest text-primary mb-2">GROWTH</p>
                <div className="flex items-baseline gap-1">
                  <span className="font-display text-5xl font-bold">${PRICES[billingTab].monthly}</span>
                  <span className="text-[#9E9E9E] text-sm">/mo</span>
                </div>
                <p className="text-[#9E9E9E] text-sm mt-1">{PRICES[billingTab].note}</p>
                {billingTab === "annual_prepaid" && (
                  <span className="inline-block mt-2 text-xs bg-green-500/10 text-green-400 px-2 py-0.5 rounded">
                    Save $840/year
                  </span>
                )}
              </div>

              <ul className="space-y-3 mb-8">
                {GROWTH_FEATURES.map((f) => (
                  <li key={f} className="flex items-center gap-3 text-sm text-[#ccc]">
                    <ChevronRight size={14} className="text-primary flex-shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>

              <button
                onClick={() => router.push("/register")}
                className="w-full bg-primary hover:bg-primary-hover text-white py-3 rounded-sm font-medium transition-colors"
              >
                Start Building Pipeline
              </button>
            </div>

            {/* Committed Spend */}
            <div className="rounded-lg border border-[#2A2A2A] bg-[#111] p-8 flex flex-col">
              <div className="mb-6">
                <p className="text-label uppercase tracking-widest text-[#9E9E9E] mb-2">COMMITTED SPEND</p>
                <h3 className="font-display text-3xl font-bold mb-2">Enterprise</h3>
                <p className="text-[#9E9E9E] text-sm">Volume-based pricing for teams at scale</p>
              </div>

              <ul className="space-y-3 mb-8 flex-1">
                {ENTERPRISE_FEATURES.map((f) => (
                  <li key={f} className="flex items-center gap-3 text-sm text-[#ccc]">
                    <ChevronRight size={14} className="text-[#9E9E9E] flex-shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>

              <button
                onClick={() => router.push("/register")}
                className="w-full border border-[#333] text-white py-3 rounded-sm font-medium hover:bg-[#1A1A1A] transition-colors"
              >
                Contact Sales
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────── */}
      <footer className="border-t border-[#1A1A1A] px-6 py-8">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Crosshair size={18} className="text-primary" />
            <span className="font-display font-bold text-sm">
              HUNTER<span className="text-primary">.OS</span>
            </span>
          </div>
          <p className="text-xs text-[#9E9E9E]">© 2026 HUNTER.OS Inc. All rights reserved.</p>
          <div className="flex items-center gap-6 text-xs text-[#9E9E9E]">
            <Link href="#" className="hover:text-white flex items-center gap-1"><Lock size={12} /> Privacy</Link>
            <Link href="#" className="hover:text-white flex items-center gap-1"><FileCheck size={12} /> Terms</Link>
            <Link href="#" className="hover:text-white flex items-center gap-1"><Shield size={12} /> Security</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
