import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
  ChevronDown,
  ChevronRight,
  FileText,
  Loader2,
  MessageSquareText,
  Send,
  Sparkles,
  UserRound,
} from "lucide-react";

import { askDocumentQuestion, getQuestionHistory } from "../lib/api.js";
import { Button } from "../components/ui/Button.jsx";
import { Card } from "../components/ui/Card.jsx";
import { EmptyState } from "../components/ui/EmptyState.jsx";
import { LoadingState } from "../components/ui/LoadingState.jsx";

const suggestedQuestions = [
  "What are the main financial themes in this document?",
  "What risks are discussed in the report?",
  "Which reported figures are most relevant?",
];

function formatTimestamp(value) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleString();
}

function SourceList({ sources = [], sourcePages = [] }) {
  const [expandedSources, setExpandedSources] = useState({});
  if (sources.length === 0 && sourcePages.length === 0) return null;

  return (
    <div className="mt-4 border-t border-border pt-3">
      {sourcePages.length > 0 && <p className="text-xs font-medium text-muted">Sources: {sourcePages.map((page) => `Page ${page}`).join(", ")}</p>}
      {sources.length > 0 && (
        <div className="mt-2 space-y-2">
          {sources.map((source, index) => {
            const sourceKey = `${source.page}-${index}`;
            const isOpen = expandedSources[sourceKey];
            return (
              <div key={sourceKey} className="rounded-md border border-border bg-panelRaised/60">
                <button
                  type="button"
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-medium text-foreground hover:bg-panelRaised"
                  onClick={() => setExpandedSources((current) => ({ ...current, [sourceKey]: !isOpen }))}
                  aria-expanded={isOpen}
                >
                  {isOpen ? <ChevronDown size={15} aria-hidden="true" /> : <ChevronRight size={15} aria-hidden="true" />}
                  <FileText size={14} className="text-accent" aria-hidden="true" />
                  Source: Page {source.page}
                  {source.score !== undefined && <span className="ml-auto text-muted">Match {Math.round(source.score)}</span>}
                </button>
                {isOpen && <p className="border-t border-border px-3 py-3 text-sm leading-6 text-muted">{source.excerpt}</p>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function AssistantMessage({ message }) {
  const insufficientEvidence = message.status === "insufficient_evidence";
  return (
    <div className="flex gap-3">
      <div className="flex size-8 shrink-0 items-center justify-center rounded-md border border-primary/25 bg-primary/10 text-primary"><Bot size={17} aria-hidden="true" /></div>
      <div className="min-w-0 flex-1">
        <div className={`rounded-lg border px-4 py-3 ${insufficientEvidence ? "border-amber-200 bg-amber-50" : "border-border bg-panel"}`}>
          <p className="whitespace-pre-wrap text-sm leading-7 text-foreground">{message.answer}</p>
          {message.disclaimer && <p className="mt-3 text-xs leading-5 text-muted">{message.disclaimer}</p>}
          <SourceList sources={message.sources} sourcePages={message.source_pages} />
        </div>
        {message.created_at && <p className="mt-1.5 text-xs text-muted">{formatTimestamp(message.created_at)}</p>}
      </div>
    </div>
  );
}

function UserMessage({ message }) {
  return (
    <div id={message.anchorId} className="flex justify-end gap-3">
      <div className="max-w-[85%] rounded-lg bg-primary px-4 py-3 text-sm leading-6 text-slate-950 shadow-sm">{message.question}</div>
      <div className="flex size-8 shrink-0 items-center justify-center rounded-md border border-border bg-panelRaised text-muted"><UserRound size={16} aria-hidden="true" /></div>
    </div>
  );
}

function historyToMessages(entries) {
  return entries.flatMap((entry) => [
    { id: `${entry.id}-question`, anchorId: `question-${entry.id}`, type: "user", question: entry.question },
    { id: `${entry.id}-answer`, type: "assistant", ...entry },
  ]);
}

export function ResearchAssistantPage({
  recentDocuments,
  documentsLoading,
  documentsError,
  selectedDocumentId: activeDocumentId,
  onSelectDocument,
  embedded = false,
}) {
  const [selectedDocumentId, setSelectedDocumentId] = useState("");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [requestError, setRequestError] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const conversationEndRef = useRef(null);

  const selectedDocument = useMemo(
    () => recentDocuments.find((document) => document.document_id === selectedDocumentId),
    [recentDocuments, selectedDocumentId],
  );

  useEffect(() => {
    if (activeDocumentId && recentDocuments.some((document) => document.document_id === activeDocumentId)) {
      setSelectedDocumentId(activeDocumentId);
    } else if (!selectedDocumentId && recentDocuments.length > 0) {
      setSelectedDocumentId(recentDocuments[0].document_id);
    }
  }, [activeDocumentId, recentDocuments, selectedDocumentId]);

  useEffect(() => {
    if (!selectedDocumentId) {
      setHistory([]);
      setMessages([]);
      return;
    }

    let active = true;
    setHistoryLoading(true);
    setHistoryError("");
    setRequestError("");
    getQuestionHistory(selectedDocumentId)
      .then((payload) => {
        if (!active) return;
        const entries = [...(payload.questions ?? [])].sort((first, second) => new Date(first.created_at) - new Date(second.created_at));
        setHistory(entries);
        setMessages(historyToMessages(entries));
      })
      .catch((error) => {
        if (!active) return;
        setHistoryError(error.message);
        setHistory([]);
        setMessages([]);
      })
      .finally(() => {
        if (active) setHistoryLoading(false);
      });

    return () => { active = false; };
  }, [selectedDocumentId]);

  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isAsking]);

  async function handleAskQuestion() {
    const normalizedQuestion = question.trim();
    if (!selectedDocumentId) {
      setRequestError("Select a saved document before asking a question.");
      return;
    }
    if (!normalizedQuestion || isAsking) return;

    const pendingId = `pending-${Date.now()}`;
    setMessages((current) => [...current, { id: pendingId, anchorId: pendingId, type: "user", question: normalizedQuestion }]);
    setQuestion("");
    setRequestError("");
    setIsAsking(true);

    try {
      const payload = await askDocumentQuestion(selectedDocumentId, normalizedQuestion);
      if (!payload.success) throw new Error(payload.error ?? "The Ask workspace could not answer that question.");

      const storedEntry = { ...payload, id: payload.history_id ?? `response-${Date.now()}`, created_at: new Date().toISOString() };
      setMessages((current) => [
        ...current.filter((message) => message.id !== pendingId),
        { id: `${storedEntry.id}-question`, anchorId: `question-${storedEntry.id}`, type: "user", question: normalizedQuestion },
        { id: `${storedEntry.id}-answer`, type: "assistant", ...storedEntry },
      ]);
      setHistory((current) => [...current, storedEntry]);
    } catch (error) {
      setMessages((current) => current.filter((message) => message.id !== pendingId));
      setQuestion(normalizedQuestion);
      setRequestError(error.message);
    } finally {
      setIsAsking(false);
    }
  }

  function handleComposerKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleAskQuestion();
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      {!embedded && <section className="flex flex-col gap-4 border-b border-border pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-medium text-primary">Ask</p>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">Ask grounded questions about a saved financial document. Answers include retrieved source pages and excerpts.</p>
        </div>
        {!activeDocumentId && <label className="block min-w-0 lg:w-80">
          <span className="mb-1.5 block text-xs font-medium uppercase tracking-[0.1em] text-muted">Active document</span>
          <select value={selectedDocumentId} onChange={(event) => { setSelectedDocumentId(event.target.value); onSelectDocument?.(event.target.value); }} disabled={documentsLoading || recentDocuments.length === 0} className="h-10 w-full truncate rounded-md border border-border bg-panel px-3 text-sm text-foreground shadow-sm outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10 disabled:cursor-not-allowed disabled:opacity-60">
            {recentDocuments.length === 0 ? <option value="">No saved documents</option> : recentDocuments.map((document) => <option key={document.document_id} value={document.document_id}>{document.filename ?? "Untitled document"}</option>)}
          </select>
        </label>}
      </section>}

      {documentsError && <p className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{documentsError}</p>}
      {documentsLoading ? <LoadingState label="Loading document library" description="Restoring saved documents for research." /> : recentDocuments.length === 0 ? (
        <EmptyState icon={FileText} title="No document selected" description="Upload a PDF in Documents before starting a research conversation." />
      ) : (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_17rem]">
          <Card className="flex min-h-[620px] flex-col overflow-hidden">
            <div className="flex items-center gap-3 border-b border-border px-5 py-4">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-md border border-primary/25 bg-primary/10 text-primary"><MessageSquareText size={18} aria-hidden="true" /></div>
              <div className="min-w-0"><p className="truncate text-sm font-semibold text-foreground" title={selectedDocument?.filename}>{selectedDocument?.filename ?? "Selected document"}</p><p className="mt-0.5 text-xs text-muted">Document-grounded research conversation</p></div>
            </div>
            <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5">
              {historyLoading ? <LoadingState label="Loading previous conversation" /> : historyError ? <p className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{historyError}</p> : messages.length === 0 ? (
                <div className="flex min-h-80 flex-col justify-center">
                  <EmptyState icon={Sparkles} title="Start with a document question" description="The assistant retrieves evidence only from the selected PDF." />
                  <div className="mt-5 flex flex-wrap gap-2">
                    {suggestedQuestions.map((suggestion) => <button key={suggestion} type="button" className="rounded-full border border-border bg-panel px-3 py-2 text-left text-xs text-muted transition-colors hover:border-primary/40 hover:text-foreground" onClick={() => setQuestion(suggestion)}>{suggestion}</button>)}
                  </div>
                </div>
              ) : messages.map((message) => message.type === "user" ? <UserMessage key={message.id} message={message} /> : <AssistantMessage key={message.id} message={message} />)}
              {isAsking && <div className="flex items-center gap-3 text-sm text-muted"><Loader2 className="animate-spin text-primary" size={18} aria-hidden="true" />Retrieving document evidence and preparing an answer...</div>}
              <div ref={conversationEndRef} />
            </div>
            <div className="border-t border-border bg-panel px-4 py-4 sm:px-5">
              {requestError && <p className="mb-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{requestError}</p>}
              <div className="flex items-end gap-3 rounded-lg border border-border bg-panelRaised p-2 focus-within:border-primary focus-within:ring-4 focus-within:ring-primary/10">
                <textarea value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={handleComposerKeyDown} disabled={isAsking} rows={2} placeholder="Ask a question about this document..." className="min-h-14 flex-1 resize-none bg-transparent px-2 py-2 text-sm leading-6 text-foreground outline-none placeholder:text-muted disabled:cursor-not-allowed" />
                <Button onClick={handleAskQuestion} disabled={!question.trim() || isAsking} className="size-10 min-h-10 shrink-0 rounded-md px-0" aria-label="Send research question"><Send size={17} aria-hidden="true" /></Button>
              </div>
              <p className="mt-2 px-1 text-xs text-muted">Enter to send · Shift + Enter for a new line</p>
            </div>
          </Card>
          <aside className="space-y-4">
            <section className="rounded-lg border border-border bg-panel p-4 shadow-panel">
              <p className="text-xs font-medium uppercase tracking-[0.1em] text-muted">Document context</p>
              <p className="mt-3 truncate text-sm font-semibold text-foreground" title={selectedDocument?.filename}>{selectedDocument?.filename ?? "Selected document"}</p>
              <dl className="mt-3 space-y-2 text-xs text-muted"><div className="flex justify-between gap-3"><dt>Pages</dt><dd className="font-medium text-foreground">{selectedDocument?.pages ?? "-"}</dd></div><div className="flex justify-between gap-3"><dt>Words</dt><dd className="font-medium text-foreground">{Number(selectedDocument?.words ?? 0).toLocaleString()}</dd></div></dl>
            </section>
            <section className="rounded-lg border border-border bg-panel p-4 shadow-panel">
              <p className="text-xs font-medium uppercase tracking-[0.1em] text-muted">Previous questions</p>
              {history.length === 0 ? <p className="mt-3 text-sm leading-6 text-muted">Questions asked for this document will appear here.</p> : <div className="mt-3 space-y-1">{history.slice().reverse().map((entry) => <button key={entry.id} type="button" className="w-full truncate rounded-md px-2 py-2 text-left text-xs text-muted transition-colors hover:bg-panelRaised hover:text-foreground" onClick={() => document.getElementById(`question-${entry.id}`)?.scrollIntoView({ behavior: "smooth", block: "center" })} title={entry.question}>{entry.question}</button>)}</div>}
            </section>
          </aside>
        </div>
      )}
    </div>
  );
}
