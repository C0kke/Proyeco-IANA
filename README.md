# IANA — Inteligencia Artificial para la Normativa Arquitectónica en Chile

**IANA** es una plataforma tecnológica avanzada diseñada para la pre-revisión, verificación y auditoría normativa de proyectos de edificación, arquitectura y urbanismo en Chile. Automatiza el cotejo contra la **Ordenanza General de Urbanismo y Construcciones (OGUC / LGUC)** y las **Ordenanzas Locales de los Planes Reguladores Comunales (PRC)**.

---

## 🏛️ Arquitectura de Verificación Multicapa

IANA no depende exclusivamente de un modelo generativo; utiliza una arquitectura híbrida de tres motores complementarios que garantizan exactitud, transparencia y trazabilidad:

```
+-----------------------------------------------------------------------------------------+
|                                    EXPEDIENTE DEL PROYECTO                              |
|         (CIP, ETT, Planos de Emplazamiento, Arquitectura, Cortes, Elevaciones)          |
+-----------------------------------------------------------------------------------------+
                                             |
                   +-------------------------+-------------------------+
                   |                         |                         |
                   v                         v                         v
        +--------------------+    +--------------------+    +--------------------+
        |  CIENCIA DE DATOS  |    |     MODELO IANA    |    |  MOTOR PARAMÉTRICO |
        |   (Regex / NLP)    |    | (Gemini Multimodal)|    |        PRC         |
        +--------------------+    +--------------------+    +--------------------+
        | • Extracción de    |    | • Inspección visual|    | • Constructibilidad|
        |   bloques y texto  |    |   de láminas PDF   |    | • Ocupación suelo  |
        | • Cotas mínimas    |    | • Rasantes teóricas|    | • Alturas máximas  |
        | • Resistencia F-60 |    | • Iluminación rec. |    | • Fichas por zona  |
        +--------------------+    +--------------------+    +--------------------+
                   \                         |                         /
                    \                        |                        /
                     v                       v                       v
        +------------------------------------------------------------------------+
        |                  AUDITORÍA Y TRAZABILIDAD NORMATIVA                    |
        |  (Registro de cada elemento: CUMPLE / NO CUMPLE / ALERTA + Evidencia)  |
        +------------------------------------------------------------------------+
```

### 1. ⚙️ Ciencia de Datos (Regex / NLP / Bag of Words)
* **Función:** Búsqueda sintáctica y análisis determinista en las capas de texto extraídas de los documentos y especificaciones técnicas (ETT).
* **Casos típicos:** Detección de anchos de vanos en puertas principales ($\ge 0.90\text{ m}$ según Art. 4.1.7 OGUC), resistencia al fuego de elementos divisorios, palabras clave obligatorias en memorias de cálculo.

### 2. ✨ Modelo IANA (IA Multimodal)
* **Función:** Comprensión visual y semántica profunda mediante modelos multimodales.
* **Procesamiento de Planos:** Los planos de arquitectura, emplazamiento, cortes y elevaciones en formato PDF son renderizados en alta resolución a través de **PyMuPDF (`fitz`)**. La IA inspecciona directamente las líneas de dibujo, cotas gráficas, ángulos de rasantes, alturas de fachadas y distanciamientos laterales hacia ejes medianeros.

### 3. 📐 Motor Determinista PRC (Plan Regulador Comunal)
* **Función:** Validación paramétrica matemática directa contra los límites normativos del Plan Regulador Comunal de la comuna y zona territorial asignada (ej. Coquimbo, zona `ZU-4`).
* **Cálculos automáticos:** Coeficiente de constructibilidad ($\frac{\text{m}^2\text{ construidos}}{\text{m}^2\text{ terreno}}$), coeficiente de ocupación de suelo y altura máxima en metros.

---

## 📚 Bases Normativas e Inyección Contextual

