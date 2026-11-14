import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useProjectStore } from '@/stores/projectStore';
import { useTraces } from '@/hooks/useTraces';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { formatCost, formatTokens, formatDuration, formatDate, getStatusColor } from '@/lib/utils';
import { Search, Filter, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react';
import { TraceStatus } from '@/types';

export function TracesPage() {
  const { currentProject } = useProjectStore();
  const [page, setPage] = useState(1);
  const [searchAgent, setSearchAgent] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const { data, isLoading, refetch } = useTraces(currentProject?.id, {
    page,
    pageSize: 15,
    agentName: searchAgent || undefined,
    status: statusFilter !== 'all' ? (statusFilter as TraceStatus) : undefined,
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Trace Explorer</h1>
          <p className="text-sm text-muted-foreground">
            Search, inspect, and debug distributed execution traces
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" /> Refresh
        </Button>
      </div>

      {/* ── Filters ── */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Filter by agent name..."
                value={searchAgent}
                onChange={(e) => {
                  setSearchAgent(e.target.value);
                  setPage(1);
                }}
                className="pl-9"
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <select
                aria-label="Filter traces by status"
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="all">All Statuses</option>
                <option value="success">Success</option>
                <option value="error">Error</option>
                <option value="running">Running</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Table ── */}
      <Card>
        <CardContent className="pt-6">
          {isLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : !data?.items?.length ? (
            <div className="py-12 text-center text-muted-foreground">
              No matching traces found for this project.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="py-3 px-4">Trace ID</th>
                    <th className="py-3 px-4">Agent</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Duration</th>
                    <th className="py-3 px-4">Tokens</th>
                    <th className="py-3 px-4">Cost</th>
                    <th className="py-3 px-4">Session</th>
                    <th className="py-3 px-4">Started At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {data.items.map((trace) => (
                    <tr key={trace.id} className="hover:bg-muted/50 transition-colors">
                      <td className="py-3 px-4 font-mono text-xs text-primary font-medium">
                        <Link to={`/traces/${trace.id}`} className="hover:underline">
                          {trace.id.substring(0, 8)}...
                        </Link>
                      </td>
                      <td className="py-3 px-4 font-medium">{trace.agent_name}</td>
                      <td className="py-3 px-4">
                        <Badge variant="outline" className={getStatusColor(trace.status)}>
                          {trace.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {formatDuration(trace.duration_ms ?? 0)}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {formatTokens(trace.total_tokens)}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {formatCost(trace.total_cost_usd)}
                      </td>
                      <td className="py-3 px-4 font-mono text-xs text-muted-foreground">
                        {trace.session_id || '—'}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {formatDate(trace.started_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* ── Pagination ── */}
              <div className="mt-4 flex items-center justify-between border-t border-border pt-4 text-sm text-muted-foreground">
                <div>
                  Page {data.page} of {data.pages} ({data.total} total traces)
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={data.page <= 1}
                    onClick={() => setPage((p) => Math.max(p - 1, 1))}
                  >
                    <ChevronLeft className="h-4 w-4" /> Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={data.page >= data.pages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
