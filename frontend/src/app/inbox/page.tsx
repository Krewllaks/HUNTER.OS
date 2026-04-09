"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import {
  Mail, Linkedin, Search, Clock, Send, Loader2, AlertCircle, RefreshCw,
} from "lucide-react";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type InboxMessage = any;

function ChannelIcon({ channel }: { channel: string }) {
  if (channel === "linkedin_dm") return <Linkedin size={14} className="text-blue-600" />;
  return <Mail size={14} className="text-text-muted" />;
}

function SentimentDot({ sentiment }: { sentiment: string | null }) {
  const colors: Record<string, string> = {
    positive: "bg-green-400",
    negative: "bg-red-400",
    neutral: "bg-gray-400",
  };
  if (!sentiment) return null;
  return <span className={`w-2 h-2 rounded-full ${colors[sentiment] || "bg-gray-400"}`} />;
}

function AutoLabel({ label }: { label: string | null }) {
  if (!label) return null;
  const styles: Record<string, string> = {
    meeting_request: "bg-green-50 text-green-700",
    price_inquiry: "bg-blue-50 text-blue-700",
    not_interested: "bg-red-50 text-red-600",
    follow_up: "bg-yellow-50 text-yellow-700",
    interested: "bg-green-50 text-green-700",
    objection: "bg-orange-50 text-orange-700",
  };
  return (
    <span className={`text-body-sm px-1.5 py-0.5 rounded ${styles[label] || "bg-gray-100 text-gray-500"}`}>
      {label.replace(/_/g, " ")}
    </span>
  );
}

