from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.supabase.db_helpers import (
    create_conversation,
    create_message,
    create_property,
    create_tenant,
    create_unit,
    create_user,
    create_work_order,
    get_tenant,
    get_work_order,
    list_conversations,
    list_messages_for_conversation,
    list_messages_for_work_order,
    list_properties,
    list_units,
    list_users,
    list_work_orders,
)

router = APIRouter()


class TenantCreate(BaseModel):
    name: str


class UserCreate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None


class PropertyCreate(BaseModel):
    address: str | None = None


class UnitCreate(BaseModel):
    unit_label: str


class WorkOrderCreate(BaseModel):
    property_id: str
    unit_id: str | None = None
    reported_by_user_id: str | None = None
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    status: str | None = None


class ConversationCreate(BaseModel):
    party_type: str
    party_user_id: str | None = None


class MessageCreate(BaseModel):
    work_order_id: str
    direction: str
    channel: str
    sender_user_id: str | None = None
    recipient_user_id: str | None = None
    body: str | None = None
    raw_payload: dict | None = None


@router.post("/tenants")
async def create_tenant_endpoint(payload: TenantCreate):
    return create_tenant(payload.name)


@router.get("/tenants/{tenant_id}")
async def get_tenant_endpoint(tenant_id: str):
    tenant = get_tenant(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.post("/tenants/{tenant_id}/users")
async def create_user_endpoint(tenant_id: str, payload: UserCreate):
    return create_user(
        tenant_id,
        full_name=payload.full_name,
        phone=payload.phone,
        email=payload.email,
    )


@router.get("/tenants/{tenant_id}/users")
async def list_users_endpoint(tenant_id: str):
    return list_users(tenant_id)


@router.post("/tenants/{tenant_id}/properties")
async def create_property_endpoint(tenant_id: str, payload: PropertyCreate):
    return create_property(tenant_id, address=payload.address)


@router.get("/tenants/{tenant_id}/properties")
async def list_properties_endpoint(tenant_id: str):
    return list_properties(tenant_id)


@router.post("/properties/{property_id}/units")
async def create_unit_endpoint(property_id: str, payload: UnitCreate):
    return create_unit(property_id, payload.unit_label)


@router.get("/properties/{property_id}/units")
async def list_units_endpoint(property_id: str):
    return list_units(property_id)


@router.post("/tenants/{tenant_id}/work-orders")
async def create_work_order_endpoint(tenant_id: str, payload: WorkOrderCreate):
    return create_work_order(
        tenant_id,
        payload.property_id,
        unit_id=payload.unit_id,
        reported_by_user_id=payload.reported_by_user_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        status=payload.status or "new",
    )


@router.get("/tenants/{tenant_id}/work-orders")
async def list_work_orders_endpoint(tenant_id: str):
    return list_work_orders(tenant_id)


@router.get("/work-orders/{work_order_id}")
async def get_work_order_endpoint(work_order_id: str):
    work_order = get_work_order(work_order_id)
    if work_order is None:
        raise HTTPException(status_code=404, detail="Work order not found")
    return work_order


@router.post("/work-orders/{work_order_id}/conversations")
async def create_conversation_endpoint(work_order_id: str, payload: ConversationCreate):
    return create_conversation(
        work_order_id,
        party_type=payload.party_type,
        party_user_id=payload.party_user_id,
    )


@router.get("/work-orders/{work_order_id}/conversations")
async def list_conversations_endpoint(work_order_id: str):
    return list_conversations(work_order_id)


@router.post("/conversations/{conversation_id}/messages")
async def create_message_endpoint(conversation_id: str, payload: MessageCreate):
    return create_message(
        conversation_id,
        payload.work_order_id,
        direction=payload.direction,
        channel=payload.channel,
        sender_user_id=payload.sender_user_id,
        recipient_user_id=payload.recipient_user_id,
        body=payload.body,
        raw_payload=payload.raw_payload,
    )


@router.get("/conversations/{conversation_id}/messages")
async def list_messages_for_conversation_endpoint(conversation_id: str):
    return list_messages_for_conversation(conversation_id)


@router.get("/work-orders/{work_order_id}/messages")
async def list_messages_for_work_order_endpoint(work_order_id: str):
    return list_messages_for_work_order(work_order_id)
