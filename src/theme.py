"""Visual system: warm paper canvas, ink navy, teal signal, rust alert."""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

INK = "#12233A"
TEAL = "#0F766E"
TEAL_SOFT = "#5BA8A0"
RUST = "#C2410C"
AMBER = "#B45309"
PAPER = "#F3EEE4"
PAPER_DEEP = "#E7E0D2"
LINE = "#D4CBB8"
MUTED = "#5C6570"
GOOD = "#3F6B4A"
WARN = "#B45309"
CRIT = "#9F2D00"

COLORWAY = [TEAL, RUST, "#1D4E89", AMBER, "#3F3F46", TEAL_SOFT, "#7C2D12"]

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,560;9..144,700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

html, body, [class*="css"], .stApp, p, div, span, label, input {
  font-family: "IBM Plex Sans", sans-serif;
}

h1, h2, h3, h4, .hero-title, .section-kicker {
  font-family: "Fraunces", serif !important;
  letter-spacing: -0.02em;
}

.stApp {
  background: #F3EEE4;
}

[data-testid="stSidebar"] {
  background: #12233A;
  border-right: 1px solid #0B1828;
}

[data-testid="stSidebar"] * {
  color: #E7E0D2 !important;
}

[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {
  color: #C9C2B4 !important;
}

[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
  color: #F3EEE4 !important;
}

[data-testid="stHeader"] {
  background: transparent;
}

div[data-testid="stMetric"] {
  background: #E7E0D2;
  border: 1px solid #D4CBB8;
  padding: 12px 14px;
  border-radius: 2px;
}

div[data-testid="stMetric"] label {
  color: #5C6570 !important;
  text-transform: uppercase;
  font-size: 0.72rem !important;
  letter-spacing: 0.06em;
}

.block-container {
  padding-top: 1.4rem;
  max-width: 1280px;
}

.hero-title {
  font-size: 2.15rem;
  color: #12233A;
  margin: 0 0 0.25rem 0;
  font-weight: 700;
}

.hero-sub {
  color: #5C6570;
  font-size: 1.02rem;
  max-width: 46rem;
  margin-bottom: 1.4rem;
}

.step-rail {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 6px;
  margin: 0 0 1.4rem 0;
}

.step-chip {
  background: #E7E0D2;
  border: 1px solid #D4CBB8;
  padding: 8px 8px 10px 8px;
  text-align: center;
}

.step-chip .n {
  display: block;
  font-family: "Fraunces", serif;
  font-size: 1.05rem;
  color: #0F766E;
  font-weight: 700;
}

.step-chip .l {
  display: block;
  font-size: 0.68rem;
  color: #5C6570;
  line-height: 1.25;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.panel {
  background: #FBF8F1;
  border: 1px solid #D4CBB8;
  padding: 16px 18px;
  margin: 0 0 1rem 0;
}

.kicker {
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #0F766E;
  font-weight: 600;
  margin-bottom: 4px;
}

.status-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin: 8px 0 14px 0;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border: 1px solid #D4CBB8;
  font-size: 0.84rem;
  background: #FBF8F1;
}

.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  display: inline-block;
}

