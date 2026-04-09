"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import {
  Search,
  Download,
  ExternalLink,
  MoreVertical,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Crosshair,
  Mail,
  Trash2,
  MessageSquare,
  Eye,
  FileText,
  FileSpreadsheet,
  Fingerprint,
  X,
} from "lucide-react";
import Link from "next/link";

type Lead = {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  linkedin_url: string | null;
  company_name: string;
  company_domain: string;
  title: string;
  industry: string;
  intent_score: number;
  confidence: number;
  status: string;
  sentiment: string | null;
  technographics: string[];
  hiring_signals: { role: string }[];
  social_engagement: string[];
  notes: string | null;
  source: string;
  created_at: string;
};

type LeadListResponse = {
  leads: Lead[];
  total: number;
  page: number;
  per_page: number;
};

function ScoreBadge({ score }: { score: number }) {
  const level = score >= 75 ? "hot" : score >= 50 ? "warm" : score >= 25 ? "cool" : "cold";
  return <span className={`score-badge score-badge--${level}`}>{Math.round(score)}</span>;
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    new: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
    researched: "bg-purple-500/10 text-purple-400 border border-purple-500/20",
    contacted: "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20",
    replied: "bg-green-500/10 text-green-400 border border-green-500/20",
    meeting: "bg-primary/10 text-primary border border-primary/20",
    won: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
    lost: "bg-red-500/10 text-red-400 border border-red-500/20",
  };
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-semibold uppercase tracking-wide ${styles[status] || "bg-gray-500/10 text-gray-400 border border-gray-500/20"}`}>
      {status}
    </span>
  );
}

/* ── Actions Dropdown ─────────────────────────────────────── */
function ActionsDropdown({ lead, onAction }: { lead: Lead; onAction: (action: string, lead: Lead) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const actions = [
    { key: "view", label: "View Details", icon: Eye },
    { key: "email", label: "Send Email", icon: Mail },
    { key: "message", label: "Generate Message", icon: MessageSquare },
    ...(lead.linkedin_url ? [{ key: "linkedin", label: "Open LinkedIn", icon: ExternalLink }] : []),
    { key: "delete", label: "Delete Lead", icon: Trash2, danger: true },
  ];

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={(e) => { e.stopPropagation(); setOpen(!open); }}
        className="btn-ghost p-1.5 hover:bg-white/5 rounded"
        title="More Actions"
      >
        <MoreVertical size={14} />
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 w-48 bg-[#1A1A1A] border border-[#2A2A2A] rounded-md shadow-xl z-50 py-1 animate-in fade-in slide-in-from-top-1">
          {actions.map((action) => (
            <button
              key={action.key}
              onClick={(e) => {
                e.stopPropagation();
                setOpen(false);
                onAction(action.key, lead);
              }}
              className={`w-full flex items-center gap-2.5 px-3 py-2 text-sm transition-colors ${
                "danger" in action && action.danger
                  ? "text-red-400 hover:bg-red-500/10"
                  : "text-[#ccc] hover:bg-white/5"
              }`}
            >
              <action.icon size={14} />
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Export Dropdown ───────────────────────────────────────── */
function ExportDropdown({ leads, total }: { leads: Lead[]; total: number }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const exportCSV = () => {
    const headers = ["Name", "Email", "Company", "Title", "Industry", "Score", "Status", "LinkedIn", "Source"];
    const rows = leads.map((l) => [
      `${l.first_name} ${l.last_name}`,
      l.email || "",
      l.company_name || "",
      l.title || "",
      l.industry || "",
      String(l.intent_score),
      l.status,
      l.linkedin_url || "",
      l.source || "",
    ]);
    const csv = [headers, ...rows].map((r) => r.map((c) => `"${c.replace(/"/g, '""')}"`).join(",")).join("\n");
    downloadFile(csv, "leads.csv", "text/csv");
    setOpen(false);
  };

  const exportJSON = () => {
    const json = JSON.stringify(leads, null, 2);
    downloadFile(json, "leads.json", "application/json");
    setOpen(false);
  };

  const downloadFile = (content: string, filename: string, type: string) => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="btn-secondary flex items-center gap-2"
      >
        <Download size={16} />
        Export
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 w-56 bg-[#1A1A1A] border border-[#2A2A2A] rounded-md shadow-xl z-50 py-1 animate-in fade-in slide-in-from-top-1">
          <div className="px-3 py-2 border-b border-[#2A2A2A]">
            <p className="text-xs text-[#9E9E9E]">{total} leads available</p>
          </div>
          <button
            onClick={exportCSV}
            className="w-full flex items-center gap-2.5 px-3 py-2.5 text-sm text-[#ccc] hover:bg-white/5 transition-colors"
          >
            <FileSpreadsheet size={14} className="text-green-400" />
            Export as CSV
          </button>
          <button
            onClick={exportJSON}
            className="w-full flex items-center gap-2.5 px-3 py-2.5 text-sm text-[#ccc] hover:bg-white/5 transition-colors"
          >
            <FileText size={14} className="text-blue-400" />
            Export as JSON
          </button>
        </div>
      )}
    </div>
  );
}

