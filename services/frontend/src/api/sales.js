const API_BASE_URL = "http://127.0.0.1:8000";


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