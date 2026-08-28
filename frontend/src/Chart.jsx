import { useEffect, useRef } from "react";
import Plotly from "plotly.js-dist-min";

export default function Chart({ figure, title }) {
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || !figure) return undefined;
    const layout = {
      ...(figure.layout || {}),
      autosize: true,
      paper_bgcolor: "#F3EEE4",
      plot_bgcolor: "#F3EEE4",
      font: { family: "IBM Plex Sans, sans-serif", color: "#12233A", size: 12 },
      margin: { l: 56, r: 24, t: 48, b: 52, ...(figure.layout?.margin || {}) },
    };
    Plotly.react(el, figure.data || [], layout, {
      responsive: true,
      displayModeBar: false,
    });
    const onResize = () => Plotly.Plots.resize(el);
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      Plotly.purge(el);
    };
  }, [figure]);

  if (!figure) return null;
  return (
    <div className="chart-frame">
      {title ? <p className="chart-caption">{title}</p> : null}
      <div ref={ref} className="chart" />
    </div>
  );
}
