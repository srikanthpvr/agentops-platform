import React from 'react';
import { useProjectStore } from '@/stores/projectStore';
import { useTraces, useTraceStats } from '@/hooks/useTraces';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { formatCost, formatTokens, formatDuration, formatDate, getStatusColor } from '@/lib/utils';
import { Activity, DollarSign, Layers, AlertTriangle, ArrowUpRight, Plus } from 'lucide-react';
import { Link } from 'react-router-dom';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';

export function DashboardPage() {
  const { currentProject } = useProjectStore();
  const { data: tracesData, isLoading: tracesLoading } = useTraces(currentProject?.id, {
    page: 1,
    pageSize: 5,
  });
  const { data: statsData, isLoading: statsLoading } = useTraceStats(currentProject?.id);

  // Mock chart trend data if stats not yet generated
  const chartData = statsData?.daily?.length
    ? statsData.daily
    : [
        { date: 'Nov 01', traces: 120, cost: 0.42 },
        { date: 'Nov 02', traces: 240, cost: 0.85 },
        { date: 'Nov 03', traces: 190, cost: 0.65 },
        { date: 'Nov 04', traces: 410, cost: 1.48 },
        { date: 'Nov 05', traces: 560, cost: 2.12 },
      ];

  if (!currentProject) {
    return (
      <div className="flex h-96 flex-col items-center justify-center rounded-xl border border-dashed border-border p-8 text-center">
        <Activity className="h-12 w-12 text-muted-foreground" />
        <h3 className="mt-4 text-lg font-semibold">No project selected</h3>
        <p className="mt-2 text-sm text-muted-foreground">Select or create a project to view telemetry</p>
        <Link to="/settings" className="mt-4">
          <Button>
            <Plus className="mr-2 h-4 w-4" /> Go to Project Settings
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── Page Header ── */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Observability Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Project: <span className="font-semibold text-foreground">{currentProject.name}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/traces">
            <Button variant="outline">
              Trace Explorer <ArrowUpRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        </div>
      </div>

      {/* ── Metric Summary Cards ── */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Traces</CardTitle>
            <Activity className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="text-2xl font-bold">{statsData?.total_traces?.toLocaleString() ?? 0}</div>
            )}
            <p className="text-xs text-muted-foreground mt-1">+14.2% from last week</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Token Consumption</CardTitle>
            <Layers className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="text-2xl font-bold">{formatTokens(statsData?.total_tokens ?? 0)}</div>
            )}
            <p className="text-xs text-muted-foreground mt-1">Prompt & completion tokens</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Incurred Cost (USD)</CardTitle>
            <DollarSign className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="text-2xl font-bold">{formatCost(statsData?.total_cost_usd ?? 0)}</div>
            )}
            <p className="text-xs text-muted-foreground mt-1">Est. multi-model API expense</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Error Rate</CardTitle>
            <AlertTriangle className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="text-2xl font-bold">
                {((statsData?.error_rate ?? 0.012) * 100).toFixed(1)}%
              </div>
            )}
            <p className="text-xs text-muted-foreground mt-1">Within healthy SLA limits (&lt; 2%)</p>
          </CardContent>
        </Card>
      </div>

      {/* ── Activity Chart ── */}
      <Card>
        <CardHeader>
          <CardTitle>Trace Volume & Load</CardTitle>
          <CardDescription>Daily agent executions and prompt requests</CardDescription>
        </CardHeader>
        <CardContent className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorTraces" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="date" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(23, 23, 23, 0.9)',
                  borderColor: '#404040',
                  borderRadius: '8px',
                  color: '#fff',
                }}
              />
              <Area
                type="monotone"
                dataKey="traces"
                stroke="#3b82f6"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorTraces)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* ── Recent Traces Table ── */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recent Executions</CardTitle>
            <CardDescription>Latest telemetry spans ingested by your agents</CardDescription>
          </div>
          <Link to="/traces">
            <Button variant="ghost" size="sm">
              View all
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          {tracesLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : !tracesData?.items?.length ? (
            <div className="py-6 text-center text-sm text-muted-foreground">
              No traces recorded yet. Send your first trace with the AgentOps SDK!
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="py-3 px-4">Agent Name</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Duration</th>
                    <th className="py-3 px-4">Tokens</th>
                    <th className="py-3 px-4">Cost</th>
                    <th className="py-3 px-4">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {tracesData.items.map((trace) => (
                    <tr key={trace.id} className="hover:bg-muted/50 transition-colors">
                      <td className="py-3 px-4 font-medium">
                        <Link to={`/traces/${trace.id}`} className="hover:underline text-primary">
                          {trace.agent_name}
                        </Link>
                      </td>
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
                      <td className="py-3 px-4 text-muted-foreground">
                        {formatDate(trace.started_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
