# IANA v0.1 MVP (Vector PDF normative pre-check)

## Run
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Test
POST `http://127.0.0.1:8000/api/upload` (form-data `file=PDF`)

Then open:
- `GET /api/result/{job_id}`
- `GET /api/report/{job_id}`
