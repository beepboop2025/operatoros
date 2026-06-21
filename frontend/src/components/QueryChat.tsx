import { useState, useRef, useEffect, FormEvent, ChangeEvent } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queriesApi, clientsApi, getErrorMessage } from '../api/client';
import { useToast } from './Toast';
import type {
  Client,
  QueryItem,
  QuerySource,
  QueryResponse,
  QuerySubmitRequest,
  ClientListResponse,
  QueryListResponse,
} from '../api/client';
import {
  Send,
  Loader2,
  MessageSquare,
  User,
  Bot,
  BookOpen,
  ChevronRight,
  History,
  X,
} from 'lucide-react';
import { formatDateTime } from '../utils/format';
import { Panel, Button, Input, Select } from './textura';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: (string | QuerySource)[];
  isError?: boolean;
  timestamp: string;
}

let msgCounter = 0;
function generateMsgId(): string {
  return `msg-${Date.now()}-${++msgCounter}`;
}

export default function QueryChat() {
  const queryClient = useQueryClient();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [question, setQuestion] = useState<string>('');
  const [clientId, setClientId] = useState<string>('');
  const [showHistory, setShowHistory] = useState<boolean>(false);
  const [conversation, setConversation] = useState<ChatMessage[]>([]);

  const { data: clients } = useQuery<ClientListResponse | Client[]>({
    queryKey: ['clients', 'list-all'],
    queryFn: () => clientsApi.list({ page_size: 200 }),
  });

  const { data: history } = useQuery<QueryListResponse | QueryItem[]>({
    queryKey: ['queries', 'history'],
    queryFn: () => queriesApi.list({ page_size: 50 }),
  });

  const normalizedClients = clients as ClientListResponse | undefined;
  const clientList: Client[] = normalizedClients?.items || normalizedClients?.clients || (Array.isArray(clients) ? clients : []);

  const normalizedHistory = history as QueryListResponse | undefined;
  const historyList: QueryItem[] = normalizedHistory?.items || normalizedHistory?.queries || (Array.isArray(history) ? history : []);

  const toast = useToast();

  const submitMutation = useMutation<QueryResponse, Error, QuerySubmitRequest>({
    mutationFn: queriesApi.submit,
    onSuccess: (data) => {
      setConversation((prev) => [
        ...prev,
        {
          id: generateMsgId(),
          role: 'assistant',
          content: data.answer || data.response || 'No response received.',
          sources: data.sources || data.citations || [],
          timestamp: new Date().toISOString(),
        },
      ]);
      queryClient.invalidateQueries({ queryKey: ['queries'] });
      toast.success('Query processed successfully');
    },
    onError: (err) => {
      const errorMsg = getErrorMessage(err, 'Failed to process query. Please try again.');
      setConversation((prev) => [
        ...prev,
        {
          id: generateMsgId(),
          role: 'assistant',
          content: `Error: ${errorMsg}`,
          isError: true,
          timestamp: new Date().toISOString(),
        },
      ]);
      toast.error(errorMsg);
    },
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation]);

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const q = question.trim();
    if (!q || submitMutation.isPending) return;

    setConversation((prev) => [
      ...prev,
      {
        id: generateMsgId(),
        role: 'user',
        content: q,
        timestamp: new Date().toISOString(),
      },
    ]);
    setQuestion('');
    submitMutation.mutate({
      question: q,
      client_id: clientId || undefined,
    });
  };

  const loadHistoryItem = (item: QueryItem) => {
    setConversation([
      {
        id: generateMsgId(),
        role: 'user',
        content: item.question || item.query || '',
        timestamp: item.created_at || new Date().toISOString(),
      },
      {
        id: generateMsgId(),
        role: 'assistant',
        content: item.answer || item.response || 'No response',
        sources: item.sources || item.citations || [],
        timestamp: item.created_at || new Date().toISOString(),
      },
    ]);
    setShowHistory(false);
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      {/* History sidebar (desktop) */}
      <div className={`
        ${showHistory ? 'fixed inset-0 z-50 lg:relative lg:inset-auto' : 'hidden lg:block'}
        lg:w-72 shrink-0
      `}>
        {showHistory && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-md lg:hidden animate-backdrop" onClick={() => setShowHistory(false)} />
        )}
        <Panel
          className={`
            ${showHistory ? 'fixed right-0 top-0 h-full w-80 z-50' : ''}
            lg:relative lg:w-72 lg:h-full
            flex flex-col
          `}
          overflowHidden
        >
          <div className="px-4 py-3 border-b border-textura-line-subtle flex items-center justify-between">
            <h3 className="text-[13px] font-semibold text-textura-dim flex items-center gap-2">
              <History className="w-4 h-4" /> Query History
            </h3>
            <button className="lg:hidden p-1 text-textura-muted hover:text-textura-dim transition-colors" onClick={() => setShowHistory(false)}>
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {historyList.length === 0 ? (
              <div className="p-6 text-center">
                <MessageSquare className="w-8 h-8 text-textura-muted mx-auto mb-2" />
                <p className="text-xs text-textura-muted">No queries yet</p>
              </div>
            ) : (
              <div className="divide-y divide-textura-line-subtle">
                {historyList.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => loadHistoryItem(item)}
                    className="w-full text-left px-4 py-3 row-hover transition-colors"
                  >
                    <p className="text-sm text-textura-dim truncate">{item.question || item.query}</p>
                    <p className="text-xs text-textura-muted mt-0.5">{formatDateTime(item.created_at)}</p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </Panel>
      </div>

      {/* Main chat area */}
      <Panel className="flex-1 flex flex-col overflow-hidden">
        {/* Chat header */}
        <div className="px-5 py-3 border-b border-textura-line-subtle flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <button
              className="lg:hidden p-1.5 text-textura-dim hover:bg-textura-panel-raised rounded-lg transition-colors"
              onClick={() => setShowHistory(true)}
            >
              <History className="w-4 h-4" />
            </button>
            <div>
              <h2 className="text-[13px] font-semibold text-textura-text">AI Tax &amp; Compliance Assistant</h2>
              <p className="text-xs text-textura-muted">Ask questions about tax law, compliance, or client matters</p>
            </div>
          </div>
          <Select
            value={clientId}
            onChange={(e: ChangeEvent<HTMLSelectElement>) => setClientId(e.target.value)}
            className="w-auto"
          >
            <option value="">General Query</option>
            {clientList.map((c) => (
              <option key={c.id} value={c.id}>{c.firm_name || c.name}</option>
            ))}
          </Select>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {conversation.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center animate-fade-in">
              <div className="w-16 h-16 bg-textura-accent/10 border border-textura-accent/20 rounded-2xl flex items-center justify-center mb-4 glow-blue">
                <Bot className="w-8 h-8 text-textura-accent" />
              </div>
              <h3 className="text-lg font-semibold text-textura-text">How can I help you?</h3>
              <p className="text-sm text-textura-dim mt-1 max-w-md">
                Ask about income tax provisions, compliance deadlines, TDS rates, GST rules, or anything related to your clients.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-6 max-w-lg">
                {[
                  'What is the due date for ITR filing for companies?',
                  'Explain Section 44AD presumptive taxation',
                  'What are the TDS rates for professional fees?',
                  'How to compute HRA exemption for metro cities?',
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => { setQuestion(q); inputRef.current?.focus(); }}
                    className="text-left p-3 bg-textura-panel-raised/50 hover:bg-textura-accent/[0.08] rounded-xl text-xs text-textura-dim hover:text-textura-accent transition-all border border-textura-line-subtle hover:border-textura-accent/20"
                  >
                    <ChevronRight className="w-3 h-3 inline mr-1" />{q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {conversation.map((msg) => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''} animate-fade-in`}>
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 bg-textura-accent/15 border border-textura-accent/20 rounded-lg flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4 text-textura-accent" />
                </div>
              )}
              <div className={`max-w-[75%] ${msg.role === 'user' ? 'order-first' : ''}`}>
                <div
                  className={`px-4 py-3 rounded-2xl text-sm leading-relaxed
                    ${msg.role === 'user'
                      ? 'gradient-brand text-white rounded-br-md shadow-lg shadow-textura-accent/15'
                      : msg.isError
                        ? 'bg-red-500/10 text-red-300 border border-red-500/20 rounded-bl-md'
                        : 'bg-textura-panel-raised/60 text-textura-text border border-textura-line-subtle rounded-bl-md'
                    }
                  `}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {msg.sources.map((src, si) => {
                      const label = typeof src === 'string' ? src : src.title || src.section || `Source ${si + 1}`;
                      return (
                        <span
                          key={`${msg.id}-src-${label}-${si}`}
                          className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-500/10 text-amber-400 text-xs rounded-full border border-amber-500/20"
                        >
                          <BookOpen className="w-3 h-3" />
                          {label}
                        </span>
                      );
                    })}
                  </div>
                )}
                <p className="text-xs text-textura-muted mt-1">
                  {new Date(msg.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
              {msg.role === 'user' && (
                <div className="w-8 h-8 bg-textura-panel-raised border border-textura-line-subtle rounded-lg flex items-center justify-center shrink-0">
                  <User className="w-4 h-4 text-textura-dim" />
                </div>
              )}
            </div>
          ))}

          {submitMutation.isPending && (
            <div className="flex gap-3 animate-fade-in">
              <div className="w-8 h-8 bg-textura-accent/15 border border-textura-accent/20 rounded-lg flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-textura-accent" />
              </div>
              <div className="bg-textura-panel-raised/60 border border-textura-line-subtle rounded-2xl rounded-bl-md px-4 py-3 flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-textura-accent" />
                <span className="text-sm text-textura-dim">Thinking...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="p-4 border-t border-textura-line-subtle shrink-0">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <Input
              ref={inputRef}
              type="text"
              value={question}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setQuestion(e.target.value)}
              placeholder="Ask a question about tax, compliance, or your clients..."
              className="flex-1"
              disabled={submitMutation.isPending}
            />
            <Button
              type="submit"
              variant="gradient"
              icon={<Send className="w-4 h-4" />}
              disabled={!question.trim() || submitMutation.isPending}
              className="shrink-0"
            >
              <span className="hidden sm:inline">Send</span>
            </Button>
          </form>
        </div>
      </Panel>
    </div>
  );
}
