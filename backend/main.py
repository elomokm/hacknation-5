from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

from extractor import extract_skills, Skill

app = FastAPI(title="Traji API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExtractRequest(BaseModel):
    text: str
    image_base64: Optional[str] = None


class ExtractResponse(BaseModel):
    skills: list[Skill]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/extract", response_model=ExtractResponse)
async def extract(req: ExtractRequest):
    skills = extract_skills(req.text, req.image_base64)
    return ExtractResponse(skills=skills)


# kept for scaffold compatibility
@app.post("/predict")
async def predict(req: ExtractRequest):
    return await extract(req)
