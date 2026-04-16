"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { ResultsTable } from "@/components/results-table";
import { askQuestion, type AskResponse, type Provider } from "@/lib/api";

type QueryPanelProps = {
  dbFilename: string | null;
  question: string;
  onQuestionChange: (value: string) => void;
  onAsked?: () => void;
};

const PROVIDER_OPTIONS: { value: Provider; label: string; hint: string }[] = [
  { value: "auto", label: "Auto", hint: "Ollama first, Gemini fallback" },
  { value: "ollama", label: "Ollama", hint: "Local only" },
  { value: "gemini", label: "Gemini", hint: "Requires GEMINI_API_KEY" },
];

export function QueryPanel({ dbFilename, question, onQuestionChange, onAsked }: QueryPanelProps) {
  const [result, setResult] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [provider, setProvider] = useState<Provider>("auto");

  const canSubmit = Boolean(dbFilename) && question.trim().length > 0 && !loading;

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!dbFilename || !question.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await askQuestion(dbFilename, question.trim(), 200, provider);
      setResult(res);
      onAsked?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ask failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Ask a question</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="question">
              Question{dbFilename ? ` about ${dbFilename}` : ""}
            </Label>
            <textarea
              id="question"
              value={question}
              onChange={(e) => onQuestionChange(e.target.value)}
              placeholder={
                dbFilename
                  ? "e.g. Show the top 5 customers by total spending"
                  : "Select a database first"
              }
              disabled={!dbFilename || loading}
              rows={3}
              className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs uppercase tracking-wide text-muted-foreground">
              Model provider
            </Label>
            <div className="inline-flex rounded-md border border-input bg-muted/30 p-1" role="radiogroup">
              {PROVIDER_OPTIONS.map((option) => {
                const active = provider === option.value;
                return (
                  <button
                    key={option.value}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    title={option.hint}
                    onClick={() => setProvider(option.value)}
                    disabled={loading}
                    className={`rounded px-3 py-1 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                      active
                        ? "bg-background font-medium shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {option.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button type="submit" disabled={!canSubmit}>
              {loading ? "Generating…" : "Ask"}
            </Button>
            {result?.provider ? (
              <span className="text-xs text-muted-foreground">
                answered via <strong>{result.provider}</strong>
              </span>
            ) : null}
            {error ? <span className="text-sm text-destructive">{error}</span> : null}
          </div>
        </form>

        {result ? (
          <div className="mt-6">
            <ResultsTable result={result} />
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
