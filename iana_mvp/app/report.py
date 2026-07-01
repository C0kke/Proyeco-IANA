from __future__ import annotations

from typing import Any, Dict, List
from datetime import datetime
from jinja2 import Template

HTML_TMPL = Template(
    """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <title>Informe IANA v0.1</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; color: #333; }
    h1 { margin-bottom: 8px; }
    .meta { color: #666; margin-bottom: 16px; font-size: 14px; }
    table { border-collapse: collapse; width: 100%; margin-top: 16px; }
    th, td { border: 1px solid #ddd; padding: 8px; vertical-align: top; }
    th { background: #f6f6f6; text-align: left; }
    .ALTA { color: #b71c1c; font-weight: 700; }
    .MEDIA { color: #e65100; font-weight: 700; }
    .BAJA { color: #0d47a1; font-weight: 700; }
    .summary-box { background: #f9f9f9; border: 1px solid #ddd; padding: 16px; margin-bottom: 20px; border-radius: 4px; }
    .summary-box h3 { margin-top: 0; margin-bottom: 8px; }
    code { font-family: Consolas, monospace; background: #eee; padding: 2px 4px; border-radius: 3px; }
  </style>
</head>
<body>
  <h1>Informe preliminar — IANA v0.1</h1>
  <div class="meta">
    Archivo: <b>{{ result.filename }}</b> &middot; 
    Proyecto: <strong>{{ result.project_name }}</strong> &middot; 
    Viabilidad Normativa: <strong>{{ "%.1f"|format(result.success_probability) }}%</strong>
  </div>

  <div class="summary-box">
    <h3>Resumen Ejecutivo:</h3>
    <p style="white-space: pre-line; margin: 0;">{{ result.summary_notes }}</p>
  </div>

  <h2>Infracciones Identificadas (OGUC)</h2>
  <table>
    <thead>
      <tr>
        <th>Artículo OGUC</th>
        <th>Descripción de Infracción</th>
        <th>Severidad</th>
        <th>Evidencia en Documento</th>
        <th>Justificación Legal (OGUC)</th>
      </tr>
    </thead>
    <tbody>
      {% if result.infractions and result.infractions|length > 0 %}
        {% for infraction in result.infractions %}
        <tr>
          <td><b>{{ infraction.rule_id }}</b></td>
          <td>{{ infraction.description }}</td>
          <td class="{{ infraction.severity }}">{{ infraction.severity }}</td>
          <td><code>{{ infraction.evidence }}</code></td>
          <td>{{ infraction.justification }}</td>
        </tr>
        {% endfor %}
      {% else %}
        <tr>
          <td colspan="5" style="text-align: center; color: green; font-weight: bold; padding: 20px;">
            ¡Proyecto Aprobable! No se detectaron infracciones normativas en el análisis.
          </td>
        </tr>
      {% endif %}
    </tbody>
  </table>
</body>
</html>
"""
)

