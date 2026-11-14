import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useProjectStore } from '@/stores/projectStore';
import { useAuthStore } from '@/stores/authStore';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
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
import { Key, CreditCard, Copy, Check, Trash2, Plus, Sparkles } from 'lucide-react';
import { APIKey } from '@/types';

export function SettingsPage() {
  const { user } = useAuthStore();
  const { currentProject, setProjects, setCurrentProject } = useProjectStore();
  const queryClient = useQueryClient();

  const [createKeyOpen, setCreateKeyOpen] = useState(false);
  const [keyName, setKeyName] = useState('');
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // New project state
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDesc, setNewProjectDesc] = useState('');

  // Queries
  const { data: apiKeysData } = useQuery({
    queryKey: ['api-keys', currentProject?.id],
    queryFn: () => api.projects.listApiKeys(currentProject!.id),
    enabled: !!currentProject?.id,
  });

  // Mutations
  const createApiKeyMutation = useMutation({
    mutationFn: (name: string) => api.projects.createApiKey(currentProject!.id, { name }),
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys', currentProject?.id] });
      setGeneratedKey(data.full_key);
      setKeyName('');
    },
  });

  const revokeApiKeyMutation = useMutation({
    mutationFn: (keyId: string) => api.projects.revokeApiKey(currentProject!.id, keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys', currentProject?.id] });
    },
  });

  const createProjectMutation = useMutation({
    mutationFn: (data: { name: string; description?: string }) => api.projects.create(data),
    onSuccess: (project: any) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setCurrentProject(project);
      setNewProjectName('');
      setNewProjectDesc('');
    },
  });

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Manage projects, access keys, billing subscriptions, and team access
        </p>
      </div>

      <Tabs defaultValue="apikeys">
        <TabsList>
          <TabsTrigger value="apikeys">API Keys (Ingestion)</TabsTrigger>
          <TabsTrigger value="billing">Plan & Billing</TabsTrigger>
          <TabsTrigger value="general">Project Profile</TabsTrigger>
        </TabsList>

        {/* ── API Keys Tab ── */}
        <TabsContent value="apikeys" className="pt-4 space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Ingestion API Keys</CardTitle>
                <CardDescription>
                  Use these secret keys with the AgentOps SDK to send telemetry to this project
                </CardDescription>
              </div>
              <Dialog
                open={createKeyOpen}
                onOpenChange={(open) => {
                  setCreateKeyOpen(open);
                  if (!open) setGeneratedKey(null);
                }}
              >
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="mr-2 h-4 w-4" /> Generate New Key
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Generate AgentOps API Key</DialogTitle>
                    <DialogDescription>
                      Keys authenticate your backend agent runs against project &apos;{currentProject?.name}&apos;.
                    </DialogDescription>
                  </DialogHeader>

                  {!generatedKey ? (
                    <div className="space-y-4 py-4">
                      <div className="space-y-2">
                        <Label htmlFor="keyName">Key Description / Purpose</Label>
                        <Input
                          id="keyName"
                          placeholder="Production Agent Fleet"
                          value={keyName}
                          onChange={(e) => setKeyName(e.target.value)}
                        />
                      </div>
                      <DialogFooter>
                        <Button
                          onClick={() => createApiKeyMutation.mutate(keyName)}
                          disabled={!keyName || createApiKeyMutation.isPending}
                        >
                          Generate Key
                        </Button>
                      </DialogFooter>
                    </div>
                  ) : (
                    <div className="space-y-4 py-4">
                      <div className="rounded-md bg-amber-500/15 p-3 text-xs text-amber-500">
                        Make sure to copy this key now! You won&apos;t be able to see it again.
                      </div>
                      <div className="flex items-center gap-2">
                        <Input readOnly value={generatedKey} className="font-mono text-xs" />
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => copyToClipboard(generatedKey)}
                        >
                          {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                        </Button>
                      </div>
                      <DialogFooter>
                        <Button onClick={() => setCreateKeyOpen(false)}>Done</Button>
                      </DialogFooter>
                    </div>
                  )}
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                    <tr>
                      <th className="py-3 px-4">Key Name</th>
                      <th className="py-3 px-4">Prefix</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Created At</th>
                      <th className="py-3 px-4">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {apiKeysData?.items?.map((key: APIKey) => (
                      <tr key={key.id} className="hover:bg-muted/50">
                        <td className="py-3 px-4 font-semibold">{key.name}</td>
                        <td className="py-3 px-4 font-mono text-xs">{key.key_prefix}...</td>
                        <td className="py-3 px-4">
                          <Badge variant={key.is_active ? 'default' : 'destructive'}>
                            {key.is_active ? 'Active' : 'Revoked'}
                          </Badge>
                        </td>
                        <td className="py-3 px-4 text-muted-foreground">
                          {formatDate(key.created_at)}
                        </td>
                        <td className="py-3 px-4">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive hover:bg-destructive/10"
                            onClick={() => revokeApiKeyMutation.mutate(key.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Billing Tab ── */}
        <TabsContent value="billing" className="pt-4 space-y-4">
          <div className="grid gap-6 md:grid-cols-2">
            <Card className="border-primary/50 relative overflow-hidden">
              <div className="absolute top-0 right-0 bg-primary px-3 py-1 text-[10px] font-bold uppercase text-primary-foreground">
                Current Plan
              </div>
              <CardHeader>
                <CardTitle className="text-xl">Developer Free Tier</CardTitle>
                <CardDescription>Ideal for prototyping and early-stage AI agent builders</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-3xl font-bold">$0 <span className="text-sm font-normal text-muted-foreground">/ month</span></div>
                <div className="space-y-2">
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>Traces Used</span>
                    <span>1,420 / 10,000 (14.2%)</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                    <div className="h-full bg-primary" style={{ width: '14.2%' }} />
                  </div>
                </div>
                <ul className="space-y-2 text-xs text-muted-foreground">
                  <li>✓ 10,000 traces included per month</li>
                  <li>✓ 7-day retention of execution telemetry</li>
                  <li>✓ Presidio PII scanning guardrails</li>
                </ul>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-xl">
                  <Sparkles className="h-5 w-5 text-amber-500" /> Upgrade to Pro
                </CardTitle>
                <CardDescription>Scale your production AI agents with enterprise-grade SLA</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-3xl font-bold">$49 <span className="text-sm font-normal text-muted-foreground">/ month</span></div>
                <ul className="space-y-2 text-xs text-muted-foreground">
                  <li>✓ 500,000 traces included</li>
                  <li>✓ 90-day retention & instant session replay</li>
                  <li>✓ Unlimited automated LLM-as-judge evals</li>
                  <li>✓ Priority Slack / Discord agent support</li>
                </ul>
              </CardContent>
              <CardFooter>
                <Button className="w-full">
                  <CreditCard className="mr-2 h-4 w-4" /> Upgrade Plan via Stripe
                </Button>
              </CardFooter>
            </Card>
          </div>
        </TabsContent>

        {/* ── General Tab ── */}
        <TabsContent value="general" className="pt-4 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Create Another Project</CardTitle>
              <CardDescription>Segment telemetry across different environments (dev/staging/prod)</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 max-w-md">
              <div className="space-y-2">
                <Label htmlFor="projName">Project Name</Label>
                <Input
                  id="projName"
                  placeholder="Coding Assistant Staging"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="projDesc">Description</Label>
                <Input
                  id="projDesc"
                  placeholder="Staging telemetry for QA and red-teaming"
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                />
              </div>
              <Button
                onClick={() =>
                  createProjectMutation.mutate({
                    name: newProjectName,
                    description: newProjectDesc,
                  })
                }
                disabled={!newProjectName || createProjectMutation.isPending}
              >
                Create Project
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
