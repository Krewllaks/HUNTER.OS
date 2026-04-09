"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { useHuntStream, HuntEvent } from "@/hooks/useHuntStream";
import {
  Crosshair,
  Globe,
  Linkedin,
  Search,
  Loader2,
  Zap,
  Brain,
  CheckCircle,
  AlertCircle,
  User,
  Building2,
  TrendingUp,
} from "lucide-react";

type Product = {
  id: number;
  name: string;
  description_prompt: string;
};

export default function HuntPage() {
  const { user } = useAuth();
  const {
    events,
    leadsFound,
    progress,
    status: streamStatus,
    connect,
    disconnect,
  } = useHuntStream();

  // Form state
  const [selectedProductId, setSelectedProductId] = useState<number | null>(null);
  const [domains, setDomains] = useState("");
  const [linkedinUrls, setLinkedinUrls] = useState("");
  const [icpDescription, setIcpDescription] = useState("");
  const [lookalikeCompany, setLookalikeCompany] = useState("");
  const [maxLeads, setMaxLeads] = useState(100);
  const [signals, setSignals] = useState<string[]>([
    "technographics",
    "hiring_intent",
    "news",
    "website_changes",
    "social_engagement",
    "content_intent",
  ]);

  // UI state
  const [products, setProducts] = useState<Product[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [huntResult, setHuntResult] = useState<{
    hunt_id: string;
    message: string;
    estimated_leads: number;
  } | null>(null);

  const allSignals = [
    { id: "technographics", label: "Technographics", desc: "Detect tech stack" },
    { id: "hiring_intent", label: "Hiring Intent", desc: "Job postings & team growth" },
    { id: "news", label: "News & Funding", desc: "Recent press mentions" },
    { id: "website_changes", label: "Website Changes", desc: "New pages & pricing updates" },
    { id: "social_engagement", label: "Social Radar", desc: "LinkedIn engagement tracking" },
    { id: "content_intent", label: "Content Intent", desc: "Blog, podcast, video analysis" },
  ];

  // Load products on mount
  useEffect(() => {
    async function loadProducts() {
      try {
        const data = (await api.products.list()) as { items?: Product[]; products?: Product[] } | Product[];
        const list = Array.isArray(data) ? data : data.items || data.products || [];
        setProducts(list);
        if (list.length > 0 && !selectedProductId) {
          setSelectedProductId(list[0].id);
        }
      } catch {
        // Products might not exist yet
      }
    }
    loadProducts();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleSignal = (id: string) => {
    setSignals((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  const isHunting = streamStatus === "connecting" || streamStatus === "streaming";

  const handleStartHunt = async () => {
    setError(null);

    // Validate inputs
    const targetDomains = domains
      .split("\n")
      .map((d) => d.trim())
      .filter(Boolean);
    const targetLinkedinUrls = linkedinUrls
      .split("\n")
      .map((u) => u.trim())
      .filter(Boolean);

    if (
      targetDomains.length === 0 &&
      targetLinkedinUrls.length === 0 &&
      !icpDescription &&
      !lookalikeCompany
    ) {
      setError("Please provide at least one target: domains, LinkedIn URLs, ICP description, or lookalike company.");
      return;
    }

    setIsSubmitting(true);
    setHuntResult(null);

    try {
      const result = (await api.hunt.start({
        target_domains: targetDomains,
        target_linkedin_urls: targetLinkedinUrls,
        icp_description: icpDescription || undefined,
        lookalike_company: lookalikeCompany || undefined,
        max_leads: maxLeads,
        signals_to_track: signals,
        auto_personalize: true,
        auto_score: true,
        campaign_id: undefined,
      })) as { hunt_id: string; status: string; message: string; estimated_leads: number };

      setHuntResult({
        hunt_id: result.hunt_id,
        message: result.message,
        estimated_leads: result.estimated_leads,
      });

      // Connect SSE stream if product is selected
      if (selectedProductId) {
        connect(selectedProductId);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Hunt failed to start";
      if (message.includes("402") || message.includes("Payment Required") || message.includes("plan")) {
        setError("Plan limit reached. Upgrade to continue hunting.");
      } else {
        setError(message);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStopHunt = () => {
    disconnect();
  };

  // Get recent lead_found events for display
  const foundLeads = events
    .filter((e) => e.type === "lead_found")
    .slice(-10)
    .reverse();

  return (
    <div className="space-y-grid-4 max-w-[900px]">
      {/* Header */}
      <div>
        <h1 className="font-display text-display-lg flex items-center gap-3">
          <Crosshair className="text-primary" size={32} />
          Start Hunt
        </h1>
        <p className="text-body-md text-text-secondary mt-1">
          Deploy the ARES research agent to find and enrich leads
        </p>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-md p-grid-2 flex items-center gap-2">
          <AlertCircle size={16} className="text-red-500 shrink-0" />
          <p className="text-body-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Product Selector */}
      {products.length > 0 && (
        <div className="card">
          <label className="text-label text-text-muted block mb-1">
            SELECT PRODUCT
          </label>
          <select
            value={selectedProductId ?? ""}
            onChange={(e) => setSelectedProductId(Number(e.target.value))}
            className="input w-full"
            disabled={isHunting}
          >
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Target Input */}
      <div className="card space-y-grid-3">
        <h2 className="font-display text-heading">Targets</h2>

        <div>
          <label className="text-label text-text-muted block mb-1">
            <Globe size={12} className="inline mr-1" />
            COMPANY DOMAINS
          </label>
          <textarea
            value={domains}
            onChange={(e) => setDomains(e.target.value)}
            placeholder={"techflow.com\ncloudnine.io\ngrowthlabs.co"}
            className="input min-h-[100px] resize-y font-mono text-body-sm"
            disabled={isHunting}
          />
          <p className="text-body-sm text-text-muted mt-1">One domain per line</p>
        </div>

        <div>
          <label className="text-label text-text-muted block mb-1">
            <Linkedin size={12} className="inline mr-1" />
            LINKEDIN PROFILE URLS
          </label>
          <textarea
            value={linkedinUrls}
            onChange={(e) => setLinkedinUrls(e.target.value)}
            placeholder={"https://linkedin.com/in/sarah-chen\nhttps://linkedin.com/in/marcus-weber"}
            className="input min-h-[100px] resize-y font-mono text-body-sm"
            disabled={isHunting}
          />
        </div>

        <div className="grid grid-cols-2 gap-grid-2">
          <div>
            <label className="text-label text-text-muted block mb-1">
              <Brain size={12} className="inline mr-1" />
              ICP DESCRIPTION
            </label>
            <textarea
              value={icpDescription}
              onChange={(e) => setIcpDescription(e.target.value)}
              placeholder="B2B SaaS companies, 10-50 employees, using WordPress but no CRM..."
              className="input min-h-[80px] resize-y text-body-sm"
              disabled={isHunting}
            />
          </div>
          <div>
            <label className="text-label text-text-muted block mb-1">
              <Search size={12} className="inline mr-1" />
              SEMANTIC LOOKALIKE
            </label>
            <input
              type="text"
              value={lookalikeCompany}
              onChange={(e) => setLookalikeCompany(e.target.value)}
              placeholder="e.g., HubSpot, Salesforce"
              className="input text-body-sm"
              disabled={isHunting}
            />
            <p className="text-body-sm text-text-muted mt-1">
              Find companies similar to this one
            </p>
          </div>
        </div>

        {/* Max Leads */}
        <div>
          <label className="text-label text-text-muted block mb-1">
            MAX LEADS
          </label>
          <input
            type="number"
            value={maxLeads}
            onChange={(e) => setMaxLeads(Math.max(1, Math.min(500, Number(e.target.value))))}
            className="input w-32 text-body-sm"
            min={1}
            max={500}
            disabled={isHunting}
          />
        </div>
      </div>

      {/* Signal Selection */}
      <div className="card space-y-grid-2">
        <h2 className="font-display text-heading">Intelligence Signals</h2>
        <p className="text-body-sm text-text-secondary">
          Select which signals ARES should track
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-grid-1">
          {allSignals.map((signal) => (
            <button
              key={signal.id}
              onClick={() => toggleSignal(signal.id)}
              disabled={isHunting}
              className={`text-left p-grid-2 rounded-md border transition-all ${
                signals.includes(signal.id)
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-accent"
              } ${isHunting ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              <div className="text-body-md font-medium">{signal.label}</div>
              <div className="text-body-sm text-text-muted">{signal.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Launch / Stop Button */}
      {isHunting ? (
        <button
          onClick={handleStopHunt}
          className="btn-primary w-full py-grid-2 text-heading bg-red-600 hover:bg-red-700"
        >
          Stop Hunt
        </button>
      ) : (
        <button
          onClick={handleStartHunt}
          disabled={isSubmitting}
          className="btn-primary w-full py-grid-2 text-heading disabled:opacity-60"
        >
          {isSubmitting ? (
            <>
              <Loader2 size={20} className="animate-spin" />
              Starting hunt...
            </>
          ) : (
            <>
              <Zap size={20} />
              Deploy ARES Agent
            </>
          )}
        </button>
      )}

      {/* Hunt Result Banner */}
      {huntResult && !isHunting && (
        <div className="bg-primary/10 border border-primary/30 rounded-md p-grid-2">
          <p className="text-body-md text-primary font-medium">
            {huntResult.message}
          </p>
          <p className="text-body-sm text-text-muted mt-1">
            Hunt ID: {huntResult.hunt_id} | Estimated: {huntResult.estimated_leads} leads
          </p>
        </div>
      )}

      {/* Live Progress Panel */}
      {(isHunting || streamStatus === "complete" || streamStatus === "error") && (
        <div className="card space-y-grid-2">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-heading flex items-center gap-2">
              {streamStatus === "complete" ? (
                <CheckCircle size={18} className="text-green-500" />
              ) : (
                <Loader2 size={18} className="animate-spin text-primary" />
              )}
              {streamStatus === "complete" ? "Hunt Complete" : "Hunt in Progress"}
            </h2>
            <div className="flex items-center gap-grid-2">
              <span className="text-body-sm text-text-muted">
                {leadsFound} leads found
              </span>
              <span className="text-body-sm font-mono text-primary">
                {progress}%
              </span>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-surface rounded-full h-2 overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Found Leads List */}
          {foundLeads.length > 0 && (
            <div className="space-y-1 mt-grid-2">
              <p className="text-label text-text-muted">RECENTLY FOUND</p>
              {foundLeads.map((event: HuntEvent, i: number) => (
                <div
                  key={`${event.timestamp}-${i}`}
                  className="flex items-center gap-grid-2 p-grid-1 rounded bg-surface/50 text-body-sm"
                >
                  <User size={14} className="text-text-muted shrink-0" />
                  <span className="font-medium">
                    {String(event.data.name || "Unknown")}
                  </span>
                  {typeof event.data.company === "string" && (
                    <>
                      <Building2 size={12} className="text-text-muted shrink-0" />
                      <span className="text-text-secondary">
                        {event.data.company}
                      </span>
                    </>
                  )}
                  {typeof event.data.score === "number" && (
                    <span className="ml-auto flex items-center gap-1 text-primary">
                      <TrendingUp size={12} />
                      {event.data.score}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Stream Status */}
          {streamStatus === "error" && (
            <div className="flex items-center gap-2 text-red-400 text-body-sm">
              <AlertCircle size={14} />
              Stream connection lost. Results are still being processed in the background.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