PDF_TMPL = Template(
    """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <title>Informe IANA v0.1</title>
  <style>
    @page {
      size: letter;
      margin: 0.8in;
    }
    
    body {
      font-family: Arial, sans-serif;
      color: #333333;
      font-size: 9.5px;
      line-height: 1.35;
      margin: 0;
      padding: 0;
    }
    
    .page-break {
      page-break-before: always;
      break-before: page;
      clear: both;
    }
    
    .cover-page {
      position: relative;
      height: 100%;
      box-sizing: border-box;
      padding-top: 120px;
    }
    
    .cover-title {
      font-size: 28px;
      font-weight: bold;
      color: #0d47a1;
      margin-bottom: 8px;
      text-align: center;
      text-transform: uppercase;
      letter-spacing: 1px;
    }
    
    .cover-subtitle {
      font-size: 14px;
      color: #555555;
      margin-bottom: 120px;
      text-align: center;
      font-weight: normal;
    }
    
    .cover-meta {
      width: 60%;
      margin-left: auto;
      margin-right: 0;
      text-align: left;
      background: transparent;
      padding: 0;
      border: none;
      box-sizing: border-box;
      font-size: 9px;
    }
    
    .cover-meta p {
      margin: 5px 0;
      color: #444444;
    }
    
    .section-title {
      font-size: 12px;
      font-weight: bold;
      color: #0d47a1;
      margin-top: 0;
      margin-bottom: 12px;
      border-bottom: 1.5px solid #0d47a1;
      padding-bottom: 4px;
      text-transform: uppercase;
      text-align: left;
    }
    
    .metrics-table {
      width: 100%;
      border-collapse: collapse;
      border: none !important;
      margin-bottom: 15px;
    }
    
    .metrics-table td {
      width: 33.33%;
      border: none !important;
      padding: 6px 4px;
      text-align: center;
      background: transparent !important;
    }
    
    .metric-label {
      font-size: 8px;
      color: #666666;
      text-transform: uppercase;
      font-weight: bold;
      margin-bottom: 4px;
    }
    
    .metric-value {
      font-size: 15px;
      font-weight: bold;
      color: #111111;
    }
    
    .summary-box {
      margin-top: 15px;
      margin-bottom: 15px;
      line-height: 1.4;
      font-size: 9px;
    }
    
    .summary-box h3 {
      margin-top: 0;
      margin-bottom: 6px;
      font-size: 10px;
      color: #0d47a1;
      text-transform: uppercase;
      font-weight: bold;
    }
    
    .summary-text {
      white-space: pre-line;
      margin: 0;
      color: #444444;
    }
    
    .infraction-list {
      margin-top: 10px;
    }
    
    .infraction-item {
      border-bottom: 1px solid #e0e0e0;
      padding-top: 8px;
      padding-bottom: 8px;
      page-break-inside: avoid;
      break-inside: avoid;
    }
    
    .infraction-header {
      overflow: hidden;
      margin-bottom: 6px;
    }
    
    .infraction-rule {
      font-size: 11px;
      font-weight: bold;
      color: #0d47a1;
      float: left;
    }
    
    .infraction-severity-container {
      float: right;
    }
    
    .infraction-detail {
      margin-top: 4px;
      font-size: 9px;
      color: #333333;
      clear: both;
    }
    
    .infraction-detail p {
      margin: 4px 0;
    }
    
    .badge {
      display: inline-block;
      padding: 2px 5px;
      border-radius: 3px;
      font-size: 8px;
      font-weight: bold;
      text-align: center;
    }
    
    .badge-alta {
      background-color: #ffebee;
      color: #c62828;
      border: 1px solid #ffcdd2;
    }
    
    .badge-media {
      background-color: #fff3e0;
      color: #ef6c00;
      border: 1px solid #ffe0b2;
    }
    
    .badge-baja {
      background-color: #e3f2fd;
      color: #1565c0;
      border: 1px solid #bbdefb;
    }
    
    code {
      font-family: Consolas, Monaco, monospace;
      background: #f5f5f5;
      padding: 1px 3px;
      border: 1px solid #e0e0e0;
      border-radius: 3px;
      font-size: 8px;
    }
  </style>
</head>
<body>
  <div class="cover-page">
    <div class="cover-title">Informe Preliminar</div>
    <div class="cover-subtitle">IANA V0.1.1</div>
    
    <div class="cover-meta">
      <p><b>Archivo Analizado:</b> {{ result.filename }}</p>
      <p><b>Proyecto Registrado:</b> {{ result.project_name }}</p>
      <p><b>Fecha de Emisión:</b> {{ created_at }}</p>
      <p><b>Estado de Viabilidad:</b> 
        {% if result.infractions|length > 0 %}
          Aprobado con observaciones
        {% else %}
          Aprobado
        {% endif %}
      </p>
      <p><b>Cumplimiento Normativo:</b> {{ "%.1f"|format(result.success_probability) }}%</p>
    </div>
    <div style="margin-top: 30px; font-size: 7.5px; color: #777777; text-align: left; width: 60%; margin-left: auto; line-height: 1.25;">
      * Este informe preliminar actúa estrictamente como una herramienta de apoyo al diagnóstico preventivo de cumplimiento normativo y no constituye una aprobación formal de edificación.
    </div>
  </div>

  <div class="page-break"></div>

  <div class="section-title">1. Resumen Ejecutivo de Viabilidad</div>
  
  <table class="metrics-table">
    <tr>
      <td>
        <div class="metric-label">Viabilidad Normativa</div>
        <div class="metric-value">{{ "%.1f"|format(result.success_probability) }}%</div>
      </td>
      <td>
        <div class="metric-label">Infracciones Detectadas</div>
        <div class="metric-value">{{ result.infractions|length }}</div>
      </td>
      <td>
        <div class="metric-label">Estado General</div>
        <div class="metric-value" style="font-size: 11px; font-weight: bold; padding-top: 2px;">
          {% if result.infractions|length > 0 %}
            Aprobado con obs.
          {% else %}
            Aprobado
          {% endif %}
        </div>
      </td>
    </tr>
  </table>

  <div class="summary-box">
    <h3>Análisis y Observaciones Generales</h3>
    <p class="summary-text">{{ result.summary_notes }}</p>
  </div>

  <div class="page-break"></div>

  <div class="section-title">2. Detalle de Infracciones Identificadas (OGUC)</div>
  
  <div class="infraction-list">
    {% if result.infractions and result.infractions|length > 0 %}
      {% for infraction in result.infractions %}
      <div class="infraction-item">
        <div class="infraction-header">
          <div class="infraction-rule">Artículo {{ infraction.rule_id }}</div>
          <div class="infraction-severity-container">
            {% if infraction.severity == 'ALTA' %}
              <span class="badge badge-alta">ALTA</span>
            {% elif infraction.severity == 'MEDIA' %}
              <span class="badge badge-media">MEDIA</span>
            {% else %}
              <span class="badge badge-baja">BAJA</span>
            {% endif %}
          </div>
        </div>
        <div class="infraction-detail">
          <p><b>Descripción de Infracción:</b> {{ infraction.description }}</p>
          <p><b>Evidencia en Documento:</b> <code>{{ infraction.evidence }}</code></p>
          <p><b>Justificación Legal (OGUC):</b> {{ infraction.justification }}</p>
        </div>
      </div>
      {% endfor %}
    {% else %}
      <div style="text-align: center; color: green; font-weight: bold; padding: 20px; font-size: 11px;">
        ¡Proyecto Aprobable! No se detectaron infracciones normativas en el análisis.
      </div>
    {% endif %}
  </div>
</body>
</html>
"""
)


def render_html_report(filename: str, result: Dict[str, Any]) -> str:
    """
    Renderiza el reporte HTML utilizando la plantilla original (llamativa) del validador.
    Soporta la estructura de infractions (IA).
    """
    return HTML_TMPL.render(filename=filename, result=result)


def render_pdf_report(filename: str, result: Dict[str, Any]) -> bytes:
    """
    Renderiza el reporte en formato PDF utilizando PyMuPDF a partir del mismo template HTML.
    """
    import fitz

    now_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    html_content = PDF_TMPL.render(filename=filename, result=result, created_at=now_str)
    
    doc = fitz.open("html", html_content.encode("utf-8"))
    pdf_bytes = doc.convert_to_pdf()
    doc.close()
    return pdf_bytes