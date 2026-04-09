"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Check,
  Search,
  Brain,
  Target,
  MessageSquare,
  Mail,
  ChevronRight,
} from "lucide-react";

/* ── Data ──────────────────────────────────────────────────── */

const STEPS = [
  {
    num: "01",
    icon: Search,
    title: "Autonomous Discovery",
    desc: "AI agents scan the entire web to identify your ideal customers using advanced ICP matching, Google & LinkedIn intelligence.",
  },
  {
    num: "02",
    icon: Brain,
    title: "Deep Research",
    desc: "7 intelligence signals analyzed per prospect: social posts, hiring signals, technographics, website changes, and buying intent.",
  },
  {
    num: "03",
    icon: Target,
    title: "Predictive Scoring",
    desc: "Chain-of-Thought scoring across 4 dimensions: ICP fit, engagement signals, timing patterns, and buying committee analysis.",
  },
  {
    num: "04",
    icon: MessageSquare,
    title: "Hyper-Personalization",
    desc: "6-layer personalization engine crafts human-quality messages that reference real context from each prospect's digital footprint.",
  },
  {
    num: "05",
    icon: Mail,
    title: "Multi-Channel Outreach",
    desc: "Coordinated Email + LinkedIn sequences with anti-ban protection, warmup scheduling, and intelligent reply detection.",
  },
];

const STATS = [
  { value: "10,000+", label: "Leads Processed Daily" },
  { value: "94%", label: "ICP Match Accuracy" },
  { value: "6×", label: "Faster Than Manual" },
  { value: "$0.50", label: "Cost Per Lead" },
];

const PRICING = [
  {
    name: "Trial",
    price: "Free",
    period: "",
    desc: "Try before you commit.",
    features: [
      "10 lead discovery",
      "5 personalized messages",
      "Basic ICP analysis",
      "Email outreach",
    ],
    cta: "Start Free",
    href: "/register",
    highlight: false,
  },
  {
    name: "Pro",
    price: "$49",
    period: "/mo",
    desc: "For growing sales teams.",
    features: [
      "Unlimited discovery",
      "Unlimited messages",
      "LinkedIn + Email outreach",
      "Analytics dashboard",
      "Real-time reply detection",
      "Anti-ban protection",
    ],
    cta: "Get Started",
    href: "/register",
    highlight: true,
  },
  {
    name: "Enterprise",
    price: "$149",
    period: "/mo",
    desc: "For agencies and teams.",
    features: [
      "Everything in Pro",
      "Multi-product hunting",
      "Team management",
      "CRM integration",
      "API access",
      "Dedicated support",
    ],
    cta: "Get Started",
    href: "/register",
    highlight: false,
  },
];

/* ── Hawk Logo SVG ─────────────────────────────────────────── */
function HawkLogo({
  size = 48,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  return (
    <img
      src="/logo.png"
      alt="Hunter OS Logo"
      width={size}
      height={size}
      className={className}
      style={{ width: size, height: "auto", display: "block" }}
    />
  );
}

/* ── Intro Loading Screen ──────────────────────────────────── */
function IntroLoader({ onDone }: { onDone: () => void }) {
  const [logoVisible, setLogoVisible] = useState(false);
  const [fading, setFading] = useState(false);

  useEffect(() => {
    const showTimer = window.setTimeout(() => setLogoVisible(true), 150);
    const fadeTimer = window.setTimeout(() => setFading(true), 1700);
    const doneTimer = window.setTimeout(() => onDone(), 2400);

    return () => {
      window.clearTimeout(showTimer);
      window.clearTimeout(fadeTimer);
      window.clearTimeout(doneTimer);
    };
  }, [onDone]);

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        background: "radial-gradient(120% 120% at 50% 0%, #0f264d 0%, #050d21 58%, #020712 100%)",
        transition: "opacity 0.8s ease",
        opacity: fading ? 0 : 1,
        pointerEvents: fading ? "none" : "all",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 12,
          zIndex: 10,
          transition: "opacity 0.65s ease",
          opacity: logoVisible ? 1 : 0,
        }}
      >
        <HawkLogo size={82} className="text-white" />
        <div
          style={{
            fontFamily: "'Space Grotesk', sans-serif",
            fontWeight: 700,
            fontSize: 13,
            letterSpacing: "0.14em",
            color: "white",
            textTransform: "uppercase",
          }}
        >
          HUNTER.OS
        </div>
      </div>
    </div>
  );
}

