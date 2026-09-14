import { useState } from "react";

import { createSale } from "../api/sales";


// Must stay in sync with the SaleCategory enum in services/api/app/routes/sales.py,
// which mirrors the accepted values enforced by the dbt staging tests.
const CATEGORIES = [
  "Set",
  "Kurta",
  "Western Dress",
  "Top",
  "Ethnic Dress",
  "Blouse",
  "Bottom",
  "Saree",
  "Dupatta",
];


function AddSaleForm({ onCreated }) {
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [quantity, setQuantity] = useState("1");
  const [amount, setAmount] = useState("");
  const [shipCity, setShipCity] = useState("");
  const [shipState, setShipState] = useState("");

  const [error, setError] = useState(null);
  const [createdOrderId, setCreatedOrderId] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();

    setSubmitting(true);
    setError(null);
    setCreatedOrderId(null);

    const payload = {
      category,
      quantity: Number(quantity),
      amount: Number(amount),
    };

    // Blank optional fields are omitted rather than sent as empty strings,
    // so they land in the database as NULL.
    if (shipCity.trim()) {
      payload.ship_city = shipCity.trim();
    }

    if (shipState.trim()) {
      payload.ship_state = shipState.trim();
    }

    try {
      const created = await createSale(payload);

      setCreatedOrderId(created.order_id);
      setQuantity("1");
      setAmount("");
      setShipCity("");
      setShipState("");

      await onCreated();

    } catch (err) {
      setError(err.message);

    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="panel">

      <h2>Add a sale</h2>

      <form className="form form-grid" onSubmit={handleSubmit}>

        <label className="field">
          <span>Category</span>
          <select
            value={category}
            onChange={(event) => setCategory(event.target.value)}
          >
            {CATEGORIES.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Quantity</span>
          <input
            type="number"
            min="1"
            max="1000"
            step="1"
            value={quantity}
            required
            onChange={(event) => setQuantity(event.target.value)}
          />
        </label>

        <label className="field">
          <span>Amount (INR)</span>
          <input
            type="number"
            min="0.01"
            max="10000000"
            step="0.01"
            value={amount}
            required
            onChange={(event) => setAmount(event.target.value)}
          />
        </label>

        <label className="field">
          <span>Ship city <em>(optional)</em></span>
          <input
            type="text"
            maxLength="128"
            value={shipCity}
            onChange={(event) => setShipCity(event.target.value)}
          />
        </label>

        <label className="field">
          <span>Ship state <em>(optional)</em></span>
          <input
            type="text"
            maxLength="128"
            value={shipState}
            onChange={(event) => setShipState(event.target.value)}
          />
        </label>

        <div className="form-actions">
          <button type="submit" disabled={submitting}>
            {submitting ? "Saving..." : "Add sale"}
          </button>
        </div>

      </form>

      {error && <p className="form-error">{error}</p>}

      {createdOrderId && (
        <p className="form-success">
          Added <strong>{createdOrderId}</strong>. The dashboard below is up to date.
        </p>
      )}

    </section>
  );
}


export default AddSaleForm;
