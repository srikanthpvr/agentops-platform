import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useProjectStore } from '@/stores/projectStore';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from '@/components/ui/dialog';
import { formatDate } from '@/lib/utils';
import { Plus, Play, Database, Award, CheckCircle, Clock } from 'lucide-react';
import { EvalDataset, EvalRun } from '@/types';

export function EvaluationsPage() {
  const { currentProject } = useProjectStore();
  const queryClient = useQueryClient();

  // Dialog states
  const [createDatasetOpen, setCreateDatasetOpen] = useState(false);
  const [datasetName, setDatasetName] = useState('');
  const [datasetDesc, setDatasetDesc] = useState('');

  const [createRunOpen, setCreateRunOpen] = useState(false);
  const [runName, setRunName] = useState('');
  const [selectedDatasetId, setSelectedDatasetId] = useState('');
  const [modelName, setModelName] = useState('gpt-4o');

  // Queries
  const { data: datasetsData, isLoading: datasetsLoading } = useQuery({
    queryKey: ['eval-datasets', currentProject?.id],
    queryFn: () => api.evals.listDatasets(currentProject!.id),
    enabled: !!currentProject?.id,
  });

  const { data: runsData, isLoading: runsLoading } = useQuery({
    queryKey: ['eval-runs', currentProject?.id],
    queryFn: () => api.evals.listRuns(currentProject!.id),
    enabled: !!currentProject?.id,
  });

  // Mutations
  const createDatasetMutation = useMutation({
    mutationFn: (data: { name: string; description?: string }) =>
      api.evals.createDataset(currentProject!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['eval-datasets', currentProject?.id] });
      setCreateDatasetOpen(false);
      setDatasetName('');
      setDatasetDesc('');
    },
  });

  const createRunMutation = useMutation({
    mutationFn: (data: { name: string; dataset_id: string; model_config: any }) =>
      api.evals.createRun(currentProject!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['eval-runs', currentProject?.id] });
      setCreateRunOpen(false);
      setRunName('');
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">EvalBox Sandbox</h1>
          <p className="text-sm text-muted-foreground">
            Benchmark agent performance, score LLM outputs, and run automated evaluations
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Dialog open={createDatasetOpen} onOpenChange={setCreateDatasetOpen}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <Database className="mr-2 h-4 w-4" /> New Dataset
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create Evaluation Dataset</DialogTitle>
                <DialogDescription>Define a benchmark dataset of prompts and gold answers</DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="dsName">Dataset Name</Label>
                  <Input
                    id="dsName"
                    placeholder="Customer Support Golden Set v1"
                    value={datasetName}
                    onChange={(e) => setDatasetName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="dsDesc">Description</Label>
                  <Input
                    id="dsDesc"
                    placeholder="50 complex multi-turn support interactions"
                    value={datasetDesc}
                    onChange={(e) => setDatasetDesc(e.target.value)}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  onClick={() =>
                    createDatasetMutation.mutate({
                      name: datasetName,
                      description: datasetDesc,
                    })
                  }
                  disabled={!datasetName || createDatasetMutation.isPending}
                >
                  Create Dataset
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          <Dialog open={createRunOpen} onOpenChange={setCreateRunOpen}>
            <DialogTrigger asChild>
              <Button>
                <Play className="mr-2 h-4 w-4" /> Run Evaluation
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Launch Evaluation Run</DialogTitle>
                <DialogDescription>Execute an automated benchmark against a dataset</DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="rName">Run Name</Label>
                  <Input
                    id="rName"
                    placeholder="GPT-4o vs Claude 3.5 Sonnet Benchmark"
                    value={runName}
                    onChange={(e) => setRunName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="rDataset">Target Dataset</Label>
                  <select
                    id="rDataset"
                    value={selectedDatasetId}
                    onChange={(e) => setSelectedDatasetId(e.target.value)}
                    className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="">Select dataset...</option>
                    {datasetsData?.items?.map((d: EvalDataset) => (
                      <option key={d.id} value={d.id}>
                        {d.name} ({d.row_count} rows)
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="rModel">Model under test</Label>
                  <Input
                    id="rModel"
                    value={modelName}
                    onChange={(e) => setModelName(e.target.value)}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  onClick={() =>
                    createRunMutation.mutate({
                      name: runName,
                      dataset_id: selectedDatasetId,
                      model_config: { model: modelName, temperature: 0.2 },
                    })
                  }
                  disabled={!runName || !selectedDatasetId || createRunMutation.isPending}
                >
                  Start Run
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <Tabs defaultValue="runs">
        <TabsList>
          <TabsTrigger value="runs">Evaluation Runs</TabsTrigger>
          <TabsTrigger value="datasets">Benchmark Datasets</TabsTrigger>
        </TabsList>

        <TabsContent value="runs" className="pt-4 space-y-4">
          <Card>
            <CardContent className="pt-6">
              {!runsData?.items?.length ? (
                <div className="py-12 text-center text-muted-foreground">
                  No evaluation runs recorded yet. Click &quot;Run Evaluation&quot; to test your agents!
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="py-3 px-4">Run Name</th>
                        <th className="py-3 px-4">Status</th>
                        <th className="py-3 px-4">Model</th>
                        <th className="py-3 px-4">Score (0-1)</th>
                        <th className="py-3 px-4">Started At</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {runsData.items.map((run: EvalRun) => (
                        <tr key={run.id} className="hover:bg-muted/50">
                          <td className="py-3 px-4 font-semibold">{run.name}</td>
                          <td className="py-3 px-4">
                            <Badge variant={run.status === 'completed' ? 'default' : 'secondary'}>
                              {run.status}
                            </Badge>
                          </td>
                          <td className="py-3 px-4 font-mono text-xs">
                            {run.model_config?.model || 'gpt-4o'}
                          </td>
                          <td className="py-3 px-4 font-bold text-primary">
                            {run.avg_score !== null && run.avg_score !== undefined
                              ? `${(run.avg_score * 100).toFixed(1)}%`
                              : 'Pending'}
                          </td>
                          <td className="py-3 px-4 text-muted-foreground">
                            {formatDate(run.created_at)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="datasets" className="pt-4 space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            {datasetsData?.items?.map((ds: EvalDataset) => (
              <Card key={ds.id}>
                <CardHeader>
                  <CardTitle className="text-base">{ds.name}</CardTitle>
                  <CardDescription>{ds.description || 'No description provided'}</CardDescription>
                </CardHeader>
                <CardContent className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{ds.row_count} evaluation pairs</span>
                  <span>{formatDate(ds.created_at)}</span>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
