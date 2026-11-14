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
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from '@/components/ui/dialog';
import { formatDate, getSeverityColor } from '@/lib/utils';
import { ShieldAlert, Plus, ShieldCheck, FileText, AlertOctagon } from 'lucide-react';
import { Policy, AuditLog, PolicyAction } from '@/types';

export function GovernancePage() {
  const { currentProject } = useProjectStore();
  const queryClient = useQueryClient();

  const [createPolicyOpen, setCreatePolicyOpen] = useState(false);
  const [policyName, setPolicyName] = useState('');
  const [policyDesc, setPolicyDesc] = useState('');
  const [policyAction, setPolicyAction] = useState<PolicyAction>(PolicyAction.BLOCK);

  // Queries
  const { data: policiesData } = useQuery({
    queryKey: ['policies', currentProject?.id],
    queryFn: () => api.governance.listPolicies(currentProject!.id),
    enabled: !!currentProject?.id,
  });

  const { data: auditLogsData } = useQuery({
    queryKey: ['audit-logs', currentProject?.id],
    queryFn: () => api.governance.listAuditLogs(currentProject!.id),
    enabled: !!currentProject?.id,
  });

  // Mutations
  const createPolicyMutation = useMutation({
    mutationFn: (data: { name: string; description?: string; action: PolicyAction; rules: any }) =>
      api.governance.createPolicy(currentProject!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policies', currentProject?.id] });
      setCreatePolicyOpen(false);
      setPolicyName('');
      setPolicyDesc('');
    },
  });

  const togglePolicyMutation = useMutation({
    mutationFn: ({ policyId, isEnabled }: { policyId: string; isEnabled: boolean }) =>
      api.governance.updatePolicy(currentProject!.id, policyId, { is_enabled: isEnabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policies', currentProject?.id] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">GovernAI & Compliance</h1>
          <p className="text-sm text-muted-foreground">
            Enforce guardrails, detect PII leaks, and review immutable enterprise audit logs
          </p>
        </div>
        <Dialog open={createPolicyOpen} onOpenChange={setCreatePolicyOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" /> Add Security Guardrail
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Configure Policy Rule</DialogTitle>
              <DialogDescription>Define an automated constraint for agent inputs & outputs</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="pName">Guardrail Name</Label>
                <Input
                  id="pName"
                  placeholder="Block PII (SSN, Passwords, Credit Cards)"
                  value={policyName}
                  onChange={(e) => setPolicyName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="pDesc">Rule Description</Label>
                <Input
                  id="pDesc"
                  placeholder="Scans agent inputs and outputs for sensitive identifiers"
                  value={policyDesc}
                  onChange={(e) => setPolicyDesc(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="pAction">Enforcement Action</Label>
                <select
                  id="pAction"
                  value={policyAction}
                  onChange={(e) => setPolicyAction(e.target.value as PolicyAction)}
                  className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="block">Block Request (Hard Guardrail)</option>
                  <option value="alert">Alert Security Team (Slack/Webhook)</option>
                  <option value="log">Log Only (Silent Monitoring)</option>
                </select>
              </div>
            </div>
            <DialogFooter>
              <Button
                onClick={() =>
                  createPolicyMutation.mutate({
                    name: policyName,
                    description: policyDesc,
                    action: policyAction,
                    rules: { scan_pii: true, scan_prompt_injection: true },
                  })
                }
                disabled={!policyName || createPolicyMutation.isPending}
              >
                Save Guardrail
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Tabs defaultValue="policies">
        <TabsList>
          <TabsTrigger value="policies">Active Policies ({policiesData?.items?.length ?? 0})</TabsTrigger>
          <TabsTrigger value="audit">Security Audit Trail</TabsTrigger>
        </TabsList>

        <TabsContent value="policies" className="pt-4 space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {policiesData?.items?.map((p: Policy) => (
              <Card key={p.id}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0">
                  <div>
                    <CardTitle className="text-base">{p.name}</CardTitle>
                    <CardDescription className="mt-1">{p.description}</CardDescription>
                  </div>
                  <Switch
                    checked={p.is_enabled}
                    onCheckedChange={(checked) =>
                      togglePolicyMutation.mutate({ policyId: p.id, isEnabled: checked })
                    }
                  />
                </CardHeader>
                <CardContent className="flex items-center justify-between text-xs text-muted-foreground pt-4 border-t border-border mt-4">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-foreground">Action:</span>
                    <Badge variant={p.action === 'block' ? 'destructive' : 'secondary'}>
                      {p.action.toUpperCase()}
                    </Badge>
                  </div>
                  <span>Created {formatDate(p.created_at)}</span>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="audit" className="pt-4 space-y-4">
          <Card>
            <CardContent className="pt-6">
              {!auditLogsData?.items?.length ? (
                <div className="py-12 text-center text-muted-foreground">
                  <ShieldCheck className="mx-auto h-12 w-12 text-green-500 mb-2" />
                  No security policy violations detected. System is clean.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="py-3 px-4">Violation Type</th>
                        <th className="py-3 px-4">Severity</th>
                        <th className="py-3 px-4">Trace Link</th>
                        <th className="py-3 px-4">Payload Summary</th>
                        <th className="py-3 px-4">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {auditLogsData.items.map((log: AuditLog) => (
                        <tr key={log.id} className="hover:bg-muted/50">
                          <td className="py-3 px-4 font-semibold text-destructive">
                            {log.violation_type}
                          </td>
                          <td className="py-3 px-4">
                            <Badge variant="outline" className={getSeverityColor(log.severity)}>
                              {log.severity}
                            </Badge>
                          </td>
                          <td className="py-3 px-4 font-mono text-xs">
                            {log.trace_id ? log.trace_id.substring(0, 8) : '—'}
                          </td>
                          <td className="py-3 px-4 font-mono text-xs truncate max-w-xs">
                            {JSON.stringify(log.payload)}
                          </td>
                          <td className="py-3 px-4 text-muted-foreground">
                            {formatDate(log.created_at)}
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
      </Tabs>
    </div>
  );
}
