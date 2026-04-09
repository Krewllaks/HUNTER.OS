"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/hooks/useI18n";
import {
  Zap, Plus, Play, Pause, BarChart3, ChevronRight,
  Mail, Linkedin, Clock, ArrowRight, Loader2, AlertCircle, X,
  Users, MessageSquare, TrendingUp,
} from "lucide-react";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Campaign = any;

function ChannelIcon({ channel }: { channel: string }) {
  const icons: Record<string, React.ReactNode> = {
    email: <Mail size={14} className="text-text-secondary" />,
    linkedin_visit: <Linkedin size={14} className="text-blue-500" />,
    linkedin_connect: <Linkedin size={14} className="text-blue-600" />,
    linkedin_dm: <Linkedin size={14} className="text-blue-700" />,
  };
  return <>{icons[channel] || <Mail size={14} />}</>;
}

export default function CampaignsPage() {
  const { t } = useI18n();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [analyticsModal, setAnalyticsModal] = useState<Campaign | null>(null);

  const fetchCampaigns = useCallback(async () => {
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const res = (await api.campaigns.list()) as any;
      setCampaigns(res.campaigns || []);
    } catch (err) {
      console.error("Failed to fetch campaigns:", err);
      setError(t("common.noData"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  const handleActivate = async (id: number) => {
    setActionLoading(id);
    try {
      await api.campaigns.activate(id);
      await fetchCampaigns();
    } catch (err) {
      console.error("Activate failed:", err);
    } finally {
      setActionLoading(null);
    }
  };

  const handlePause = async (id: number) => {
    setActionLoading(id);
    try {
      await api.campaigns.pause(id);
      await fetchCampaigns();
    } catch (err) {
      console.error("Pause failed:", err);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-primary" size={32} />
      </div>
    );
  }

  return (
    <div className="space-y-grid-3 max-w-[1400px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-display-lg">{t("campaigns.title")}</h1>
          <p className="text-body-md text-text-secondary mt-1">
            {t("campaigns.subtitle")}
          </p>
        </div>
        <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
          <Plus size={16} />
          {t("campaigns.new")}
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-danger text-body-sm bg-red-50 p-3 rounded-sm">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* Campaign Cards */}
      {campaigns.length === 0 && !error ? (
        <div className="card text-center py-12">
          <Zap size={48} className="text-text-muted mx-auto mb-4" />
          <h3 className="font-display text-heading mb-2">{t("campaigns.noData")}</h3>
          <p className="text-body-md text-text-secondary">
            {t("campaigns.noDataDesc")}
          </p>
          <button
            className="btn-primary mt-4"
            onClick={() => setShowCreateModal(true)}
          >
            <Plus size={16} />
            {t("campaigns.new")}
          </button>
        </div>
      ) : (
        <div className="space-y-grid-2">
          {campaigns.map((camp: Campaign, i: number) => {
            const steps = camp.workflow_steps || [];
            const tags = camp.tags || [];

            return (
              <div
                key={camp.id}
                className="card stagger-item cursor-pointer hover:shadow-card-hover"
                style={{ animationDelay: `${i * 80}ms` }}
              >
                <div className="flex items-start justify-between mb-grid-2">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-display text-heading">{camp.name}</h3>
                      <span
                        className={`text-body-sm px-2 py-0.5 rounded-sm font-medium ${
                          camp.status === "active"
                            ? "bg-green-50 text-green-600"
                            : camp.status === "paused"
                            ? "bg-yellow-50 text-yellow-600"
                            : camp.status === "completed"
                            ? "bg-blue-50 text-blue-600"
                            : "bg-gray-50 text-gray-600"
                        }`}
                      >
                        {camp.status}
                      </span>
                    </div>
                    {camp.description && (
                      <p className="text-body-sm text-text-secondary mb-1">{camp.description}</p>
                    )}
                    <div className="flex gap-1">
                      {tags.map((tag: string) => (
                        <span key={tag} className="text-body-sm bg-background px-1.5 py-0.5 rounded text-text-muted">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-1">
                    {actionLoading === camp.id ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : camp.status === "active" ? (
                      <button
                        onClick={() => handlePause(camp.id)}
                        className="btn-ghost p-2"
                        title={t("campaigns.pause")}
                      >
                        <Pause size={16} />
                      </button>
                    ) : camp.status !== "completed" ? (
                      <button
                        onClick={() => handleActivate(camp.id)}
                        className="btn-ghost p-2 text-success"
                        title={t("campaigns.activate")}
                      >
                        <Play size={16} />
                      </button>
                    ) : null}
                    <button
                      className="btn-ghost p-2"
                      title={t("nav.analytics")}
                      onClick={() => setAnalyticsModal(camp)}
                    >
                      <BarChart3 size={16} />
                    </button>
                  </div>
                </div>

                {/* Stats Row */}
                <div className="grid grid-cols-5 gap-grid-2 mb-grid-2">
                  <div>
                    <div className="text-label text-text-muted">{t("campaigns.leads")}</div>
                    <div className="font-display text-display-sm">{camp.total_leads || 0}</div>
                  </div>
                  <div>
                    <div className="text-label text-text-muted">{t("campaigns.contacted")}</div>
                    <div className="font-display text-display-sm">{camp.total_contacted || 0}</div>
                  </div>
                  <div>
                    <div className="text-label text-text-muted">{t("campaigns.replied")}</div>
                    <div className="font-display text-display-sm text-success">{camp.total_replied || 0}</div>
                  </div>
                  <div>
                    <div className="text-label text-text-muted">{t("campaigns.meetings")}</div>
                    <div className="font-display text-display-sm text-primary">{camp.total_meetings || 0}</div>
                  </div>
                  <div>
                    <div className="text-label text-text-muted">{t("campaigns.replyRate")}</div>
                    <div className="font-display text-display-sm">{camp.reply_rate?.toFixed(1) || "0.0"}%</div>
                  </div>
                </div>

                {/* Workflow Steps */}
                {steps.length > 0 && (
                  <div className="flex items-center gap-1 py-grid-1 border-t border-border-light pt-grid-2">
                    <span className="text-label text-text-muted mr-2">{t("campaigns.workflow")}:</span>
                    {steps.map((step: { channel: string; delay_hours?: number }, j: number) => (
                      <div key={j} className="flex items-center gap-1">
                        <div className="flex items-center gap-1 bg-background px-2 py-1 rounded-sm">
                          <ChannelIcon channel={step.channel} />
                          <span className="text-body-sm">{step.channel.replace("_", " ")}</span>
                          {(step.delay_hours || 0) > 0 && (
                            <span className="text-body-sm text-text-muted flex items-center gap-0.5">
                              <Clock size={10} />{step.delay_hours}h
                            </span>
                          )}
                        </div>
                        {j < steps.length - 1 && <ArrowRight size={12} className="text-text-muted" />}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Create Campaign Modal */}
      {showCreateModal && (
        <CreateCampaignModal
          onClose={() => setShowCreateModal(false)}
          onCreated={() => {
            setShowCreateModal(false);
            fetchCampaigns();
          }}
        />
      )}

      {/* Analytics Modal */}
      {analyticsModal && (
        <CampaignAnalyticsModal
          campaign={analyticsModal}
          onClose={() => setAnalyticsModal(null)}
        />
      )}
    </div>
  );
}

function CreateCampaignModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const { t } = useI18n();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setCreating(true);
    setError("");
    try {
      await api.campaigns.create({
        name: name.trim(),
        description: description.trim() || undefined,
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        workflow_steps: [
          { step: 1, channel: "email", delay_hours: 0 },
          { step: 2, channel: "email", delay_hours: 72 },
          { step: 3, channel: "linkedin_connect", delay_hours: 48 },
        ],
      });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create campaign");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[100]">
      <div className="bg-surface rounded-lg shadow-xl w-full max-w-lg mx-4 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-display text-display-sm">{t("campaigns.new")}</h2>
          <button onClick={onClose} className="btn-ghost p-1">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-label text-text-muted mb-1">
              {t("campaigns.name")}
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-border rounded-sm text-body-sm focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder={t("campaigns.namePlaceholder")}
              autoFocus
            />
          </div>

          <div>
            <label className="block text-label text-text-muted mb-1">
              {t("campaigns.description")}
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-border rounded-sm text-body-sm focus:outline-none focus:ring-1 focus:ring-primary h-20 resize-none"
              placeholder={t("campaigns.descPlaceholder")}
            />
          </div>

          <div>
            <label className="block text-label text-text-muted mb-1">
              {t("campaigns.tags")}
            </label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-border rounded-sm text-body-sm focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder={t("campaigns.tagsPlaceholder")}
            />
          </div>

          {error && (
            <div className="text-danger text-body-sm flex items-center gap-1">
              <AlertCircle size={14} />
              {error}
            </div>
          )}

          <div className="flex gap-2 justify-end pt-2">
            <button type="button" onClick={onClose} className="btn-ghost px-4 py-2">
              {t("common.cancel")}
            </button>
            <button
              type="submit"
              disabled={!name.trim() || creating}
              className="btn-primary px-4 py-2 disabled:opacity-50"
            >
              {creating ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Plus size={16} />
              )}
              {t("campaigns.createBtn")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function CampaignAnalyticsModal({
  campaign,
  onClose,
}: {
  campaign: Campaign;
  onClose: () => void;
}) {
  const totalLeads = campaign.total_leads || 0;
  const contacted = campaign.total_contacted || 0;
  const replied = campaign.total_replied || 0;
  const meetings = campaign.total_meetings || 0;
  const replyRate = campaign.reply_rate?.toFixed(1) || "0.0";

  const funnel = [
    { label: "Leads", value: totalLeads, icon: Users, color: "text-blue-400", bg: "bg-blue-500/10" },
    { label: "Contacted", value: contacted, icon: Mail, color: "text-yellow-400", bg: "bg-yellow-500/10" },
    { label: "Replied", value: replied, icon: MessageSquare, color: "text-green-400", bg: "bg-green-500/10" },
    { label: "Meetings", value: meetings, icon: TrendingUp, color: "text-primary", bg: "bg-primary/10" },
  ];

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[100]" onClick={onClose}>
      <div
        className="bg-[#141414] border border-[#2A2A2A] rounded-lg shadow-2xl w-full max-w-lg mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-5 border-b border-[#2A2A2A]">
          <div>
            <h2 className="font-display text-lg font-bold">{campaign.name}</h2>
            <p className="text-sm text-[#9E9E9E]">Campaign Analytics</p>
          </div>
          <button onClick={onClose} className="btn-ghost p-1.5 hover:bg-white/5 rounded">
            <X size={18} />
          </button>
        </div>

        <div className="p-5 space-y-5">
          {/* Funnel */}
          <div className="grid grid-cols-4 gap-3">
            {funnel.map((step) => (
              <div key={step.label} className={`${step.bg} rounded-md p-3 text-center`}>
                <step.icon size={18} className={`${step.color} mx-auto mb-1`} />
                <p className="font-display text-xl font-bold">{step.value}</p>
                <p className="text-xs text-[#9E9E9E] uppercase tracking-wider">{step.label}</p>
              </div>
            ))}
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-[#1A1A1A] rounded-md p-4">
              <p className="text-xs text-[#9E9E9E] uppercase tracking-wider mb-1">Reply Rate</p>
              <p className="font-display text-2xl font-bold text-green-400">{replyRate}%</p>
            </div>
            <div className="bg-[#1A1A1A] rounded-md p-4">
              <p className="text-xs text-[#9E9E9E] uppercase tracking-wider mb-1">Status</p>
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-semibold uppercase ${
                  campaign.status === "active"
                    ? "bg-green-500/10 text-green-400"
                    : campaign.status === "paused"
                    ? "bg-yellow-500/10 text-yellow-400"
                    : "bg-gray-500/10 text-gray-400"
                }`}
              >
                {campaign.status}
              </span>
            </div>
          </div>

          {/* Workflow Steps */}
          {(campaign.workflow_steps || []).length > 0 && (
            <div>
              <p className="text-xs text-[#9E9E9E] uppercase tracking-wider mb-2">Workflow</p>
              <div className="flex items-center gap-2 flex-wrap">
                {(campaign.workflow_steps || []).map((step: { channel: string; delay_hours?: number }, j: number) => (
                  <div key={j} className="flex items-center gap-1">
                    <div className="bg-[#1A1A1A] border border-[#2A2A2A] px-3 py-1.5 rounded-md flex items-center gap-2 text-sm">
                      <span className="text-primary font-mono text-xs">#{j + 1}</span>
                      <span className="text-[#ccc]">{step.channel.replace("_", " ")}</span>
                      {(step.delay_hours || 0) > 0 && (
                        <span className="text-[#9E9E9E] flex items-center gap-0.5">
                          <Clock size={10} />{step.delay_hours}h
                        </span>
                      )}
                    </div>
                    {j < (campaign.workflow_steps || []).length - 1 && (
                      <ArrowRight size={12} className="text-[#333]" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {totalLeads === 0 && (
            <div className="bg-yellow-500/5 border border-yellow-500/10 rounded-md p-3">
              <p className="text-sm text-yellow-400">
                No leads assigned to this campaign yet. Add leads from the Leads page to start outreach.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
