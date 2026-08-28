import { useEffect, useMemo, useState } from "react";
import Chart from "./Chart.jsx";
import { loadSample, postJson, uploadCsv } from "./api.js";

const STEPS = [
  ["1", "Load"],
  ["2", "Structure"],
  ["3", "Quality"],
  ["4", "Univariate"],
  ["5", "Relations"],
  ["6", "Prepare"],
  ["7", "Insights"],
];

function Table({ rows }) {
  if (!rows?.length) return <p className="muted">No rows to show.</p>;
  const cols = Object.keys(rows[0]);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td key={c}>{row[c] == null ? "" : String(row[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function md(text) {
  const esc = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  const html = esc
    .replace(/^### (.*)$/gm, "<h3>$1</h3>")
    .replace(/^## (.*)$/gm, "<h2>$1</h2>")
    .replace(/^# (.*)$/gm, "<h2>$1</h2>")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/^- (.*)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`)
    .replace(/\n\n/g, "</p><p>")
    .replace(/\n/g, "<br/>");
  return `<p>${html}</p>`;
}

export default function App() {
  const [tab, setTab] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [profile, setProfile] = useState(null);
  const [target, setTarget] = useState("");
  const [uniCol, setUniCol] = useState("");
  const [uni, setUni] = useState(null);
  const [xy, setXy] = useState({ x: "", y: "", color: "", gnum: "", gcat: "" });
  const [rel, setRel] = useState(null);
  const [prep, setPrep] = useState(null);
  const [question, setQuestion] = useState("");
  const [insights, setInsights] = useState("");
  const [provider, setProvider] = useState("Groq (Llama, free API)");
  const [model, setModel] = useState("openai/gpt-oss-20b");

  const kinds = profile?.kinds || { numeric: [], categorical: [], datetime: [] };
  const catOpts = profile?.cat_opts || kinds.categorical || [];
  const q = profile?.quality;

  async function run(task, { quiet } = {}) {
    if (!quiet) setBusy(true);
    setError("");
    try {
      await task();
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      if (!quiet) setBusy(false);
    }
  }

  function applyProfile(data) {
    setProfile(data);
    setTarget(data.target || "");
    const firstNum = data.kinds?.numeric?.[0] || data.columns?.[0] || "";
    setUniCol(firstNum);
    setUni(null);
    setRel(null);
    setPrep(null);
    setInsights("");
    setXy({
      x: data.kinds?.numeric?.[0] || "",
      y: data.kinds?.numeric?.[1] || data.kinds?.numeric?.[0] || "",
      color: data.target || "",
      gnum: data.kinds?.numeric?.[0] || "",
      gcat: data.cat_opts?.[0] || "",
    });
    setTab(0);
  }

  function onFile(ev) {
    const file = ev.target.files?.[0];
    ev.target.value = "";
    if (!file) return;
    run(async () => applyProfile(await uploadCsv(file)));
  }

  function onSample() {
    run(async () => applyProfile(await loadSample()));
  }

  function onTarget(next) {
    setTarget(next);
    if (!profile) return;
    run(async () => {
      const data = await postJson("/api/profile", {
        session_id: profile.session_id,
        target: next || null,
      });
      setProfile(data);
      setPrep(null);
      setInsights("");
    });
  }

  useEffect(() => {
    if (!profile || !uniCol) return undefined;
    run(async () => {
      setUni(
        await postJson("/api/univariate", {
          session_id: profile.session_id,
          column: uniCol,
        })
      );
    }, { quiet: true });
    return undefined;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile?.session_id, uniCol]);

  useEffect(() => {
    if (!profile) return undefined;
    run(async () => {
      setRel(
        await postJson("/api/relations", {
          session_id: profile.session_id,
          x: xy.x,
          y: xy.y,
          color: xy.color || null,
          gnum: xy.gnum,
          gcat: xy.gcat,
        })
      );
    }, { quiet: true });
    return undefined;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile?.session_id, xy.x, xy.y, xy.color, xy.gnum, xy.gcat]);

  const needle = useMemo(() => {
    const pct = q?.balance?.minority_pct ?? 50;
    return Math.max(8, Math.min(92, 92 - pct * 1.6));
  }, [q]);

  return (
    <div className="app">
      <aside className="sidebar">
        <div>
          <p className="brand">EDA Studio</p>
          <p>Understand the data before building the model.</p>
        </div>
        <label className="file-btn">
          Upload CSV
          <input type="file" accept=".csv,text/csv" onChange={onFile} />
        </label>
        <button className="btn ghost" type="button" onClick={onSample} disabled={busy}>
          Load sample churn data
        </button>
        {profile ? (
          <>
            <label>
              Target column
              <select value={target} onChange={(e) => onTarget(e.target.value)}>
                <option value="">None</option>
                {profile.columns.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </label>
          </>
        ) : null}
        <h2>Open LLM</h2>
        <label>
          Provider
          <select value={provider} onChange={(e) => setProvider(e.target.value)}>
            <option>Groq (Llama, free API)</option>
            <option>Ollama (local)</option>
          </select>
        </label>
        <label>
          Groq model
          <select value={model} onChange={(e) => setModel(e.target.value)}>
            <option value="openai/gpt-oss-20b">openai/gpt-oss-20b</option>
            <option value="qwen/qwen3.8-27b">qwen/qwen3.8-27b</option>
            <option value="openai/gpt-oss-120b">openai/gpt-oss-120b</option>
          </select>
        </label>
        <small>Groq key is read from the server .env file.</small>
      </aside>

      <main className="main">
        <div className="hero">
          <h1>Magic of Exploratory Data Analysis</h1>
          <p>
            Load a CSV, inspect structure and quality, chart every feature, then ask a free open LLM
            for insights and a model-ready plan. Fit preprocessing on training data only — never on
            the test fold.
          </p>
        </div>

        <div className="step-rail">
          {STEPS.map(([n, label], i) => (
            <button
              key={label}
              type="button"
              className={`step-chip ${tab === i ? "on" : ""}`}
              onClick={() => setTab(i)}
            >
              <span className="n">{n}</span>
              <span className="l">{label}</span>
            </button>
          ))}
        </div>

        {error ? <p className="error">{error}</p> : null}
        {busy ? <p className="muted">Working…</p> : null}

        {!profile ? (
          <div className="panel">
            <p className="kicker">Start</p>
            <p>
              Drop a CSV in the sidebar, or load the bundled customer-churn sample. The sample is
              messy on purpose: missing cells, duplicate rows, spelling variants, outliers, class
              imbalance, and a leaky <code>churn_score</code> column.
            </p>
          </div>
        ) : (
          <>
            <div className="pills">
              <span className="pill">
                <span className={`dot ${q.status}`} />
                Quality {q.status} · score {q.score}/100
              </span>
              <span className="pill">
                {q.n_rows} rows × {q.n_cols} columns
              </span>
              <span className="pill">{q.duplicate_rows} duplicate rows</span>
              <span className="pill">{q.missing.length} columns with missing values</span>
              <span className="pill">{q.leakage.length} leakage flags</span>
            </div>

            {tab === 0 && (
              <section>
                <p className="kicker">Data overview</p>
                <div className="metrics">
                  <div className="metric">
                    <span>Rows</span>
                    <strong>{profile.n_rows}</strong>
                  </div>
                  <div className="metric">
                    <span>Columns</span>
                    <strong>{profile.n_cols}</strong>
                  </div>
                  <div className="metric">
                    <span>Memory</span>
                    <strong>{profile.memory_mb} MB</strong>
                  </div>
                  <div className="metric">
                    <span>Source</span>
                    <strong>{profile.source_name}</strong>
                  </div>
                </div>
                <Table rows={profile.preview} />
              </section>
            )}

            {tab === 1 && (
              <section>
                <p className="kicker">Inspect structure</p>
                <div className="metrics">
                  <div className="metric">
                    <span>Numeric</span>
                    <strong>{kinds.numeric.length}</strong>
                  </div>
                  <div className="metric">
                    <span>Categorical</span>
                    <strong>{kinds.categorical.length}</strong>
                  </div>
                  <div className="metric">
                    <span>Datetime-like</span>
                    <strong>{kinds.datetime.length}</strong>
                  </div>
                </div>
                <Table rows={profile.structure} />
                <p>
                  <strong>Summary statistics</strong>
                </p>
                <p className="muted">Count, mean, median, mode, std, min, Q1, Q3, max, skew.</p>
                <Table rows={profile.stats} />
              </section>
            )}

            {tab === 2 && (
              <section>
                <p className="kicker">Data quality checks</p>
                {q.status !== "good" ? (
                  <div className="warn">
                    <strong>Quality needs attention.</strong> Resolve critical flags before you trust
                    a model. Fit imputers and encoders on the training fold only.
                  </div>
                ) : null}
                <div className="grid-2">
                  <div>
                    {profile.charts.missing ? (
                      <Chart figure={profile.charts.missing} />
                    ) : (
                      <p>No missing values detected.</p>
                    )}
                    <p>
                      <strong>Outliers (IQR)</strong>
                    </p>
                    <Table rows={q.outliers} />
                  </div>
                  <div>
                    <p>
                      <strong>Automated flags</strong>
                    </p>
                    <Table rows={q.inconsistent} />
                    <Table rows={q.invalid} />
                    <Table rows={q.leakage} />
                    {q.constant?.length ? (
                      <p>Constant columns: {q.constant.join(", ")}</p>
                    ) : null}
                    <Table rows={q.near_constant} />
                  </div>
                </div>
              </section>
            )}

            {tab === 3 && (
              <section>
                <p className="kicker">Univariate analysis</p>
                <div className="row">
                  <label>
                    Feature
                    <select value={uniCol} onChange={(e) => setUniCol(e.target.value)}>
                      {profile.columns.map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  </label>
                </div>
                {uni?.kind === "numeric" ? (
                  <div className="grid-2">
                    <Chart figure={uni.histogram} />
                    <Chart figure={uni.box} />
                  </div>
                ) : (
                  <Chart figure={uni?.bar} />
                )}
                <Table rows={uni?.table} />
              </section>
            )}

            {tab === 4 && (
              <section>
                <p className="kicker">Bivariate and multivariate</p>
                <div className="grid-2">
                  <Chart figure={profile.charts.target} />
                  {q.balance?.kind === "classification" ? (
                    <div className="gauge">
                      <p className="kicker">Imbalance risk</p>
                      <strong>{q.balance.imbalance_risk}</strong> — minority class is{" "}
                      {q.balance.minority_pct}% of labeled rows.
                      <div className="gauge-track">
                        <div className="gauge-needle" style={{ left: `${needle}%` }} />
                      </div>
                      <p className="muted">Recommended hold-out: 70% train / 30% test, stratified.</p>
                    </div>
                  ) : (
                    <div className="panel">
                      <p className="kicker">Split</p>
                      Recommended hold-out: <strong>70% train / 30% test</strong>.
                    </div>
                  )}
                </div>
                <Chart figure={profile.charts.heatmap} />
                <Chart figure={profile.charts.corr_vs_target} />
                <p>
                  <strong>Feature vs feature</strong>
                </p>
                <div className="grid-3">
                  <label>
                    X
                    <select value={xy.x} onChange={(e) => setXy({ ...xy, x: e.target.value })}>
                      {kinds.numeric.map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Y
                    <select value={xy.y} onChange={(e) => setXy({ ...xy, y: e.target.value })}>
                      {kinds.numeric.map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Color
                    <select value={xy.color} onChange={(e) => setXy({ ...xy, color: e.target.value })}>
                      <option value="">None</option>
                      {catOpts.map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  </label>
                </div>
                <Chart figure={rel?.scatter} />
                <div className="grid-2">
                  <label>
                    Numeric
                    <select value={xy.gnum} onChange={(e) => setXy({ ...xy, gnum: e.target.value })}>
                      {kinds.numeric.map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Category
                    <select value={xy.gcat} onChange={(e) => setXy({ ...xy, gcat: e.target.value })}>
                      {catOpts.map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  </label>
                </div>
                <Chart figure={rel?.grouped_box} />
                <Chart figure={profile.charts.pair} />
              </section>
            )}

            {tab === 5 && (
              <section>
                <p className="kicker">Prepare features</p>
                <div className="warn">
                  <strong>Avoid data leakage.</strong> Fit every imputer, encoder, and scaler on the
                  training fold only.
                </div>
                {profile.recommendations.map((rec) => (
                  <p className="rec" key={rec.step}>
                    <strong>{rec.step}</strong> — {rec.detail}
                  </p>
                ))}
                <button
                  className="btn"
                  type="button"
                  style={{ width: "auto", padding: "10px 16px" }}
                  disabled={busy}
                  onClick={() =>
                    run(async () =>
                      setPrep(
                        await postJson("/api/prepare", {
                          session_id: profile.session_id,
                          target,
                        })
                      )
                    )
                  }
                >
                  Build cleaned preview + 70/30 split
                </button>
                {prep ? (
                  <>
                    <div className="metrics">
                      <div className="metric">
                        <span>Train (70%)</span>
                        <strong>{prep.train_rows}</strong>
                      </div>
                      <div className="metric">
                        <span>Test (30%)</span>
                        <strong>{prep.test_rows}</strong>
                      </div>
                    </div>
                    <Table rows={prep.class_mix} />
                    <Table rows={prep.cleaned_preview} />
                    <a
                      className="btn"
                      style={{ width: "auto", display: "inline-block", textDecoration: "none" }}
                      href={`data:text/csv;charset=utf-8,${encodeURIComponent(prep.cleaned_csv)}`}
                      download="model_ready_preview.csv"
                    >
                      Download cleaned preview
                    </a>
                  </>
                ) : null}
              </section>
            )}

            {tab === 6 && (
              <section>
                <p className="kicker">Insights and model readiness</p>
                <p className="muted">
                  Llama reads the EDA profile — not the raw file — and writes insights plus modeling
                  recommendations.
                </p>
                <textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Optional question, e.g. Which three features should I engineer first?"
                />
                <button
                  className="btn"
                  type="button"
                  style={{ width: "auto", padding: "10px 16px" }}
                  disabled={busy}
                  onClick={() =>
                    run(async () => {
                      const data = await postJson("/api/insights", {
                        session_id: profile.session_id,
                        target,
                        extra_question: question,
                        provider,
                        groq_model: model,
                      });
                      setInsights(data.markdown);
                    })
                  }
                >
                  Generate insights
                </button>
                {insights ? (
                  <div className="panel insights" dangerouslySetInnerHTML={{ __html: md(insights) }} />
                ) : (
                  <div className="panel">
                    <p className="kicker">What you will get</p>
                    <ul>
                      <li>Key insights tied to this table</li>
                      <li>Quality and leakage risks</li>
                      <li>A feature-preparation sequence</li>
                      <li>Algorithm, metric, and split advice</li>
                    </ul>
                  </div>
                )}
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}
