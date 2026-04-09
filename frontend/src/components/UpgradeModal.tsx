"use client";

import { useRouter } from "next/navigation";
import { X, Crown, ArrowRight, TrendingUp } from "lucide-react";

interface UpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  reason?: string;
  message?: string;
  missedLeads?: number;
}

export default function UpgradeModal({
  isOpen,
  onClose,
  reason = "limit_reached",
  message,
  missedLeads,
}: UpgradeModalProps) {
  const router = useRouter();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      <div className="relative bg-background border border-border rounded-sm p-grid-6 max-w-md w-full mx-4 animate-in">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-text-muted hover:text-text"
        >
          <X size={20} />
        </button>

        <div className="text-center mb-grid-4">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary/10 mb-grid-3">
            <Crown size={24} className="text-primary" />
          </div>

          <h2 className="font-display text-display-sm mb-grid-2">
            {reason === "trial_expired"
              ? "Deneme Süreniz Doldu"
              : reason === "feature_locked"
              ? "Bu Özellik Pro Planda"
              : "Limitinize Ulaştınız"}
          </h2>

          <p className="text-body-md text-text-secondary">
            {message || "Pro plana geçerek sınırsız kullanıma erişin."}
          </p>
        </div>

        {/* FOMO: Missed leads count */}
        {missedLeads && missedLeads > 0 && (
          <div className="bg-danger/10 border border-danger/20 rounded-sm p-grid-3 mb-grid-4">
            <div className="flex items-center gap-2 text-danger">
              <TrendingUp size={16} />
              <span className="text-body-sm font-medium">
                Son 7 günde kaçırdığınız {missedLeads} potansiyel müşteri var!
              </span>
            </div>
          </div>
        )}

        {/* Pro benefits */}
        <div className="space-y-2 mb-grid-4">
          {[
            "Sınırsız lead keşfi",
            "Sınırsız kişiselleştirilmiş mesaj",
            "LinkedIn otomasyonu",
            "Email gönderim + tracking",
            "Detaylı analitik dashboard",
          ].map((benefit) => (
            <div key={benefit} className="flex items-center gap-2 text-body-sm">
              <div className="w-1.5 h-1.5 rounded-full bg-primary" />
              {benefit}
            </div>
          ))}
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => router.push("/pricing")}
            className="btn-primary flex-1 flex items-center justify-center gap-2"
          >
            Pro&apos;ya Geç — $49/ay
            <ArrowRight size={14} />
          </button>
        </div>

        <p className="text-center text-body-xs text-text-muted mt-grid-3">
          14 gün içinde iptal edebilirsiniz. Taahhüt yok.
        </p>
      </div>
    </div>
  );
}
