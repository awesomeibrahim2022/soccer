import React, { useEffect, useMemo, useState } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";

const API_BASE = "http://127.0.0.1:8000";

const seedFixtures = [
  { league: "Premier League", home_team: "Arsenal", away_team: "Liverpool", home_motivation: 0.8, away_motivation: 0.9, home_injury_impact: 0.3, away_injury_impact: 0.6, home_rest_days: 6, away_rest_days: 4 },
  { league: "La Liga", home_team: "Real Madrid", away_team: "Barcelona", home_motivation: 0.95, away_motivation: 0.9, home_injury_impact: 0.2, away_injury_impact: 0.4, home_rest_days: 4, away_rest_days: 3 },
  { league: "Bundesliga", home_team: "Bayern", away_team: "Dortmund", home_motivation: 0.9, away_motivation: 0.85, home_injury_impact: 0.5, away_injury_impact: 0.3, home_rest_days: 5, away_rest_days: 5 },
  { league: "Serie A", home_team: "Inter", away_team: "Napoli", home_motivation: 0.8, away_motivation: 0.75, home_injury_impact: 0.1, away_injury_impact: 0.7, home_rest_days: 5, away_rest_days: 3 },
  { league: "UEFA Champions League", home_team: "PSG", away_team: "Man City", home_motivation: 0.95, away_motivation: 0.95, home_injury_impact: 0.35, away_injury_impact: 0.5, home_rest_days: 3, away_rest_days: 3 },
];

function App() {
  const [leagues, setLeagues] = useState([]);
  const [selectedLeague, setSelectedLeague] = useState("All");
  const [predictions, setPredictions] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [dataSource, setDataSource] = useState(null);
  const [ingestion, setIngestion] = useState(null);

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/meta/leagues`).then((r) => r.json()),
      fetch(`${API_BASE}/model/metrics`).then((r) => r.json()),
      fetch(`${API_BASE}/meta/data-source`).then((r) => r.json()),
      fetch(`${API_BASE}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(seedFixtures),
      }).then((r) => r.json()),
    ]).then(([meta, metricData, sourceData, predData]) => {
      setLeagues(meta.leagues || []);
      setMetrics(metricData);
      setPredictions(predData.predictions || []);
      setDataSource(sourceData);
      setIngestion(sourceData.ingestion || null);
    }).catch(() => {
      setLeagues(["Premier League", "La Liga", "Bundesliga", "Serie A", "UEFA Champions League"]);
      setPredictions([]);
      setDataSource({ mode: "offline", description: "API unreachable from dashboard" });
      setIngestion(null);
    });
  }, []);

  const visibleRows = useMemo(() => {
    if (selectedLeague === "All") return predictions;
    return predictions.filter((p) => p.league === selectedLeague);
  }, [predictions, selectedLeague]);

  return React.createElement(
    "div",
    { className: "wrapper" },
    React.createElement("h1", null, "Soccer ML Predictor"),
    React.createElement("div", { className: "subtitle" }, "Continual-learning predictions for top European leagues + UCL"),
    React.createElement("div", { className: "source-pill" }, `Data source: ${dataSource?.mode || "unknown"} — ${dataSource?.description || "not loaded"}`),
    React.createElement("div", { className: "source-pill" }, `Last ingestion: ${ingestion?.ingested_at || "not yet ingested"} (${ingestion?.freshness_window || "n/a"})`),
    React.createElement(
      "div",
      { className: "filters" },
      React.createElement("span", null, "League:"),
      React.createElement(
        "select",
        { value: selectedLeague, onChange: (e) => setSelectedLeague(e.target.value) },
        ["All", ...leagues].map((league) => React.createElement("option", { key: league, value: league }, league))
      )
    ),
    React.createElement(
      "div",
      { className: "cards" },
      React.createElement("div", { className: "card" }, React.createElement("div", { className: "label" }, "Model sample size"), React.createElement("div", { className: "value" }, metrics?.sample_size ?? "-")),
      React.createElement("div", { className: "card" }, React.createElement("div", { className: "label" }, "Baseline Home Win"), React.createElement("div", { className: "value" }, metrics ? `${(metrics.baseline_rates.home_win * 100).toFixed(1)}%` : "-")),
      React.createElement("div", { className: "card" }, React.createElement("div", { className: "label" }, "Baseline Draw"), React.createElement("div", { className: "value" }, metrics ? `${(metrics.baseline_rates.draw * 100).toFixed(1)}%` : "-")),
      React.createElement("div", { className: "card" }, React.createElement("div", { className: "label" }, "Last retrain matches"), React.createElement("div", { className: "value" }, metrics?.last_retrain_matches ?? "-"))
    ),
    React.createElement(
      "div",
      { className: "table-wrap" },
      React.createElement(
        "table",
        null,
        React.createElement(
          "thead",
          null,
          React.createElement(
            "tr",
            null,
            ["League", "Match", "Home", "Draw", "Away", "Confidence"].map((h) => React.createElement("th", { key: h }, h))
          )
        ),
        React.createElement(
          "tbody",
          null,
          visibleRows.map((row, idx) =>
            React.createElement(
              "tr",
              { key: `${row.home_team}-${row.away_team}-${idx}` },
              React.createElement("td", null, row.league),
              React.createElement("td", null, `${row.home_team} vs ${row.away_team}`),
              React.createElement("td", null, `${(row.home_win * 100).toFixed(1)}%`),
              React.createElement("td", null, `${(row.draw * 100).toFixed(1)}%`),
              React.createElement("td", null, `${(row.away_win * 100).toFixed(1)}%`),
              React.createElement("td", null, React.createElement("span", { className: "badge" }, `${(row.confidence * 100).toFixed(1)}%`))
            )
          )
        )
      )
    )
  );
}

createRoot(document.getElementById("root")).render(React.createElement(App));
