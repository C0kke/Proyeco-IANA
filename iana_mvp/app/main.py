from __future__ import annotations

import json
import os
import uuid

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from .pdf_extract import extract_text_blocks
from .report import render_html_report
from .rules_engine import load_rules, run_rules

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOADS = os.path.join(DATA_DIR, "uploads")
RESULTS = os.path.join(DATA_DIR, "results")
RULES_PATH = os.path.join(BASE_DIR, "rules.yaml")

os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(RESULTS, exist_ok=True)

app = FastAPI(title="IANA v0.1 MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)) -> JSONResponse:
    job_id = str(uuid.uuid4())
    pdf_path = os.path.join(UPLOADS, f"{job_id}.pdf")
    with open(pdf_path, "wb") as handle:
        handle.write(await file.read())

    blocks = extract_text_blocks(pdf_path)
    rules = load_rules(RULES_PATH)
    findings = run_rules(blocks, rules)

    result = {
        "job_id": job_id,
        "filename": file.filename,
        "counts": {
            "blocks": len(blocks),
            "findings": len(findings),
            "pass": sum(1 for x in findings if x["status"] == "PASS"),
            "fail": sum(1 for x in findings if x["status"] == "FAIL"),
            "unverifiable": sum(1 for x in findings if x["status"] == "UNVERIFIABLE"),
        },
        "findings": findings,
    }
    out_json = os.path.join(RESULTS, f"{job_id}.json")
    with open(out_json, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)

    out_html = os.path.join(RESULTS, f"{job_id}.html")
    with open(out_html, "w", encoding="utf-8") as handle:
        handle.write(render_html_report(file.filename, findings))

    return JSONResponse({"job_id": job_id})


@app.get("/api/status/{job_id}")
def status(job_id: str) -> JSONResponse:
    ok = os.path.exists(os.path.join(RESULTS, f"{job_id}.json"))
    return JSONResponse({"job_id": job_id, "status": "DONE" if ok else "NOT_FOUND"})


@app.get("/api/result/{job_id}")
def result(job_id: str) -> JSONResponse:
    path = os.path.join(RESULTS, f"{job_id}.json")
    if not os.path.exists(path):
        return JSONResponse({"error": "not_found"}, status_code=404)
    with open(path, "r", encoding="utf-8") as handle:
        return JSONResponse(json.load(handle))


@app.get("/api/report/{job_id}", response_class=HTMLResponse)
def report(job_id: str) -> HTMLResponse:
    path = os.path.join(RESULTS, f"{job_id}.html")
    if not os.path.exists(path):
        return HTMLResponse("<h1>Not found</h1>", status_code=404)
    with open(path, "r", encoding="utf-8") as handle:
        return HTMLResponse(handle.read())