export default function InboxPage() {
  const [messages, setMessages] = useState<InboxMessage[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [unreadCount, setUnreadCount] = useState(0);
  const [replyText, setReplyText] = useState("");
  const [sending, setSending] = useState(false);

  const fetchMessages = useCallback(async () => {
    try {
      const params: Record<string, string | number> = { per_page: 50 };
      if (filter === "unread") params.is_read = 0;
      if (filter === "inbound") params.direction = "inbound";
      if (filter === "positive") params.sentiment = "positive";
      if (searchQuery) params.search = searchQuery;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const res = (await api.inbox.unified(params)) as any;
      setMessages(res.messages || []);
      setUnreadCount(res.unread || 0);
      if (!selectedId && res.messages?.length > 0) {
        setSelectedId(res.messages[0].id);
      }
    } catch (err) {
      console.error("Failed to fetch inbox:", err);
      setError("Mesajlar yüklenemedi");
    } finally {
      setLoading(false);
    }
  }, [filter, searchQuery]);

  useEffect(() => {
    fetchMessages();
  }, [fetchMessages]);

  const handleMarkRead = async (id: number) => {
    try {
      await api.inbox.markRead(id);
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, is_read: true } : m))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      console.error("Mark read failed:", err);
    }
  };

  const handleSelectMessage = (msg: InboxMessage) => {
    setSelectedId(msg.id);
    if (!msg.is_read && msg.direction === "inbound") {
      handleMarkRead(msg.id);
    }
  };

  const handleReply = async () => {
    if (!replyText.trim() || !selectedMessage) return;
    setSending(true);
    try {
      await api.inbox.compose({
        lead_id: selectedMessage.lead_id,
        channel: selectedMessage.channel || "email",
        subject: selectedMessage.subject ? `Re: ${selectedMessage.subject}` : undefined,
        body: replyText,
      });
      setReplyText("");
      await fetchMessages();
    } catch (err) {
      console.error("Reply failed:", err);
    } finally {
      setSending(false);
    }
  };

  const selectedMessage = messages.find((m: InboxMessage) => m.id === selectedId);

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
          <h1 className="font-display text-display-lg">Unified Inbox</h1>
          <p className="text-body-md text-text-secondary mt-1">
            {unreadCount} okunmamış mesaj
          </p>
        </div>
        <button onClick={() => fetchMessages()} className="btn-ghost p-2">
          <RefreshCw size={16} />
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-danger text-body-sm bg-red-50 p-3 rounded-sm">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* Inbox Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-grid-2 h-[calc(100vh-200px)]">
        {/* Message List */}
        <div className="lg:col-span-2 table-container flex flex-col overflow-hidden">
          {/* Search & Filters */}
          <div className="p-grid-2 border-b border-border-light space-y-2">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
              <input
                type="text"
                placeholder="Mesaj ara..."
                className="input pl-8 text-body-sm"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <div className="flex gap-1">
              {["all", "unread", "inbound", "positive"].map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`text-body-sm px-2 py-1 rounded-sm transition-colors ${
                    filter === f ? "bg-primary text-white" : "text-text-muted hover:text-text"
                  }`}
                >
                  {f === "all" ? "Tümü" : f === "unread" ? "Okunmamış" : f === "inbound" ? "Gelen" : "Pozitif"}
                </button>
              ))}
            </div>
          </div>

          {/* Message List */}
          <div className="flex-1 overflow-y-auto divide-y divide-border-light">
            {messages.length === 0 ? (
              <div className="p-8 text-center text-text-muted">
                <Mail size={32} className="mx-auto mb-2 opacity-50" />
                <p>Mesaj bulunamadı</p>
              </div>
            ) : (
              messages.map((msg: InboxMessage) => (
                <div
                  key={msg.id}
                  onClick={() => handleSelectMessage(msg)}
                  className={`px-grid-2 py-grid-2 cursor-pointer transition-colors ${
                    selectedId === msg.id ? "bg-primary/5 border-l-2 border-l-primary" : "hover:bg-background/50"
                  } ${!msg.is_read && msg.direction === "inbound" ? "bg-blue-50/50" : ""}`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <ChannelIcon channel={msg.channel} />
                      <span className={`text-body-md ${!msg.is_read ? "font-semibold" : ""}`}>
                        {msg.lead_name || `Lead #${msg.lead_id}`}
                      </span>
                      <SentimentDot sentiment={msg.sentiment_label} />
                    </div>
                    <span className="text-body-sm text-text-muted">
                      {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                  <div className="text-body-sm text-text-secondary mb-1">
                    {msg.subject && <span className="font-medium text-text">{msg.subject} - </span>}
                    {msg.lead_company || ""}
                  </div>
                  <div className="text-body-sm text-text-muted line-clamp-1">
                    {msg.body?.substring(0, 100)}
                  </div>
                  <div className="flex items-center gap-1 mt-1">
                    <AutoLabel label={msg.auto_label} />
                    {msg.direction === "outbound" && (
                      <span className="text-body-sm text-text-muted flex items-center gap-0.5">
                        <Send size={10} /> Gönderildi
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Message Detail */}
        <div className="lg:col-span-3 table-container flex flex-col overflow-hidden">
          {selectedMessage ? (
            <>
              <div className="p-grid-3 border-b border-border-light">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <ChannelIcon channel={selectedMessage.channel} />
                    <h2 className="font-display text-heading">
                      {selectedMessage.lead_name || `Lead #${selectedMessage.lead_id}`}
                    </h2>
                    <span className="text-body-sm text-text-muted">
                      {selectedMessage.lead_company || ""}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <AutoLabel label={selectedMessage.auto_label} />
                    <SentimentDot sentiment={selectedMessage.sentiment_label} />
                  </div>
                </div>
                {selectedMessage.subject && (
                  <h3 className="text-body-lg font-medium">{selectedMessage.subject}</h3>
                )}
                <div className="flex items-center gap-2 mt-1 text-body-sm text-text-muted">
                  <Clock size={12} />
                  {new Date(selectedMessage.created_at).toLocaleString()}
                  <span>| {selectedMessage.channel?.replace("_", " ")}</span>
                  <span>| {selectedMessage.direction === "inbound" ? "Gelen" : "Giden"}</span>
                </div>
              </div>

              <div className="flex-1 p-grid-3 overflow-y-auto">
                <p className="text-body-lg leading-relaxed whitespace-pre-wrap">
                  {selectedMessage.body}
                </p>
                {selectedMessage.ai_generated && (
                  <div className="mt-4 text-body-xs text-text-muted bg-primary/5 px-2 py-1 rounded inline-block">
                    AI tarafından oluşturuldu
                  </div>
                )}
              </div>

              {/* Reply Bar */}
              <div className="p-grid-2 border-t border-border-light">
                <div className="flex gap-grid-1">
                  <input
                    type="text"
                    placeholder="Cevabınızı yazın..."
                    className="input flex-1"
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleReply()}
                  />
                  <button
                    onClick={handleReply}
                    disabled={sending || !replyText.trim()}
                    className="btn-primary"
                  >
                    {sending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                    Cevapla
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-text-muted">
              Görüntülemek için bir mesaj seçin
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
