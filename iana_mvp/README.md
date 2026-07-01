# IANA v0.1 MVP (Vector PDF normative pre-check)

## Run
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

## Test
POST `http://127.0.0.1:8000/api/upload` (form-data `file=PDF`)

Then open:
- `GET /api/result/{job_id}`
- `GET /api/report/{job_id}`
- `GET /api/jobs` (Lista los trabajos recientes paginados, útil en caso de timeouts del cliente)

## Streamlit Web UI

Para iniciar la interfaz gráfica interactiva con Streamlit localmente:
```bash
streamlit run streamlit_app.py
```

### Despliegue en Streamlit Community Cloud:
1. Sube este repositorio a tu cuenta de GitHub.
2. Ve a [Streamlit Community Cloud](https://share.streamlit.io/) y crea una nueva app apuntando a tu repositorio.
3. Configura el **Main file path** como `iana_mvp/streamlit_app.py`.
4. Ve a **Settings** -> **Secrets** en Streamlit Cloud y añade tu API Key:
   ```toml
   GEMINI_API_KEY = "tu-clave-api-aqui"
   ```
5. ¡Listo! La app se instalará automáticamente con las librerías del `requirements.txt` y estará pública en la web.