### A. OGUC Nacional (`OGUC_2026.md`)
* **Indexación Léxico-Semántica:** La OGUC completa de Chile (+1.1 MB) está segmentada por artículos individuales.
* **Filtro de Relevancia:** Un algoritmo de overlap léxico extrae exclusivamente los artículos pertinentes al tipo de obra analizada, inyectándolos con precisión en el prompt para evitar saturación de tokens y alucinaciones.

### B. Planes Reguladores Comunales (`knowledge/prc/`)
* **Catálogo Estructurado por Región y Comuna:** Base de datos modular de ordenanzas comunales.
* **Fichas Técnicas Oficiales:** Para comunas registradas (iniciando con la **Actualización del Plan Regulador Comunal de Coquimbo**), el sistema cuenta con las **38 zonas oficiales** (`ZU3` a `ZU17`, `ZP1` a `ZP3`, `ZE1` a `ZE4`, `ZAV`, `ZPI`, etc.) con sus coeficientes, antejardines y usos de suelo permitidos/prohibidos.
* **Plano Territorial Comunal (`PLAN_REGULADOR_PLANO.pdf`):**
  * *Estado Actual:* Se extrajeron e indexaron los ejes viales estructurantes, nombres de calles y descripciones de límites.
  * *Hoja de Ruta (Fase 2 SIG):* Vectorización de capas CAD/GIS a polígonos GeoJSON / PostGIS para asignación satelital automática de la zona al marcar un punto en el mapa interactivo.

---

## 🔍 Trazabilidad y Auditoría en el Frontend

Dentro del panel del proyecto, la pestaña **"Auditoría y Trazabilidad Normativa"** provee certidumbre total:
* **Indicador de Estado:** `✔ CUMPLE` (Aprobado), `✖ NO CUMPLE` (Infracción), `⚠ ALERTA` (Observación / Pendiente).
* **Insignia del Motor:** Indica explícitamente si la regla fue auditada por *Ciencia de Datos*, *Modelo IANA* o *Plan Regulador Comunal*.
* **Evidencia Documental:** Cita la cota, lámina o página exacta donde se encontró la información en el expediente.
* **Fundamentación Técnica:** Explica el motivo legal y constructivo de la validación.
* **Filtros y Paginación:** Filtros por estado y método de detección, con carga progresiva (+10 ítems).

---

## 📋 Formularios de Ingreso DOM (MINVU)

Clasificación automática del trámite municipal correspondiente según las características de la obra:
* **Formulario 1:** Permiso de Edificación / Obras Menores ($\le 100\text{ m}^2$ o modificaciones interiores).
* **Formulario 2:** Permiso de Edificación / Obra Nueva y Ampliaciones mayores a $100\text{ m}^2$.
* **Formulario 3:** Obras de Urbanización / Loteos con afectación a utilidad pública.
* **Formulario 4:** Subdivisiones y Fusión Predial.
* **Formulario 5:** Otras Obras / Demoliciones totales o parciales.

Descarga directa en PDF de los formularios oficiales del Ministerio de Vivienda y Urbanismo (MINVU).

---

## 🚀 Instalación y Puesta en Marcha Local

### Prerrequisitos
* Python 3.11+
* Entorno virtual (`.venv`)

### 1. Clonar e Instalar Dependencias
```bash
git clone https://github.com/tu-usuario/Proyeco-IANA.git
cd Proyeco-IANA
python -m venv .venv
.\.venv\Scripts\activate
pip install -r iana_mvp/requirements.txt
```

### 2. Variables de Entorno (`iana_mvp/.env`)
Crear o verificar el archivo `.env` dentro de `iana_mvp/`:
```env
GEMINI_API_KEY="tu-api-key-de-gemini"
SUPABASE_URL="https://tu-proyecto.supabase.co"
SUPABASE_KEY="tu-clave-anon-supabase"
```

### 3. Ejecutar la Aplicación Streamlit
```bash
cd iana_mvp
streamlit run streamlit_app.py
```

### 4. Ejecutar la Suite de Pruebas
```bash
& "..\.venv\Scripts\pytest.exe"
```
*(Suite completa de 59 pruebas unitarias automatizadas con 100% de éxito).*
