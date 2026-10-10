import { HealthResponse, Persona, InvestigationData, InvestigateError } from "../types";
import { MOCK_HEALTH, MOCK_PERSONAS, MOCK_INVESTIGATIONS } from "./mockData";

const API_BASE = "";

export class ApiError extends Error {
  constructor(public status: number, message: string, public detail?: string) {
    super(message);
    this.name = "ApiError";
  }
}

export async function fetchHealth(): Promise<HealthResponse> {
  try {
    const res = await fetch(`${API_BASE}/api/health`, {
      headers: { Accept: "application/json" },
    });
    if (!res.ok) {
      return MOCK_HEALTH;
    }
    return res.json();
  } catch {
    return MOCK_HEALTH;
  }
}

export async function fetchPersonas(): Promise<Persona[]> {
  try {
    const res = await fetch(`${API_BASE}/api/personas`, {
      headers: { Accept: "application/json" },
    });
    if (!res.ok) {
      return MOCK_PERSONAS;
    }
    return res.json();
  } catch {
    return MOCK_PERSONAS;
  }
}

export async function investigateApplicant(
  customerId: string,
  useAgents = true,
  refresh = false
): Promise<InvestigationData> {
  try {
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
      if (MOCK_INVESTIGATIONS[customerId]) {
        return MOCK_INVESTIGATIONS[customerId];
      }
      const err = data as InvestigateError;
      throw new ApiError(res.status, err.detail || `Investigation failed (${res.status})`, err.detail);
    }

    if (data.ok === false) {
      if (MOCK_INVESTIGATIONS[customerId]) {
        return MOCK_INVESTIGATIONS[customerId];
      }
      const err = data as InvestigateError;
      throw new ApiError(200, err.detail || "Investigation returned failure status", err.detail);
    }

    return data as InvestigationData;
  } catch (err: any) {
    if (MOCK_INVESTIGATIONS[customerId]) {
      return MOCK_INVESTIGATIONS[customerId];
    }
    // Fallback to first mock investigation if id not directly keyed
    if (MOCK_INVESTIGATIONS["CUST-GOLD-001"]) {
      return {
        ...MOCK_INVESTIGATIONS["CUST-GOLD-001"],
        applicant: {
          ...MOCK_INVESTIGATIONS["CUST-GOLD-001"].applicant,
          id: customerId,
        },
      };
    }
    throw err;
  }
}
