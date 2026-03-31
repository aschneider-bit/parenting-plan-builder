import logging
from pathlib import Path

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import (
    init_db,
    create_lawyer,
    get_all_lawyers,
    get_lawyer,
    create_client,
    get_client,
    get_client_by_token,
    get_clients_for_lawyer,
    save_intake_response,
    get_intake_response,
    save_survey_response,
    get_survey_results,
)
from pdf_generator import generate_intake_pdf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app")

app = FastAPI(title="OFW Pro - Parenting Plan Builder")

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def _render(request: Request, name: str, context: dict | None = None):
    ctx = {"request": request}
    if context:
        ctx.update(context)
    return templates.TemplateResponse(name=name, request=request, context=ctx)


@app.on_event("startup")
async def startup():
    init_db()
    logger.info("Parenting Plan Builder started")


def _get_current_lawyer() -> dict | None:
    lawyers = get_all_lawyers()
    return lawyers[0] if lawyers else None


def _lawyer_initials(name: str) -> str:
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()


# --- Lawyer Setup ---

@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    lawyer = _get_current_lawyer()
    if lawyer:
        return RedirectResponse("/", status_code=302)
    return _render(request, "setup.html")


@app.post("/setup")
async def setup_submit(
    request: Request,
    firm_name: str = Form(...),
    lawyer_name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
):
    create_lawyer(firm_name, lawyer_name, email, phone)
    logger.info("Lawyer account created: %s", lawyer_name)
    return RedirectResponse("/", status_code=302)


# --- Dashboard ---

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    lawyer = _get_current_lawyer()
    if not lawyer:
        return RedirectResponse("/setup", status_code=302)

    clients = get_clients_for_lawyer(lawyer["id"])
    total = len(clients)
    pending = sum(1 for c in clients if c["status"] == "pending")
    completed = sum(1 for c in clients if c["status"] == "completed")

    return _render(request, "dashboard.html", {
        "lawyer": lawyer,
        "lawyer_initials": _lawyer_initials(lawyer["lawyer_name"]),
        "clients": clients,
        "total_clients": total,
        "pending_count": pending,
        "completed_count": completed,
        "active_tab": "plans",
    })


# --- Client Management ---

@app.post("/clients/new")
async def new_client(request: Request):
    lawyer = _get_current_lawyer()
    if not lawyer:
        raise HTTPException(status_code=401, detail="No lawyer account")

    client = create_client(lawyer["id"])
    logger.info("New client created: %s", client["id"])
    return RedirectResponse("/", status_code=302)


@app.get("/clients/{client_id}", response_class=HTMLResponse)
async def client_detail(request: Request, client_id: str):
    lawyer = _get_current_lawyer()
    if not lawyer:
        return RedirectResponse("/setup", status_code=302)

    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    intake = get_intake_response(client_id)
    if not intake:
        raise HTTPException(status_code=404, detail="No intake response yet")

    return _render(request, "client_detail.html", {
        "lawyer": lawyer,
        "lawyer_initials": _lawyer_initials(lawyer["lawyer_name"]),
        "client": client,
        "intake": intake,
        "active_tab": "plans",
    })


@app.get("/clients/{client_id}/pdf")
async def client_pdf(client_id: str):
    lawyer = _get_current_lawyer()
    if not lawyer:
        raise HTTPException(status_code=401)

    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404)

    intake = get_intake_response(client_id)
    if not intake:
        raise HTTPException(status_code=404, detail="No intake response")

    pdf_bytes = generate_intake_pdf(lawyer, intake)
    filename = f"intake_{intake.get('full_name', 'client').replace(' ', '_')}.pdf"

    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --- Client Intake (Public, Token-Based) ---

@app.get("/intake/{token}", response_class=HTMLResponse)
async def intake_form(request: Request, token: str):
    client = get_client_by_token(token)
    if not client:
        raise HTTPException(status_code=404, detail="Invalid intake link")

    lawyer = get_lawyer(client["lawyer_id"])
    if not lawyer:
        raise HTTPException(status_code=404)

    already_submitted = client["status"] == "completed"

    return _render(request, "intake_form.html", {
        "lawyer": lawyer,
        "token": token,
        "already_submitted": already_submitted,
        "show_survey": True,
    })


@app.post("/intake/{token}/submit")
async def intake_submit(request: Request, token: str):
    client = get_client_by_token(token)
    if not client:
        raise HTTPException(status_code=404, detail="Invalid intake link")

    if client["status"] == "completed":
        return RedirectResponse(f"/intake/{token}", status_code=302)

    form = await request.form()
    data = dict(form)

    save_intake_response(client["id"], data)
    logger.info("Intake submitted for client %s", client["id"])

    lawyer = get_lawyer(client["lawyer_id"])

    return _render(request, "intake_success.html", {
        "lawyer": lawyer,
        "name": data.get("full_name", ""),
        "show_survey": True,
    })


# --- Survey API ---

@app.post("/api/survey")
async def survey_submit(request: Request):
    body = await request.json()
    selection = body.get("selection", "")
    client_id = body.get("client_id")

    if not selection:
        raise HTTPException(status_code=400, detail="Selection required")

    result = save_survey_response(client_id, selection)
    logger.info("Survey response: %s", selection)
    return result


@app.get("/api/survey/results")
async def survey_results():
    return get_survey_results()


# --- Health Check ---

@app.get("/health")
async def health():
    return {"status": "ok"}
