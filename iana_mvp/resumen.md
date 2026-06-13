# Resumen del Sistema IANA (MVP v0.1)

Este documento explica cómo funciona y cómo se utiliza el flujo de análisis de PDFs del sistema **IANA v0.1 MVP**.

---

## Flujo de Trabajo General

El sistema automatiza la verificación normativa preliminar de planos y documentos en formato PDF a través de cuatro etapas principales:

```mermaid
graph TD
    A[Cliente] -->|POST /api/upload| B(FastAPI Endpoint)
    B -->|Guardar PDF| C[(data/uploads)]
    B -->|Llamar extractor| D[pdf_extract.py]
    D -->|Extraer bloques de texto| E[rules_engine.py]
    E -->|Cargar reglas.yaml| F[Motor de Reglas]
    F -->|Evaluar reglas| G[Generar Resultados]
    G -->|Guardar JSON/HTML| H[(data/results)]
    A -->|GET /api/result/{job_id}| H
    A -->|GET /api/report/{job_id}| H
```

---

## Componentes del Flujo

### 1. Endpoint de Carga (`POST /api/upload`)
Definido en el archivo principal [app/main.py](file:///c:/Users/cokey/Documents/Programacion/Proyeco-IANA/iana_mvp/app/main.py):
* Recibe un archivo PDF a través de una petición `multipart/form-data` con la clave `file`.
* Genera un identificador único único (`job_id`) mediante `uuid.uuid4()`.
* Almacena el PDF temporalmente en la ruta `data/uploads/{job_id}.pdf`.

### 2. Extracción de Texto (`pdf_extract.py`)
Implementado en [app/pdf_extract.py](file:///c:/Users/cokey/Documents/Programacion/Proyeco-IANA/iana_mvp/app/pdf_extract.py):
* Abre el PDF usando la biblioteca PyMuPDF (`fitz`).
* Recorre cada página y extrae el texto por bloques mediante `page.get_text("blocks")`.
* Normaliza el texto de cada bloque (eliminando espacios redundantes y convirtiendo todo a minúsculas) para facilitar la búsqueda.
* Retorna una lista estructurada de objetos `TextBlock` que contienen la página, las coordenadas (`bbox`), el texto original y el texto normalizado.

### 3. Motor de Reglas (`rules_engine.py`)
Implementado en [app/rules_engine.py](file:///c:/Users/cokey/Documents/Programacion/Proyeco-IANA/iana_mvp/app/rules_engine.py):
* Carga el archivo de reglas [rules.yaml](file:///c:/Users/cokey/Documents/Programacion/Proyeco-IANA/iana_mvp/rules.yaml) que define los criterios normativos y severidades.
* Evalúa los bloques de texto extraídos según el tipo de regla:
  * **`keyword_any`**: Busca la presencia de cualquiera de las palabras clave especificadas.
  * **`regex`**: Aplica expresiones regulares generales sobre el texto.
  * **`door_width`**: Lógica especializada que valida la presencia de la palabra "puerta" acompañada de dimensiones estándar de ancho de puerta (ej. `0.90 m`, `90 cm`, `900 mm`) dentro de un mismo bloque.
* Asigna un estado (`PASS`, `FAIL` o `UNVERIFIABLE`) y un nivel de confianza a cada hallazgo.

### 4. Generación de Reportes y Resultados
Una vez finalizada la evaluación, el sistema realiza dos acciones de guardado:
1. **JSON de Resultados:** Guarda la información detallada (conteo de aciertos, fallos y lista de evidencias) en `data/results/{job_id}.json`.
2. **HTML de Reporte:** Utiliza una plantilla Jinja2 en [app/report.py](file:///c:/Users/cokey/Documents/Programacion/Proyeco-IANA/iana_mvp/app/report.py) para generar una página web de informe visual en `data/results/{job_id}.html`.

---

## Endpoints de Consulta

El cliente puede consultar la información del procesamiento de forma asíncrona mediante los siguientes endpoints:

1. **Estado (`GET /api/status/{job_id}`)**: Indica si el procesamiento ya terminó (`DONE` si existe el archivo JSON) o no (`NOT_FOUND`).
2. **Resultado (`GET /api/result/{job_id}`)**: Devuelve el archivo JSON con los datos puros recopilados de la evaluación.
3. **Reporte (`GET /api/report/{job_id}`)**: Devuelve el HTML renderizado para visualizar los resultados de forma amigable.
