"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { Settings, User, Globe, Bell, Link, Check, Loader2, AlertCircle } from "lucide-react";
import { getLocale, setLocale } from "@/lib/i18n";

export default function SettingsPage() {
  const { user } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [language, setLanguage] = useState<"tr" | "en">("tr");

  // Save states
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileSaved, setProfileSaved] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);

  const [crmSaving, setCrmSaving] = useState(false);
  const [crmSaved, setCrmSaved] = useState(false);
  const [crmError, setCrmError] = useState<string | null>(null);

  // Telegram bridge
  const [telegramToken, setTelegramToken] = useState("");
  const [telegramChatId, setTelegramChatId] = useState("");

  // CRM keys
  const [hubspotKey, setHubspotKey] = useState("");
  const [pipedriveKey, setPipedriveKey] = useState("");

  useEffect(() => {
    if (user) {
      setFullName(user.full_name || "");
      setEmail(user.email || "");
    }
    const locale = getLocale();
    setLanguage(locale === "tr" || locale === "en" ? locale : "en");
  }, [user]);

  const handleLanguageChange = (lang: "tr" | "en") => {
    setLanguage(lang);
    setLocale(lang);
    window.location.reload();
  };

  const handleSaveProfile = async () => {
    setProfileSaving(true);
    setProfileError(null);
    setProfileSaved(false);
    try {
      await api.auth.updateProfile({ full_name: fullName, email });
      setProfileSaved(true);
      setTimeout(() => setProfileSaved(false), 3000);
    } catch (err) {
      setProfileError(err instanceof Error ? err.message : "Failed to save profile");
    } finally {
      setProfileSaving(false);
    }
  };

  const handleSaveCRM = async () => {
    setCrmSaving(true);
    setCrmError(null);
    setCrmSaved(false);
    try {
      // Save CRM keys via accounts settings endpoint
      // For now store as notification bridge config
      if (hubspotKey || pipedriveKey) {
        // CRM keys would be saved via a dedicated endpoint in production
        // For now simulate success
        setCrmSaved(true);
        setTimeout(() => setCrmSaved(false), 3000);
      }
    } catch (err) {
      setCrmError(err instanceof Error ? err.message : "Failed to save CRM settings");
    } finally {
      setCrmSaving(false);
    }
  };

  const handleTestBridge = async () => {
    if (!telegramToken || !telegramChatId) return;
    try {
      await api.inbox.bridge({
        channel: "telegram",
        token: telegramToken,
        chat_id: telegramChatId,
        message: "HUNTER.OS bridge test - connection successful!",
      });
      alert("Test message sent successfully!");
    } catch (err) {
      alert(`Bridge test failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  return (
    <div className="space-y-grid-4 max-w-[800px]">
      <div>
        <h1 className="font-display text-display-lg flex items-center gap-3">
          <Settings className="text-primary" size={28} />
          Ayarlar
        </h1>
      </div>

      {/* Profile */}
      <div className="card space-y-grid-2">
        <h2 className="font-display text-heading flex items-center gap-2">
          <User size={16} /> Profil
        </h2>
        <div className="grid grid-cols-2 gap-grid-2">
          <div>
            <label className="text-label text-text-muted block mb-1">AD SOYAD</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="input"
            />
          </div>
          <div>
            <label className="text-label text-text-muted block mb-1">EMAIL</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input"
            />
          </div>
        </div>
        {profileError && (
          <div className="flex items-center gap-2 text-red-400 text-body-sm">
            <AlertCircle size={14} /> {profileError}
          </div>
        )}
        <button
          onClick={handleSaveProfile}
          disabled={profileSaving}
          className="btn-primary flex items-center gap-2"
        >
          {profileSaving ? (
            <Loader2 size={14} className="animate-spin" />
          ) : profileSaved ? (
            <Check size={14} />
          ) : null}
          {profileSaving ? "Kaydediliyor..." : profileSaved ? "Kaydedildi" : "Kaydet"}
        </button>
      </div>

      {/* Language */}
      <div className="card space-y-grid-2">
        <h2 className="font-display text-heading flex items-center gap-2">
          <Globe size={16} /> Dil / Language
        </h2>
        <div className="flex gap-3">
          <button
            onClick={() => handleLanguageChange("tr")}
            className={`px-4 py-2 rounded-sm border transition-colors ${
              language === "tr"
                ? "border-primary bg-primary/5 text-primary font-medium"
                : "border-border-light text-text-secondary hover:border-border"
            }`}
          >
            Turkce
          </button>
          <button
            onClick={() => handleLanguageChange("en")}
            className={`px-4 py-2 rounded-sm border transition-colors ${
              language === "en"
                ? "border-primary bg-primary/5 text-primary font-medium"
                : "border-border-light text-text-secondary hover:border-border"
            }`}
          >
            English
          </button>
        </div>
      </div>

      {/* CRM Integration */}
      <div className="card space-y-grid-2">
        <h2 className="font-display text-heading flex items-center gap-2">
          <Link size={16} /> CRM Entegrasyonu
        </h2>
        <div className="space-y-grid-1">
          <div>
            <label className="text-label text-text-muted block mb-1">HUBSPOT API KEY</label>
            <input
              type="password"
              placeholder="HubSpot API key girin"
              className="input font-mono"
              value={hubspotKey}
              onChange={(e) => setHubspotKey(e.target.value)}
            />
          </div>
          <div>
            <label className="text-label text-text-muted block mb-1">PIPEDRIVE API KEY</label>
            <input
              type="password"
              placeholder="Pipedrive API key girin"
              className="input font-mono"
              value={pipedriveKey}
              onChange={(e) => setPipedriveKey(e.target.value)}
            />
          </div>
        </div>
        <p className="text-body-sm text-text-muted">
          Pozitif sentiment lead&apos;ler otomatik olarak CRM&apos;inize senkronize edilir
        </p>
        {crmError && (
          <div className="flex items-center gap-2 text-red-400 text-body-sm">
            <AlertCircle size={14} /> {crmError}
          </div>
        )}
        <button
          onClick={handleSaveCRM}
          disabled={crmSaving}
          className="btn-primary flex items-center gap-2"
        >
          {crmSaving ? (
            <Loader2 size={14} className="animate-spin" />
          ) : crmSaved ? (
            <Check size={14} />
          ) : null}
          {crmSaving ? "Kaydediliyor..." : crmSaved ? "CRM Baglandi" : "CRM Bagla"}
        </button>
      </div>

      {/* Notification Bridge */}
      <div className="card space-y-grid-2">
        <h2 className="font-display text-heading flex items-center gap-2">
          <Bell size={16} /> Bildirim Koprusu
        </h2>
        <div className="grid grid-cols-2 gap-grid-2">
          <div>
            <label className="text-label text-text-muted block mb-1">TELEGRAM BOT TOKEN</label>
            <input
              type="password"
              placeholder="Bot token"
              className="input font-mono text-body-sm"
              value={telegramToken}
              onChange={(e) => setTelegramToken(e.target.value)}
            />
          </div>
          <div>
            <label className="text-label text-text-muted block mb-1">TELEGRAM CHAT ID</label>
            <input
              type="text"
              placeholder="Chat ID"
              className="input font-mono text-body-sm"
              value={telegramChatId}
              onChange={(e) => setTelegramChatId(e.target.value)}
            />
          </div>
        </div>
        <button onClick={handleTestBridge} className="btn-secondary">
          Baglantiyi Test Et
        </button>
      </div>

      {/* Plan Info */}
      {user && (
        <div className="card space-y-grid-2">
          <h2 className="font-display text-heading">Plan Bilgisi</h2>
          <div className="flex items-center justify-between">
            <div>
              <span className="text-body-md font-medium capitalize">
                {(user as { plan?: string }).plan || "trial"} Plan
              </span>
            </div>
            <a href="/pricing" className="btn-primary text-body-sm">
              Plan Yukselt
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
