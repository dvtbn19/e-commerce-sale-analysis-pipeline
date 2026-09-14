import { useCallback, useEffect, useState } from "react";

import {
  getSales,
  getSalesByCategory,
  getSalesSummary,
} from "./api/sales";

import { getCurrentUser, logout } from "./api/auth";

import AddSaleForm from "./components/AddSaleForm";
import LoginForm from "./components/LoginForm";

import "./App.css";


function App() {
  const [summary, setSummary] = useState(null);
  const [categories, setCategories] = useState([]);
  const [sales, setSales] = useState([]);

  const [currentUser, setCurrentUser] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);


  const loadDashboard = useCallback(async () => {
    try {
      const [
        summaryData,
        categoriesData,
        salesData,
      ] = await Promise.all([
        getSalesSummary(),
        getSalesByCategory(),
        getSales(1, 10),
      ]);

      setSummary(summaryData);
      setCategories(categoriesData.data);
      setSales(salesData.data);
      setError(null);

    } catch (err) {
      setError(err.message);
    }
  }, []);


  useEffect(() => {
    async function loadInitialState() {
      setLoading(true);

      // The session check runs alongside the dashboard fetches: a logged-out
      // visitor still gets the full dashboard, just without the add-sale form.
      const [, user] = await Promise.all([
        loadDashboard(),
        getCurrentUser(),
      ]);

      setCurrentUser(user);
      setLoading(false);
    }

    loadInitialState();
  }, [loadDashboard]);


  async function handleLogout() {
    await logout();
    setCurrentUser(null);
  }


  if (loading) {
    return <div className="container">Loading...</div>;
  }


  if (error) {
    return (
      <div className="container">
        Error: {error}
      </div>
    );
  }


  return (
    <div className="container">

      <header className="app-header">

        <h1>E-Commerce Sales Dashboard</h1>

        {currentUser && (
          <div className="session">
            <span>
              Signed in as <strong>{currentUser}</strong>
            </span>

            <button type="button" onClick={handleLogout}>
              Log out
            </button>
          </div>
        )}

      </header>


      {currentUser
        ? <AddSaleForm onCreated={loadDashboard} />
        : <LoginForm onLoggedIn={setCurrentUser} />}


      <section className="summary-grid">

        <div className="card">
          <h3>Total Sales</h3>
          <p>
            ₹
            {summary.total_sales.toLocaleString(
              undefined,
              {
                maximumFractionDigits: 2,
              }
            )}
          </p>
        </div>

        <div className="card">
          <h3>Total Orders</h3>
          <p>
            {summary.total_orders.toLocaleString()}
          </p>
        </div>

        <div className="card">
          <h3>Total Quantity</h3>
          <p>
            {summary.total_quantity.toLocaleString()}
          </p>
        </div>

      </section>


      <section>

        <h2>Sales by Category</h2>

        <table>
          <thead>
            <tr>
              <th>Category</th>
              <th>Records</th>
              <th>Quantity</th>
              <th>Sales</th>
            </tr>
          </thead>

          <tbody>
            {categories.map((item) => (
              <tr key={item.category}>
                <td>{item.category}</td>

                <td>
                  {item.total_records.toLocaleString()}
                </td>

                <td>
                  {item.total_quantity.toLocaleString()}
                </td>

                <td>
                  ₹
                  {item.total_sales.toLocaleString(
                    undefined,
                    {
                      maximumFractionDigits: 2,
                    }
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

      </section>


      <section>

        <h2>Recent Sales</h2>

        <table>
          <thead>
            <tr>
              <th>Order ID</th>
              <th>Date</th>
              <th>Category</th>
              <th>Quantity</th>
              <th>Amount</th>
              <th>Status</th>
            </tr>
          </thead>

          <tbody>
            {sales.map((sale) => (
              <tr key={sale.index}>
                <td>{sale.order_id}</td>
                <td>{sale.date}</td>
                <td>{sale.category}</td>
                <td>{sale.qty}</td>

                <td>
                  {sale.amount == null
                    ? "-"
                    : `₹${sale.amount.toLocaleString()}`}
                </td>

                <td>{sale.status}</td>
              </tr>
            ))}
          </tbody>
        </table>

      </section>

    </div>
  );
}


export default App;