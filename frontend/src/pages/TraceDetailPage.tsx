import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useProjectStore } from '@/stores/projectStore';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { formatCost, formatTokens, formatDuration, formatDate, getStatusColor } from '@/lib/utils';
import { ArrowLeft, Clock, DollarSign, Layers, CheckCircle2, XCircle, ChevronDown, ChevronRight, Terminal } from 'lucide-react';
import { Span } from '@/types';

export function TraceDetailPage() {
  const { traceId } = useParams<{ traceId: string }>();
  const { currentProject } = useProjectStore();
  const [expandedSpans, setExpandedSpans] = useState<Record<string, boolean>>({});

  const { data: trace, isLoading } = useQuery({
    queryKey: ['trace', currentProject?.id, traceId],
    queryFn: () => api.traces.get(currentProject!.id, traceId!),
    enabled: !!currentProject?.id && !!traceId,
  });

  const toggleSpan = (spanId: string) => {
    setExpandedSpans((prev) => ({ ...prev, [spanId]: !prev[spanId] }));
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!trace) {
    return (
      <div className="py-12 text-center">
        <p className="text-muted-foreground">Trace not found.</p>
        <Link to="/traces" className="mt-4 inline-block">
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to traces
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <div className="flex items-center gap-4">
        <Link to="/traces">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">{trace.agent_name}</h1>
            <Badge variant="outline" className={getStatusColor(trace.status)}>
              {trace.status}
            </Badge>
          </div>
          <p className="font-mono text-xs text-muted-foreground mt-1">Trace ID: {trace.id}</p>
        </div>
      </div>

      {/* ── Key Metrics Overview ── */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs uppercase text-muted-foreground">Duration</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">{formatDuration(trace.duration_ms ?? 0)}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs uppercase text-muted-foreground">Total Tokens</CardTitle>
            <Layers className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">{formatTokens(trace.total_tokens)}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs uppercase text-muted-foreground">Incurred Cost</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">{formatCost(trace.total_cost_usd)}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs uppercase text-muted-foreground">Session</CardTitle>
            <Terminal className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="truncate font-mono text-xs">{trace.session_id || 'N/A'}</div>
          </CardContent>
        </Card>
      </div>

      {/* ── Spans & Timeline ── */}
      <Tabs defaultValue="spans">
        <TabsList>
          <TabsTrigger value="spans">Execution Waterfall ({trace.spans?.length ?? 0} spans)</TabsTrigger>
          <TabsTrigger value="metadata">Metadata & Environment</TabsTrigger>
        </TabsList>

        <TabsContent value="spans" className="space-y-4 pt-4">
          {!trace.spans?.length ? (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                No child spans logged for this execution trace.
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {trace.spans.map((span: Span) => {
                const isExpanded = !!expandedSpans[span.id];
                return (
                  <Card key={span.id} className="overflow-hidden border border-border">
                    <div
                      onClick={() => toggleSpan(span.id)}
                      className="flex cursor-pointer items-center justify-between p-4 hover:bg-muted/40 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-muted-foreground" />
                        )}
                        <span className="font-semibold text-sm">{span.name}</span>
                        <Badge variant="secondary" className="text-xs">
                          {span.span_type}
                        </Badge>
                        {span.model && (
                          <span className="font-mono text-xs text-muted-foreground">
                            {span.model}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>{formatDuration(span.latency_ms ?? 0)}</span>
                        <span>{formatTokens((span.tokens_input ?? 0) + (span.tokens_output ?? 0))} tok</span>
                        <span>{formatCost(span.cost_usd)}</span>
                        {span.error ? (
                          <XCircle className="h-4 w-4 text-destructive" />
                        ) : (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        )}
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="border-t border-border bg-muted/20 p-4 space-y-4 text-sm font-mono">
                        {span.error && (
                          <div className="rounded bg-destructive/15 p-3 text-destructive">
                            <p className="font-bold">Error Output:</p>
                            <pre className="mt-1 whitespace-pre-wrap text-xs">{span.error}</pre>
                          </div>
                        )}
                        {span.input && (
                          <div>
                            <p className="font-bold text-xs uppercase text-muted-foreground mb-1">
                              Input Payload:
                            </p>
                            <pre className="rounded bg-background p-3 text-xs overflow-x-auto border border-border">
                              {span.input}
                            </pre>
                          </div>
                        )}
                        {span.output && (
                          <div>
                            <p className="font-bold text-xs uppercase text-muted-foreground mb-1">
                              Output Response:
                            </p>
                            <pre className="rounded bg-background p-3 text-xs overflow-x-auto border border-border">
                              {span.output}
                            </pre>
                          </div>
                        )}
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>
          )}
        </TabsContent>

        <TabsContent value="metadata" className="pt-4">
          <Card>
            <CardHeader>
              <CardTitle>Trace Metadata</CardTitle>
              <CardDescription>Custom tags and environment parameters recorded by the agent</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="rounded bg-muted p-4 text-xs font-mono overflow-x-auto">
                {JSON.stringify(trace.metadata || {}, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
