import { HealthResponse, Persona, InvestigationData, InvestigateError } from "../types";

const API_BASE = "";

export class ApiError extends Error {
  constructor(public status: number, message: string, public detail?: string) {
    super(message);
    this.name = "ApiError";
  }
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/api/health`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new ApiError(res.status, `Health check failed with status ${res.status}`);
  }
  return res.json();
}

export async function fetchPersonas(): Promise<Persona[]> {
  const res = await fetch(`${API_BASE}/api/personas`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new ApiError(res.status, `Failed to load customer personas: ${res.status}`);
  }
  return res.json();
}

export async function investigateApplicant(
  customerId: string,
  useAgents = true,
  refresh = false
): Promise<InvestigationData> {
  const res = await fetch(`${API_BASE}/api/investigate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      customer_id: customerId,
      use_agents: useAgents,
      refresh: refresh,
    }),
  });

  const data = await res.json();

  if (!res.ok) {
    const err = data as InvestigateError;
    throw new ApiError(res.status, err.detail || `Investigation failed (${res.status})`, err.detail);
  }

  if (data.ok === false) {
    const err = data as InvestigateError;
    throw new ApiError(200, err.detail || "Investigation returned failure status", err.detail);
  }

  return data as InvestigationData;
}
