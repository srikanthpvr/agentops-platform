/**
 * src/types/index.ts
 *
 * Canonical TypeScript interfaces mirroring all backend Pydantic schemas.
 * Keep these in sync with the OpenAPI spec whenever the backend evolves.
 */

// ─────────────────────────────────────────────────────────────────────────────
// Enum types
// ─────────────────────────────────────────────────────────────────────────────

/** Lifecycle state of a trace (session). */
export enum TraceStatus {
  Running = 'running',
  Success = 'success',
  Error = 'error',
  Timeout = 'timeout',
}

/** Span type classifies the kind of operation a span represents. */
export enum SpanType {
  LLM = 'llm',
  Tool = 'tool',
  Chain = 'chain',
  Embedding = 'embedding',
  Retrieval = 'retrieval',
  Custom = 'custom',
}

/** Governance policy enforcement action. */
export enum PolicyAction {
  Block = 'block',
  Warn = 'warn',
  Redact = 'redact',
  Log = 'log',
}

/** Audit log / violation severity level. */
export enum Severity {
  Info = 'info',
  Low = 'low',
  Medium = 'medium',
  High = 'high',
  Critical = 'critical',
}

/** User role within an organisation. */
export enum UserRole {
  Owner = 'owner',
  Admin = 'admin',
  Member = 'member',
  Viewer = 'viewer',
}

/** Organisation subscription tier. */
export enum OrgTier {
  Free = 'free',
  Pro = 'pro',
  Enterprise = 'enterprise',
}

// ─────────────────────────────────────────────────────────────────────────────
// Auth & identity
// ─────────────────────────────────────────────────────────────────────────────

export interface Org {
  id: string;
  name: string;
  slug: string;
  tier: OrgTier;
  /** Maximum number of traces allowed per month */
  trace_limit: number;
  /** Traces consumed in the current billing period */
  traces_used: number;
  created_at: string; // ISO-8601
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  org_id: string;
  org: Org;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: 'bearer';
  /** Seconds until the token expires */
  expires_in: number;
  user: User;
}

export interface ErrorResponse {
  detail: string;
  code?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Projects & API keys
// ─────────────────────────────────────────────────────────────────────────────

export interface Project {
  id: string;
  name: string;
  description?: string;
  org_id: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface APIKey {
  id: string;
  project_id: string;
  name: string;
  /** Only the key prefix is stored/returned after creation */
  prefix: string;
  /** Full key is ONLY returned at creation time — never stored in full */
  key?: string;
  is_active: boolean;
  last_used_at?: string;
  created_at: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Traces & spans
// ─────────────────────────────────────────────────────────────────────────────

export interface Span {
  id: string;
  trace_id: string;
  parent_span_id?: string;
  name: string;
  span_type: SpanType;
  model?: string;
  /** LLM prompt / tool input (truncated for display) */
  input?: unknown;
  /** LLM completion / tool output (truncated for display) */
  output?: unknown;
  /** Token counts for LLM spans */
  tokens_input?: number;
  tokens_output?: number;
  tokens_total?: number;
  /** Cost of this span in USD */
  cost_usd?: number;
  /** Wall-clock latency in milliseconds */
  latency_ms?: number;
  error?: string;
  metadata?: Record<string, unknown>;
  started_at: string;
  ended_at?: string;
}

export interface Trace {
  id: string;
  session_id: string;
  project_id: string;
  agent_name: string;
  status: TraceStatus;
  /** Total tokens across all spans */
  total_tokens?: number;
  /** Aggregate cost in USD */
  total_cost_usd?: number;
  /** Total wall-clock duration in milliseconds */
  total_latency_ms?: number;
  tags?: string[];
  metadata?: Record<string, unknown>;
  spans?: Span[];
  started_at: string;
  ended_at?: string;
  error?: string;
}

export interface TraceStats {
  total_traces: number;
  total_tokens: number;
  total_cost_usd: number;
  error_rate: number; // 0–1
  /** Array of { date: "YYYY-MM-DD", count: number } for the last N days */
  daily_counts: Array<{ date: string; count: number }>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Evaluations
// ─────────────────────────────────────────────────────────────────────────────

export interface EvalDatasetItem {
  id: string;
  input: string;
  expected_output?: string;
  metadata?: Record<string, unknown>;
}

export interface EvalDataset {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  item_count: number;
  items?: EvalDatasetItem[];
  created_by: string;
  created_at: string;
}

export interface EvalRunConfig {
  model: string;
  temperature?: number;
  max_tokens?: number;
  system_prompt?: string;
  evaluator?: string;
}

export interface EvalRun {
  id: string;
  project_id: string;
  dataset_id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  config: EvalRunConfig;
  avg_score?: number;
  min_score?: number;
  max_score?: number;
  items_total?: number;
  items_completed?: number;
  error?: string;
  created_by: string;
  created_at: string;
  completed_at?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Governance
// ─────────────────────────────────────────────────────────────────────────────

export interface PolicyCondition {
  field: string;
  operator: 'contains' | 'equals' | 'regex' | 'gt' | 'lt';
  value: string | number;
}

export interface Policy {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  action: PolicyAction;
  conditions: PolicyCondition[];
  is_enabled: boolean;
  priority: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface AuditLog {
  id: string;
  project_id: string;
  trace_id?: string;
  policy_id?: string;
  policy_name?: string;
  violation_type: string;
  severity: Severity;
  action_taken: PolicyAction;
  details?: Record<string, unknown>;
  created_at: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Generic helpers
// ─────────────────────────────────────────────────────────────────────────────

/** Standard paginated list response from the backend. */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/** Query params for paginated list endpoints. */
export interface PaginationParams {
  page?: number;
  page_size?: number;
}
