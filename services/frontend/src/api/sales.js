import { API_BASE_URL } from "./config";

export async function getSalesSummary() {
  const response = await fetch(
    `${API_BASE_URL}/api/sales/summary`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch sales summary");
  }

  return response.json();
}

export async function getSalesByCategory() {
  const response = await fetch(
    `${API_BASE_URL}/api/sales/categories`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch sales categories");
  }

  return response.json();
}

export async function getSales(page = 1, pageSize = 10) {
  const response = await fetch(
    `${API_BASE_URL}/api/sales?page=${page}&page_size=${pageSize}`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch sales");
  }

  return response.json();
}

export async function createSale(payload) {
  const response = await fetch(`${API_BASE_URL}/api/sales`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

// FastAPI returns `detail` as a string for HTTPException and as a list of
// field errors for validation failures, so both shapes need handling.
async function readErrorMessage(response) {
  if (response.status === 401) {
    return "Your session has expired. Please log in again.";
  }

  const body = await response.json().catch(() => null);
  const detail = body?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const field = detail[0].loc?.at(-1);
    return field ? `${field}: ${detail[0].msg}` : detail[0].msg;
  }

  return "Failed to create sale";
}