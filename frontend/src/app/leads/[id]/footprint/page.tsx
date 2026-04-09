"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import {
  ArrowLeft,
  Globe,
  Loader2,
  RefreshCw,
  ExternalLink,
  User,
  Building2,
  TrendingUp,
  Code,
  PenTool,
  Briefcase,
  Search,
  Zap,
} from "lucide-react";

type SocialProfile = {
  platform: string;
  url: string;
  username: string;
  verified: boolean;
  category: string;
  sales_relevance: number;
};

type DossierData = {
  lead_id: number;
  lead_name: string;
  lead_company: string | null;
  profiles: SocialProfile[];
  footprint_score: number;
  total_platforms: number;
  active_categories: string[];
  primary_platform: string | null;
  content_creator: boolean;
  tech_oriented: boolean;
  scanned_at: string | null;
};

const CATEGORY_ICONS: Record<string, typeof Globe> = {
  developer: Code,
  design: PenTool,
  professional: Briefcase,
  startup: Zap,
  business: Building2,
  social: User,
  content: PenTool,
  default: Globe,
};

const CATEGORY_COLORS: Record<string, string> = {
  developer: "text-green-400 bg-green-500/10 border-green-500/30",
  design: "text-purple-400 bg-purple-500/10 border-purple-500/30",
  professional: "text-blue-400 bg-blue-500/10 border-blue-500/30",
  startup: "text-orange-400 bg-orange-500/10 border-orange-500/30",
  business: "text-cyan-400 bg-cyan-500/10 border-cyan-500/30",
  social: "text-pink-400 bg-pink-500/10 border-pink-500/30",
  content: "text-yellow-400 bg-yellow-500/10 border-yellow-500/30",
  default: "text-text-muted bg-surface border-border",
};

function getScoreColor(score: number): string {
  if (score >= 70) return "text-green-400";
  if (score >= 40) return "text-yellow-400";
  return "text-red-400";
}

function getScoreLabel(score: number): string {
  if (score >= 70) return "Strong";
  if (score >= 40) return "Moderate";
  return "Weak";
}

