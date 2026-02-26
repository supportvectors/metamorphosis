"use client";

import { AgentState } from "@/lib/types";
import { useState, useEffect, useRef, useCallback } from "react";
import { useCopilotChat } from "@copilotkit/react-core";
import { Role, TextMessage } from "@copilotkit/runtime-client-gql";
import { RadarChart } from "./RadarChart";
import { StatusIndicator, StatusType } from "./StatusIndicator";

// define the props expected including the AgentState managed by CopilotKit and the state setter function
interface SelfReviewProps {
  state: AgentState;
  setState: (state: Partial<AgentState>) => void;
}

// The main interactive widget that contains tabs, the review input, and displays the streamed results.
export function SelfReviewInterface({ state, setState }: SelfReviewProps) {
  // Local state for driving the textarea input
  const [inputText, setInputText] = useState(state.original_text || "");
  const [isFocused, setIsFocused] = useState(false);
  // Destructure utilities from useCopilotChat to push the starting user prompt and read the loading status
  const { appendMessage, isLoading } = useCopilotChat();
  const [activeTab, setActiveTab] = useState("input");

  // Track if we have already auto-switched to avoid repeated switching after AI processing
  const hasAutoSwitchedRef = useRef(false);
  const [error, setError] = useState<string | null>(null);

  // Status indicator state (ready, processing, or done) driven by the `isLoading` effect below
  const [status, setStatus] = useState<StatusType>("ready");

  // Effect to manage status transitions based on loading state
  // Effect to manage status transitions based on loading state
  useEffect(() => {
    if (isLoading) {
      setStatus("processing");
    } else if (!isLoading && status === "processing") {
      setStatus("done");
    }
  }, [isLoading, status]);

  // Separate effect to handle the reset timer when status becomes 'done'
  useEffect(() => {
    if (status === "done") {
      const timer = setTimeout(() => {
        setStatus("ready");
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [status]);

  // Auto-switch to Rationalized tab when processing is complete/results arrive
  useEffect(() => {
    if (state.reviewed_text && !hasAutoSwitchedRef.current) {
      setActiveTab("rationalized");
      hasAutoSwitchedRef.current = true;
    }
  }, [state.reviewed_text]);

  const handleSubmit = useCallback(() => {
    const trimmed = inputText.trim();
    if (!trimmed) {
      setError("Please enter your self-review text.");
      return;
    }
    if (trimmed.length < 30) {
      setError("Review is too short. Please enter at least 30 characters for a meaningful analysis.");
      return;
    }

    setError(null);
    // Clear previous AgentState results before starting a new analysis
    setState({
      original_text: trimmed,
      reviewed_text: undefined,
      summarized_text: undefined,
      achievements: undefined,
      evaluation: undefined,
      wordcloud_path: undefined,
      review_complete: false
    });

    // Send the prompt to the language model (ADK agent backend) via CopilotKit
    appendMessage(
      new TextMessage({
        role: Role.User,
        content: `Please process the following review text and extract achievements, generate a summary, and evaluate the review:\n\n${trimmed}`,
      })
    );
  }, [inputText, setState, appendMessage]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputText(e.target.value);
    setError((prev) => (prev ? null : prev)); // Clear error if typing
  }, []);

  const handleFocus = useCallback(() => setIsFocused(true), []);
  const handleBlur = useCallback(() => setIsFocused(false), []);

  const tabs = [
    { id: "input", label: "Input", icon: "✏️" },
    { id: "rationalized", label: "Rationalized", icon: "✨" },
    { id: "summary", label: "Summary", icon: "📝" },
    { id: "visuals", label: "Visuals", icon: "🎨" },
    { id: "achievements", label: "Achievements", icon: "🏆" },
    { id: "scorecard", label: "Scorecard", icon: "📊" },
  ];

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700 pb-12 relative">
      <StatusIndicator status={status} />
      {/* Header */}
      <div className="text-center space-y-4 pt-4">
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-primary">
          Self-Review <span className="text-muted-foreground">Wizard</span>
        </h1>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
          Craft a compelling narrative of your impact. Let AI refine your achievements and evaluate your performance.
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex flex-wrap justify-center gap-2 p-1 bg-muted/30 rounded-xl border border-border/50 backdrop-blur-sm sticky top-4 z-10 shadow-sm">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`
              flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200
              ${activeTab === tab.id
                ? "bg-primary text-primary-foreground shadow-md scale-100"
                : "text-muted-foreground hover:bg-muted hover:text-foreground scale-95 hover:scale-100"
              }
            `}
          >
            <span>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content Areas */}
      <div className="min-h-[500px]">
        {/* INPUT TAB */}
        {activeTab === "input" && (
          <section className="group relative rounded-xl border border-border bg-card shadow-sm transition-all hover:shadow-md animate-in fade-in zoom-in-95 duration-300">
            <div className="p-6 md:p-8 space-y-6">
              <div className="flex justify-between items-center">
                <h2 className="text-xl font-semibold tracking-tight text-card-foreground flex items-center gap-2">
                  Review Input
                </h2>
                {inputText.trim() && (
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-widest">
                    {inputText.length} chars
                  </span>
                )}
              </div>

              <div className={`relative transition-all duration-300 ${isFocused ? "scale-[1.01]" : "scale-100"}`}>
                <textarea
                  value={inputText}
                  onChange={handleInputChange}
                  onFocus={handleFocus}
                  onBlur={handleBlur}
                  placeholder="Reflect on your key accomplishments, challenges overcome, and growth areas..."
                  className={`w-full h-96 p-6 text-lg bg-secondary/30 border rounded-xl resize-y focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent placeholder:text-muted-foreground/50 leading-relaxed font-serif ${error ? "border-destructive focus:ring-destructive" : "border-input"}`}
                />
                {error && (
                  <div className="absolute -bottom-8 left-0 right-0 text-center animate-in fade-in slide-in-from-top-1">
                    <span className="text-sm font-medium text-destructive bg-destructive/10 px-3 py-1 rounded-full border border-destructive/20 inline-flex items-center gap-2">
                      ⚠️ {error}
                    </span>
                  </div>
                )}
              </div>

              <div className="flex justify-end">
                <button
                  onClick={handleSubmit}
                  disabled={!inputText.trim() || isLoading}
                  className="px-8 py-3 bg-primary text-primary-foreground font-medium rounded-lg shadow-lg shadow-primary/20 hover:bg-primary/90 hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none disabled:translate-y-0 flex items-center gap-2"
                >
                  {isLoading ? (
                    <>
                      <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                      Processing...
                    </>
                  ) : (
                    "Analyze & Process Review"
                  )}
                </button>
              </div>
            </div>
          </section>
        )}

        {/* RATIONALIZED TAB */}
        {activeTab === "rationalized" && (
          <section className="rounded-xl border border-border bg-card shadow-sm overflow-hidden animate-in fade-in zoom-in-95 duration-300">
            <div className="border-b border-border bg-muted/40 px-6 py-4 flex justify-between items-center">
              <h2 className="text-lg font-semibold tracking-tight text-card-foreground flex items-center gap-2">
                <span className="text-muted-foreground">✨</span> Refined Narrative
              </h2>
            </div>
            <div className="p-6 md:p-8">
              {isLoading ? (
                <div className="flex flex-col items-center justify-center h-64 text-muted-foreground animate-in fade-in duration-300">
                  <span className="w-8 h-8 border-4 border-primary/30 border-t-primary rounded-full animate-spin mb-4"></span>
                  <p>Refining your narrative...</p>
                </div>
              ) : state.reviewed_text ? (
                <div className="p-6 bg-secondary/30 rounded-lg border border-border/50">
                  <p className="whitespace-pre-wrap text-lg leading-relaxed text-foreground font-serif">{state.reviewed_text}</p>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
                  <p>No refined text generated yet.</p>
                  <p className="text-sm">Submit your review in the Input tab to start.</p>
                </div>
              )}
            </div>
          </section>
        )}

        {/* SUMMARY TAB */}
        {activeTab === "summary" && (
          <section className="rounded-xl border border-border bg-card shadow-sm h-full flex flex-col animate-in fade-in zoom-in-95 duration-300">
            <div className="border-b border-border bg-muted/40 px-6 py-4">
              <h2 className="text-lg font-semibold tracking-tight text-card-foreground">
                Executive Summary
              </h2>
            </div>
            <div className="p-6 flex-grow">
              {isLoading ? (
                <div className="flex flex-col items-center justify-center h-64 text-muted-foreground animate-in fade-in duration-300">
                  <span className="w-8 h-8 border-4 border-primary/30 border-t-primary rounded-full animate-spin mb-4"></span>
                  <p>Generating summary...</p>
                </div>
              ) : state.summarized_text ? (
                <p className="whitespace-pre-wrap text-muted-foreground leading-relaxed text-lg">{state.summarized_text}</p>
              ) : (
                <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
                  <p>No summary available.</p>
                </div>
              )}
            </div>
          </section>
        )}

        {/* VISUALS TAB */}
        {activeTab === "visuals" && (
          <section className="rounded-xl border border-border bg-card shadow-sm h-full flex flex-col animate-in fade-in zoom-in-95 duration-300">
            <div className="border-b border-border bg-muted/40 px-6 py-4">
              <h2 className="text-lg font-semibold tracking-tight text-card-foreground">
                Key Themes
              </h2>
            </div>
            <div className="p-6 flex items-center justify-center flex-grow bg-white/50 min-h-[400px]">
              {isLoading ? (
                <div className="flex flex-col items-center justify-center h-64 text-muted-foreground animate-in fade-in duration-300">
                  <span className="w-8 h-8 border-4 border-primary/30 border-t-primary rounded-full animate-spin mb-4"></span>
                  <p>Creating visualization...</p>
                </div>
              ) : state.wordcloud_path ? (
                <img
                  src={state.wordcloud_path ? `/word_clouds/${state.wordcloud_path.split(/[/\\]/).pop()}?t=${new Date().getTime()}` : ""}
                  alt="Word Cloud Analysis"
                  className="max-w-full max-h-[500px] object-contain drop-shadow-sm hover:scale-105 transition-transform duration-500"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.style.display = "none";
                    const parent = target.parentElement;
                    if (parent) {
                      parent.innerHTML = `<div class="text-destructive text-sm p-4 text-center border border-destructive/20 rounded bg-destructive/5">Could not load visualization</div>`;
                    }
                  }}
                />
              ) : (
                <div className="flex flex-col items-center justify-center text-muted-foreground">
                  <p>No visualization generated.</p>
                </div>
              )}
            </div>
          </section>
        )}

        {/* ACHIEVEMENTS TAB */}
        {activeTab === "achievements" && (
          <section className="space-y-6 animate-in fade-in zoom-in-95 duration-300">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold tracking-tight text-primary">
                Extracted Achievements <span className="ml-2 text-muted-foreground text-lg font-normal">({state.achievements?.items?.length || 0})</span>
              </h2>
              {/* Review Complete Status Badge */}
              {state.review_complete !== undefined && (
                <div
                  className={`px-4 py-1.5 rounded-full border text-sm font-medium flex items-center gap-2 ${state.review_complete
                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                    : "bg-amber-50 text-amber-700 border-amber-200"
                    }`}
                >
                  <span className={`w-2 h-2 rounded-full ${state.review_complete ? "bg-emerald-500" : "bg-amber-500"}`}></span>
                  {state.review_complete
                    ? "Assessment Complete"
                    : "Review In Progress"}
                </div>
              )}
            </div>

            {isLoading ? (
              <div className="flex flex-col items-center justify-center h-64 text-muted-foreground animate-in fade-in duration-300">
                <span className="w-8 h-8 border-4 border-primary/30 border-t-primary rounded-full animate-spin mb-4"></span>
                <p>Extracting achievements...</p>
              </div>
            ) : state.achievements?.items && state.achievements.items.length > 0 ? (
              <div className="grid gap-6 md:grid-cols-1">
                {state.achievements.items.map((achievement, idx) => (
                  <div
                    key={idx}
                    className="group relative bg-card rounded-xl border border-border p-6 shadow-sm hover:shadow-md transition-all hover:border-primary/20"
                  >
                    <div className="flex flex-col md:flex-row md:items-start gap-4 justify-between mb-4">
                      <div>
                        <h3 className="text-lg font-bold text-card-foreground mb-1 group-hover:text-primary transition-colors">
                          {achievement.title}
                        </h3>
                        {achievement.timeframe && (
                          <p className="text-sm text-muted-foreground font-medium">{achievement.timeframe}</p>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {achievement.contribution && (
                          <span className={`px-2.5 py-1 rounded-md text-xs font-semibold border ${achievement.contribution === 'Critical' ? 'bg-indigo-50 text-indigo-700 border-indigo-200' :
                            achievement.contribution === 'Significant' ? 'bg-purple-50 text-purple-700 border-purple-200' :
                              'bg-secondary text-secondary-foreground border-border'
                            }`}>
                            {achievement.contribution} Impact
                          </span>
                        )}
                        <span className="px-2.5 py-1 bg-secondary text-secondary-foreground rounded-md text-xs font-semibold border border-border">
                          {achievement.impact_area}
                        </span>
                        {achievement.ownership_scope && (
                          <span className="px-2.5 py-1 bg-muted text-muted-foreground rounded-md text-xs font-medium border border-border">
                            {achievement.ownership_scope}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="mb-4">
                      <p className="text-muted-foreground leading-relaxed">{achievement.outcome}</p>
                    </div>

                    {achievement.metric_strings && achievement.metric_strings.length > 0 && (
                      <div className="bg-secondary/30 rounded-lg p-4 border border-border/50 mb-4">
                        <p className="text-xs font-bold text-primary uppercase tracking-wider mb-2">Key Metrics</p>
                        <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {achievement.metric_strings.map((metric, mIdx) => (
                            <li key={mIdx} className="flex items-start gap-2 text-sm text-foreground/90">
                              <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary/60 shrink-0"></span>
                              {metric}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {achievement.rationale && (
                      <div className="text-sm text-muted-foreground border-t border-border pt-4 mt-4 bg-gradient-to-b from-transparent to-secondary/10">
                        <span className="font-semibold text-foreground/80">Analysis: </span>
                        {achievement.rationale}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-muted-foreground bg-card rounded-xl border border-border border-dashed">
                <p>No achievements extracted yet.</p>
              </div>
            )}
          </section>
        )}

        {/* SCORECARD TAB */}
        {activeTab === "scorecard" && (
          <section className="rounded-xl border border-border bg-card shadow-sm overflow-hidden animate-in fade-in zoom-in-95 duration-300">
            <div className="border-b border-border bg-muted/40 px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <h2 className="text-xl font-semibold tracking-tight text-card-foreground">
                Review Scorecard
              </h2>
              {state.evaluation && state.evaluation.overall !== undefined && (
                <div className="flex items-center gap-3 bg-background px-4 py-2 rounded-lg border border-border shadow-sm">
                  <span className="text-sm font-medium text-muted-foreground">Overall Rating</span>
                  <span className="text-2xl font-bold text-primary">{state.evaluation.overall}<span className="text-muted-foreground/60 text-lg">/100</span></span>
                </div>
              )}
            </div>

            <div className="p-6 md:p-8 space-y-8">
              {isLoading ? (
                <div className="flex flex-col items-center justify-center h-64 text-muted-foreground animate-in fade-in duration-300">
                  <span className="w-8 h-8 border-4 border-primary/30 border-t-primary rounded-full animate-spin mb-4"></span>
                  <p>Calculating score...</p>
                </div>
              ) : state.evaluation ? (
                <>
                  {state.evaluation.verdict && (
                    <div className="bg-primary/5 border border-primary/20 rounded-lg p-4">
                      <p className="font-medium text-primary text-lg">
                        Verdict: {state.evaluation.verdict}
                      </p>
                    </div>
                  )}

                  {state.evaluation.radar_labels && state.evaluation.radar_values && (
                    <div className="bg-card rounded-xl border border-border p-4 shadow-sm mb-6">
                      <h3 className="text-sm font-semibold text-muted-foreground mb-4 text-center uppercase tracking-wider">Performance Radar</h3>
                      <RadarChart
                        labels={state.evaluation.radar_labels}
                        values={state.evaluation.radar_values}
                      />
                    </div>
                  )}

                  {state.evaluation.metrics && state.evaluation.metrics.length > 0 && (
                    <div className="grid gap-6 md:grid-cols-2">
                      {state.evaluation.metrics.map((metric, idx) => (
                        <div
                          key={idx}
                          className="space-y-3"
                        >
                          <div className="flex justify-between items-end">
                            <h3 className="font-medium text-foreground">{metric.name}</h3>
                            <span className="text-sm font-bold text-primary">{metric.score}/100</span>
                          </div>
                          <div className="w-full bg-secondary rounded-full h-2 overflow-hidden">
                            <div
                              className="bg-primary h-full rounded-full transition-all duration-1000 ease-out"
                              style={{ width: `${metric.score}%` }}
                            />
                          </div>
                          <div className="text-sm space-y-1">
                            <p className="text-muted-foreground">
                              <span className="font-medium text-foreground/80">Why:</span> {metric.rationale}
                            </p>
                            {metric.suggestion && (
                              <p className="text-indigo-600 dark:text-indigo-400">
                                <span className="font-medium">Tip:</span> {metric.suggestion}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {state.evaluation.notes && state.evaluation.notes.length > 0 && (
                    <div className="border-t border-border pt-6 mt-2">
                      <p className="font-semibold text-foreground mb-3 flex items-center gap-2">
                        <span className="text-amber-500">💡</span> Evaluator Notes
                      </p>
                      <ul className="grid gap-2 text-sm text-muted-foreground">
                        {state.evaluation.notes.map((note, idx) => (
                          <li key={idx} className="flex gap-2 p-3 bg-amber-50 dark:bg-amber-950/20 border border-amber-100 dark:border-amber-900/30 rounded-lg">
                            <span>•</span> {note}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              ) : (
                <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
                  <p>No evaluation data available.</p>
                </div>
              )}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
