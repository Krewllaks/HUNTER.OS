import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, useScroll, useTransform, useInView, AnimatePresence } from 'framer-motion';
import './styles.css';

// ─── Animation Variants ───
const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  visible: (i = 0) => ({
    opacity: 1, y: 0,
    transition: { duration: 0.7, ease: [0.25, 0.46, 0.45, 0.94], delay: i * 0.1 }
  })
};

const staggerContainer = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.12 } }
};

const scaleIn = {
  hidden: { opacity: 0, scale: 0.92 },
  visible: { opacity: 1, scale: 1, transition: { duration: 0.6, ease: 'easeOut' } }
};

// ─── Hooks ───
function useCounter(target, options = {}) {
  const { duration = 1800, suffix = '', prefix = '', decimals = 0 } = options;
  const [value, setValue] = useState(0);
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-50px' });
  const rafRef = useRef(null);

  useEffect(() => {
    if (!isInView) return;
    const start = performance.now();
    const tick = (now) => {
      const p = Math.min((now - start) / duration, 1);
      const ease = 1 - Math.pow(1 - p, 3);
      setValue(ease * target);
      if (p < 1) rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [isInView, target, duration]);

  const display = prefix + (decimals > 0 ? value.toFixed(decimals) : Math.floor(value).toLocaleString()) + suffix;
  return { ref, display };
}

// ─── Loader Component — Green Horizon text reveal ───
function LoaderLetter({ char, revealed }) {
  return (
    <motion.span
      className={`loader-letter ${revealed ? 'revealed' : 'ghost'}`}
      initial={revealed ? { opacity: 0.3, filter: 'blur(3px)', y: 4 } : {}}
      animate={revealed ? { opacity: 1, filter: 'blur(0px)', y: 0 } : {}}
      transition={{ duration: 0.8, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {char}
    </motion.span>
  );
}

function Loader({ onComplete }) {
  const word1 = 'Green';
  const word2 = 'Horizon';
  const allLetters = [...word1.split(''), ...word2.split('')];
  const totalLetters = allLetters.length;

  const [revealedCount, setRevealedCount] = useState(0);
  const [visible, setVisible] = useState(true);
  const [subtitleVisible, setSubtitleVisible] = useState(false);
  const [lineAnimating, setLineAnimating] = useState(false);
  const timeoutRefs = useRef([]);

  useEffect(() => {
    // Start line & subtitle after a short delay
    const t1 = setTimeout(() => { setLineAnimating(true); setSubtitleVisible(true); }, 300);
    timeoutRefs.current.push(t1);

    // Reveal letters one by one with organic timing
    const letterInterval = 4200 / totalLetters;
    let idx = 0;

    function scheduleNext() {
      if (idx >= totalLetters) {
        // All revealed — hold then fade out
        const t = setTimeout(() => {
          setVisible(false);
          const t2 = setTimeout(onComplete, 800);
          timeoutRefs.current.push(t2);
        }, 900);
        timeoutRefs.current.push(t);
        return;
      }
      idx++;
      setRevealedCount(idx);
      const jitter = (Math.random() - 0.4) * (letterInterval * 0.5);
      const t = setTimeout(scheduleNext, letterInterval + jitter);
      timeoutRefs.current.push(t);
    }

    const startT = setTimeout(scheduleNext, 600);
    timeoutRefs.current.push(startT);

    return () => timeoutRefs.current.forEach(clearTimeout);
  }, [onComplete, totalLetters]);

  const progress = Math.floor((revealedCount / totalLetters) * 100);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          className="loader"
          exit={{ opacity: 0 }}
          transition={{ duration: 1.2, ease: [0.4, 0, 0.2, 1] }}
        >
          <div className="loader-content">
            <div className="loader-title-wrap">
              <div className="loader-title-line">
                {word1.split('').map((ch, i) => (
                  <LoaderLetter key={`w1-${i}`} char={ch} revealed={i < revealedCount} />
                ))}
              </div>
              <div className="loader-title-line">
                {word2.split('').map((ch, i) => (
                  <LoaderLetter key={`w2-${i}`} char={ch} revealed={(i + word1.length) < revealedCount} />
                ))}
              </div>
            </div>
            <div className={`loader-subtitle ${subtitleVisible ? 'visible' : ''}`}>
              Precision Meets Experience
            </div>
            <div className={`loader-line ${lineAnimating ? 'animating' : ''}`} />
          </div>
          <div className="loader-counter">{progress}</div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ─── HeroStars Canvas ───
function HeroStars() {
  const canvasRef = useRef(null);
  const starsRef = useRef([]);

  useEffect(() => {
    const c = canvasRef.current;
    const ctx = c.getContext('2d');

    const resize = () => {
      c.width = window.innerWidth;
      c.height = window.innerHeight;
      starsRef.current = Array.from({ length: 80 }, () => ({
        x: Math.random() * c.width,
        y: Math.random() * c.height,
        r: Math.random() * 1.2 + 0.3,
        a: Math.random(),
        s: Math.random() * 0.005 + 0.002
      }));
    };
    resize();
    window.addEventListener('resize', resize);

    let raf;
    const draw = () => {
      ctx.clearRect(0, 0, c.width, c.height);
      starsRef.current.forEach(s => {
        s.a += s.s;
        const alpha = (Math.sin(s.a) + 1) / 2 * 0.6 + 0.1;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(180,210,240,${alpha})`;
        ctx.fill();
      });
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', resize); };
  }, []);

  return <canvas ref={canvasRef} className="hero-stars" />;
}

// ─── Magnetic Button ───
function MagneticButton({ children, className = '', ...props }) {
  const ref = useRef(null);

  const handleMove = useCallback((e) => {
    const r = ref.current.getBoundingClientRect();
    const x = e.clientX - r.left - r.width / 2;
    const y = e.clientY - r.top - r.height / 2;
    ref.current.style.transform = `translate(${x * 0.15}px, ${y * 0.15}px)`;
  }, []);

  const handleLeave = useCallback(() => {
    ref.current.style.transform = '';
  }, []);

  return (
    <button
      ref={ref}
      className={`magnetic-btn ${className}`}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      {...props}
    >
      {children}
    </button>
  );
}

// ─── Section Wrapper ───
function RevealSection({ children, className = '', id }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <motion.section
      ref={ref}
      id={id}
      className={className}
      initial="hidden"
      animate={isInView ? 'visible' : 'hidden'}
      variants={staggerContainer}
    >
      {children}
    </motion.section>
  );
}

// ─── Nav ───
function Nav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 60);
    window.addEventListener('scroll', handler, { passive: true });
    return () => window.removeEventListener('scroll', handler);
  }, []);

  return (
    <nav className={`main-nav ${scrolled ? 'scrolled' : ''}`}>
      <div className="nav-logo">
        <svg viewBox="0 0 32 32" fill="none" width="28" height="28">
          <path d="M16 2L4 28h6l6-14 6 14h6L16 2z" fill="currentColor" opacity="0.9" />
          <path d="M16 10l-3 8h6l-3-8z" fill="var(--accent)" />
        </svg>
        Velox
      </div>
      <div className="nav-links">
        <a href="#">How It Works</a>
        <a href="#">Features</a>
        <a href="#">Pricing</a>
        <a href="#">Results</a>
      </div>
      <div className="nav-actions">
        <button className="btn-ghost">Sign In</button>
        <button className="btn-primary">Get Started</button>
      </div>
    </nav>
  );
}

// ─── Hero ───
function Hero() {
  const { scrollY } = useScroll();
  const starsY = useTransform(scrollY, [0, 800], [0, 240]);
  const bgY = useTransform(scrollY, [0, 800], [0, 120]);

  const items = [
    <motion.div className="hero-badge" variants={fadeUp} custom={0} key="badge">AI-Powered Outreach Engine</motion.div>,
    <motion.h1 className="hero-title" variants={fadeUp} custom={1} key="title">
      AI That Researches, Writes,<br /><em>& Books Meetings</em> For You
    </motion.h1>,
    <motion.p className="hero-sub" variants={fadeUp} custom={2} key="sub">
      Deploy autonomous sales agents that find prospects, craft hyper-personalized outreach, and convert conversations into booked calls — while you focus on closing.
    </motion.p>,
    <motion.div className="hero-cta-wrap" variants={fadeUp} custom={3} key="cta">
      <MagneticButton className="btn-large primary">Start Free Trial</MagneticButton>
      <button className="btn-large secondary">Watch Demo</button>
    </motion.div>
  ];

  return (
    <section id="hero">
      <motion.div className="hero-bg" style={{ y: bgY }} />
      <motion.div style={{ y: starsY, position: 'absolute', inset: 0, zIndex: 0 }}>
        <HeroStars />
      </motion.div>
      <motion.div
        className="hero-content"
        initial="hidden"
        animate="visible"
        variants={staggerContainer}
      >
        {items}
      </motion.div>
    </section>
  );
}

// ─── Stats ───
function StatCard({ count, suffix = '', prefix = '', label, decimal }) {
  const display = useCounter(count, { suffix, prefix, decimals: decimal ? 2 : 0 });

  return (
    <motion.div className="stat-card" variants={fadeUp}>
      <div className="stat-num" ref={display.ref}>
        {decimal && display.display === `${prefix}0${suffix}` ? `${prefix}0${suffix}` : display.display}
      </div>
      <div className="stat-label">{label}</div>
    </motion.div>
  );
}

function Stats() {
  return (
    <RevealSection id="stats" className="stats-section">
      <StatCard count={12000} suffix="+" label="Meetings booked monthly" />
      <StatCard count={94} suffix="%" label="Email deliverability rate" />
      <StatCard count={6} suffix="x" label="Pipeline velocity increase" />
      <StatCard count={50} prefix="<$" label="Cost per qualified lead" />
    </RevealSection>
  );
}

// ─── Logo Carousel ───
const LOGOS = ['Arcline','Meridian','Stratos','Polaris','Nextera','Evoqua','Pinnacle','Vantage','Summit','Luminary','Zenith','Vertex'];

function LogoCarousel() {
  const doubled = [...LOGOS, ...LOGOS];
  return (
    <section id="logos">
      <div className="logos-label">Trusted by forward-thinking teams</div>
      <div className="logos-track">
        {doubled.map((name, i) => (
          <span className="logo-item" key={i}>{name}</span>
        ))}
      </div>
    </section>
  );
}

// ─── Problem ───
const PROBLEMS = [
  { icon: '📉', title: 'Manual Prospecting Drains Time', text: 'Hours wasted researching accounts, finding contacts, and building lists that go stale within weeks.' },
  { icon: '📧', title: 'Generic Outreach Gets Ignored', text: 'Template-based emails deliver <1% reply rates. Prospects can smell automation from a mile away.' },
  { icon: '🔄', title: 'Inconsistent Follow-Up', text: 'Reps cherry-pick leads and abandon sequences early, leaving 73% of potential pipeline untouched.' },
];

function Problem() {
  return (
    <RevealSection className="section" id="problem">
      <motion.div className="section-label" variants={fadeUp}>The Challenge</motion.div>
      <motion.h2 className="section-title" variants={fadeUp}>Your Sales Pipeline Is <em>Starving</em></motion.h2>
      <motion.p className="section-sub" variants={fadeUp} style={{ margin: '0 auto 60px' }}>
        Traditional outbound is broken. Reps spend 68% of their time on non-selling activities while quota attainment drops year over year.
      </motion.p>
      <div className="problem-grid">
        {PROBLEMS.map((p, i) => (
          <motion.div className="problem-card" key={i} variants={fadeUp} custom={i} whileHover={{ y: -4, boxShadow: '0 20px 60px rgba(0,0,0,0.3)' }}>
            <div className="problem-icon">{p.icon}</div>
            <h3>{p.title}</h3>
            <p>{p.text}</p>
          </motion.div>
        ))}
      </div>
    </RevealSection>
  );
}

// ─── Transformation ───
function Transformation() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section id="transformation" ref={ref}>
      <div className="transform-bg" />
      <div className="section" style={{ position: 'relative', zIndex: 2 }}>
        <motion.div className="section-label" initial="hidden" animate={isInView ? 'visible' : 'hidden'} variants={fadeUp}>The Shift</motion.div>
        <motion.h2 className="section-title" initial="hidden" animate={isInView ? 'visible' : 'hidden'} variants={fadeUp}>From Guesswork to <em>Precision</em></motion.h2>
        <motion.p className="section-sub" initial="hidden" animate={isInView ? 'visible' : 'hidden'} variants={fadeUp} style={{ margin: '0 auto 60px' }}>
          See the difference when AI handles your entire outbound workflow end-to-end.
        </motion.p>
        <div className="transform-visual">
          <motion.div
            className="transform-before"
            initial={{ opacity: 0, x: -40 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.7, delay: 0.2 }}
          >
            <div className="transform-tag">Before Velox</div>
            <ul className="transform-list">
              <li><span>✕</span> 3-4 hrs/day prospecting manually</li>
              <li><span>✕</span> 0.8% average reply rate</li>
              <li><span>✕</span> 12 meetings booked per rep/month</li>
              <li><span>✕</span> $320 cost per meeting</li>
              <li><span>✕</span> Inconsistent messaging quality</li>
            </ul>
          </motion.div>
          <motion.div
            className="transform-arrow"
            initial={{ opacity: 0, scale: 0.5 }}
            animate={isInView ? { opacity: 1, scale: 1 } : {}}
            transition={{ duration: 0.5, delay: 0.5 }}
          >
            →
          </motion.div>
          <motion.div
            className="transform-after"
            initial={{ opacity: 0, x: 40 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.7, delay: 0.3 }}
          >
            <div className="transform-tag">With Velox</div>
            <ul className="transform-list">
              <li><span>✓</span> Zero manual prospecting time</li>
              <li><span>✓</span> 9.4% average reply rate</li>
              <li><span>✓</span> 84 meetings booked per rep/month</li>
              <li><span>✓</span> $47 cost per meeting</li>
              <li><span>✓</span> Hyper-personalized at scale</li>
            </ul>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

// ─── Solution / How It Works ───
const STEPS = [
  { num: '01', icon: '🎯', title: 'Define Your Ideal Buyer', text: 'Set firmographic, technographic, and intent signals. Velox continuously discovers and scores new prospects matching your ICP in real time.' },
  { num: '02', icon: '✍️', title: 'AI Crafts the Outreach', text: 'Each message is uniquely written using company research, recent news, tech stack data, and persona pain points — no templates, ever.' },
  { num: '03', icon: '📅', title: 'Meetings Appear on Calendar', text: 'Velox handles replies, objections, and scheduling. Qualified meetings land directly on your calendar with full context briefs.' },
];

function Solution() {
  return (
    <RevealSection className="section" id="solution">
      <motion.div className="section-label" variants={fadeUp}>How It Works</motion.div>
      <motion.h2 className="section-title" variants={fadeUp}>Three Steps to Autonomous <em>Pipeline</em></motion.h2>
      <motion.p className="section-sub" variants={fadeUp} style={{ margin: '0 auto 72px' }}>
        From cold prospect to booked meeting in minutes, not months. Set your ICP criteria and let Velox orchestrate the rest.
      </motion.p>
      <div className="steps">
        {STEPS.map((s, i) => (
          <motion.div className="step-card" key={i} variants={fadeUp} custom={i} whileHover={{ y: -4 }}>
            <div className="step-number">{s.num}</div>
            <div className="step-icon">{s.icon}</div>
            <h3>{s.title}</h3>
            <p>{s.text}</p>
          </motion.div>
        ))}
      </div>
    </RevealSection>
  );
}

// ─── Features ───
const FEATURES = [
  {
    tag: 'Intelligence', title: 'Deep Prospect Research',
    text: 'Velox scans 50+ data sources per prospect — tech stack, hiring patterns, funding events, social signals — to build a living profile that fuels truly relevant outreach.',
    items: ['Real-time company intelligence', 'Buying intent signal detection', 'Organizational mapping']
  },
  {
    tag: 'Personalization', title: 'Messages That Feel Human',
    text: 'Our language model adapts tone, structure, and hooks based on persona, industry, and seniority. Every email reads like a thoughtful note from a seasoned rep.',
    items: ['Persona-adaptive writing styles', 'Dynamic pain-point matching', 'A/B variant optimization']
  },
  {
    tag: 'Deliverability', title: 'Inbox-First Architecture',
    text: 'Managed sending infrastructure, domain warming, and real-time reputation monitoring ensure 94%+ deliverability without the ops headache.',
    items: ['Automated domain warm-up', 'Smart send-time optimization', 'Bounce & spam monitoring']
  },
];

function Features() {
  return (
    <section id="features">
      <div className="features-header" style={{ textAlign: 'center', marginBottom: 80 }}>
        <motion.div className="section-label" initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp}>Capabilities</motion.div>
        <motion.h2 className="section-title" initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp}>Built for Revenue <em>Precision</em></motion.h2>
        <motion.p className="section-sub" initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp} style={{ margin: '0 auto' }}>
          Every feature is designed to eliminate manual work and maximize conversion at every stage of outbound.
        </motion.p>
      </div>
      {FEATURES.map((f, i) => (
        <motion.div
          className="feature-row"
          key={i}
          initial={{ opacity: 0, y: 50 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.7, delay: 0.1 }}
        >
          <div className="feature-text">
            <span className="feature-tag">{f.tag}</span>
            <h3>{f.title}</h3>
            <p>{f.text}</p>
            <ul className="feat-list">
              {f.items.map((item, j) => <li key={j}>{item}</li>)}
            </ul>
          </div>
          <div className="feature-visual">
            <div className="feature-visual-inner" />
          </div>
        </motion.div>
      ))}
    </section>
  );
}

// ─── Pricing ───
const PRICING_PLANS = [
  {
    tier: 'Growth', amount: '$279', per: '/mo', featured: true,
    desc: 'Everything you need to launch autonomous outbound and book qualified meetings at scale.',
    features: ['Unlimited AI-written sequences', '5,000 enriched prospects/month', 'Multi-channel outreach (email + LinkedIn)', 'Automated follow-up & scheduling', 'Real-time intent signal alerts', 'Dedicated sending infrastructure', 'Priority deliverability monitoring'],
    btnText: 'Get Started', btnStyle: 'filled'
  },
  {
    tier: 'Enterprise', amount: 'Custom', per: '', featured: false,
    desc: 'Tailored deployment with dedicated support, custom integrations, and SLA-backed performance guarantees.',
    features: ['Everything in Growth', 'Unlimited prospect volume', 'Custom AI model fine-tuning', 'CRM & workflow integrations', 'Dedicated success manager', 'Custom reporting & analytics', 'SOC 2 & GDPR compliance'],
    btnText: 'Contact Sales', btnStyle: 'outline'
  }
];

function Pricing() {
  const [activeTab, setActiveTab] = useState(0);
  const tabs = ['Start Free Trial', 'Monthly', 'Annual'];

  return (
    <RevealSection id="pricing">
      <motion.div className="section-label" variants={fadeUp}>Transparent Pricing</motion.div>
      <motion.h2 className="section-title" variants={fadeUp}>Predictable, Scalable <em>Plans</em></motion.h2>
      <motion.p className="section-sub" variants={fadeUp} style={{ margin: '0 auto 24px' }}>No hidden fees. No per-seat charges. Pay for results, not headcount.</motion.p>
      <motion.div className="pricing-toggle" variants={fadeUp}>
        {tabs.map((t, i) => (
          <button key={i} className={activeTab === i ? 'active' : ''} onClick={() => setActiveTab(i)}>{t}</button>
        ))}
      </motion.div>
      <div className="pricing-grid">
        {PRICING_PLANS.map((plan, i) => (
          <motion.div
            className={`pricing-card ${plan.featured ? 'featured' : ''}`}
            key={i}
            variants={fadeUp}
            custom={i}
            whileHover={{ y: -4, boxShadow: '0 20px 60px rgba(0,0,0,0.3)' }}
          >
            <div className="pricing-tier">{plan.tier}</div>
            <div className="pricing-amount">{plan.amount}{plan.per && <span>{plan.per}</span>}</div>
            <div className="pricing-desc">{plan.desc}</div>
            <ul className="pricing-features">
              {plan.features.map((f, j) => <li key={j}>{f}</li>)}
            </ul>
            <button className={`pricing-btn ${plan.btnStyle}`}>{plan.btnText}</button>
          </motion.div>
        ))}
      </div>
    </RevealSection>
  );
}

// ─── Dashboard ───
const DASH_ROWS = [
  { name: 'Sarah Mitchell', company: 'Arcline Systems', status: 'active', statusText: 'Booked', score: 94, progress: 94 },
  { name: 'James Thornton', company: 'Meridian Labs', status: 'active', statusText: 'Booked', score: 91, progress: 91 },
  { name: 'Elena Rodriguez', company: 'Stratos Health', status: 'pending', statusText: 'Replied', score: 87, progress: 87 },
  { name: 'Marcus Chen', company: 'Apex Fintech', status: 'review', statusText: 'In Review', score: 82, progress: 82 },
];

function DashboardMetric({ id, target, suffix = '', prefix = '', decimals = 0, label, change }) {
  const counter = useCounter(target, { suffix, prefix, decimals });
  return (
    <motion.div className="dash-metric" whileHover={{ y: -2, boxShadow: '0 8px 24px rgba(0,0,0,0.3)' }}>
      <div className="dash-metric-val" ref={counter.ref}>{counter.display}</div>
      <div className="dash-metric-label">{label}</div>
      <div className="dash-metric-change up">{change}</div>
    </motion.div>
  );
}

function Dashboard() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });
  const [activeTab, setActiveTab] = useState(3);
  const dashTabs = ['All', 'Active', 'Replied', 'Booked'];

  return (
    <section id="dashboard" ref={ref}>
      <motion.div className="section-label" initial="hidden" animate={isInView ? 'visible' : 'hidden'} variants={fadeUp}>Command Center</motion.div>
      <motion.h2 className="section-title" initial="hidden" animate={isInView ? 'visible' : 'hidden'} variants={fadeUp}>Your Precision <em>Dashboard</em></motion.h2>
      <motion.p className="section-sub" initial="hidden" animate={isInView ? 'visible' : 'hidden'} variants={fadeUp} style={{ margin: '0 auto 56px' }}>
        Monitor every metric that matters — from send volume to booked meetings — in a single pane of glass.
      </motion.p>
      <motion.div
        className="dashboard-wrap"
        initial={{ opacity: 0, y: 40 }}
        animate={isInView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.7, delay: 0.2 }}
      >
        <div className="dash-topbar">
          <div className="dash-dot r" />
          <div className="dash-dot y" />
          <div className="dash-dot g" />
          <span>Velox — Command Dashboard</span>
        </div>
        <div className="dash-body">
          <div className="dash-metrics">
            <DashboardMetric target={47} label="Meetings This Week" change="↑ 24% vs last week" />
            <DashboardMetric target={2247} label="Emails Sent Today" change="↑ 12% vs avg" />
            <DashboardMetric target={18.1} suffix="%" decimals={1} label="Reply Rate" change="↑ 3.2% vs baseline" />
            <DashboardMetric target={312} prefix="$" suffix="K" label="Pipeline Generated" change="↑ $48K this month" />
          </div>
          <div className="dash-tabs">
            {dashTabs.map((t, i) => (
              <button key={i} className={`dash-tab ${activeTab === i ? 'active' : ''}`} onClick={() => setActiveTab(i)}>{t}</button>
            ))}
          </div>
          <table className="dash-table">
            <thead><tr><th>Prospect</th><th>Company</th><th>Stage</th><th>Score</th><th>Progress</th></tr></thead>
            <tbody>
              {DASH_ROWS.map((row, i) => (
                <tr key={i}>
                  <td>{row.name}</td>
                  <td>{row.company}</td>
                  <td><span className={`dash-status ${row.status}`}>{row.statusText}</span></td>
                  <td>{row.score}</td>
                  <td>
                    <div className="dash-progress">
                      <motion.div
                        className="dash-progress-fill"
                        initial={{ width: 0 }}
                        animate={isInView ? { width: `${row.progress}%` } : {}}
                        transition={{ duration: 1.5, delay: 0.5 + i * 0.15, ease: 'easeOut' }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </section>
  );
}

// ─── Testimonials ───
const TESTIMONIALS = [
  { text: '"We went from 15 meetings a month to 90+ in our first quarter. Velox didn\'t just replace our SDR motion — it 6x\'d it."', avatar: 'AK', name: 'Anika Kapoor', role: 'VP Sales, Stratos Health' },
  { text: '"The personalization is uncanny. Prospects consistently reply thinking a human wrote the email. Our reply rate tripled overnight."', avatar: 'DL', name: 'David Lawson', role: 'CRO, Meridian Labs' },
  { text: '"We saved $180K annually by consolidating three tools into Velox. The ROI was obvious within the first 30 days."', avatar: 'RN', name: 'Rachel Nguyen', role: 'Head of Growth, Apex Fintech' },
];

function Testimonials() {
  return (
    <RevealSection id="testimonials">
      <motion.div className="section-label" variants={fadeUp}>What Teams Say</motion.div>
      <motion.h2 className="section-title" variants={fadeUp}>Results Speak <em>Volumes</em></motion.h2>
      <motion.p className="section-sub" variants={fadeUp} style={{ margin: '0 auto 56px' }}>
        Don't take our word for it — see what revenue leaders are saying after deploying Velox.
      </motion.p>
      <div className="testimonial-grid">
        {TESTIMONIALS.map((t, i) => (
          <motion.div className="testimonial-card" key={i} variants={fadeUp} custom={i} whileHover={{ y: -4 }}>
            <div className="testimonial-stars">★★★★★</div>
            <p className="testimonial-text">{t.text}</p>
            <div className="testimonial-author">
              <div className="testimonial-avatar">{t.avatar}</div>
              <div>
                <div className="testimonial-name">{t.name}</div>
                <div className="testimonial-role">{t.role}</div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </RevealSection>
  );
}

// ─── CTA ───
function CtaSection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section id="cta" ref={ref}>
      <div className="cta-bg" />
      <div style={{ position: 'relative', zIndex: 2 }}>
        <motion.div className="section-label" initial="hidden" animate={isInView ? 'visible' : 'hidden'} variants={fadeUp}>Ready?</motion.div>
        <motion.h2 className="section-title" initial="hidden" animate={isInView ? 'visible' : 'hidden'} variants={fadeUp}>
          Deploy Your Autonomous<br />Sales Engine <em>Today</em>
        </motion.h2>
        <motion.p className="section-sub" initial="hidden" animate={isInView ? 'visible' : 'hidden'} variants={fadeUp} style={{ margin: '0 auto 44px', maxWidth: 520 }}>
          Join 1,200+ revenue teams using Velox to book more qualified meetings with less effort. Start your free trial — no credit card required.
        </motion.p>
        <motion.div initial="hidden" animate={isInView ? 'visible' : 'hidden'} variants={fadeUp}>
          <MagneticButton className="btn-large primary">Get Started Free</MagneticButton>
        </motion.div>
      </div>
    </section>
  );
}

// ─── Footer ───
function Footer() {
  const cols = [
    { title: 'Product', links: ['Features', 'Pricing', 'Integrations', 'Changelog'] },
    { title: 'Company', links: ['About', 'Careers', 'Blog', 'Contact'] },
    { title: 'Legal', links: ['Privacy', 'Terms', 'Security', 'GDPR'] },
  ];

  return (
    <footer>
      <div className="footer-top">
        <div className="footer-brand">
          <div className="footer-brand-name">Velox</div>
          <p>AI-powered outbound that researches, writes, and books meetings — so your team can focus on closing.</p>
        </div>
        <div className="footer-cols">
          {cols.map((col, i) => (
            <div className="footer-col" key={i}>
              <h4>{col.title}</h4>
              {col.links.map((l, j) => <a href="#" key={j}>{l}</a>)}
            </div>
          ))}
        </div>
      </div>
      <div className="footer-bottom">
        <span>© 2026 Velox. All rights reserved.</span>
        <span>Built with precision.</span>
      </div>
    </footer>
  );
}

// ─── App ───
export default function App() {
  const [loaded, setLoaded] = useState(false);
  const handleLoaded = useCallback(() => setLoaded(true), []);

  return (
    <>
      <Loader onComplete={handleLoaded} />
      {loaded && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
          <Nav />
          <Hero />
          <Stats />
          <LogoCarousel />
          <Problem />
          <Transformation />
          <Solution />
          <Features />
          <Pricing />
          <Dashboard />
          <Testimonials />
          <CtaSection />
          <Footer />
        </motion.div>
      )}
    </>
  );
}