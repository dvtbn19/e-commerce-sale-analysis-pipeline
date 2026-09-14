import { API_BASE_URL } from "./config";

// Every call sends `credentials: "include"` so the httpOnly session cookie
// issued by /api/auth/login travels with cross-origin requests to the API.

export async function login(username, password) {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    throw new Error("Incorrect username or password");
  }

  const data = await response.json();

  return data.username;
}

export async function logout() {
  await fetch(`${API_BASE_URL}/api/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}

// Returns the signed-in username, or null when there is no valid session.
// A missing session is an expected state on page load, not an error.
export async function getCurrentUser() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      credentials: "include",
    });

    if (!response.ok) {
      return null;
    }

    const data = await response.json();

    return data.username;
  } catch {
    return null;
  }
}
