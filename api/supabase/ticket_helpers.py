from __future__ import annotations

from datetime import datetime, timezone

from api.supabase.supabase_client import get_supabase


class TicketStorageError(RuntimeError):
    """Raised when Supabase ticket operations fail."""


def _expect_single(response, *, context: str) -> dict:
    data = getattr(response, "data", None)
    if not data:
        raise TicketStorageError(f"No data returned for {context}.")
    return data[0]


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def find_ticket_by_message_id(message_id: str) -> dict | None:
    sb = get_supabase()
    response = (
        sb.table("tickets")
        .select("*")
        .contains("message_ids", [message_id])
        .limit(1)
        .execute()
    )
    data = response.data or []
    return data[0] if data else None


def create_ticket(tenant_email: str, subject: str) -> dict:
    sb = get_supabase()
    payload = {
        "tenant_email": tenant_email,
        "subject": subject,
        "status": "open",
        "issue_category": "unknown",
        "severity": "unknown",
        "message_ids": [],
        "created_at": _utc_now_iso(),
        "updated_at": _utc_now_iso(),
    }
    response = sb.table("tickets").insert(payload).execute()
    return _expect_single(response, context="create_ticket")


def append_ticket_message_id(ticket_id: str, message_id: str) -> list[str]:
    sb = get_supabase()
    existing_response = (
        sb.table("tickets").select("message_ids").eq("id", ticket_id).limit(1).execute()
    )
    existing = _expect_single(existing_response, context="ticket_message_ids")
    message_ids = list(existing.get("message_ids") or [])
    if message_id not in message_ids:
        message_ids.append(message_id)

    update_payload = {"message_ids": message_ids, "updated_at": _utc_now_iso()}
    sb.table("tickets").update(update_payload).eq("id", ticket_id).execute()
    return message_ids


def update_ticket_classification(
    ticket_id: str,
    *,
    issue_category: str,
    severity: str,
    message_id: str | None = None,
) -> None:
    payload = {
        "issue_category": issue_category,
        "severity": severity,
        "updated_at": _utc_now_iso(),
    }
    if message_id is not None:
        payload["last_ai_message_id"] = message_id
    sb = get_supabase()
    sb.table("tickets").update(payload).eq("id", ticket_id).execute()


def create_ticket_message(
    ticket_id: str,
    message_id: str,
    *,
    sender: str,
    content: str,
    images: list[str] | None = None,
) -> dict:
    sb = get_supabase()
    payload = {
        "ticket_id": ticket_id,
        "message_id": message_id,
        "sender": sender,
        "content": content,
        "images": images or [],
        "created_at": _utc_now_iso(),
    }
    response = sb.table("ticket_messages").insert(payload).execute()
    return _expect_single(response, context="create_ticket_message")
