"""Create visual×visual chord diagram (PNG + interactive HTML)."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from pycirclize import Circos

DATA = Path("bib/cooccurrence/visual_chord_data.json")
OUT_DIR = Path("src/data/figures")
OUT_DIR.mkdir(parents=True, exist_ok=True)

payload = json.loads(DATA.read_text(encoding="utf-8"))
labels = payload["short"]
matrix = np.array(payload["matrix"], dtype=float)

# Circos chord from dataframe-like matrix
df = pd.DataFrame(matrix, index=labels, columns=labels)

circos = Circos.chord_diagram(
    df,
    space=2,
    cmap="tab20",
    ticks_interval=10,
    label_kws=dict(size=8),
    link_kws=dict(direction=0, ec="black", lw=0.2),
)

png_path = OUT_DIR / "visual_x_visual_chord.png"
circos.savefig(png_path, dpi=200)
print("Wrote", png_path)

# Also SVG for paper
svg_path = OUT_DIR / "visual_x_visual_chord.svg"
circos.savefig(svg_path)
print("Wrote", svg_path)

# Interactive HTML (D3)
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Visual × Visual Co-occurrence Chord Diagram</title>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<style>
  body {{
    margin: 0;
    font-family: Georgia, "Times New Roman", serif;
    background: #f7f5f1;
    color: #1a1a1a;
  }}
  header {{
    padding: 20px 28px 8px;
    max-width: 960px;
    margin: 0 auto;
  }}
  h1 {{
    font-size: 22px;
    font-weight: 600;
    margin: 0 0 6px;
  }}
  p {{
    margin: 0;
    font-size: 14px;
    line-height: 1.45;
    color: #444;
  }}
  #chart {{
    display: flex;
    justify-content: center;
    padding: 8px 12px 28px;
  }}
  .caption {{
    max-width: 960px;
    margin: 0 auto 24px;
    padding: 0 28px;
    font-size: 12px;
    color: #666;
  }}
  .ribbon:hover {{
    stroke-opacity: 0.9 !important;
  }}
  #tooltip {{
    position: absolute;
    pointer-events: none;
    background: #1a1a1a;
    color: #fff;
    padding: 8px 10px;
    font-size: 12px;
    border-radius: 2px;
    opacity: 0;
    transition: opacity 0.12s;
    max-width: 280px;
    z-index: 10;
  }}
</style>
</head>
<body>
<header>
  <h1>Co-occurrence of visual representations</h1>
  <p>Chord diagram of how chart/view types appear together across classified papers. Ribbon thickness encodes co-occurrence count. Hover a ribbon or arc for details.</p>
</header>
<div id="chart"></div>
<div class="caption">Source: Survey classifications · <code>bib/cooccurrence/visual_x_visual.csv</code> · Self-links show papers using that type alone or counted on-diagonal.</div>
<div id="tooltip"></div>
<script>
const data = {json.dumps({"names": labels, "full": payload["labels"], "matrix": payload["matrix"]})};

const width = 820;
const height = 820;
const innerRadius = Math.min(width, height) * 0.5 - 110;
const outerRadius = innerRadius + 14;

const colors = d3.quantize(d3.interpolateRainbow, data.names.length + 1);

const chord = d3.chord()
  .padAngle(0.03)
  .sortSubgroups(d3.descending)
  .sortChords(d3.descending);

const arc = d3.arc()
  .innerRadius(innerRadius)
  .outerRadius(outerRadius);

const ribbon = d3.ribbon()
  .radius(innerRadius - 2);

const svg = d3.select("#chart").append("svg")
  .attr("width", width)
  .attr("height", height)
  .attr("viewBox", [-width/2, -height/2, width, height])
  .attr("style", "max-width: 100%; height: auto;");

const matrix = data.matrix;
const chords = chord(matrix);
const tooltip = d3.select("#tooltip");

const group = svg.append("g")
  .selectAll("g")
  .data(chords.groups)
  .join("g");

group.append("path")
  .attr("fill", d => colors[d.index])
  .attr("stroke", "#222")
  .attr("stroke-width", 0.4)
  .attr("d", arc)
  .on("mouseover", (event, d) => {{
    const name = data.full[d.index];
    const total = d3.sum(matrix[d.index]);
    tooltip.style("opacity", 1)
      .html(`<b>${{name}}</b><br/>Total linked count: ${{total}}`)
      .style("left", (event.pageX + 12) + "px")
      .style("top", (event.pageY - 10) + "px");
    fade(d.index);
  }})
  .on("mousemove", (event) => {{
    tooltip.style("left", (event.pageX + 12) + "px")
      .style("top", (event.pageY - 10) + "px");
  }})
  .on("mouseout", () => {{
    tooltip.style("opacity", 0);
    reset();
  }});

group.append("text")
  .each(d => {{ d.angle = (d.startAngle + d.endAngle) / 2; }})
  .attr("dy", "0.35em")
  .attr("transform", d => `
    rotate(${{(d.angle * 180 / Math.PI - 90)}})
    translate(${{outerRadius + 8}})
    ${{d.angle > Math.PI ? "rotate(180)" : ""}}
  `)
  .attr("text-anchor", d => d.angle > Math.PI ? "end" : "start")
  .attr("font-size", 11)
  .text(d => data.names[d.index]);

const ribbons = svg.append("g")
  .attr("fill-opacity", 0.72)
  .selectAll("path")
  .data(chords)
  .join("path")
  .attr("class", "ribbon")
  .attr("d", ribbon)
  .attr("fill", d => colors[d.source.index])
  .attr("stroke", "#222")
  .attr("stroke-opacity", 0.15)
  .attr("stroke-width", 0.3)
  .on("mouseover", (event, d) => {{
    const a = data.full[d.source.index];
    const b = data.full[d.target.index];
    const v = d.source.value;
    tooltip.style("opacity", 1)
      .html(`<b>${{a}}</b> ↔ <b>${{b}}</b><br/>Co-occurrence: ${{v}}`)
      .style("left", (event.pageX + 12) + "px")
      .style("top", (event.pageY - 10) + "px");
    ribbons.attr("fill-opacity", r =>
      (r.source.index === d.source.index && r.target.index === d.target.index) ||
      (r.source.index === d.target.index && r.target.index === d.source.index) ? 0.9 : 0.08
    );
  }})
  .on("mousemove", (event) => {{
    tooltip.style("left", (event.pageX + 12) + "px")
      .style("top", (event.pageY - 10) + "px");
  }})
  .on("mouseout", () => {{
    tooltip.style("opacity", 0);
    reset();
  }});

function fade(index) {{
  ribbons.attr("fill-opacity", d =>
    d.source.index === index || d.target.index === index ? 0.9 : 0.08
  );
}}
function reset() {{
  ribbons.attr("fill-opacity", 0.72);
}}
</script>
</body>
</html>
"""

html_path = OUT_DIR / "visual_x_visual_chord.html"
html_path.write_text(html, encoding="utf-8")
print("Wrote", html_path)
