from fastapi import FastAPI, Request
from uuid import uuid4
from firebase_admin import firestore
from app.firebase import db
from app.ai import run_ai_agent
from app.email import send_email

app = FastAPI()

@app.post("/email/inbound")
async def inbound_email(request: Request):
    form = await request.form()

    tenant_email = form.get("from")
    subject = form.get("subject") or "(No subject)"
    body = form.get("text") or ""

    ticket_id = str(uuid4())
    ticket_ref = db.collection("tickets").document(ticket_id)

    ticket_ref.set({
        "tenantEmail": tenant_email,
        "subject": subject,
        "status": "open",
        "issueCategory": "unknown",
        "severity": "unknown",
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP
    })

    ticket_ref.collection("messages").add({
        "sender": "tenant",
        "content": body,
        "createdAt": firestore.SERVER_TIMESTAMP
    })

    ai_result = run_ai_agent(subject, body)

    ticket_ref.update({
        "issueCategory": ai_result["issue_category"],
        "severity": ai_result["severity"],
        "updatedAt": firestore.SERVER_TIMESTAMP
    })

    send_email(
        to=tenant_email,
        subject=f"Re: {subject}",
        body=ai_result["reply"]
    )

    ticket_ref.collection("messages").add({
        "sender": "ai",
        "content": ai_result["reply"],
        "createdAt": firestore.SERVER_TIMESTAMP
    })

    return {"status": "ok"}
