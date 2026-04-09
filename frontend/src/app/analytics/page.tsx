"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import {
  BarChart3, TrendingUp, Users, CalendarCheck,
  DollarSign, Loader2, AlertCircle,
} from "lucide-react";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type DashboardData = any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ScoringData = any;

export default function AnalyticsPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [scoring, setScoring] = useState<ScoringData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchData = useCallback(async () => {
    try {
      const [dashRes, scoreRes] = await Promise.all([
        api.analytics.dashboard(),
        api.analytics.scoringDistribution(),
      ]);
      setData(dashRes);
      setScoring(scoreRes);
    } catch (err) {
      console.error("Failed to fetch analytics:", err);
      setError("Analitik veriler yüklenemedi");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-primary" size={32} />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex items-center gap-2 text-danger text-body-sm bg-red-50 p-3 rounded-sm">
        <AlertCircle size={16} />
        {error || "Veri yüklenemedi"}
      </div>
    );
  }

  const overview = data.overview || {};
  const sentiment = data.sentiment || { positive: 0, negative: 0, neutral: 0 };
  const totalSentiment = sentiment.positive + sentiment.negative + sentiment.neutral;

  // Build funnel from overview data
  const funnel = [
    { stage: "Total Leads", count: overview.total_leads || 0, pct: 100 },
    { stage: "Contacted", count: overview.contacted || 0, pct: overview.total_leads ? Math.round((overview.contacted / overview.total_leads) * 100) : 0 },
    { stage: "Replied", count: overview.replied || 0, pct: overview.total_leads ? Math.round((overview.replied / overview.total_leads) * 100) : 0 },
    { stage: "Meetings", count: overview.meetings || 0, pct: overview.total_leads ? Math.round((overview.meetings / overview.total_leads) * 100) : 0 },
    { stage: "Won", count: overview.won || 0, pct: overview.total_leads ? Math.round((overview.won / overview.total_leads) * 100) : 0 },
  ];

  const scoringDist = scoring?.distribution || { hot: 0, warm: 0, cool: 0, cold: 0 };

  return (
    <div className="space-y-grid-4 max-w-[1400px]">
      {/* Header */}
      <div>
        <h1 className="font-display text-display-lg flex items-center gap-3">
          <BarChart3 className="text-primary" size={28} />
          Analytics
        </h1>
        <p className="text-body-md text-text-secondary mt-1">
          ROI tracking and performance intelligence
        </p>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-grid-2">
        <div className="kpi-card stagger-item">
          <Users size={16} className="text-text-muted" />
          <div className="kpi-value">{(overview.total_leads || 0).toLocaleString()}</div>
          <div className="kpi-label">TOTAL LEADS</div>
        </div>
        <div className="kpi-card stagger-item" style={{ animationDelay: "60ms" }}>
          <TrendingUp size={16} className="text-success" />
          <div className="kpi-value">{overview.reply_rate?.toFixed(1) || "0.0"}%</div>
          <div className="kpi-label">REPLY RATE</div>
        </div>
        <div className="kpi-card stagger-item" style={{ animationDelay: "120ms" }}>
          <CalendarCheck size={16} className="text-primary" />
          <div className="kpi-value">{overview.meetings || 0}</div>
          <div className="kpi-label">MEETINGS BOOKED</div>
        </div>
        <div className="kpi-card stagger-item" style={{ animationDelay: "180ms" }}>
          <DollarSign size={16} className="text-chart-1" />
          <div className="kpi-value">${(data.revenue?.total_attributed || 0).toLocaleString()}</div>
          <div className="kpi-label">REVENUE ATTRIBUTED</div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-grid-3">
        {/* Funnel */}
        <div className="card">
          <h2 className="font-display text-heading mb-grid-3">Conversion Funnel</h2>
          <div className="space-y-2">
            {funnel.map((stage, i) => (
              <div key={stage.stage} className="stagger-item" style={{ animationDelay: `${i * 50}ms` }}>
                <div className="flex items-center justify-between text-body-md mb-1">
                  <span className="font-medium">{stage.stage}</span>
                  <span className="text-text-secondary">
                    {stage.count.toLocaleString()} <span className="text-text-muted">({stage.pct}%)</span>
                  </span>
                </div>
                <div className="w-full h-6 bg-border-light rounded-sm overflow-hidden">
                  <div
                    className="h-full bg-primary/80 rounded-sm transition-all duration-500"
                    style={{ width: `${Math.max(stage.pct, 1)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Additional Stats */}
        <div className="card">
          <h2 className="font-display text-heading mb-grid-3">Performance Summary</h2>
          <div className="space-y-grid-2">
            <div className="grid grid-cols-2 gap-grid-2">
              <div className="p-grid-2 bg-background rounded-md">
                <div className="text-label text-text-muted">MEETING RATE</div>
                <div className="font-display text-display-sm text-primary">{overview.meeting_rate?.toFixed(1) || "0.0"}%</div>
              </div>
              <div className="p-grid-2 bg-background rounded-md">
                <div className="text-label text-text-muted">WIN RATE</div>
                <div className="font-display text-display-sm text-success">{overview.win_rate?.toFixed(1) || "0.0"}%</div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-grid-2">
              <div className="p-grid-2 bg-background rounded-md">
                <div className="text-label text-text-muted">OUTBOUND MESSAGES</div>
                <div className="font-display text-display-sm">{data.messages?.total_outbound || 0}</div>
              </div>
              <div className="p-grid-2 bg-background rounded-md">
                <div className="text-label text-text-muted">INBOUND REPLIES</div>
                <div className="font-display text-display-sm">{data.messages?.total_inbound || 0}</div>
              </div>
            </div>
            <div className="p-grid-2 bg-background rounded-md">
              <div className="text-label text-text-muted">ACTIVE CAMPAIGNS</div>
              <div className="font-display text-display-sm">{data.campaigns?.active || 0}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Scoring Distribution + Sentiment */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-grid-3">
        <div className="card">
          <h2 className="font-display text-heading mb-grid-2">Lead Scoring Distribution</h2>
          <div className="grid grid-cols-4 gap-grid-2">
            {[
              { label: "Hot (75+)", count: scoringDist.hot, color: "text-primary" },
              { label: "Warm (50-74)", count: scoringDist.warm, color: "text-warning" },
              { label: "Cool (25-49)", count: scoringDist.cool, color: "text-chart-2" },
              { label: "Cold (<25)", count: scoringDist.cold, color: "text-text-muted" },
            ].map((bucket) => (
              <div key={bucket.label} className="text-center">
                <div className={`font-display text-display-sm ${bucket.color}`}>
                  {bucket.count}
                </div>
                <div className="text-body-sm text-text-muted">{bucket.label}</div>
              </div>
            ))}
          </div>
          <div className="mt-grid-2 flex justify-between text-body-sm text-text-secondary border-t border-border-light pt-grid-1">
            <span>Avg Score: <strong>{scoring?.avg_score?.toFixed(1) || "0.0"}</strong></span>
            <span>Avg Confidence: <strong>{scoring?.avg_confidence?.toFixed(1) || "0.0"}%</strong></span>
          </div>
        </div>

        <div className="card">
          <h2 className="font-display text-heading mb-grid-2">Reply Sentiment</h2>
          <div className="grid grid-cols-3 gap-grid-2 mb-grid-2">
            <div className="text-center p-grid-2 bg-green-50 rounded-md">
              <div className="font-display text-display-sm text-success">{sentiment.positive}</div>
              <div className="text-body-sm text-green-700">Positive</div>
            </div>
            <div className="text-center p-grid-2 bg-red-50 rounded-md">
              <div className="font-display text-display-sm text-danger">{sentiment.negative}</div>
              <div className="text-body-sm text-red-700">Negative</div>
            </div>
            <div className="text-center p-grid-2 bg-gray-50 rounded-md">
              <div className="font-display text-display-sm text-text-muted">{sentiment.neutral}</div>
              <div className="text-body-sm text-text-secondary">Neutral</div>
            </div>
          </div>
          <p className="text-body-sm text-text-secondary">
            {totalSentiment > 0
              ? `${Math.round((sentiment.positive / totalSentiment) * 100)}% of replies are positive`
              : "Henüz cevap verisi yok"}
          </p>
        </div>
      </div>
    </div>
  );
}
