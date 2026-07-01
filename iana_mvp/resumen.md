# Resumen del Sistema IANA (MVP v0.1)

Este documento explica cómo funciona y cómo se utiliza el flujo de análisis de PDFs del sistema **IANA v0.1 MVP - OGUC Validador**.

---

## Flujo de Trabajo General

El sistema automatiza la verificación de planos y documentos en formato PDF comparándolos con la **Ordenanza General de Urbanismo y Construcción (OGUC) de Chile** utilizando Inteligencia Artificial estructurada.

```mermaid
graph TD
    A[Cliente] -->|POST /api/upload| B(FastAPI Endpoint)
    B -->|Guardar PDF| C[(data/uploads)]
    B -->|Llamar extractor| D[pdf_extract.py]
    D -->|Extraer bloques de texto| E[FastAPI: upload_pdf]
    E -->|Combinar con OGUC_CONTENT| F[ai_verifier.py]
    F -->|Llamar Gemini API + Instructor| G[Generar ProjectEvaluation]
    G -->|Guardar JSON/HTML| H[(data/results)]
    A -->|GET /api/result/{job_id}| H
    A -->|GET /api/report/{job_id}| H
```

---

## Componentes del Flujo

### 1. Carga de la Legislación en Memoria (Startup)
Al iniciar la aplicación FastAPI en [app/main.py](file:///c:/Users/cokey/Documents/Programacion/Proyeco-IANA/iana_mvp/app/main.py):
* Se ejecuta el evento `@app.on_event("startup")` que lee el archivo de la legislación chilena [OGUC_2026.md](file:///c:/Users/cokey/Documents/Programacion/Proyeco-IANA/iana_mvp/knowledge/OGUC_2026.md) (~1.1MB).
* Se guarda su contenido en una variable global llamada `OGUC_CONTENT`. Esto evita la necesidad de configurar bases de datos vectoriales en esta primera etapa, cargando el marco normativo directamente en memoria.

### 2. Endpoint de Carga (`POST /api/upload`)
Definido en el archivo principal [app/main.py](file:///c:/Users/cokey/Documents/Programacion/Proyeco-IANA/iana_mvp/app/main.py):
* Recibe el plano/documento en PDF (puede ser vectorial o escaneado con texto seleccionable).
* Genera un identificador único de proceso (`job_id`) mediante `uuid.uuid4()`.
* Almacena el PDF en la ruta `data/uploads/{job_id}.pdf`.

### 3. Extracción de Texto (`pdf_extract.py`)
Implementado en [app/pdf_extract.py](file:///c:/Users/cokey/Documents/Programacion/Proyeco-IANA/iana_mvp/app/pdf_extract.py):
* Abre el archivo PDF usando PyMuPDF (`fitz`).
* Recorre cada página y extrae el texto por bloques de coordenadas (`blocks`).
* Retorna la lista estructurada de bloques, los cuales en [app/main.py](file:///c:/Users/cokey/Documents/Programacion/Proyeco-IANA/iana_mvp/app/main.py) se concatenan en un único string de texto (`plan_text`).

### 4. Capa de Verificación por IA (`ai_verifier.py`)
Implementado en [app/ai_verifier.py](file:///c:/Users/cokey/Documents/Programacion/Proyeco-IANA/iana_mvp/app/ai_verifier.py):
* **Librería Instructor:** Utiliza `instructor.from_genai` envolviendo al cliente oficial `google-genai` para interactuar con los modelos de Google AI Studio.
* **Modelo Utilizado:** `gemini-2.5-flash` debido a su gran ventana de contexto (1M de tokens), ideal para digerir los más de 250,000 tokens de la OGUC.
* **Esquema Pydantic (`ProjectEvaluation` y `Infraction`):** Define el formato estricto de salida. Para evitar errores con Gemini, no se utilizan tipos `Union` ni `Optional`, manteniendo tipos primitivos y listas estructuradas.
* **Procesamiento:** Une la variable global de la ley con el texto extraído del plano y solicita a Gemini que analice y retorne la probabilidad de éxito (0-100) y la lista de infracciones detectadas con su severidad, justificación legal y la cota/evidencia exacta del plano.

### 5. Generación de Reportes y Resultados
Tras la respuesta de la IA:
1. **JSON de Resultados:** Guarda la información estructurada devuelta en `data/results/{job_id}.json`.
2. **HTML de Reporte:** Utiliza [app/report.py](file:///c:/Users/cokey/Documents/Programacion/Proyeco-IANA/iana_mvp/app/report.py) para renderizar un informe visual premium de estilo oscuro, con indicadores visuales de cumplimiento y una tabla limpia para cada infracción normada.