.dot-good { background: #3F6B4A; }
.dot-warn { background: #B45309; }
.dot-crit { background: #9F2D00; }

.gauge-wrap {
  border: 1px solid #D4CBB8;
  background: #FBF8F1;
  padding: 14px 16px;
}

.gauge-track {
  height: 10px;
  background: linear-gradient(90deg, #3F6B4A 0%, #B45309 55%, #9F2D00 100%);
  position: relative;
  margin-top: 8px;
}

.gauge-needle {
  position: absolute;
  top: -4px;
  width: 3px;
  height: 18px;
  background: #12233A;
}

.warn-banner {
  border-left: 4px solid #9F2D00;
  background: #F6E8DC;
  padding: 12px 14px;
  margin: 10px 0 16px 0;
  color: #12233A;
}

.insight-box {
  background: #12233A;
  color: #E7E0D2;
  padding: 18px 20px;
  border: 1px solid #0B1828;
}

.insight-box h3 {
  color: #F3EEE4 !important;
  margin-top: 0;
}

.insight-box p, .insight-box li {
  color: #D7D0C2 !important;
}

.stTabs [data-baseweb="tab-list"] {
  gap: 4px;
  background: transparent;
  border-bottom: 1px solid #D4CBB8;
}

.stTabs [data-baseweb="tab"] {
  background: transparent;
  color: #5C6570;
  padding: 10px 14px;
}

.stTabs [aria-selected="true"] {
  color: #12233A !important;
  border-bottom: 2px solid #0F766E;
}

.stButton>button {
  border-radius: 2px;
  border: 1px solid #0F766E;
  background: #0F766E;
  color: #F3EEE4;
  font-weight: 500;
}

.stButton>button:hover {
  background: #0C5F59;
  border-color: #0C5F59;
  color: #fff;
}

hr { border-color: #D4CBB8; }

.table-wrap {
  overflow: auto;
  max-height: 440px;
  border: 1px solid #D4CBB8;
  background: #FBF8F1;
  margin: 0 0 1rem 0;
}
.table-wrap table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.84rem;
}
.table-wrap th {
  text-align: left;
  background: #E7E0D2;
  position: sticky;
  top: 0;
  padding: 7px 8px;
  border-bottom: 1px solid #D4CBB8;
  white-space: nowrap;
}
.table-wrap td {
  padding: 6px 8px;
  border-bottom: 1px solid #E7E0D2;
  vertical-align: top;
}
"""


def inject_css() -> None:
    import streamlit as st

    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def show_table(df, max_rows: int = 80, show_index: bool = False) -> None:
    """HTML table — avoids Streamlit's pyarrow path (blocked on some Windows machines)."""
    import streamlit as st

    if df is None or len(df) == 0:
        st.caption("No rows to show.")
        return
    view = df.head(max_rows)
    html = view.to_html(index=show_index, border=0, classes="eda-tbl", escape=True, na_rep="")
    extra = f"<p style='font-size:0.75rem;color:#5C6570;padding:6px 8px;'>Showing {len(view):,} of {len(df):,} rows.</p>" if len(df) > max_rows else ""
    st.markdown(f'<div class="table-wrap">{html}{extra}</div>', unsafe_allow_html=True)


def apply_plotly_theme() -> None:
    layout = go.Layout(
        paper_bgcolor=PAPER,
        plot_bgcolor=PAPER,
        font=dict(family="IBM Plex Sans, sans-serif", color=INK, size=12),
        colorway=COLORWAY,
        margin=dict(l=48, r=24, t=48, b=48),
        title=dict(font=dict(family="Fraunces, serif", size=16, color=INK)),
        xaxis=dict(
            gridcolor=LINE,
            zerolinecolor=LINE,
            linecolor=LINE,
            ticks="outside",
        ),
        yaxis=dict(
            gridcolor=LINE,
            zerolinecolor=LINE,
            linecolor=LINE,
            ticks="outside",
        ),
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
        hoverlabel=dict(bgcolor=INK, font=dict(color=PAPER)),
    )
    pio.templates["eda_studio"] = go.layout.Template(layout=layout)
    pio.templates.default = "eda_studio"


def style_fig(fig: go.Figure, title: str, x: str | None = None, y: str | None = None) -> go.Figure:
    if "eda_studio" not in pio.templates:
        apply_plotly_theme()
    fig.update_layout(
        title=title,
        paper_bgcolor=PAPER,
        plot_bgcolor=PAPER,
        font=dict(family="IBM Plex Sans, sans-serif", color=INK, size=12),
        colorway=COLORWAY,
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
    )
    if x:
        fig.update_xaxes(title=x, gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE)
    if y:
        fig.update_yaxes(title=y, gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE)
    return fig