/* ── Lead Detail Modal ────────────────────────────────────── */
function LeadDetailModal({ lead, onClose }: { lead: Lead; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[100]" onClick={onClose}>
      <div
        className="bg-[#141414] border border-[#2A2A2A] rounded-lg shadow-2xl w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-5 border-b border-[#2A2A2A]">
          <div>
            <h2 className="font-display text-lg font-bold">
              {lead.first_name} {lead.last_name}
            </h2>
            <p className="text-sm text-[#9E9E9E]">{lead.title} {lead.company_name ? `at ${lead.company_name}` : ""}</p>
          </div>
          <button onClick={onClose} className="btn-ghost p-1.5 hover:bg-white/5 rounded">
            <X size={18} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-[#9E9E9E] uppercase tracking-wider mb-1">Score</p>
              <ScoreBadge score={lead.intent_score} />
            </div>
            <div>
              <p className="text-xs text-[#9E9E9E] uppercase tracking-wider mb-1">Status</p>
              <StatusBadge status={lead.status} />
            </div>
            <div>
              <p className="text-xs text-[#9E9E9E] uppercase tracking-wider mb-1">Email</p>
              <p className="text-sm text-[#ccc]">{lead.email || "—"}</p>
            </div>
            <div>
              <p className="text-xs text-[#9E9E9E] uppercase tracking-wider mb-1">Industry</p>
              <p className="text-sm text-[#ccc]">{lead.industry || "—"}</p>
            </div>
            <div>
              <p className="text-xs text-[#9E9E9E] uppercase tracking-wider mb-1">Company Domain</p>
              <p className="text-sm text-[#ccc]">{lead.company_domain || "—"}</p>
            </div>
            <div>
              <p className="text-xs text-[#9E9E9E] uppercase tracking-wider mb-1">Source</p>
              <p className="text-sm text-[#ccc]">{lead.source || "—"}</p>
            </div>
          </div>

          {lead.linkedin_url && (
            <a
              href={lead.linkedin_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 transition-colors"
            >
              <ExternalLink size={14} />
              View LinkedIn Profile
            </a>
          )}

          {lead.notes && (
            <div>
              <p className="text-xs text-[#9E9E9E] uppercase tracking-wider mb-1">Notes</p>
              <p className="text-sm text-[#A3A3A3] leading-relaxed">{lead.notes}</p>
            </div>
          )}

          <div>
            <p className="text-xs text-[#9E9E9E] uppercase tracking-wider mb-1">Created</p>
            <p className="text-sm text-[#A3A3A3]">
              {new Date(lead.created_at).toLocaleDateString("tr-TR", {
                year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit",
              })}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [perPage] = useState(20);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStatus, setSelectedStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = {
        page,
        per_page: perPage,
        sort_by: "intent_score",
        sort_order: "desc",
      };
      if (searchQuery) params.search = searchQuery;
      if (selectedStatus) params.status = selectedStatus;

      const data = (await api.leads.list(params)) as LeadListResponse;
      setLeads(data.leads || []);
      setTotal(data.total || 0);
    } catch {
      setLeads([]);
    } finally {
      setLoading(false);
    }
  }, [page, perPage, searchQuery, selectedStatus]);

  useEffect(() => {
    const debounce = setTimeout(() => fetchLeads(), 300);
    return () => clearTimeout(debounce);
  }, [fetchLeads]);

  const handleAction = (action: string, lead: Lead) => {
    switch (action) {
      case "view":
        setSelectedLead(lead);
        break;
      case "email":
        if (lead.email) {
          window.open(`mailto:${lead.email}`, "_blank");
        }
        break;
      case "linkedin":
        if (lead.linkedin_url) {
          window.open(lead.linkedin_url, "_blank");
        }
        break;
      case "delete":
        if (confirm(`Delete ${lead.first_name} ${lead.last_name}?`)) {
          api.leads.delete(lead.id).then(() => fetchLeads()).catch(console.error);
        }
        break;
      case "message":
        setSelectedLead(lead);
        break;
    }
  };

  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="space-y-grid-3 max-w-[1400px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-display-lg">Leads</h1>
          <p className="text-body-md text-text-secondary mt-1">
            {total} leads in pipeline
          </p>
        </div>
        <div className="flex gap-grid-1">
          <ExportDropdown leads={leads} total={total} />
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-grid-2 items-center">
        <div className="relative flex-1 max-w-md">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            placeholder="Search leads..."
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
            className="input pl-9"
          />
        </div>
        <div className="flex gap-grid-1">
          {["new", "researched", "contacted", "replied", "meeting"].map((s) => (
            <button
              key={s}
              onClick={() => { setSelectedStatus(selectedStatus === s ? null : s); setPage(1); }}
              className={`btn text-body-sm ${selectedStatus === s ? "bg-primary text-white" : "bg-surface border border-border text-text-secondary hover:border-accent"}`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="table-container">
        {loading ? (
          <div className="flex items-center justify-center py-grid-8">
            <Loader2 size={24} className="animate-spin text-primary" />
          </div>
        ) : leads.length === 0 ? (
          <div className="py-grid-8 text-center">
            <Crosshair size={40} className="text-text-muted mx-auto mb-grid-2" />
            <p className="text-body-md text-text-muted mb-grid-2">No leads found</p>
            <p className="text-body-sm text-text-muted">
              Start a hunt from the Products page to discover leads
            </p>
          </div>
        ) : (
          <>
            <table className="w-full">
              <thead>
                <tr>
                  <th className="table-header text-left">Lead</th>
                  <th className="table-header text-left">Company</th>
                  <th className="table-header text-center">Score</th>
                  <th className="table-header text-center">Status</th>
                  <th className="table-header text-left">Source</th>
                  <th className="table-header text-left">Notes</th>
                  <th className="table-header text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead, i) => (
                  <tr
                    key={lead.id}
                    className="table-row stagger-item cursor-pointer hover:bg-white/[0.02]"
                    style={{ animationDelay: `${i * 40}ms` }}
                    onClick={() => setSelectedLead(lead)}
                  >
                    <td className="px-grid-2 py-grid-2">
                      <div className="font-medium text-body-md">
                        {lead.first_name} {lead.last_name}
                      </div>
                      <div className="text-body-sm text-text-muted">{lead.title}</div>
                    </td>
                    <td className="px-grid-2 py-grid-2">
                      <div className="text-body-md">{lead.company_name}</div>
                      <div className="text-body-sm text-text-muted">{lead.industry}</div>
                    </td>
                    <td className="px-grid-2 py-grid-2 text-center">
                      <ScoreBadge score={lead.intent_score} />
                    </td>
                    <td className="px-grid-2 py-grid-2 text-center">
                      <StatusBadge status={lead.status} />
                    </td>
                    <td className="px-grid-2 py-grid-2 text-body-sm text-text-secondary">
                      {lead.source}
                    </td>
                    <td className="px-grid-2 py-grid-2 text-body-sm text-text-secondary max-w-[200px] truncate">
                      {lead.notes || "—"}
                    </td>
                    <td className="px-grid-2 py-grid-2 text-right">
                      <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                        <Link
                          href={`/leads/${lead.id}/footprint`}
                          className="btn-ghost p-1.5 hover:bg-white/5 rounded"
                          title="Digital Dossier"
                        >
                          <Fingerprint size={14} />
                        </Link>
                        {lead.linkedin_url && (
                          <a
                            href={lead.linkedin_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn-ghost p-1.5 hover:bg-white/5 rounded"
                            title="View LinkedIn"
                          >
                            <ExternalLink size={14} />
                          </a>
                        )}
                        <ActionsDropdown lead={lead} onAction={handleAction} />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-grid-3 py-grid-2 border-t border-border-light">
                <span className="text-body-sm text-text-muted">
                  Page {page} of {totalPages} ({total} total)
                </span>
                <div className="flex gap-1">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page === 1}
                    className="btn-ghost p-1 disabled:opacity-30"
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <button
                    onClick={() => setPage(Math.min(totalPages, page + 1))}
                    disabled={page === totalPages}
                    className="btn-ghost p-1 disabled:opacity-30"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Lead Detail Modal */}
      {selectedLead && (
        <LeadDetailModal lead={selectedLead} onClose={() => setSelectedLead(null)} />
      )}
    </div>
  );
}
