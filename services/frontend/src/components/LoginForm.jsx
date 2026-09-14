import { useState } from "react";

import { login } from "../api/auth";


function LoginForm({ onLoggedIn }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();

    setSubmitting(true);
    setError(null);

    try {
      const loggedInUser = await login(username, password);

      setPassword("");
      onLoggedIn(loggedInUser);

    } catch (err) {
      setError(err.message);

    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="panel">

      <h2>Sign in to add sales</h2>

      <p className="panel-hint">
        Anyone can read this dashboard. Adding a sale requires an account.
      </p>

      <form className="form" onSubmit={handleSubmit}>

        <label className="field">
          <span>Username</span>
          <input
            type="text"
            value={username}
            autoComplete="username"
            required
            onChange={(event) => setUsername(event.target.value)}
          />
        </label>

        <label className="field">
          <span>Password</span>
          <input
            type="password"
            value={password}
            autoComplete="current-password"
            required
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>

        <div className="form-actions">
          <button type="submit" disabled={submitting}>
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </div>

      </form>

      {error && <p className="form-error">{error}</p>}

    </section>
  );
}


export default LoginForm;
