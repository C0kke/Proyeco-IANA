from __future__ import annotations

from typing import Any, Dict, List

from jinja2 import Template

HTML_TMPL = Template(
    """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <title>Informe IANA v0.1</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; }
    h1 { margin-bottom: 8px; }
    .meta { color: #666; margin-bottom: 16px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 8px; vertical-align: top; }
    th { background: #f6f6f6; text-align: left; }
    .PASS { color: #1b5e20; font-weight: 700; }
    .FAIL { color: #b71c1c; font-weight: 700; }
    .UNVERIFIABLE { color: #6d4c41; font-weight: 700; }
    .sev-high { font-weight: 700; }
    .evi { font-size: 12px; color:#333; }
    .pill { display:inline-block; padding:2px 8px; border-radius: 999px; background:#eee; font-size:12px; }
  </style>
</head>
<body>
  <h1>Informe preliminar — IANA v0.1</h1>
  <div class="meta">Archivo: <b>{{ filename }}</b> · Hallazgos: <b>{{ findings|length }}</b></div>
  <table>
    <thead>
      <tr>
        <th>Regla</th><th>Severidad</th><th>Estado</th><th>Confianza</th><th>Evidencia (página / snippet)</th>
      </tr>
    </thead>
    <tbody>
      {% for f in findings %}
      <tr>
        <td><b>{{ f.id }}</b> — {{ f.title }}<br><span class="pill">{{ f.norm_ref }}</span></td>
        <td class="{{ 'sev-high' if f.severity=='high' else '' }}">{{ f.severity }}</td>
        <td class="{{ f.status }}">{{ f.status }}</td>
        <td>{{ "%.2f"|format(f.confidence) }}</td>
        <td class="evi">
          {% if f.evidence and f.evidence|length > 0 %}
            {% for e in f.evidence %}
              <div>p. {{ e.page }} — {{ e.snippet }}</div>
            {% endfor %}
          {% else %}
            {{ f.notes }}
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</body>
</html>
"""
)


def render_html_report(filename: str, findings: List[Dict[str, Any]]) -> str:
    return HTML_TMPL.render(filename=filename, findings=findings)
