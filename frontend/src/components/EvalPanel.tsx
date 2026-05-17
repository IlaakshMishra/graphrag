import { useEffect, useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  FlaskConical,
  Loader2,
  Workflow,
} from "lucide-react";
import { postEvaluate, postEvaluatePipeline } from "../api/client";
import type {
  EvaluateApiResponse,
  PipelineEvaluateApiResponse,
} from "../types";

const METRIC_LABELS: Record<string, string> = {
  faithfulness: "Faithfulness",
  answer_relevancy: "Answer relevancy",
  context_precision: "Context precision",
  context_recall: "Context recall",
};

function RelevancyHero({
  score,
  subtitle,
}: {
  score: number;
  subtitle?: string;
}) {
  const pct = Math.max(0, Math.min(1, score)) * 100;
  const tone =
    score >= 0.8 ? "text-emerald-300" : score >= 0.5 ? "text-violet-300" : "text-amber-300";

  return (
    <div className="rounded-lg border border-violet-500/25 bg-violet-500/5 px-4 py-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-zinc-500">
            Relevancy score
          </div>
          <div className={`text-3xl font-semibold tabular-nums ${tone}`}>
            {score.toFixed(3)}
          </div>
        </div>
        <div className="h-2 w-32 overflow-hidden rounded-full bg-ink-700">
          <div
            className="h-full rounded-full bg-gradient-to-r from-violet-600 to-emerald-500 transition-[width]"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
      {subtitle && (
        <p className="mt-2 text-[11px] leading-relaxed text-zinc-500">{subtitle}</p>
      )}
    </div>
  );
}