/* ── Scroll Reveal Hook ────────────────────────────────────── */
function useScrollReveal(ready: boolean) {
  useEffect(() => {
    if (!ready) return;
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) e.target.classList.add("sr-revealed");
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -40px 0px" }
    );
    document
      .querySelectorAll(".sr-left, .sr-right, .sr-up")
      .forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [ready]);
}

/* ── Landing Page ──────────────────────────────────────────── */
export default function LandingPage() {
  const [loaded, setLoaded] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const handleDone = useCallback(() => setLoaded(true), []);

  useScrollReveal(loaded);

  useEffect(() => {
    if (!loaded) return;
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [loaded]);

  const BG = "linear-gradient(180deg, #030916 0%, #050d1f 52%, #020712 100%)";
  const SURFACE = "rgba(255,255,255,0.024)";
  const BORDER = "rgba(173, 198, 240, 0.18)";
  const TEXT = "#f2f7ff";
  const MUTED = "rgba(210, 225, 252, 0.58)";
  const ACCENT = "#7ea6f8";

  return (
    <>
      <IntroLoader onDone={handleDone} />

      <div
        style={{
          visibility: loaded ? "visible" : "hidden",
          opacity: loaded ? 1 : 0,
          transition: "opacity 0.5s ease 0.15s",
          background: BG,
          minHeight: "100vh",
          color: TEXT,
          fontFamily: "'Inter', system-ui, sans-serif",
          overflowX: "hidden",
        }}
      >
        {/* ── Navbar ── */}
        <nav
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            zIndex: 100,
            height: 64,
            padding: "0 clamp(20px, 5vw, 56px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: scrolled
              ? "rgba(6,9,26,0.88)"
              : "transparent",
            backdropFilter: scrolled ? "blur(14px)" : "none",
            borderBottom: scrolled ? `1px solid ${BORDER}` : "none",
            transition: "all 0.35s ease",
          }}
        >
          {/* Logo */}
          <Link
            href="/"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              textDecoration: "none",
            }}
          >
            <HawkLogo size={30} className="text-white" />
            <span
              style={{
                fontWeight: 900,
                fontSize: 15,
                letterSpacing: "-0.025em",
                color: "white",
              }}
            >
              HUNTER<span style={{ color: ACCENT }}>.OS</span>
            </span>
          </Link>

          {/* Center nav */}
          <div
            style={{ display: "flex", gap: 40, alignItems: "center" }}
          >
            {[
              { label: "How It Works", href: "#how-it-works" },
              { label: "Results", href: "#results" },
              { label: "Pricing", href: "#pricing" },
            ].map(({ label, href }) => (
              <a
                key={href}
                href={href}
                style={{
                  color: MUTED,
                  textDecoration: "none",
                  fontSize: 14,
                  fontWeight: 500,
                  transition: "color 0.2s",
                }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.color = TEXT)
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.color = MUTED)
                }
              >
                {label}
              </a>
            ))}
          </div>

          {/* Right CTA */}
          <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
            <Link
              href="/login"
              style={{
                color: MUTED,
                textDecoration: "none",
                fontSize: 14,
                fontWeight: 500,
                transition: "color 0.2s",
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.color = TEXT)
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.color = MUTED)
              }
            >
              Sign In
            </Link>
            <Link
              href="/register"
              style={{
                background: ACCENT,
                color: "white",
                textDecoration: "none",
                fontSize: 13,
                fontWeight: 700,
                padding: "8px 20px",
                borderRadius: 7,
                letterSpacing: "0.01em",
                transition: "background 0.2s, transform 0.15s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "#3b7ef5";
                e.currentTarget.style.transform = "translateY(-1px)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = ACCENT;
                e.currentTarget.style.transform = "none";
              }}
            >
              Get Started
            </Link>
          </div>
        </nav>

        {/* ── Hero ── */}
        <section
          style={{
            minHeight: "100vh",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "100px clamp(20px, 6vw, 80px) 60px",
            textAlign: "center",
            position: "relative",
            overflow: "hidden",
          }}
        >
          {/* BG radial glow */}
          <div
            style={{
              position: "absolute",
              top: "38%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              width: 900,
              height: 900,
              background:
                "radial-gradient(circle, rgba(79,142,247,0.055) 0%, transparent 68%)",
              pointerEvents: "none",
            }}
          />

          <div
            style={{
              position: "relative",
              zIndex: 1,
              maxWidth: 820,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 28,
            }}
          >
            {/* Eyebrow badge */}
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                background: "rgba(79,142,247,0.08)",
                border: "1px solid rgba(79,142,247,0.22)",
                borderRadius: 100,
                padding: "6px 18px",
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: "0.1em",
                color: ACCENT,
                textTransform: "uppercase",
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: ACCENT,
                  display: "inline-block",
                  boxShadow: `0 0 8px ${ACCENT}`,
                }}
              />
              AI-Powered Autonomous Sales
            </div>

            {/* Headline */}
            <h1
              style={{
                fontSize: "clamp(42px, 7.5vw, 86px)",
                fontWeight: 900,
                lineHeight: 1.03,
                letterSpacing: "-0.045em",
                color: "white",
                margin: 0,
              }}
            >
              The Sales Hunter
              <br />
              <span
                style={{
                  background:
                    "linear-gradient(130deg, #4f8ef7 10%, #38bdf8 90%)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                }}
              >
                That Never Sleeps
              </span>
            </h1>

            <p
              style={{
                fontSize: "clamp(15px, 1.8vw, 19px)",
                lineHeight: 1.7,
                color: MUTED,
                maxWidth: 560,
                margin: 0,
                fontWeight: 400,
              }}
            >
              Fully autonomous AI finds your ideal customers, analyzes their
              digital footprint, and sends hyper-personalized messages —
              while you sleep.
            </p>

            <div
              style={{
                display: "flex",
                gap: 16,
                alignItems: "center",
                flexWrap: "wrap",
                justifyContent: "center",
                marginTop: 6,
              }}
            >
              <Link
                href="/register"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  background: ACCENT,
                  color: "white",
                  textDecoration: "none",
                  fontSize: 15,
                  fontWeight: 700,
                  padding: "15px 30px",
                  borderRadius: 9,
                  transition: "all 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "#3b7ef5";
                  e.currentTarget.style.transform = "translateY(-2px)";
                  e.currentTarget.style.boxShadow =
                    "0 8px 28px rgba(79,142,247,0.35)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = ACCENT;
                  e.currentTarget.style.transform = "none";
                  e.currentTarget.style.boxShadow = "none";
                }}
              >
                Start Hunting Free
                <ArrowRight size={16} />
              </Link>
              <a
                href="#how-it-works"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  color: MUTED,
                  textDecoration: "none",
                  fontSize: 14,
                  fontWeight: 500,
                  transition: "color 0.2s",
                }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.color = TEXT)
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.color = MUTED)
                }
              >
                See how it works <ChevronRight size={14} />
              </a>
            </div>
          </div>
        </section>

        {/* ── Results / Stats ── */}
        <section
          id="results"
          style={{ padding: "72px clamp(20px, 6vw, 80px)" }}
        >
          <div style={{ maxWidth: 1120, margin: "0 auto" }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(4, 1fr)",
                borderTop: `1px solid ${BORDER}`,
                borderLeft: `1px solid ${BORDER}`,
              }}
            >
              {STATS.map((stat, i) => (
                <div
                  key={i}
                  className={i % 2 === 0 ? "sr-left" : "sr-right"}
                  style={{
                    padding: "44px 36px",
                    borderRight: `1px solid ${BORDER}`,
                    borderBottom: `1px solid ${BORDER}`,
                  }}
                >
                  <div
                    style={{
                      fontSize: "clamp(34px, 4vw, 50px)",
                      fontWeight: 900,
                      letterSpacing: "-0.045em",
                      color: "white",
                      lineHeight: 1,
                    }}
                  >
                    {stat.value}
                  </div>
                  <div
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      letterSpacing: "0.12em",
                      color: "rgba(238,242,255,0.28)",
                      textTransform: "uppercase",
                      marginTop: 10,
                    }}
                  >
                    {stat.label}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── How It Works ── */}
        <section
          id="how-it-works"
          style={{ padding: "80px clamp(20px, 6vw, 80px) 110px" }}
        >
          <div style={{ maxWidth: 1120, margin: "0 auto" }}>
            <div className="sr-left" style={{ marginBottom: 64 }}>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: "0.16em",
                  color: ACCENT,
                  textTransform: "uppercase",
                  marginBottom: 14,
                }}
              >
                The System
              </div>
              <h2
                style={{
                  fontSize: "clamp(28px, 4vw, 50px)",
                  fontWeight: 900,
                  letterSpacing: "-0.035em",
                  color: "white",
                  margin: 0,
                }}
              >
                How It Works
              </h2>
            </div>

            <div style={{ display: "flex", flexDirection: "column" }}>
              {STEPS.map((step, i) => {
                const Icon = step.icon;
                return (
                  <div
                    key={i}
                    className={i % 2 === 0 ? "sr-left" : "sr-right"}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "88px 1fr",
                      gap: 36,
                      padding: "36px 0",
                      borderBottom: `1px solid ${BORDER}`,
                      alignItems: "start",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 10,
                      }}
                    >
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 700,
                          letterSpacing: "0.1em",
                          color: "rgba(238,242,255,0.2)",
                        }}
                      >
                        {step.num}
                      </span>
                      <div
                        style={{
                          width: 44,
                          height: 44,
                          borderRadius: 9,
                          background: "rgba(79,142,247,0.07)",
                          border: "1px solid rgba(79,142,247,0.18)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        <Icon size={19} color={ACCENT} />
                      </div>
                    </div>
                    <div>
                      <h3
                        style={{
                          fontSize: 19,
                          fontWeight: 700,
                          letterSpacing: "-0.015em",
                          color: "white",
                          marginBottom: 12,
                        }}
                      >
                        {step.title}
                      </h3>
                      <p
                        style={{
                          fontSize: 15,
                          lineHeight: 1.7,
                          color: MUTED,
                          margin: 0,
                          maxWidth: 580,
                        }}
                      >
                        {step.desc}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* ── Pricing ── */}
        <section
          id="pricing"
          style={{ padding: "80px clamp(20px, 6vw, 80px) 110px" }}
        >
          <div style={{ maxWidth: 1120, margin: "0 auto" }}>
            <div
              className="sr-right"
              style={{ marginBottom: 64, textAlign: "center" }}
            >
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: "0.16em",
                  color: ACCENT,
                  textTransform: "uppercase",
                  marginBottom: 14,
                }}
              >
                Pricing
              </div>
              <h2
                style={{
                  fontSize: "clamp(28px, 4vw, 50px)",
                  fontWeight: 900,
                  letterSpacing: "-0.035em",
                  color: "white",
                  margin: 0,
                }}
              >
                Simple, Transparent Pricing
              </h2>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: 1,
                border: `1px solid ${BORDER}`,
                borderRadius: 12,
                overflow: "hidden",
              }}
            >
              {PRICING.map((plan, i) => (
                <div
                  key={i}
                  className={
                    i === 0 ? "sr-left" : i === 2 ? "sr-right" : "sr-up"
                  }
                  style={{
                    padding: "44px 36px",
                    background: plan.highlight
                      ? "rgba(79,142,247,0.05)"
                      : SURFACE,
                    borderRight: i < 2 ? `1px solid ${BORDER}` : "none",
                    position: "relative",
                  }}
                >
                  {plan.highlight && (
                    <div
                      style={{
                        position: "absolute",
                        top: 0,
                        left: "50%",
                        transform: "translateX(-50%)",
                        background: ACCENT,
                        color: "white",
                        fontSize: 9,
                        fontWeight: 800,
                        letterSpacing: "0.14em",
                        padding: "4px 16px",
                        borderRadius: "0 0 8px 8px",
                      }}
                    >
                      MOST POPULAR
                    </div>
                  )}

                  <div style={{ marginBottom: 28 }}>
                    <div
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                        letterSpacing: "0.12em",
                        color: "rgba(238,242,255,0.35)",
                        textTransform: "uppercase",
                        marginBottom: 10,
                      }}
                    >
                      {plan.name}
                    </div>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "baseline",
                        gap: 3,
                        marginBottom: 10,
                      }}
                    >
                      <span
                        style={{
                          fontSize: 44,
                          fontWeight: 900,
                          letterSpacing: "-0.045em",
                          color: "white",
                        }}
                      >
                        {plan.price}
                      </span>
                      {plan.period && (
                        <span
                          style={{ fontSize: 14, color: MUTED }}
                        >
                          {plan.period}
                        </span>
                      )}
                    </div>
                    <p style={{ fontSize: 13, color: MUTED, margin: 0 }}>
                      {plan.desc}
                    </p>
                  </div>

                  <ul
                    style={{
                      listStyle: "none",
                      padding: 0,
                      margin: "0 0 36px",
                      display: "flex",
                      flexDirection: "column",
                      gap: 11,
                    }}
                  >
                    {plan.features.map((f, fi) => (
                      <li
                        key={fi}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 10,
                          fontSize: 13,
                          color: "rgba(238,242,255,0.65)",
                        }}
                      >
                        <Check
                          size={14}
                          color={ACCENT}
                          style={{ flexShrink: 0 }}
                        />
                        {f}
                      </li>
                    ))}
                  </ul>

                  <Link
                    href={plan.href}
                    style={{
                      display: "block",
                      textAlign: "center",
                      textDecoration: "none",
                      padding: "12px 20px",
                      borderRadius: 7,
                      fontSize: 13,
                      fontWeight: 700,
                      background: plan.highlight ? ACCENT : "transparent",
                      color: plan.highlight
                        ? "white"
                        : "rgba(238,242,255,0.55)",
                      border: plan.highlight
                        ? "none"
                        : "1px solid rgba(255,255,255,0.14)",
                      transition: "all 0.2s",
                    }}
                    onMouseEnter={(e) => {
                      if (plan.highlight) {
                        e.currentTarget.style.background = "#3b7ef5";
                      } else {
                        e.currentTarget.style.borderColor =
                          "rgba(255,255,255,0.4)";
                        e.currentTarget.style.color = "white";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (plan.highlight) {
                        e.currentTarget.style.background = ACCENT;
                      } else {
                        e.currentTarget.style.borderColor =
                          "rgba(255,255,255,0.14)";
                        e.currentTarget.style.color =
                          "rgba(238,242,255,0.55)";
                      }
                    }}
                  >
                    {plan.cta}
                  </Link>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── CTA ── */}
        <section
          style={{
            padding: "80px clamp(20px, 6vw, 80px) 120px",
            textAlign: "center",
          }}
        >
          <div
            className="sr-up"
            style={{ maxWidth: 580, margin: "0 auto" }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                marginBottom: 28,
                opacity: 0.55,
              }}
            >
              <HawkLogo size={60} className="text-white" />
            </div>
            <h2
              style={{
                fontSize: "clamp(28px, 4vw, 50px)",
                fontWeight: 900,
                letterSpacing: "-0.035em",
                color: "white",
                marginBottom: 18,
              }}
            >
              Ready to Hunt?
            </h2>
            <p
              style={{
                fontSize: 16,
                color: MUTED,
                marginBottom: 38,
                lineHeight: 1.7,
              }}
            >
              Start free. No credit card required. Your first 10 leads are
              on us.
            </p>
            <Link
              href="/register"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 10,
                background: ACCENT,
                color: "white",
                textDecoration: "none",
                fontSize: 15,
                fontWeight: 700,
                padding: "16px 34px",
                borderRadius: 9,
                transition: "all 0.2s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "#3b7ef5";
                e.currentTarget.style.transform = "translateY(-2px)";
                e.currentTarget.style.boxShadow =
                  "0 10px 32px rgba(79,142,247,0.38)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = ACCENT;
                e.currentTarget.style.transform = "none";
                e.currentTarget.style.boxShadow = "none";
              }}
            >
              Start Hunting Free
              <ArrowRight size={16} />
            </Link>
          </div>
        </section>

        {/* ── Footer ── */}
        <footer
          style={{
            padding: "28px clamp(20px, 6vw, 80px)",
            borderTop: `1px solid ${BORDER}`,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 12,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <HawkLogo size={22} className="text-white" />
            <span
              style={{
                fontSize: 12,
                fontWeight: 800,
                color: "rgba(255,255,255,0.3)",
                letterSpacing: "0.05em",
              }}
            >
              HUNTER.OS
            </span>
          </div>
          <div style={{ fontSize: 12, color: "rgba(255,255,255,0.18)" }}>
            © 2025 HUNTER.OS. All rights reserved.
          </div>
        </footer>
      </div>
    </>
  );
}
