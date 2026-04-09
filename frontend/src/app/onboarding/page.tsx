"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import {
  Crosshair,
  ArrowRight,
  ArrowLeft,
  Loader2,
  CheckCircle2,
  Target,
  Search,
  Sparkles,
  Plus,
  Building2,
  Users,
  Briefcase,
  MapPin,
  MessageSquare,
  HelpCircle,
} from "lucide-react";

type Product = {
  id: number;
  name: string;
  description_prompt: string;
  ai_analysis: Record<string, unknown> | null;
  icp_profile: Record<string, unknown> | null;
  search_queries: Record<string, unknown> | null;
  target_industries: string[] | null;
  target_titles: string[] | null;
  target_company_sizes: string[] | null;
  status: string;
};

type ProductListResponse = {
  products: Product[];
  total: number;
};

type RefinementQuestion = {
  id: string;
  question: string;
  type: "multi_select" | "single_select" | "text";
  options?: string[];
  placeholder?: string;
};

export default function OnboardingPage() {
  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);
  const [showWizard, setShowWizard] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    try {
      const data = (await api.products.list()) as ProductListResponse;
      setProducts(data.products);
    } catch {
      // No products yet
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 size={24} className="animate-spin text-primary" />
      </div>
    );
  }

  if (showWizard) {
    return (
      <ProductWizard
        onComplete={() => {
          setShowWizard(false);
          loadProducts();
        }}
        onCancel={() => setShowWizard(false)}
      />
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-grid-4">
        <div>
          <h1 className="font-display text-display-md">Products</h1>
          <p className="text-body-md text-text-secondary mt-1">
            Define your product and let AI find your ideal customers
          </p>
        </div>
        <button onClick={() => setShowWizard(true)} className="btn-primary">
          <Plus size={18} />
          New Product
        </button>
      </div>

      {products.length === 0 ? (
        <EmptyState onStart={() => setShowWizard(true)} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-grid-3">
          {products.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              onRefresh={loadProducts}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function EmptyState({ onStart }: { onStart: () => void }) {
  return (
    <div className="card text-center py-grid-12">
      <Crosshair size={48} className="text-primary mx-auto mb-grid-3" />
      <h2 className="font-display text-display-sm mb-grid-2">
        Start Your First Hunt
      </h2>
      <p className="text-body-md text-text-secondary max-w-md mx-auto mb-grid-4">
        Describe your product or service. Our AI will analyze it, identify your
        ideal customer profile, and autonomously find potential customers.
      </p>
      <button onClick={onStart} className="btn-primary">
        <Target size={18} />
        Define Your Product
      </button>
    </div>
  );
}

function ProductCard({
  product,
  onRefresh,
}: {
  product: Product;
  onRefresh: () => void;
}) {
  const router = useRouter();
  const [analyzing, setAnalyzing] = useState(false);
  const [hunting, setHunting] = useState(false);
  const [progress, setProgress] = useState<{
    phase?: string; percent?: number; detail?: string;
    leads_created?: number; leads_reused?: number;
  }>({});

  // Poll progress when hunting
  useEffect(() => {
    if (product.status !== "hunting") return;
    const poll = async () => {
      try {
        const res = await api.products.huntProgress(product.id);
        setProgress(res.progress || {});
        if (res.progress?.phase === "complete" || res.status === "active") {
          onRefresh();
        }
      } catch { /* ignore */ }
    };
    poll(); // Initial fetch
    const interval = setInterval(poll, 3000);
    return () => clearInterval(interval);
  }, [product.status, product.id, onRefresh]);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      await api.products.analyze(product.id);
      onRefresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleStartHunting = async () => {
    setHunting(true);
    try {
      await api.products.startHunting(product.id);
      onRefresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to start hunting");
    } finally {
      setHunting(false);
    }
  };

  const statusColors: Record<string, string> = {
    draft: "bg-border-light text-text-muted",
    analyzing: "bg-warning/10 text-warning",
    ready: "bg-success/10 text-success",
    hunting: "bg-primary/10 text-primary",
    active: "bg-chart-2/10 text-chart-1",
  };

  const icp = product.icp_profile as Record<string, unknown> | null;
  const percent = progress.percent || 0;

  return (
    <div className="card">
      <div className="flex items-start justify-between mb-grid-2">
        <div>
          <h3 className="font-display text-heading">{product.name}</h3>
          <span
            className={`status-badge mt-1 ${statusColors[product.status] || ""}`}
          >
            {product.status.toUpperCase()}
          </span>
        </div>
        <Crosshair size={20} className="text-text-muted" />
      </div>

      <p className="text-body-sm text-text-secondary mb-grid-3 line-clamp-3">
        {product.description_prompt}
      </p>

      {/* ICP Summary */}
      {icp && (
        <div className="space-y-grid-1 mb-grid-3">
          {product.target_industries && product.target_industries.length > 0 && (
            <div className="flex items-center gap-2 text-body-sm">
              <Building2 size={14} className="text-text-muted" />
              <span className="text-text-secondary">
                {(product.target_industries as string[]).slice(0, 3).join(", ")}
              </span>
            </div>
          )}
          {product.target_titles && product.target_titles.length > 0 && (
            <div className="flex items-center gap-2 text-body-sm">
              <Briefcase size={14} className="text-text-muted" />
              <span className="text-text-secondary">
                {(product.target_titles as string[]).slice(0, 3).join(", ")}
              </span>
            </div>
          )}
          {product.target_company_sizes &&
            product.target_company_sizes.length > 0 && (
              <div className="flex items-center gap-2 text-body-sm">
                <Users size={14} className="text-text-muted" />
                <span className="text-text-secondary">
                  {(product.target_company_sizes as string[]).join(", ")}{" "}
                  employees
                </span>
              </div>
            )}
        </div>
      )}

      {/* Hunt Progress Bar (visible when hunting) */}
      {product.status === "hunting" && (
        <div className="mb-grid-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-label text-text-muted">
              {progress.phase === "searching" ? "Searching..." :
               progress.phase === "analyzing" ? "Analyzing..." :
               progress.phase === "complete" ? "Complete!" : "Starting..."}
            </span>
            <span className="text-body-sm font-mono font-semibold text-primary">{percent}%</span>
          </div>
          <div className="w-full h-2 bg-background rounded-full overflow-hidden border border-border-light">
            <div
              className="h-full rounded-full bg-primary transition-all duration-700 ease-out"
              style={{ width: `${percent}%` }}
            />
          </div>
          {progress.detail && (
            <p className="text-body-sm text-text-muted mt-1 truncate">{progress.detail}</p>
          )}
          {(progress.leads_created || 0) > 0 && (
            <p className="text-body-sm text-success mt-1">
              {progress.leads_created} new leads found
              {(progress.leads_reused || 0) > 0 && `, ${progress.leads_reused} reused`}
            </p>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        {product.status === "draft" && (
          <button
            onClick={handleAnalyze}
            disabled={analyzing}
            className="btn-primary flex-1"
          >
            {analyzing ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Sparkles size={16} />
            )}
            {analyzing ? "Analyzing..." : "AI Analyze"}
          </button>
        )}
        {(product.status === "ready" || product.status === "active") && (
          <button
            onClick={handleStartHunting}
            disabled={hunting}
            className="btn-primary flex-1"
          >
            {hunting ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Search size={16} />
            )}
            {hunting ? "Starting..." : "Start Hunting"}
          </button>
        )}
        {product.status === "hunting" && (
          <div className="btn-secondary flex-1 cursor-default">
            <Loader2 size={16} className="animate-spin text-primary" />
            Hunting in progress...
          </div>
        )}
      </div>
    </div>
  );
}

function ProductWizard({
  onComplete,
  onCancel,
}: {
  onComplete: () => void;
  onCancel: () => void;
}) {
  const [step, setStep] = useState(1);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [refining, setRefining] = useState(false);
  const [product, setProduct] = useState<Product | null>(null);
  const [error, setError] = useState("");

  // Step 2: Clarifying questions
  const [questions, setQuestions] = useState<RefinementQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [loadingQuestions, setLoadingQuestions] = useState(false);

  const handleCreate = async () => {
    if (!name.trim() || !description.trim()) return;
    setSaving(true);
    setError("");

    try {
      const created = (await api.products.create({
        name: name.trim(),
        description_prompt: description.trim(),
      })) as Product;
      setProduct(created);

      // Automatically start analysis
      setAnalyzing(true);
      const analyzed = (await api.products.analyze(created.id)) as Product;
      setProduct(analyzed);

      // Fetch clarifying questions
      setLoadingQuestions(true);
      try {
        const qRes = await api.products.getQuestions(analyzed.id) as { questions: RefinementQuestion[] };
        setQuestions(qRes.questions || []);
      } catch {
        // If questions fail, skip to review
        setQuestions([]);
      }
      setLoadingQuestions(false);
      setStep(2);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create product");
    } finally {
      setSaving(false);
      setAnalyzing(false);
    }
  };

  const handleAnswerChange = (questionId: string, value: string | string[]) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  const handleToggleOption = (questionId: string, option: string) => {
    setAnswers((prev) => {
      const current = (prev[questionId] as string[]) || [];
      if (current.includes(option)) {
        return { ...prev, [questionId]: current.filter((o) => o !== option) };
      }
      return { ...prev, [questionId]: [...current, option] };
    });
  };

  const handleRefineIcp = async () => {
    if (!product) return;
    setRefining(true);
    setError("");

    try {
      const refined = (await api.products.refineIcp(product.id, answers)) as Product;
      setProduct(refined);
      setStep(3);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Refinement failed");
    } finally {
      setRefining(false);
    }
  };

  const handleSkipQuestions = () => {
    setStep(3);
  };

  const icpProfile = product?.icp_profile as Record<string, unknown> | null;
  const aiAnalysis = product?.ai_analysis as Record<string, unknown> | null;
  const searchQueries = product?.search_queries as Record<string, unknown> | null;

  return (
    <div className="max-w-2xl mx-auto">
      {/* Progress — 4 steps */}
      <div className="flex items-center gap-grid-2 mb-grid-6">
        <StepIndicator num={1} active={step === 1} completed={step > 1} label="Describe" />
        <div className="flex-1 h-px bg-border" />
        <StepIndicator num={2} active={step === 2} completed={step > 2} label="Refine" />
        <div className="flex-1 h-px bg-border" />
        <StepIndicator num={3} active={step === 3} completed={step > 3} label="Review" />
        <div className="flex-1 h-px bg-border" />
        <StepIndicator num={4} active={step === 4} completed={false} label="Hunt" />
      </div>

      {/* Step 1: Product Description */}
      {step === 1 && (
        <div className="card">
          <h2 className="font-display text-display-sm mb-grid-1">
            Describe Your Product
          </h2>
          <p className="text-body-md text-text-secondary mb-grid-3">
            Tell us about your product or service in detail. The more context you
            give, the better AI can identify your ideal customers.
          </p>

          {error && (
            <div className="bg-danger/10 text-danger text-body-sm p-grid-2 rounded-sm mb-grid-2">
              {error}
            </div>
          )}

          <div className="space-y-grid-2">
            <div>
              <label className="text-label text-text-muted block mb-1">
                PRODUCT NAME
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input"
                placeholder="e.g. HUNTER.OS, Acme CRM, ..."
                autoFocus
              />
            </div>

            <div>
              <label className="text-label text-text-muted block mb-1">
                PRODUCT DESCRIPTION
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="input min-h-[200px] resize-y"
                placeholder={`Describe your product in detail. Include:\n\n- What does it do?\n- What problem does it solve?\n- Who is it for?\n- What makes it different?\n- What's the pricing model?\n\nExample: "We build an AI-powered cold outreach tool that helps marketing agencies automate their sales process. It finds potential clients, analyzes their content, and sends hyper-personalized messages. Unlike competitors, our tool actually finds the customers for you instead of just sending emails to a list."`}
              />
            </div>
          </div>

          <div className="flex justify-between mt-grid-4">
            <button onClick={onCancel} className="btn-ghost">
              Cancel
            </button>
            <button
              onClick={handleCreate}
              disabled={!name.trim() || !description.trim() || saving || analyzing}
              className="btn-primary"
            >
              {analyzing ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  AI Analyzing...
                </>
              ) : saving ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  Analyze with AI
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Clarifying Questions */}
      {step === 2 && product && (
        <div className="card">
          <h2 className="font-display text-display-sm mb-grid-1 flex items-center gap-2">
            <HelpCircle size={24} className="text-primary" />
            Help Us Find The Right People
          </h2>
          <p className="text-body-md text-text-secondary mb-grid-3">
            Answer a few quick questions to narrow down exactly who to target.
            This dramatically improves search accuracy and saves API calls.
          </p>

          {error && (
            <div className="bg-danger/10 text-danger text-body-sm p-grid-2 rounded-sm mb-grid-2">
              {error}
            </div>
          )}

          {loadingQuestions ? (
            <div className="flex items-center justify-center py-grid-6">
              <Loader2 size={24} className="animate-spin text-primary" />
              <span className="text-body-md text-text-muted ml-2">Generating questions...</span>
            </div>
          ) : (
            <div className="space-y-grid-3">
              {questions.map((q) => (
                <div key={q.id} className="bg-background rounded-md p-grid-3">
                  <label className="text-body-md font-medium block mb-grid-1">
                    {q.question}
                  </label>

                  {q.type === "multi_select" && q.options && (
                    <div className="flex flex-wrap gap-2">
                      {q.options.map((opt) => {
                        const selected = ((answers[q.id] as string[]) || []).includes(opt);
                        return (
                          <button
                            key={opt}
                            onClick={() => handleToggleOption(q.id, opt)}
                            className={`text-body-sm px-3 py-1.5 rounded-md border transition-all ${
                              selected
                                ? "bg-primary/15 border-primary text-primary font-medium"
                                : "bg-surface border-border-light text-text-secondary hover:border-primary/50"
                            }`}
                          >
                            {opt}
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {q.type === "single_select" && q.options && (
                    <div className="flex flex-wrap gap-2">
                      {q.options.map((opt) => {
                        const selected = answers[q.id] === opt;
                        return (
                          <button
                            key={opt}
                            onClick={() => handleAnswerChange(q.id, opt)}
                            className={`text-body-sm px-3 py-1.5 rounded-md border transition-all ${
                              selected
                                ? "bg-primary/15 border-primary text-primary font-medium"
                                : "bg-surface border-border-light text-text-secondary hover:border-primary/50"
                            }`}
                          >
                            {opt}
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {q.type === "text" && (
                    <textarea
                      value={(answers[q.id] as string) || ""}
                      onChange={(e) => handleAnswerChange(q.id, e.target.value)}
                      className="input min-h-[60px] resize-y"
                      placeholder={q.placeholder || "Type your answer..."}
                    />
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="flex justify-between mt-grid-4">
            <button onClick={() => setStep(1)} className="btn-ghost">
              <ArrowLeft size={16} />
              Back
            </button>
            <div className="flex gap-2">
              <button
                onClick={handleSkipQuestions}
                className="btn-ghost text-text-muted"
              >
                Skip
              </button>
              <button
                onClick={handleRefineIcp}
                disabled={refining || Object.keys(answers).length === 0}
                className="btn-primary"
              >
                {refining ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Refining...
                  </>
                ) : (
                  <>
                    Refine & Continue
                    <ArrowRight size={16} />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step 3: Review AI Analysis */}
      {step === 3 && product && (
        <div className="card">
          <h2 className="font-display text-display-sm mb-grid-1">
            Review Your ICP
          </h2>
          <p className="text-body-md text-text-secondary mb-grid-3">
            This is the refined Ideal Customer Profile we&apos;ll use to hunt leads.
          </p>

          <div className="space-y-grid-3">
            {/* Value Proposition */}
            {aiAnalysis && (
              <div className="bg-background rounded-md p-grid-3">
                <h3 className="text-label text-text-muted mb-grid-1">
                  VALUE PROPOSITION
                </h3>
                <p className="text-body-md">
                  {(aiAnalysis as Record<string, string>).summary ||
                    (aiAnalysis as Record<string, string>).core_benefit ||
                    JSON.stringify(aiAnalysis)}
                </p>
              </div>
            )}

            {/* ICP Profile */}
            {icpProfile && (
              <div className="space-y-grid-2">
                <ICPSection
                  icon={<Building2 size={16} />}
                  label="TARGET INDUSTRIES"
                  items={(icpProfile.industries as string[]) || []}
                />
                <ICPSection
                  icon={<Briefcase size={16} />}
                  label="TARGET TITLES"
                  items={(icpProfile.target_titles as string[]) || []}
                />
                <ICPSection
                  icon={<Users size={16} />}
                  label="COMPANY SIZES"
                  items={(icpProfile.company_sizes as string[]) || []}
                />
                {(icpProfile.geography as string[])?.length > 0 && (
                  <ICPSection
                    icon={<MapPin size={16} />}
                    label="GEOGRAPHY"
                    items={(icpProfile.geography as string[]) || []}
                  />
                )}
                <ICPSection
                  icon={<Target size={16} />}
                  label="PAIN POINTS"
                  items={(icpProfile.pain_points as string[]) || []}
                />
              </div>
            )}

            {/* Search Strategies */}
            {searchQueries && (
              <div className="bg-background rounded-md p-grid-3">
                <h3 className="text-label text-text-muted mb-grid-1">
                  SEARCH STRATEGIES
                </h3>
                <div className="flex flex-wrap gap-1">
                  {((searchQueries.google_queries as string[]) || [])
                    .concat((searchQueries.linkedin_queries as string[]) || [])
                    .slice(0, 8)
                    .map((q: string, i: number) => (
                      <span
                        key={i}
                        className="text-body-sm bg-surface border border-border-light rounded-sm px-2 py-0.5"
                      >
                        {q}
                      </span>
                    ))}
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-between mt-grid-4">
            <button onClick={() => setStep(2)} className="btn-ghost">
              <ArrowLeft size={16} />
              Refine Again
            </button>
            <button onClick={() => setStep(4)} className="btn-primary">
              Looks Good, Start Hunting
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Hunting */}
      {step === 4 && product && (
        <HuntingStep product={product} onComplete={onComplete} />
      )}
    </div>
  );
}

function HuntingStep({
  product,
  onComplete,
}: {
  product: Product;
  onComplete: () => void;
}) {
  const router = useRouter();
  const [started, setStarted] = useState(false);
  const [progress, setProgress] = useState<{
    phase?: string; percent?: number; detail?: string;
    leads_created?: number; leads_reused?: number; error?: string;
  }>({});

  useEffect(() => {
    const startHunt = async () => {
      try {
        await api.products.startHunting(product.id);
        setStarted(true);
      } catch (err) {
        alert(err instanceof Error ? err.message : "Failed to start hunting");
      }
    };
    startHunt();
  }, [product.id]);

  // Poll progress every 3 seconds
  useEffect(() => {
    if (!started) return;
    const interval = setInterval(async () => {
      try {
        const res = await api.products.huntProgress(product.id);
        const p = res.progress || {};
        setProgress(p);
        if (p.phase === "complete" || p.phase === "error" || res.status === "active") {
          clearInterval(interval);
          if (p.phase === "complete" || res.status === "active") {
            setTimeout(() => { onComplete(); router.push("/leads"); }, 2000);
          }
        }
      } catch { /* ignore */ }
    }, 3000);
    return () => clearInterval(interval);
  }, [started, product.id, onComplete, router]);

  const percent = progress.percent || 0;
  const phase = progress.phase || "starting";
  const isComplete = phase === "complete";
  const isError = phase === "error";

  const phaseLabels: Record<string, string> = {
    generating_queries: "Generating search queries...",
    searching: "Searching the web...",
    deduplicating: "Removing duplicates...",
    analyzing: "Analyzing results with AI...",
    complete: "Hunt complete!",
    error: "Hunt encountered an error",
    starting: "Launching the hunt...",
  };

  return (
    <div className="card py-grid-6">
      <div className="text-center mb-grid-4">
        {isComplete ? (
          <CheckCircle2 size={40} className="text-success mx-auto mb-grid-2" />
        ) : isError ? (
          <Target size={40} className="text-danger mx-auto mb-grid-2" />
        ) : (
          <Loader2 size={40} className="animate-spin text-primary mx-auto mb-grid-2" />
        )}
        <h2 className="font-display text-display-sm mb-grid-1">
          {isComplete ? "Hunt Complete!" : isError ? "Hunt Failed" : "Hunting in Progress..."}
        </h2>
        <p className="text-body-md text-text-secondary">
          {phaseLabels[phase] || phase}
        </p>
      </div>

      {/* Progress Bar */}
      <div className="max-w-md mx-auto mb-grid-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-label text-text-muted uppercase tracking-widest">Progress</span>
          <span className="text-body-sm font-mono font-semibold text-primary">{percent}%</span>
        </div>
        <div className="w-full h-3 bg-background rounded-full overflow-hidden border border-border-light">
          <div
            className={`h-full rounded-full transition-all duration-700 ease-out ${
              isError ? "bg-danger" : isComplete ? "bg-success" : "bg-primary"
            }`}
            style={{ width: `${percent}%` }}
          />
        </div>
      </div>

      {/* Detail Text */}
      {progress.detail && (
        <p className="text-body-sm text-text-muted text-center mb-grid-3 max-w-lg mx-auto truncate">
          {progress.detail}
        </p>
      )}

      {/* Stats */}
      <div className="flex items-center justify-center gap-grid-4">
        <div className="text-center">
          <p className="font-display text-display-sm text-primary">{progress.leads_created || 0}</p>
          <p className="text-label text-text-muted">NEW LEADS</p>
        </div>
        <div className="text-center">
          <p className="font-display text-display-sm text-chart-1">{progress.leads_reused || 0}</p>
          <p className="text-label text-text-muted">REUSED</p>
        </div>
      </div>

      {isError && progress.error && (
        <div className="mt-grid-3 bg-danger/10 text-danger text-body-sm p-grid-2 rounded-sm text-center">
          {progress.error}
        </div>
      )}

      {isComplete && (
        <p className="text-body-sm text-success text-center mt-grid-3">
          Redirecting to leads page...
        </p>
      )}
    </div>
  );
}

function StepIndicator({
  num,
  active,
  completed,
  label,
}: {
  num: number;
  active: boolean;
  completed: boolean;
  label: string;
}) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center text-body-sm font-semibold
          ${completed ? "bg-success text-white" : active ? "bg-primary text-white" : "bg-border-light text-text-muted"}`}
      >
        {completed ? <CheckCircle2 size={16} /> : num}
      </div>
      <span className="text-label text-text-muted">{label}</span>
    </div>
  );
}

function ICPSection({
  icon,
  label,
  items,
}: {
  icon: React.ReactNode;
  label: string;
  items: string[];
}) {
  if (!items || items.length === 0) return null;

  return (
    <div className="bg-background rounded-md p-grid-2">
      <div className="flex items-center gap-2 mb-grid-1">
        <span className="text-text-muted">{icon}</span>
        <span className="text-label text-text-muted">{label}</span>
      </div>
      <div className="flex flex-wrap gap-1">
        {items.map((item, i) => (
          <span
            key={i}
            className="text-body-sm bg-surface border border-border-light rounded-sm px-2 py-0.5"
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
