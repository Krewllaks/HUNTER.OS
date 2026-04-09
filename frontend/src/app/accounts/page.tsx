"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import {
  Shield, Mail, Linkedin, Plus, Pause, Play,
  AlertTriangle, CheckCircle2, XCircle, Loader2, RefreshCw,
} from "lucide-react";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type EmailAccount = any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type LinkedInAccount = any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type HealthDashboard = any;

function HealthBar({ score }: { score: number }) {
  const color =
    score >= 80 ? "bg-success" : score >= 50 ? "bg-warning" : "bg-danger";
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-2 bg-border-light rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-body-sm font-mono">{score}%</span>
    </div>
  );
}

function DnsCheck({ valid }: { valid: boolean }) {
  return valid ? (
    <CheckCircle2 size={14} className="text-success" />
  ) : (
    <XCircle size={14} className="text-danger" />
  );
}

export default function AccountsPage() {
  const [health, setHealth] = useState<HealthDashboard | null>(null);
  const [emailAccounts, setEmailAccounts] = useState<EmailAccount[]>([]);
  const [linkedinAccounts, setLinkedinAccounts] = useState<LinkedInAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [healthRes, emailRes, linkedinRes] = await Promise.all([
        api.accounts.health(),
        api.accounts.emailList(),
        api.accounts.linkedinList(),
      ]);
      setHealth(healthRes);
      setEmailAccounts(Array.isArray(emailRes) ? emailRes : (healthRes as HealthDashboard)?.email_accounts || []);
      setLinkedinAccounts(Array.isArray(linkedinRes) ? linkedinRes : (healthRes as HealthDashboard)?.linkedin_accounts || []);
    } catch (err) {
      console.error("Failed to fetch accounts:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handlePause = async (id: number) => {
    setActionLoading(id);
    try {
      await api.accounts.emailPause(id);
      await fetchData();
    } catch (err) {
      console.error("Pause failed:", err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleResume = async (id: number) => {
    setActionLoading(id);
    try {
      await api.accounts.emailResume(id);
      await fetchData();
    } catch (err) {
      console.error("Resume failed:", err);
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

  const totalSentToday = health?.total_sent_today || emailAccounts.reduce((a: number, b: EmailAccount) => a + (b.total_sent_today || 0), 0);
  const totalCapacity = health?.total_daily_capacity || emailAccounts.filter((a: EmailAccount) => !a.is_paused).reduce((a: number, b: EmailAccount) => a + (b.daily_send_limit || 0), 0);
  const avgHealth = health?.avg_email_health || (emailAccounts.length > 0 ? Math.round(emailAccounts.reduce((a: number, b: EmailAccount) => a + (b.health_score || 0), 0) / emailAccounts.length) : 0);

  return (
    <div className="space-y-grid-4 max-w-[1400px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-display-lg flex items-center gap-3">
            <Shield className="text-primary" size={28} />
            Account Health
          </h1>
          <p className="text-body-md text-text-secondary mt-1">
            Monitor deliverability and manage connected accounts
          </p>
        </div>
        <button onClick={() => fetchData()} className="btn-ghost p-2">
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Health Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-grid-2">
        <div className="kpi-card">
          <div className="kpi-label">EMAIL ACCOUNTS</div>
          <div className="kpi-value">{health?.total_email_accounts || emailAccounts.length}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">AVG HEALTH</div>
          <div className={`kpi-value ${avgHealth >= 80 ? "text-success" : avgHealth >= 50 ? "text-warning" : "text-danger"}`}>
            {avgHealth}%
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">SENT TODAY</div>
          <div className="kpi-value">{totalSentToday}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">DAILY CAPACITY</div>
          <div className="kpi-value">{totalCapacity}</div>
        </div>
      </div>

      {/* Warnings */}
      {health?.warnings && health.warnings.length > 0 && (
        <div className="space-y-1">
          {health.warnings.map((w: string, i: number) => (
            <div key={i} className="flex items-center gap-2 text-warning text-body-sm bg-yellow-50 p-3 rounded-sm">
              <AlertTriangle size={16} />
              {w}
            </div>
          ))}
        </div>
      )}

      {/* Email Accounts */}
      <div className="card space-y-grid-2">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-heading flex items-center gap-2">
            <Mail size={18} />
            Email Accounts
          </h2>
          <button className="btn-secondary text-body-sm">
            <Plus size={14} />
            Add Account
          </button>
        </div>

        {emailAccounts.length === 0 ? (
          <p className="text-text-muted text-body-sm py-4 text-center">Henüz email hesabı eklenmemiş</p>
        ) : (
          <div className="space-y-grid-1">
            {emailAccounts.map((acc: EmailAccount) => (
              <div
                key={acc.id}
                className={`p-grid-2 rounded-md border ${
                  acc.is_paused ? "border-danger/30 bg-red-50/30" : "border-border-light"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-body-md">{acc.email}</span>
                    <span className="text-body-sm bg-background px-1.5 py-0.5 rounded">{acc.provider}</span>
                    {acc.is_warming && (
                      <span className="text-body-sm bg-warning/10 text-warning px-1.5 py-0.5 rounded">
                        Warming (Day {acc.warmup_day}/14)
                      </span>
                    )}
                    {acc.is_paused && (
                      <span className="text-body-sm bg-danger/10 text-danger px-1.5 py-0.5 rounded flex items-center gap-1">
                        <AlertTriangle size={12} /> Paused
                        {acc.pause_reason && ` - ${acc.pause_reason}`}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    {actionLoading === acc.id ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : acc.is_paused ? (
                      <button onClick={() => handleResume(acc.id)} className="btn-ghost p-1 text-success" title="Resume">
                        <Play size={14} />
                      </button>
                    ) : (
                      <button onClick={() => handlePause(acc.id)} className="btn-ghost p-1" title="Pause">
                        <Pause size={14} />
                      </button>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-6 gap-grid-2 text-body-sm">
                  <div>
                    <span className="text-text-muted">Health</span>
                    <HealthBar score={acc.health_score || 0} />
                  </div>
                  <div>
                    <span className="text-text-muted">Sent Today</span>
                    <div className="font-medium">{acc.total_sent_today || 0} / {acc.daily_send_limit || 0}</div>
                  </div>
                  <div>
                    <span className="text-text-muted">Bounce Rate</span>
                    <div className={`font-medium ${(acc.bounce_rate || 0) > 5 ? "text-danger" : ""}`}>
                      {acc.bounce_rate?.toFixed(1) || "0.0"}%
                    </div>
                  </div>
                  <div>
                    <span className="text-text-muted">Spam Rate</span>
                    <div className={`font-medium ${(acc.spam_complaint_rate || 0) > 0.1 ? "text-danger" : ""}`}>
                      {acc.spam_complaint_rate?.toFixed(2) || "0.00"}%
                    </div>
                  </div>
                  <div>
                    <span className="text-text-muted">Open Rate</span>
                    <div className="font-medium">{acc.open_rate?.toFixed(1) || "0.0"}%</div>
                  </div>
                  <div className="flex gap-2">
                    <div className="flex items-center gap-1">
                      <DnsCheck valid={acc.spf_valid || false} /> <span className="text-text-muted">SPF</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <DnsCheck valid={acc.dkim_valid || false} /> <span className="text-text-muted">DKIM</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <DnsCheck valid={acc.dmarc_valid || false} /> <span className="text-text-muted">DMARC</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* LinkedIn Accounts */}
      <div className="card space-y-grid-2">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-heading flex items-center gap-2">
            <Linkedin size={18} />
            LinkedIn Accounts
          </h2>
          <button className="btn-secondary text-body-sm">
            <Plus size={14} />
            Add Account
          </button>
        </div>

        {linkedinAccounts.length === 0 ? (
          <p className="text-text-muted text-body-sm py-4 text-center">Henüz LinkedIn hesabı eklenmemiş</p>
        ) : (
          linkedinAccounts.map((acc: LinkedInAccount) => (
            <div key={acc.id} className="p-grid-2 rounded-md border border-border-light">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-body-md">{acc.linkedin_email}</span>
                  {acc.is_warming && (
                    <span className="text-body-sm bg-warning/10 text-warning px-1.5 py-0.5 rounded">Warming</span>
                  )}
                  {acc.is_paused && (
                    <span className="text-body-sm bg-danger/10 text-danger px-1.5 py-0.5 rounded">Paused</span>
                  )}
                </div>
                <HealthBar score={acc.health_score || 0} />
              </div>
              <div className="grid grid-cols-3 gap-grid-2 text-body-sm">
                <div>
                  <span className="text-text-muted">Connections</span>
                  <div className="font-medium">{acc.connections_sent_today || 0} / {acc.daily_connection_limit || 25}</div>
                </div>
                <div>
                  <span className="text-text-muted">Messages</span>
                  <div className="font-medium">{acc.messages_sent_today || 0} / {acc.daily_message_limit || 20}</div>
                </div>
                <div>
                  <span className="text-text-muted">Profile Visits</span>
                  <div className="font-medium">{acc.visits_today || 0} / {acc.daily_visit_limit || 50}</div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
