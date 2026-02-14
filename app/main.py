# app/main.py
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

from .services.storage import save_helpdesk_request
from .services.bus import send_helpdesk_message
from .services.analytics import ask_analytics_agent

load_dotenv()

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/health")
async def health():
    """Liveness / readiness probe for Container Apps."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def show_form(request: Request):
    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "page_title": "Cloud Helpdesk – New Request"
        }
    )


@app.post("/submit", response_class=HTMLResponse)
async def submit_form(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    priority: str = Form(...),
    actionHint: str = Form(""),
    requesterEmail: str = Form("")
):
    # 1. store in Table Storage
    entity = save_helpdesk_request(
        {
            "title": title,
            "description": description,
            "category": category,
            "priority": priority,
            "actionHint": actionHint,
            "requesterEmail": requesterEmail,
        }
    )

    # 2. send minimal message to Service Bus
    try:
        send_helpdesk_message(entity)
        success_msg = "Request submitted and queued successfully!"
    except Exception as ex:
        # we don't want the UI to crash if SB is temporarily unavailable
        success_msg = f"Request stored, but failed to queue message: {ex}"

    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "page_title": "Cloud Helpdesk – Submitted",
            "success_msg": success_msg,
            "form_data": {
                "title": title,
                "description": description,
                "category": category,
                "priority": priority,
                "actionHint": actionHint,
                "requesterEmail": requesterEmail,
            }
        }
    )


class ChatRequest(BaseModel):
    question: str


@app.get("/chat", response_class=HTMLResponse)
async def show_chat(request: Request):
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "page_title": "Cloud Helpdesk – Analytics Chat"
        }
    )


@app.post("/chat")
async def chat_message(chat_request: ChatRequest):
    """
    Handle chat messages from the analytics assistant.
    Uses the analytics agent to query helpdesk data and provide insights.
    """
    try:
        # Call the analytics agent with the user's question
        answer = await ask_analytics_agent(chat_request.question)
        return JSONResponse(content={"answer": answer})
    except Exception as ex:
        print(f"Chat endpoint error: {ex}")
        return JSONResponse(
            content={"answer": f"Sorry, I encountered an error: {str(ex)}"},
            status_code=500
        )