export default function FootprintPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const leadId = Number(params.id);

  const [dossier, setDossier] = useState<DossierData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isScanning, setIsScanning] = useState(false);
  const [isEnriching, setIsEnriching] = useState(false);
  const [enrichResult, setEnrichResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDossier();
  }, [leadId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function loadDossier() {
    setIsLoading(true);
    setError(null);
    try {
      const data = (await api.footprint.dossier(leadId)) as DossierData;
      setDossier(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load dossier";
      if (msg.includes("404")) {
        // No scan yet, show empty state
        setDossier(null);
      } else {
        setError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }

  async function handleScan() {
    setIsScanning(true);
    setError(null);
    try {
      await api.footprint.scan(leadId);
      await loadDossier();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Scan failed";
      if (msg.includes("402")) {
        setError("Plan limit reached. Upgrade to scan more leads.");
      } else {
        setError(msg);
      }
    } finally {
      setIsScanning(false);
    }
  }

  async function handleEnrich() {
    setIsEnriching(true);
    setError(null);
    setEnrichResult(null);
    try {
      const result = (await api.footprint.enrich(leadId)) as Record<string, unknown>;
      setEnrichResult(result);
      await loadDossier(); // Refresh dossier with enriched data
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Enrichment failed";
      setError(msg);
    } finally {
      setIsEnriching(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 size={32} className="animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-grid-4 max-w-[900px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={() => router.back()}
            className="text-body-sm text-text-muted hover:text-text-primary flex items-center gap-1 mb-2"
          >
            <ArrowLeft size={14} /> Back to leads
          </button>
          <h1 className="font-display text-display-lg flex items-center gap-3">
            <Search className="text-primary" size={28} />
            Digital Dossier
          </h1>
          {dossier && (
            <p className="text-body-md text-text-secondary mt-1">
              {dossier.lead_name}
              {dossier.lead_company && ` at ${dossier.lead_company}`}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {dossier && (
            <button
              onClick={handleEnrich}
              disabled={isEnriching}
              className="btn-secondary flex items-center gap-2"
            >
              {isEnriching ? (
                <>
                  <Loader2 size={16} className="animate-spin" /> Enriching...
                </>
              ) : (
                <>
                  <Zap size={16} /> Enrich
                </>
              )}
            </button>
          )}
          <button
            onClick={handleScan}
            disabled={isScanning}
            className="btn-primary flex items-center gap-2"
          >
            {isScanning ? (
              <>
                <Loader2 size={16} className="animate-spin" /> Scanning...
              </>
            ) : dossier?.scanned_at ? (
              <>
                <RefreshCw size={16} /> Re-scan
              </>
            ) : (
              <>
                <Search size={16} /> Scan Footprint
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-md p-grid-2 text-body-sm text-red-400">
          {error}
        </div>
      )}

      {/* Enrichment Result */}
      {enrichResult && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-md p-grid-2 text-body-sm text-green-400">
          Enrichment complete — {((enrichResult.providers_used as string[]) || []).length} providers used,
          score: {String(enrichResult.final_score ?? "N/A")}
        </div>
      )}

      {/* Empty State */}
      {!dossier && !error && (
        <div className="card text-center py-grid-6">
          <Globe size={48} className="text-text-muted mx-auto mb-grid-2" />
          <h2 className="font-display text-heading mb-1">No Scan Results</h2>
          <p className="text-body-md text-text-secondary mb-grid-3">
            Run a digital footprint scan to discover this lead&apos;s social profiles
            across 50+ platforms.
          </p>
          <button
            onClick={handleScan}
            disabled={isScanning}
            className="btn-primary mx-auto"
          >
            {isScanning ? (
              <>
                <Loader2 size={16} className="animate-spin" /> Scanning...
              </>
            ) : (
              <>
                <Search size={16} /> Start Scan
              </>
            )}
          </button>
        </div>
      )}

      {/* Dossier Content */}
      {dossier && (
        <>
          {/* Score & Stats Bar */}
          <div className="grid grid-cols-4 gap-grid-2">
            <div className="card text-center">
              <p className={`text-display-lg font-display ${getScoreColor(dossier.footprint_score)}`}>
                {dossier.footprint_score}
              </p>
              <p className="text-body-sm text-text-muted">
                Footprint Score ({getScoreLabel(dossier.footprint_score)})
              </p>
            </div>
            <div className="card text-center">
              <p className="text-display-lg font-display text-primary">
                {dossier.total_platforms}
              </p>
              <p className="text-body-sm text-text-muted">Platforms Found</p>
            </div>
            <div className="card text-center">
              <p className="text-display-lg font-display">
                {dossier.active_categories.length}
              </p>
              <p className="text-body-sm text-text-muted">Categories</p>
            </div>
            <div className="card text-center">
              <div className="flex justify-center gap-2 mt-1">
                {dossier.tech_oriented && (
                  <span className="text-body-sm px-2 py-0.5 rounded bg-green-500/10 text-green-400 border border-green-500/30">
                    Tech
                  </span>
                )}
                {dossier.content_creator && (
                  <span className="text-body-sm px-2 py-0.5 rounded bg-yellow-500/10 text-yellow-400 border border-yellow-500/30">
                    Creator
                  </span>
                )}
                {!dossier.tech_oriented && !dossier.content_creator && (
                  <span className="text-body-sm px-2 py-0.5 rounded bg-surface text-text-muted border border-border">
                    General
                  </span>
                )}
              </div>
              <p className="text-body-sm text-text-muted mt-1">Profile Type</p>
            </div>
          </div>

          {/* Primary Platform */}
          {dossier.primary_platform && (
            <div className="bg-primary/5 border border-primary/20 rounded-md p-grid-2 flex items-center gap-2">
              <TrendingUp size={16} className="text-primary" />
              <span className="text-body-md">
                Primary platform: <strong>{dossier.primary_platform}</strong>
              </span>
            </div>
          )}

          {/* Social Profiles Grid */}
          <div className="card">
            <h2 className="font-display text-heading mb-grid-2">
              Discovered Profiles
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-grid-2">
              {dossier.profiles.map((profile) => {
                const cat = profile.category || "default";
                const IconComp = CATEGORY_ICONS[cat] || CATEGORY_ICONS.default;
                const colorClass = CATEGORY_COLORS[cat] || CATEGORY_COLORS.default;

                return (
                  <a
                    key={profile.platform}
                    href={profile.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`flex items-center gap-grid-2 p-grid-2 rounded-md border transition-all hover:opacity-80 ${colorClass}`}
                  >
                    <IconComp size={20} />
                    <div className="flex-1 min-w-0">
                      <div className="text-body-md font-medium">
                        {profile.platform}
                      </div>
                      <div className="text-body-sm opacity-70 truncate">
                        @{profile.username}
                      </div>
                    </div>
                    <ExternalLink size={14} className="opacity-50 shrink-0" />
                  </a>
                );
              })}
            </div>
          </div>

          {/* Scan Info */}
          {dossier.scanned_at && (
            <p className="text-body-sm text-text-muted text-right">
              Last scanned: {new Date(dossier.scanned_at).toLocaleString()}
            </p>
          )}
        </>
      )}
    </div>
  );
}
