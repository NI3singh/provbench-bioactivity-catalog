"""/api/extract — LLM assay-metadata extraction, gated by anti-fabrication guards."""
from __future__ import annotations

import json
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import llm_guards

router = APIRouter(prefix="/api", tags=["extract"])

PROMPT = """You extract structured assay metadata from drug-discovery text.

From the PASSAGE, extract any of these fields that are EXPLICITLY stated:
- target (protein/gene)
- assay_type (e.g. enzymatic, cell-based, binding)
- standard_type (IC50, Ki, Kd, EC50, etc.)
- value (the numeric potency)
- unit (e.g. nM, uM)
- organism

Rules:
- For EVERY field, copy the EXACT verbatim substring from the PASSAGE that supports it
  into "source_span". The source_span MUST appear character-for-character in the PASSAGE.
- If a field is not explicitly stated, DO NOT include it. Never infer or guess.
- Return ONLY JSON: {"fields":[{"field_name","value","unit","source_span"}]}.

PASSAGE:
"""


class ExtractIn(BaseModel):
    text: str


@router.post("/extract")
def extract(inp: ExtractIn):
    text = (inp.text or "").strip()
    if not text:
        raise HTTPException(400, "text is required")
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise HTTPException(503, "GEMINI_API_KEY not configured on the server")

    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=PROMPT + text,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0),
        )
        raw = resp.text or "{}"
    except Exception as e:
        raise HTTPException(502, f"LLM call failed: {str(e)[:200]}")

    try:
        data = json.loads(raw)
        fields = data.get("fields", []) if isinstance(data, dict) else []
    except json.JSONDecodeError:
        fields = []

    result = llm_guards.validate_fields(text, fields)
    result["model"] = "gemini-2.5-flash"
    return result
