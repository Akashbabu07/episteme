import { useState } from "react";
import { submitResearchQuestion } from "./api";
import "./App.css";

function App() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await submitResearchQuestion(question);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <h1>Autonomous Research Lab</h1>

      <form onSubmit={handleSubmit} className="question-form">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a research question..."
          rows={3}
        />
        <button type="submit" disabled={loading || !question.trim()}>
          {loading ? "Researching..." : "Submit"}
        </button>
      </form>

      {loading && (
        <div className="status-box">
          Agent is working — depending on strategy (fast/standard/rigorous)
          this can take anywhere from a few seconds to a couple minutes.
        </div>
      )}

      {error && <div className="error-box">Error: {error}</div>}

      {result && (
        <div className="result-box">
          <h2>Answer</h2>
          <p>{result.answer}</p>

          <div className="meta">
            <span>Run ID: {result.run_id}</span>
            <span>Status: {result.stopped_reason}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;