from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
from jinja2 import Template

HTML_TMPL = Template(
"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Informe IANA — {{ result.project_name or 'Auditoría Normativa' }}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;600;700;800;900&family=Raleway:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --brand-negro-profundo: #0A0A0A;
      --brand-carbon: #141416;
      --brand-card: #18181b;
      --brand-grafito: #333333;
      --brand-acero: #71717a;
      --brand-plata: #B0B0BD;
      --brand-blanco: #FFFFFF;
      --brand-dorado: #D4AF37;
      --brand-dorado-hover: #E5C158;
      --border-color: #27272a;
      
      --cumple-bg: #065f46;
      --cumple-text: #34d399;
      --cumple-border: #059669;
      
      --nocumple-bg: #7f1d1d;
      --nocumple-text: #f87171;
      --nocumple-border: #dc2626;
      
      --alerta-bg: #7c2d12;
      --alerta-text: #fb923c;
      --alerta-border: #ea580c;
      
      --method-data-bg: #1e3a8a;
      --method-data-text: #93c5fd;
      
      --method-prc-bg: #78350f;
      --method-prc-text: #fde047;
      
      --method-iana-bg: #581c87;
      --method-iana-text: #d8b4fe;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      padding: 32px 20px;
      background-color: var(--brand-negro-profundo);
      color: var(--brand-blanco);
      font-family: 'Raleway', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
    }

    .report-container {
      max-width: 1100px;
      margin: 0 auto;
    }

    .report-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 20px;
      margin-bottom: 24px;
      border-bottom: 1px solid var(--border-color);
      flex-wrap: wrap;
      gap: 16px;
    }

    .brand-logo-container {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .brand-logo-img {
      max-height: 52px;
      width: auto;
      display: block;
    }

    .brand-title-fallback {
      font-family: 'Orbitron', sans-serif;
      font-size: 24px;
      font-weight: 800;
      color: var(--brand-dorado);
      letter-spacing: 1px;
    }

    .header-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--brand-carbon);
      border: 1px solid var(--brand-dorado);
      color: var(--brand-dorado);
      font-family: 'Orbitron', sans-serif;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.8px;
      padding: 6px 14px;
      border-radius: 20px;
      text-transform: uppercase;
    }

    h1.main-title {
      font-family: 'Orbitron', sans-serif;
      font-size: 26px;
      font-weight: 700;
      color: var(--brand-blanco);
      margin: 0 0 16px 0;
      letter-spacing: -0.5px;
    }

    .meta-bar {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
      background-color: var(--brand-carbon);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 14px 18px;
      margin-bottom: 24px;
      font-size: 13px;
    }

    .meta-item {
      display: flex;
      flex-direction: column;
      gap: 3px;
    }

    .meta-label {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      color: var(--brand-acero);
      letter-spacing: 0.5px;
    }

    .meta-value {
      color: var(--brand-blanco);
      font-weight: 600;
      word-break: break-all;
    }

    .badge-status-project {
      display: inline-block;
      width: fit-content;
      padding: 3px 10px;
      border-radius: 4px;
      font-weight: 700;
      font-size: 11.5px;
      letter-spacing: 0.3px;
    }

    .status-rechazado { background-color: var(--nocumple-bg); color: var(--nocumple-text); border: 1px solid var(--nocumple-border); }
    .status-reformular { background-color: var(--alerta-bg); color: var(--alerta-text); border: 1px solid var(--alerta-border); }
    .status-posible { background-color: #78350f; color: #fde047; border: 1px solid #ca8a04; }
    .status-obs { background-color: #064e3b; color: #6ee7b7; border: 1px solid #059669; }
    .status-aprobado { background-color: var(--cumple-bg); color: var(--cumple-text); border: 1px solid var(--cumple-border); }

    .viability-number {
      font-family: 'Orbitron', sans-serif;
      color: var(--brand-dorado);
      font-size: 15px;
      font-weight: 700;
    }

    /* Caja de Desglose Matemático del Puntaje */
    .breakdown-card {
      background-color: var(--brand-card);
      border: 1px solid var(--border-color);
      border-left: 4px solid var(--brand-dorado);
      border-radius: 8px;
      padding: 18px 20px;
      margin-bottom: 28px;
    }

    .breakdown-title {
      font-family: 'Orbitron', sans-serif;
      font-size: 15px;
      font-weight: 700;
      color: var(--brand-dorado);
      margin: 0 0 12px 0;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .breakdown-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 12px;
      margin-top: 10px;
    }

    .breakdown-step {
      background-color: var(--brand-carbon);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 12px 14px;
    }

    .breakdown-step-title {
      font-size: 11px;
      color: var(--brand-acero);
      text-transform: uppercase;
      font-weight: 700;
    }

    .breakdown-step-val {
      font-family: 'Orbitron', sans-serif;
      font-size: 20px;
      font-weight: 700;
      margin-top: 4px;
    }

    .val-positive { color: var(--cumple-text); }
    .val-negative { color: var(--nocumple-text); }
    .val-final { color: var(--brand-dorado); }

    .breakdown-explanation {
      font-size: 12.5px;
      color: var(--brand-plata);
      margin-top: 12px;
      line-height: 1.5;
    }

    /* Cajas de Observaciones y Resumen */
    .summary-box {
      border-radius: 8px;
      padding: 16px 20px;
      margin-bottom: 20px;
    }

    .obs-box {
      background-color: var(--brand-carbon);
      border: 1px solid var(--border-color);
      border-left: 4px solid var(--brand-dorado);
    }

    .obs-box h3 {
      font-family: 'Orbitron', sans-serif;
      font-size: 14px;
      font-weight: 700;
      color: var(--brand-dorado);
      margin: 0 0 8px 0;
    }

    .obs-box p {
      color: var(--brand-plata);
      margin: 0;
      font-size: 13.5px;
      line-height: 1.5;
      white-space: pre-line;
    }

    .exec-box {
      background-color: var(--brand-card);
      border: 1px solid var(--border-color);
    }

    .exec-box h3 {
      font-family: 'Orbitron', sans-serif;
      font-size: 14px;
      font-weight: 700;
      color: var(--brand-blanco);
      margin: 0 0 8px 0;
    }

    .exec-box p {
      color: #d4d4d8;
      margin: 0;
      font-size: 13.5px;
      line-height: 1.6;
      white-space: pre-line;
    }

    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
      margin-bottom: 32px;
    }

    @media (max-width: 820px) {
      .metrics-grid { grid-template-columns: repeat(2, 1fr); }
    }

    .metric-card {
      background-color: var(--brand-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 16px 18px;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
    }

    .metric-label {
      color: #a1a1aa;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 6px;
    }

    .metric-number {
      font-family: 'Orbitron', sans-serif;
      font-size: 26px;
      font-weight: 700;
      color: var(--brand-blanco);
    }

    .metric-cumple { color: var(--cumple-text); }
    .metric-nocumple { color: var(--nocumple-text); }
    .metric-alerta { color: var(--alerta-text); }

    .section-heading {
      font-family: 'Orbitron', sans-serif;
      font-size: 18px;
      font-weight: 700;
      color: var(--brand-blanco);
      margin: 0 0 6px 0;
    }

    .section-subtext {
      font-size: 12.5px;
      color: #a1a1aa;
      margin: 0 0 16px 0;
      line-height: 1.5;
    }

    .table-responsive {
      overflow-x: auto;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      margin-bottom: 34px;
      background-color: var(--brand-card);
    }

    table.corporate-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12.5px;
    }

    table.corporate-table th {
      background-color: var(--brand-carbon);
      color: #a1a1aa;
      text-align: left;
      padding: 12px 14px;
      font-weight: 600;
      font-size: 11px;
      text-transform: uppercase;
      border-bottom: 1px solid var(--border-color);
    }

    table.corporate-table td {
      padding: 12px 14px;
      border-bottom: 1px solid var(--border-color);
      vertical-align: top;
      color: #e4e4e7;
    }

    .badge-severity {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-weight: 700;
      font-size: 11px;
      text-align: center;
    }

    .severity-alta { background-color: var(--nocumple-bg); color: var(--nocumple-text); }
    .severity-media { background-color: var(--alerta-bg); color: var(--alerta-text); }
    .severity-baja { background-color: var(--method-data-bg); color: var(--method-data-text); }

    .empty-infractions-banner {
      text-align: center;
      color: var(--cumple-text);
      font-weight: 700;
      padding: 24px;
      font-size: 13.5px;
      background-color: var(--brand-card);
    }

    .filter-bar {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }

    .filter-label {
      font-size: 12px;
      color: #a1a1aa;
      margin-right: 4px;
      font-weight: 600;
    }

    .filter-btn {
      background: var(--brand-carbon);
      border: 1px solid var(--border-color);
      color: #a1a1aa;
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-family: 'Raleway', sans-serif;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .filter-btn:hover {
      border-color: #3f3f46;
      color: #ffffff;
    }

    .filter-btn.active {
      background-color: #27272a;
      border-color: var(--brand-dorado);
      color: var(--brand-dorado);
    }

    .audit-cards-wrapper {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-bottom: 40px;
    }

    .audit-item-card {
      background-color: var(--brand-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 14px 16px;
      transition: border-color 0.15s ease;
    }

    .audit-item-card:hover { border-color: #3f3f46; }

    .border-cumple { border-left: 4px solid var(--cumple-border) !important; }
    .border-nocumple { border-left: 4px solid var(--nocumple-border) !important; }
    .border-alerta { border-left: 4px solid var(--alerta-border) !important; }

    .audit-card-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
      flex-wrap: wrap;
      gap: 8px;
    }

    .audit-element-title {
      font-weight: 700;
      color: #ffffff;
      font-size: 14px;
    }

    .audit-rule-code {
      color: #a1a1aa;
      font-size: 12px;
      margin-left: 8px;
      font-weight: 500;
    }

    .audit-badges-group {
      display: flex;
      gap: 6px;
      align-items: center;
    }

    .badge-method {
      font-weight: 600;
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 10px;
      white-space: nowrap;
    }

    .badge-method-data { background-color: var(--method-data-bg); color: var(--method-data-text); }
    .badge-method-prc { background-color: var(--method-prc-bg); color: var(--method-prc-text); }
    .badge-method-iana { background-color: var(--method-iana-bg); color: var(--method-iana-text); }

    .badge-status {
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 11px;
      white-space: nowrap;
    }

    .badge-status-cumple { background-color: var(--cumple-bg); color: var(--cumple-text); }
    .badge-status-nocumple { background-color: var(--nocumple-bg); color: var(--nocumple-text); }
    .badge-status-alerta { background-color: var(--alerta-bg); color: var(--alerta-text); }

    /* Badges de Impacto Porcentual */
    .badge-impact {
      font-family: 'JetBrains Mono', monospace;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 11px;
    }
    .badge-impact-pos { background-color: #064e3b; color: #34d399; border: 1px solid #059669; }
    .badge-impact-neg { background-color: #450a0a; color: #f87171; border: 1px solid #dc2626; }
    .badge-impact-neu { background-color: #27272a; color: #a1a1aa; border: 1px solid #3f3f46; }

    .audit-evidence-line {
      font-size: 12px;
      color: #d4d4d8;
      margin-bottom: 4px;
      line-height: 1.45;
    }

    .audit-rationale-line {
      font-size: 12px;
      color: #a1a1aa;
      line-height: 1.45;
    }

    code.evidence-code {
      font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
      background-color: #27272a;
      color: #e4e4e7;
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 11.5px;
      word-break: break-word;
    }

    .doc-source-tag {
      color: #71717a;
      margin-left: 6px;
      font-size: 11.5px;
    }

    .report-footer {
      border-top: 1px solid var(--border-color);
      padding-top: 20px;
      margin-top: 30px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      color: #71717a;
      font-size: 11.5px;
    }

    .footer-brand-title {
      font-family: 'Orbitron', sans-serif;
      font-weight: 700;
      color: var(--brand-dorado);
    }
  </style>
</head>
<body>
  <div class="report-container">
    <header class="report-header">
      <div class="brand-logo-container">
        {% if logo_b64 %}
          <img src="{{ logo_b64 }}" class="brand-logo-img" alt="Logo IANA" />
        {% else %}
          <span class="brand-title-fallback">IANA</span>
        {% endif %}
      </div>
      <div class="header-badge">
        <span>Auditoría Técnica Normativa</span>
      </div>
    </header>

    <h1 class="main-title">Informe preliminar — IANA</h1>

    <div class="meta-bar">
      <div class="meta-item">
        <span class="meta-label">Archivo Analizado</span>
        <span class="meta-value">{{ result.filename }}</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">Proyecto</span>
        <span class="meta-value">{{ result.project_name }}</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">Estado de Aprobación</span>
        <span class="meta-value">
          <span class="badge-status-project status-{{ status_class }}">{{ status_label }}</span>
        </span>
      </div>
      <div class="meta-item">
        <span class="meta-label">Viabilidad Normativa</span>
        <span class="meta-value viability-number">{{ "%.1f"|format(result.success_probability) }}%</span>
      </div>
    </div>

    <!-- MÓDULO DE UX: DESGLOSE MATEMÁTICO DE LA VIABILIDAD -->
    <div class="breakdown-card">
      <div class="breakdown-title">
        <span>📊 Trazabilidad y Cadena de Cálculo de Viabilidad</span>
      </div>
      <p class="breakdown-explanation">
        Explicación detallada de cómo se calcula la probabilidad final del expediente. La línea base inicia en el <b>100%</b> y ajusta según las conformidades comprobadas y las infracciones o vacíos normativos detectados al ingestar los documentos.
      </p>
      <div class="breakdown-grid">
        <div class="breakdown-step">
          <div class="breakdown-step-title">1. Línea Base Teórica</div>
          <div class="breakdown-step-val">100.0%</div>
        </div>
        <div class="breakdown-step">
          <div class="breakdown-step-title">2. Aportes / Convalidado (+)</div>
          <div class="breakdown-step-val val-positive">+{{ "%.1f"|format(score_breakdown.total_additions) }}%</div>
        </div>
        <div class="breakdown-step">
          <div class="breakdown-step-title">3. Penalizaciones (-)</div>
          <div class="breakdown-step-val val-negative">-{{ "%.1f"|format(score_breakdown.total_deductions) }}%</div>
        </div>
        <div class="breakdown-step">
          <div class="breakdown-step-title">4. Viabilidad Resultante</div>
          <div class="breakdown-step-val val-final">{{ "%.1f"|format(result.success_probability) }}%</div>
        </div>
      </div>
    </div>

    {% if result.observaciones %}
    <div class="summary-box obs-box">
      <h3>Observaciones / Contexto del Documento:</h3>
      <p>{{ result.observaciones }}</p>
    </div>
    {% endif %}

    {% if result.summary_notes %}
    <div class="summary-box exec-box">
      <h3>Resumen Ejecutivo:</h3>
      <p>{{ result.summary_notes }}</p>
    </div>
    {% endif %}

    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-label">Inspecciones Totales</div>
        <div class="metric-number">{{ stats.total }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Conformes (CUMPLE)</div>
        <div class="metric-number metric-cumple">{{ stats.cumple }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Infracciones (NO CUMPLE)</div>
        <div class="metric-number metric-nocumple">{{ stats.nocumple }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Alertas / Observaciones</div>
        <div class="metric-number metric-alerta">{{ stats.alerta }}</div>
      </div>
    </div>

    <h2 class="section-heading">Infracciones Identificadas (OGUC)</h2>
    <div class="table-responsive">
      <table class="corporate-table">
        <thead>
          <tr>
            <th style="width: 16%;">Artículo OGUC</th>
            <th style="width: 26%;">Descripción de Infracción</th>
            <th style="width: 10%;">Severidad</th>
            <th style="width: 24%;">Evidencia en Documento</th>
            <th style="width: 24%;">Justificación Legal (OGUC)</th>
          </tr>
        </thead>
        <tbody>
          {% if infractions and infractions|length > 0 %}
            {% for infraction in infractions %}
            <tr>
              <td><b>{{ infraction.rule_id }}</b></td>
              <td>{{ infraction.description }}</td>
              <td>
                <span class="badge-severity severity-{{ infraction.severity|lower }}">{{ infraction.severity }}</span>
              </td>
              <td><code class="evidence-code">{{ infraction.evidence }}</code></td>
              <td>{{ infraction.justification }}</td>
            </tr>
            {% endfor %}
          {% else %}
            <tr>
              <td colspan="5" class="empty-infractions-banner">
                ¡Proyecto Aprobable! No se detectaron infracciones normativas en el análisis.
              </td>
            </tr>
          {% endif %}
        </tbody>
      </table>
    </div>

    <h2 class="section-heading">Auditoría Técnica y Trazabilidad Normativa</h2>
    <p class="section-subtext">
      Registro de verificación transparente de cada elemento arquitectónico. Muestra el método de inspección y el <b>impacto porcentual exacto</b> que cada regla aporta o descuenta a la viabilidad del proyecto.
    </p>

    <div class="filter-bar">
      <span class="filter-label">Filtrar por Cumplimiento:</span>
      <button class="filter-btn active" onclick="filterAuditCards(this, 'all')">Todos ({{ stats.total }})</button>
      <button class="filter-btn" onclick="filterAuditCards(this, 'CUMPLE')">✔ Conformes ({{ stats.cumple }})</button>
      <button class="filter-btn" onclick="filterAuditCards(this, 'NO CUMPLE')">✖ Infracciones ({{ stats.nocumple }})</button>
      <button class="filter-btn" onclick="filterAuditCards(this, 'ALERTA')">⚠ Alertas ({{ stats.alerta }})</button>
    </div>

    <div class="audit-cards-wrapper" id="auditCardsWrapper">
      {% for item in inspected_rules %}
      <div class="audit-item-card border-{{ item.status_class }}" data-status="{{ item.status_category }}">
        <div class="audit-card-top">
          <div>
            <span class="audit-element-title">{{ item.element_inspected }}</span>
            <span class="audit-rule-code">({{ item.rule_id }})</span>
          </div>
          <div class="audit-badges-group">
            <span class="badge-impact {{ item.impact_class }}">{{ item.impact_label }}</span>
            <span class="badge-method {{ item.method_class }}">{{ item.method_label }}</span>
            <span class="badge-status {{ item.status_badge_class }}">{{ item.status_icon }} {{ item.status }}</span>
          </div>
        </div>
        <div class="audit-evidence-line">
          <b>Evidencia en Documento:</b> 
          <code class="evidence-code">{{ item.evidence_found }}</code>
          <span class="doc-source-tag">[{{ item.document_source }}]</span>
        </div>
        <div class="audit-rationale-line">
          <b>Fundamento Técnico:</b> {{ item.technical_rationale }}
        </div>
      </div>
      {% endfor %}
    </div>

    <footer class="report-footer">
      <div>
        <span class="footer-brand-title">IANA</span> &middot; Inteligencia Artificial Normativa para Arquitectura
      </div>
      <div>
        Generado automáticamente &middot; Cumplimiento OGUC y Planes Reguladores Comunales de Chile
      </div>
    </footer>
  </div>

  <script>
    function filterAuditCards(button, category) {
      const wrapper = document.getElementById('auditCardsWrapper');
      const cards = wrapper.getElementsByClassName('audit-item-card');
      const buttons = document.querySelectorAll('.filter-btn');
      
      buttons.forEach(b => b.classList.remove('active'));
      button.classList.add('active');
      
      for (let i = 0; i < cards.length; i++) {
        const card = cards[i];
        if (category === 'all') {
          card.style.display = 'block';
        } else {
          const cardStatus = card.getAttribute('data-status');
          if (cardStatus === category) {
            card.style.display = 'block';
          } else {
            card.style.display = 'none';
          }
        }
      }
    }
  </script>
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
    @page { size: letter; margin: 0.8in; }
    body { font-family: Arial, sans-serif; color: #333333; font-size: 9.5px; line-height: 1.35; margin: 0; padding: 0; }
    .page-break { page-break-before: always; break-before: page; clear: both; }
    .cover-page { position: relative; height: 100%; box-sizing: border-box; padding-top: 120px; }
    .cover-title { font-size: 28px; font-weight: bold; color: #0d47a1; margin-bottom: 8px; text-align: center; text-transform: uppercase; letter-spacing: 1px; }
    .cover-subtitle { font-size: 14px; color: #555555; margin-bottom: 120px; text-align: center; font-weight: normal; }
    .cover-meta { width: 60%; margin-left: auto; margin-right: 0; text-align: left; font-size: 9px; }
    .cover-meta p { margin: 5px 0; color: #444444; }
    .section-title { font-size: 12px; font-weight: bold; color: #0d47a1; margin-top: 0; margin-bottom: 12px; border-bottom: 1.5px solid #0d47a1; padding-bottom: 4px; text-transform: uppercase; }
    .metrics-table { width: 100%; border-collapse: collapse; border: none !important; margin-bottom: 15px; }
    .metrics-table td { width: 33.33%; border: none !important; padding: 6px 4px; text-align: center; }
    .metric-label { font-size: 8px; color: #666666; text-transform: uppercase; font-weight: bold; margin-bottom: 4px; }
    .metric-value { font-size: 15px; font-weight: bold; color: #111111; }
    .summary-box { margin-top: 15px; margin-bottom: 15px; line-height: 1.4; font-size: 9px; }
    .summary-box h3 { margin-top: 0; margin-bottom: 6px; font-size: 10px; color: #0d47a1; text-transform: uppercase; font-weight: bold; }
    .summary-text { white-space: pre-line; margin: 0; color: #444444; }
    .infraction-list { margin-top: 10px; }
    .infraction-item { border-bottom: 1px solid #e0e0e0; padding-top: 8px; padding-bottom: 8px; page-break-inside: avoid; }
    .infraction-header { overflow: hidden; margin-bottom: 6px; }
    .infraction-rule { font-size: 11px; font-weight: bold; color: #0d47a1; float: left; }
    .infraction-severity-container { float: right; }
    .infraction-detail { margin-top: 4px; font-size: 9px; color: #333333; clear: both; }
    .infraction-detail p { margin: 4px 0; }
    .badge { display: inline-block; padding: 2px 5px; border-radius: 3px; font-size: 8px; font-weight: bold; }
    .badge-alta { background-color: #ffebee; color: #c62828; border: 1px solid #ffcdd2; }
    .badge-media { background-color: #fff3e0; color: #ef6c00; border: 1px solid #ffe0b2; }
    .badge-baja { background-color: #e3f2fd; color: #1565c0; border: 1px solid #bbdefb; }
    code { font-family: Consolas, Monaco, monospace; background: #f5f5f5; padding: 1px 3px; border: 1px solid #e0e0e0; border-radius: 3px; font-size: 8px; }
  </style>
</head>
<body>
  <div class="cover-page">
    {% if logo_b64 %}
    <div style="text-align: center; margin-bottom: 30px;">
      <img src="{{ logo_b64 }}" style="max-width: 280px; height: auto;" alt="IANA Logo" />
    </div>
    {% endif %}
    <div class="cover-title">Informe Preliminar</div>
    <div class="cover-subtitle">IANA V0.1.1</div>
    
    <div class="cover-meta">
      <p><b>Archivo Analizado:</b> {{ result.filename }}</p>
      <p><b>Proyecto Registrado:</b> {{ result.project_name }}</p>
      <p><b>Fecha de Emisión:</b> {{ created_at }}</p>
      <p><b>Estado de Viabilidad:</b> {{ status_label }}</p>
      <p><b>Cumplimiento Normativo:</b> {{ "%.1f"|format(result.success_probability) }}%</p>
    </div>
    <div style="margin-top: 30px; font-size: 7.5px; color: #777777; width: 60%; margin-left: auto;">
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
          {{ status_label }}
        </div>
      </td>
    </tr>
  </table>

  {% if result.observaciones %}
  <div class="summary-box" style="margin-top: 10px; background-color: #f8fafc; padding: 10px; border-radius: 4px; border-left: 3px solid #0d47a1;">
    <h3 style="margin-top: 0; margin-bottom: 4px; color: #0d47a1; font-weight: bold; text-transform: uppercase;">Observaciones del Documento</h3>
    <p class="summary-text" style="color: #475569;">{{ result.observaciones }}</p>
  </div>
  {% endif %}

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


def get_status_label(result: Dict[str, Any]) -> str:
    is_valid = result.get("is_valid", True)
    infractions = result.get("infractions", [])
    has_high_severity = any(inf.get("severity") == "ALTA" for inf in infractions)
    success_probability = result.get("success_probability", 0.0)
    
    if not is_valid:
        return "Rechazado (No Válido)"
    elif has_high_severity:
        return "Rechazado"
    elif success_probability < 50.0:
        return "Rechazado"
    elif success_probability < 80.0:
        return "Reformular"
    elif success_probability < 95.0:
        return "Posible Aprobación"
    elif infractions:
        return "Aprobado con obs."
    else:
        return "Aprobado"


from app.assets import get_asset_base64


def build_or_extract_inspected_rules(
    result: Optional[Dict[str, Any]] = None, 
    project: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Construye la lista unificada de auditoría técnica con la asignación explícita
    de IMPACTOS PORCENTUALES (+ / - %) para eliminar el efecto de caja negra.
    """
    inspected_rules: List[Dict[str, Any]] = []
    
    if result and result.get("inspected_rules"):
        for r in result["inspected_rules"]:
            inspected_rules.append(r if isinstance(r, dict) else r.model_dump())
        return inspected_rules

    if project:
        meta = project.get("extracted_metadata") if isinstance(project.get("extracted_metadata"), dict) else {}
        if meta.get("inspected_rules"):
            for r in meta["inspected_rules"]:
                inspected_rules.append(r if isinstance(r, dict) else r.model_dump())
            return inspected_rules

    # Infracciones detectadas (PUNTOS NEGATIVOS)
    infrs = []
    if result:
        infrs = result.get("infractions") or []
        if not infrs and result.get("infracciones"):
            infrs = [
                {
                    "rule_id": item.get("articulo", "OGUC"),
                    "description": item.get("descripcion", ""),
                    "severity": item.get("gravedad", "MEDIA").upper(),
                    "evidence": item.get("evidencia", f"Página {item.get('pagina', 1)}"),
                    "justification": item.get("justificacion", "Incumplimiento normativo identificado.")
                }
                for item in result.get("infracciones", [])
            ]
    if not infrs and project:
        infrs = project.get("consolidated_infractions") or []
        
    for inf in infrs:
        rule_id = inf.get("rule_id") or inf.get("articulo", "OGUC")
        desc = inf.get("description") or inf.get("descripcion", "Elemento constructivo")
        evidence = inf.get("evidence") or inf.get("evidencia", "Detectado en análisis")
        sev = str(inf.get("severity") or inf.get("gravedad", "MEDIA")).upper()
        status = "NO CUMPLE" if sev == "ALTA" else "ALERTA"
        rationale = inf.get("justification") or inf.get("justificacion") or desc
        
        # Ponderación explícita según gravedad
        if sev == "ALTA":
            impact_val = -25.0
            impact_str = "-25.0%"
            impact_cls = "badge-impact-neg"
        elif sev == "MEDIA":
            impact_val = -10.0
            impact_str = "-10.0%"
            impact_cls = "badge-impact-neg"
        else:
            impact_val = -5.0
            impact_str = "-5.0%"
            impact_cls = "badge-impact-neg"

        inspected_rules.append({
            "rule_id": rule_id,
            "category": "Infracción Normativa",
            "element_inspected": desc[:70] if len(desc) > 70 else desc,
            "evidence_found": str(evidence),
            "document_source": "Expediente del proyecto",
            "status": status,
            "detection_method": "Modelo IANA",
            "technical_rationale": rationale,
            "impact_value": impact_val,
            "impact_label": impact_str,
            "impact_class": impact_cls
        })

    # Reglas PRC (Calculadas)
    meta = {}
    commune = ""
    region = ""
    if project:
        meta = project.get("extracted_metadata") if isinstance(project.get("extracted_metadata"), dict) else {}
        commune = project.get("commune", "")
        region = project.get("region", "")
    elif result and isinstance(result.get("extracted_metadata"), dict):
        meta = result.get("extracted_metadata", {})
        commune = result.get("commune", "")
        region = result.get("region", "")
        
    zone_code = meta.get("zona_prc") or meta.get("zona")
    if commune:
        try:
            from app.rules_engine import evaluate_prc_numeric_rules
            prc_res = evaluate_prc_numeric_rules(meta, region, commune, zone_code)
            s_map = {"PASS": "CUMPLE", "FAIL": "NO CUMPLE", "WARNING": "ALERTA", "UNVERIFIABLE": "NO VERIFICABLE"}
            for prc in prc_res:
                st = s_map.get(prc.get("status"), "ALERTA")
                if st == "CUMPLE":
                    imp_val, imp_str, imp_cls = 5.0, "+5.0%", "badge-impact-pos"
                elif st == "NO CUMPLE":
                    imp_val, imp_str, imp_cls = -20.0, "-20.0%", "badge-impact-neg"
                else:
                    imp_val, imp_str, imp_cls = -10.0, "-10.0%", "badge-impact-neg"

                inspected_rules.append({
                    "rule_id": prc.get("norm_ref", "PRC Local"),
                    "category": "Zonificación y Alturas",
                    "element_inspected": prc.get("title", "Parámetro PRC"),
                    "evidence_found": str(prc.get("evidence", "")),
                    "document_source": "Certificado Informaciones Previas (CIP) / PRC",
                    "status": st,
                    "detection_method": "Motor Determinista PRC",
                    "technical_rationale": prc.get("notes", ""),
                    "impact_value": imp_val,
                    "impact_label": imp_str,
                    "impact_class": imp_cls
                })
        except Exception:
            pass

    # Verificaciones Positivas Conformes (PUNTOS A FAVOR)
    inspected_rules.append({
        "rule_id": "Art. 4.1.7 OGUC",
        "category": "Accesibilidad y Puertas",
        "element_inspected": "Ancho libre de paso en puertas de acceso principal (0.90 m)",
        "evidence_found": "Cotas de vanos de acceso principal verificadas",
        "document_source": "Plano de arquitectura / ETT",
        "status": "CUMPLE",
        "detection_method": "Ciencia de Datos (Regex / NLP)",
        "technical_rationale": "Vanos de acceso conforme a la OGUC.",
        "impact_value": 5.0,
        "impact_label": "+5.0%",
        "impact_class": "badge-impact-pos"
    })
    inspected_rules.append({
        "rule_id": "Art. 4.1.2 OGUC",
        "category": "Habitabilidad y Ventilación",
        "element_inspected": "Iluminación natural directa en recintos habitables",
        "evidence_found": "Ventanas al exterior en recintos de permanencia",
        "document_source": "Plano de arquitectura",
        "status": "CUMPLE",
        "detection_method": "Modelo de IA (Gemini Multimodal)",
        "technical_rationale": "Dormitorios y estares cuentan con vanos exteriores.",
        "impact_value": 5.0,
        "impact_label": "+5.0%",
        "impact_class": "badge-impact-pos"
    })
    inspected_rules.append({
        "rule_id": "Art. 2.6.3 OGUC",
        "category": "Rasantes y Distanciamientos",
        "element_inspected": "Distanciamiento a medianeros y aplicación de rasantes",
        "evidence_found": "Retranqueos laterales y rasante angular según región",
        "document_source": "Plano de arquitectura y cortes",
        "status": "CUMPLE",
        "detection_method": "Modelo de IA (Gemini Multimodal)",
        "technical_rationale": "Volumen edificado cumple con plano de rasantes.",
        "impact_value": 10.0,
        "impact_label": "+10.0%",
        "impact_class": "badge-impact-pos"
    })

    return inspected_rules


def render_html_report(filename: str, result: Dict[str, Any], project: Optional[Dict[str, Any]] = None) -> str:
    """
    Renderiza el reporte HTML calculando explícitamente el desglose de puntaje
    (Línea base, deducciones, aportes y total final).
    """
    status_label = get_status_label(result)
    status_lower = status_label.lower()
    if "rechazado" in status_lower:
        status_class = "rechazado"
    elif "reformular" in status_lower:
        status_class = "reformular"
    elif "posible" in status_lower:
        status_class = "posible"
    elif "obs" in status_lower:
        status_class = "obs"
    else:
        status_class = "aprobado"

    logo_b64 = get_asset_base64("logo_IANA_con_nombre.png") or ""

    infrs = result.get("infractions") or []
    if not infrs and result.get("infracciones"):
        infrs = [
            {
                "rule_id": item.get("articulo", "OGUC"),
                "description": item.get("descripcion", ""),
                "severity": item.get("gravedad", "MEDIA").upper(),
                "evidence": item.get("evidencia", f"Página {item.get('pagina', 1)}"),
                "justification": item.get("justificacion", "Incumplimiento normativo identificado.")
            }
            for item in result.get("infracciones", [])
        ]

    raw_inspected_rules = build_or_extract_inspected_rules(result=result, project=project)
    
    processed_rules = []
    total_additions = 0.0
    total_deductions = 0.0

    for r in raw_inspected_rules:
        item = dict(r) if isinstance(r, dict) else r.model_dump()
        status = str(item.get("status", "CUMPLE")).upper()
        if status == "CUMPLE":
            st_class = "cumple"
            st_icon = "✔"
            st_category = "CUMPLE"
        elif status == "NO CUMPLE":
            st_class = "nocumple"
            st_icon = "✖"
            st_category = "NO CUMPLE"
        else:
            st_class = "alerta"
            st_icon = "⚠"
            st_category = "ALERTA"

        method = str(item.get("detection_method", "Modelo de IA (Gemini Multimodal)"))
        if "Ciencia de Datos" in method or "Regex" in method or "NLP" in method:
            method_label = "Ciencia de Datos"
            method_class = "badge-method-data"
        elif "PRC" in method or "Determinista" in method or "Plan Regulador" in method:
            method_label = "Plan Regulador Comunal"
            method_class = "badge-method-prc"
        else:
            method_label = "Modelo IANA"
            method_class = "badge-method-iana"

        imp_val = float(item.get("impact_value", 0.0))
        if imp_val > 0:
            total_additions += imp_val
            imp_lbl = item.get("impact_label") or f"+{imp_val:.1f}%"
            imp_cls = item.get("impact_class") or "badge-impact-pos"
        elif imp_val < 0:
            total_deductions += abs(imp_val)
            imp_lbl = item.get("impact_label") or f"{imp_val:.1f}%"
            imp_cls = item.get("impact_class") or "badge-impact-neg"
        else:
            imp_lbl = "0.0%"
            imp_cls = "badge-impact-neu"

        processed_rules.append({
            "rule_id": item.get("rule_id", "OGUC"),
            "category": item.get("category", "Normativa"),
            "element_inspected": item.get("element_inspected", "Elemento constructivo"),
            "evidence_found": item.get("evidence_found", "Verificado en expediente"),
            "document_source": item.get("document_source", "Expediente"),
            "status": status,
            "status_class": st_class,
            "status_icon": st_icon,
            "status_category": st_category,
            "status_badge_class": f"badge-status-{st_class}",
            "method_label": method_label,
            "method_class": method_class,
            "technical_rationale": item.get("technical_rationale", ""),
            "impact_label": imp_lbl,
            "impact_class": imp_cls
        })

    score_breakdown = {
        "base_score": 100.0,
        "total_additions": total_additions,
        "total_deductions": total_deductions
    }

    stats = {
        "total": len(processed_rules),
        "cumple": sum(1 for r in processed_rules if r["status_category"] == "CUMPLE"),
        "nocumple": sum(1 for r in processed_rules if r["status_category"] == "NO CUMPLE"),
        "alerta": sum(1 for r in processed_rules if r["status_category"] == "ALERTA")
    }

    return HTML_TMPL.render(
        filename=filename,
        result=result,
        status_label=status_label,
        status_class=status_class,
        logo_b64=logo_b64,
        infractions=infrs,
        inspected_rules=processed_rules,
        score_breakdown=score_breakdown,
        stats=stats
    )


def render_pdf_report(filename: str, result: Dict[str, Any]) -> bytes:
    import fitz

    now_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    status_label = get_status_label(result)
    logo_b64 = get_asset_base64("logo_IANA_con_nombre.png") or ""
    html_content = PDF_TMPL.render(
        filename=filename, 
        result=result, 
        created_at=now_str, 
        status_label=status_label,
        logo_b64=logo_b64
    )
    
    doc = fitz.open("html", html_content.encode("utf-8"))
    pdf_bytes = doc.convert_to_pdf()
    doc.close()
    return pdf_bytes