export interface PersonaHeadline {
  loan_amount: string;
  credit_score: number;
  dti?: string;
  income?: string;
}

export interface Persona {
  id: string;
  name: string;
  tagline: string;
  headline: PersonaHeadline;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  mode: "azure" | "offline";
  deployments: {
    chat: string;
    embeddings: string;
  } | null;
  personas: number;
  policy_clauses_loaded: number;
  index_loaded: boolean;
  ml: {
    available: boolean;
    reason?: string;
  };
  warm: {
    done: number;
    total: number;
    running: boolean;
  };
  last_failure?: {
    customer: string;
    reason: string;
    at: number;
  } | null;
  degraded_reason?: string | null;
}

export interface ApplicantInfo {
  id: string;
  name: string;
  age: number;
  monthly_income: string;
  monthly_expenses: string;
  existing_debt: string;
  requested_amount: string;
  loan_tenure_months: number;
  purpose: string;
  credit_score: number;
  employment_tenure_months: number;
  dependents_count: number;
  bankruptcies_count: number;
  tax_liens_count: number;
}

export type VerdictCode =
  | "ELIGIBLE_FOR_APPROVAL"
  | "FURTHER_REVIEW_REQUIRED"
  | "DECLINE_RECOMMENDED";

export interface VerdictDriver {
  code: string;
  name: string;
  reason: string;
}

export interface Verdict {
  code: VerdictCode;
  label: string;
  note: string;
  driver: VerdictDriver | null;
  reason: string;
}

export interface RulesSummary {
  pass: number;
  review: number;
  fail: number;
  missing: number;
}

export type RuleOutcome = "pass" | "review" | "fail" | "missing";

export interface RuleBarMark {
  value: number;
  label: string;
  color?: string;
}

export interface RuleBar {
  min: number;
  max: number;
  value: number;
  marks?: RuleBarMark[];
}

export interface RuleDetail {
  code: string;
  name: string;
  status: string;
  outcome: RuleOutcome;
  decline_class: boolean;
  is_driver: boolean;
  actual: string;
  actual_num?: number;
  threshold: string;
  reason: string;
  citation: string;
  policy_excerpt: string;
  bar?: RuleBar | null;
}

export type AgentStepKey = "data" | "compliance" | "credit" | "explanation" | "engine";

export interface AgentStep {
  key: AgentStepKey;
  name: string;
  status: string;
  duration_ms: number;
  summary: string;
}

export interface MLFeatureDriver {
  feature: string;
  label: string;
  share: number;
  effect: "raises risk" | "lowers risk" | string;
}

export interface MLResult {
  available: boolean;
  score: number;
  level: "LOW_RISK" | "MEDIUM_RISK" | "HIGH_RISK" | string;
  label: string;
  precomputed: boolean;
  drivers: MLFeatureDriver[];
}

export interface ConflictDetail {
  rule: string;
  evaluator: string;
  rag: string;
  notes: string;
}

export interface CrossCheck {
  available: boolean;
  reason?: string | null;
  compared: number;
  total_rules: number;
  conflicts: ConflictDetail[];
  not_compared: string[];
}

export interface Explanation {
  text: string;
  source: "azure" | "template";
  label: string;
}

export interface ChecklistItem {
  id: string;
  text: string;
  priority: "high" | "medium" | "low";
  completed?: boolean;
}

export interface InvestigationData {
  ok: boolean;
  mode: "azure" | "offline";
  degraded_reason?: string | null;
  cached: boolean;
  timings: {
    total_ms: number;
    engine_ms: number;
  };
  applicant: ApplicantInfo;
  verdict: Verdict;
  rules_summary: RulesSummary;
  rules: RuleDetail[];
  steps: AgentStep[];
  ml: MLResult;
  cross_check: CrossCheck;
  explanation: Explanation;
  checklist: ChecklistItem[];
  data_gaps: string[];
}

export interface InvestigateError {
  ok: false;
  error: string;
  detail: string;
  available?: string[];
  mode?: string;
}
