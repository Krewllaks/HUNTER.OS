/**
 * HUNTER.OS - useI18n React Hook
 * Reactive translation hook that re-renders on locale change.
 */
"use client";

import { useState, useEffect, useCallback } from "react";
import { getLocale, setLocale, onLocaleChange, t as translate, type Locale } from "@/lib/i18n";

export function useI18n() {
  const [locale, setLocaleState] = useState<Locale>("tr");

  useEffect(() => {
    // Initialize from storage
    setLocaleState(getLocale());

    // Subscribe to changes
    const unsub = onLocaleChange((newLocale) => {
      setLocaleState(newLocale);
    });
    return unsub;
  }, []);

  const toggleLanguage = useCallback(() => {
    const next = locale === "tr" ? "en" : "tr";
    setLocale(next);
  }, [locale]);

  // t() that uses current locale (reactive)
  const t = useCallback(
    (key: string): string => {
      // Force re-read by depending on locale state
      void locale;
      return translate(key);
    },
    [locale]
  );

  return { locale, t, toggleLanguage, setLocale };
}