function ScoreBar({ name, value }: { name: string; value: number }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  const label = METRIC_LABELS[name] ?? name.replace(/_/g, " ");
  const tone =
    value >= 0.8
      ? "bg-emerald-500"
      : value >= 0.5
      ? "bg-violet-500"
      : "bg-amber-500";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-zinc-300 capitalize">{label}</span>
        <span className="font-mono text-zinc-200">{value.toFixed(3)}</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-700">
        <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

interface Props {
  /** Prefills pipeline namespace when set */
  activeNamespace?: string | null;
}

export function EvalPanel({ activeNamespace }: Props) {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [contextText, setContextText] = useState("");
  const [groundTruth, setGroundTruth] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<EvaluateApiResponse | null>(null);

  const [pipeOpen, setPipeOpen] = useState(false);
  const [pipeNs, setPipeNs] = useState("");
  const [pipeQuestions, setPipeQuestions] = useState("");
  const [pipeGt, setPipeGt] = useState("");
  const [pipeRunning, setPipeRunning] = useState(false);
  const [pipeError, setPipeError] = useState<string | null>(null);
  const [pipeResult, setPipeResult] = useState<PipelineEvaluateApiResponse | null>(
    null
  );

  useEffect(() => {
    if (activeNamespace) {
      setPipeNs((prev) => (prev.trim() ? prev : activeNamespace));
    }
  }, [activeNamespace]);

  const run = async () => {
    setError(null);
    setResult(null);
    if (!question.trim() || !answer.trim() || !contextText.trim()) {
      setError("question, answer, and context are required");
      return;
    }
    const contexts = contextText
      .split(/\n\s*---+\s*\n/g)
      .map((s) => s.trim())
      .filter(Boolean);

    setRunning(true);
    try {
      const res = await postEvaluate({
        questions: [question.trim()],
        answers: [answer.trim()],
        contexts: [contexts.length ? contexts : [contextText.trim()]],
        ground_truths: groundTruth.trim() ? [groundTruth.trim()] : [],
      });
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "evaluation failed");
    } finally {
      setRunning(false);
    }
  };

  const runPipeline = async () => {
    setPipeError(null);
    setPipeResult(null);
    const ns = (pipeNs || activeNamespace || "").trim();
    if (!ns) {
      setPipeError("Enter a Pinecone namespace (or upload a doc and use active namespace).");
      return;
    }
    const qs = pipeQuestions
      .split(/\n/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (!qs.length) {
      setPipeError("Add at least one question (one per line).");
      return;
    }
    const gtLines = pipeGt.split(/\n/);
    let ground_truths: string[] | undefined;
    if (pipeGt.trim()) {
      const aligned = qs.map((_, i) => (gtLines[i] ?? "").trim());
      if (aligned.some((g) => !g)) {
        setPipeError(
          "Ground truths: one non-empty line per question (same order as questions)."
        );
        return;
      }
      ground_truths = aligned;
    }

    setPipeRunning(true);
    try {
      const res = await postEvaluatePipeline({
        namespace: ns,
        questions: qs,
        ground_truths,
        session_id: "eval-pipeline-ui",
      });
      setPipeResult(res);
    } catch (err: unknown) {
      setPipeError(err instanceof Error ? err.message : "pipeline evaluation failed");
    } finally {
      setPipeRunning(false);
    }
  };

  return (
    <div className="card overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <div className="flex items-center gap-2">
          <FlaskConical size={16} className="text-violet-300" />
          <span className="text-sm font-medium text-zinc-100">
            Evaluation pipeline & relevancy
          </span>
          <span className="rounded-full bg-violet-500/15 px-2 py-0.5 text-[10px] uppercase tracking-wide text-violet-300">
            RAGAS
          </span>
        </div>
        {open ? (
          <ChevronUp size={16} className="text-zinc-400" />
        ) : (
          <ChevronDown size={16} className="text-zinc-400" />
        )}
      </button>

      {open && (
        <div className="border-t border-zinc-800/80 p-4 space-y-6">
          {/* Manual batch */}
          <div className="space-y-4">
            <div className="text-xs font-medium text-zinc-400">
              Manual evaluation — paste question, generated answer, and retrieved
              contexts (already produced by your RAG run).
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-1">
                <label className="text-xs text-zinc-400">Question</label>
                <textarea
                  rows={2}
                  className="input"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="What is the warranty period?"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-zinc-400">Generated answer</label>
                <textarea
                  rows={2}
                  className="input"
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder="The warranty covers …"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-zinc-400">
                Retrieved contexts{" "}
                <span className="text-zinc-500">
                  (separate chunks with a line containing only ---)
                </span>
              </label>
              <textarea
                rows={5}
                className="input font-mono text-xs"
                value={contextText}
                onChange={(e) => setContextText(e.target.value)}
                placeholder={"chunk one\n---\nchunk two"}
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs text-zinc-400">
                Ground truth{" "}
                <span className="text-zinc-500">(optional — enables context recall)</span>
              </label>
              <textarea
                rows={2}
                className="input"
                value={groundTruth}
                onChange={(e) => setGroundTruth(e.target.value)}
                placeholder="The reference answer …"
              />
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={run}
                disabled={running}
                className="btn-primary"
              >
                {running ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <FlaskConical size={14} />
                )}
                Run manual evaluation
              </button>
              {error && (
                <span className="text-xs text-red-300">{error}</span>
              )}
            </div>

            {result && (
              <div className="space-y-3 rounded-lg border border-zinc-800/80 bg-ink-800/40 p-4">
                <RelevancyHero
                  score={result.relevancy_score}
                  subtitle={result.relevancy_breakdown?.description}
                />
                <div className="flex items-center justify-between text-xs text-zinc-500">
                  <span>{result.sample_count} sample(s)</span>
                  <span className="font-mono">
                    {result.metrics_used.join(", ")}
                  </span>
                </div>
                <div className="space-y-3">
                  {Object.entries(result.scores).map(([name, val]) => (
                    <ScoreBar key={name} name={name} value={val} />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Pipeline */}
          <div className="rounded-xl border border-zinc-800/60 bg-ink-900/30">
            <button
              type="button"
              onClick={() => setPipeOpen((v) => !v)}
              className="flex w-full items-center justify-between px-4 py-3 text-left"
            >
              <div className="flex items-center gap-2">
                <Workflow size={16} className="text-emerald-400" />
                <span className="text-sm font-medium text-zinc-100">
                  End-to-end pipeline
                </span>
                <span className="text-[11px] text-zinc-500">
                  live RAG → RAGAS → relevancy
                </span>
              </div>
              {pipeOpen ? (
                <ChevronUp size={16} className="text-zinc-400" />
              ) : (
                <ChevronDown size={16} className="text-zinc-400" />
              )}
            </button>

            {pipeOpen && (
              <div className="space-y-3 border-t border-zinc-800/60 px-4 py-4">
                <p className="text-xs text-zinc-500">
                  Runs your LangGraph chain (retrieve → grade → generate) for each
                  line, then scores answers against retrieved passages.
                </p>
                <div className="space-y-1">
                  <label className="text-xs text-zinc-400">Namespace</label>
                  <input
                    className="input font-mono text-xs"
                    value={pipeNs}
                    onChange={(e) => setPipeNs(e.target.value)}
                    placeholder={activeNamespace || "upload-abc123…"}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-zinc-400">
                    Questions <span className="text-zinc-500">(one per line)</span>
                  </label>
                  <textarea
                    rows={4}
                    className="input font-mono text-xs"
                    value={pipeQuestions}
                    onChange={(e) => setPipeQuestions(e.target.value)}
                    placeholder={"What is covered?\nWho is the vendor?"}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-zinc-400">
                    Ground truths{" "}
                    <span className="text-zinc-500">
                      (optional — one line per question, same order)
                    </span>
                  </label>
                  <textarea
                    rows={3}
                    className="input font-mono text-xs"
                    value={pipeGt}
                    onChange={(e) => setPipeGt(e.target.value)}
                    placeholder="Leave empty, or align line-by-line with questions"
                  />
                </div>
                <button
                  type="button"
                  onClick={runPipeline}
                  disabled={pipeRunning}
                  className="btn-primary"
                >
                  {pipeRunning ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Workflow size={14} />
                  )}
                  Run pipeline evaluation
                </button>
                {pipeError && (
                  <div className="text-xs text-red-300">{pipeError}</div>
                )}

                {pipeResult && (
                  <div className="space-y-4 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">
                    <RelevancyHero
                      score={pipeResult.relevancy_score}
                      subtitle={pipeResult.relevancy_breakdown?.description}
                    />
                    <div className="text-xs text-zinc-500">
                      Namespace{" "}
                      <code className="text-zinc-300">{pipeResult.namespace}</code> ·{" "}
                      {pipeResult.sample_count} question(s)
                    </div>
                    <div className="space-y-3">
                      {Object.entries(pipeResult.aggregate_scores).map(
                        ([name, val]) => (
                          <ScoreBar key={name} name={name} value={val} />
                        )
                      )}
                    </div>
                    <div className="space-y-2 text-xs">
                      <div className="font-medium text-zinc-300">Per question</div>
                      {pipeResult.per_question.map((row, i) => (
                        <div
                          key={`${row.question.slice(0, 24)}-${i}`}
                          className="rounded-md border border-zinc-800/80 bg-ink-950/50 p-3 space-y-1"
                        >
                          <div className="text-zinc-400 line-clamp-2">{row.question}</div>
                          <div className="flex flex-wrap gap-3 text-[11px] text-zinc-500">
                            <span>
                              relevancy:{" "}
                              <span className="font-mono text-violet-300">
                                {row.relevancy_score.toFixed(3)}
                              </span>
                            </span>
                            <span>ctx used: {row.contexts_used}</span>
                            <span>retrieved: {row.retrieved_count}</span>
                            <span>after grader: {row.relevant_count_after_grader}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
