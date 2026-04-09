"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { X, Send, RefreshCw, Edit3, Sparkles, Check } from "lucide-react";

interface MessagePreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  leadId: number;
  leadName: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  message: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  contentProfile: any;
  onApproved?: () => void;
}

export default function MessagePreviewModal({
  isOpen,
  onClose,
  leadId,
  leadName,
  message,
  contentProfile,
  onApproved,
}: MessagePreviewModalProps) {
  const [editMode, setEditMode] = useState(false);
  const [body, setBody] = useState(message?.body || "");
  const [subject, setSubject] = useState(message?.subject_line || "");
  const [isApproving, setIsApproving] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [approved, setApproved] = useState(false);

  if (!isOpen) return null;

  const handleApprove = async () => {
    setIsApproving(true);
    try {
      await api.messages.approve(leadId, {
        body,
        subject_line: subject,
        channel: message?.channel || "email",
      });
      setApproved(true);
      onApproved?.();
      setTimeout(() => onClose(), 1500);
    } catch (err) {
      console.error("Approve failed:", err);
    } finally {
      setIsApproving(false);
    }
  };

  const handleRegenerate = async () => {
    setIsRegenerating(true);
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const res = (await api.messages.generate(leadId, {
        channel: message?.channel || "email",
      })) as any;
      if (res.message) {
        setBody(res.message.body || "");
        setSubject(res.message.subject_line || "");
      }
    } catch (err) {
      console.error("Regenerate failed:", err);
    } finally {
      setIsRegenerating(false);
    }
  };

  const signals = message?.personalization_signals_used || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      <div className="relative bg-background border border-border rounded-sm p-grid-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-text-muted hover:text-text"
        >
          <X size={20} />
        </button>

        {approved ? (
          <div className="text-center py-8">
            <Check size={48} className="text-success mx-auto mb-4" />
            <h2 className="font-display text-display-sm">Mesaj Onaylandı!</h2>
            <p className="text-text-secondary mt-2">{leadName} için mesaj gönderime hazır.</p>
          </div>
        ) : (
          <>
            <h2 className="font-display text-display-sm mb-grid-1">
              Mesaj Önizleme
            </h2>
            <p className="text-body-sm text-text-muted mb-grid-4">
              {leadName} için oluşturulan kişiselleştirilmiş mesaj
            </p>

            {/* Personalization signals */}
            {signals.length > 0 && (
              <div className="bg-primary/5 border border-primary/20 rounded-sm p-grid-3 mb-grid-4">
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles size={14} className="text-primary" />
                  <span className="text-body-xs font-medium text-primary">
                    Kişiselleştirme Sinyalleri
                  </span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {signals.map((signal: string) => (
                    <span
                      key={signal}
                      className="bg-primary/10 text-primary text-xs px-2 py-0.5 rounded"
                    >
                      {signal}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Content profile summary */}
            {contentProfile && (
              <div className="bg-surface rounded-sm p-grid-3 mb-grid-4">
                <p className="text-body-xs text-text-muted mb-1">İçerik Profili</p>
                <div className="grid grid-cols-2 gap-2 text-body-xs">
                  {contentProfile.communication_style && (
                    <div>
                      <span className="text-text-muted">Üslup: </span>
                      {contentProfile.communication_style}
                    </div>
                  )}
                  {contentProfile.tone && (
                    <div>
                      <span className="text-text-muted">Ton: </span>
                      {contentProfile.tone}
                    </div>
                  )}
                  {contentProfile.personality_type && (
                    <div>
                      <span className="text-text-muted">Kişilik: </span>
                      {contentProfile.personality_type}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Message content */}
            <div className="space-y-grid-3 mb-grid-4">
              {message?.channel === "email" && (
                <div>
                  <label className="text-label text-text-muted block mb-1">KONU</label>
                  {editMode ? (
                    <input
                      type="text"
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                      className="input"
                    />
                  ) : (
                    <p className="text-body-md font-medium">{subject}</p>
                  )}
                </div>
              )}

              <div>
                <label className="text-label text-text-muted block mb-1">MESAJ</label>
                {editMode ? (
                  <textarea
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    rows={8}
                    className="input"
                  />
                ) : (
                  <div className="bg-surface rounded-sm p-grid-3 text-body-sm whitespace-pre-wrap">
                    {body}
                  </div>
                )}
              </div>

              {message?.ps_note && !editMode && (
                <p className="text-body-sm text-text-secondary italic">
                  P.S. {message.ps_note}
                </p>
              )}

              {message?.estimated_reply_probability && (
                <p className="text-body-xs text-text-muted">
                  Tahmini cevap olasılığı: %{Math.round(message.estimated_reply_probability * 100)}
                </p>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <button
                onClick={handleApprove}
                disabled={isApproving}
                className="btn-primary flex-1 flex items-center justify-center gap-2"
              >
                <Send size={14} />
                {isApproving ? "Onaylanıyor..." : "Onayla & Gönder"}
              </button>

              <button
                onClick={handleRegenerate}
                disabled={isRegenerating}
                className="bg-surface text-text px-4 py-2 rounded-sm hover:bg-border flex items-center gap-2"
              >
                <RefreshCw size={14} className={isRegenerating ? "animate-spin" : ""} />
                Yeniden Yaz
              </button>

              <button
                onClick={() => setEditMode(!editMode)}
                className="bg-surface text-text px-4 py-2 rounded-sm hover:bg-border flex items-center gap-2"
              >
                <Edit3 size={14} />
                {editMode ? "Bitir" : "Düzenle"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
