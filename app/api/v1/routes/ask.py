import asyncio
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.auth import AuthenticatedUser, get_current_user
from app.schemas.ask import AskRequest, AskResponse
from app.services.workflow_service import (
    run_question_workflow,
    run_question_workflow_async,
)


router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AskResponse)
def ask_question(
    payload: AskRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AskResponse:
    return run_question_workflow(payload.question, current_user.role)


@router.post("/ask/stream")
async def ask_question_stream(
    payload: AskRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> StreamingResponse:
    async def event_stream():
        yield "event: status\ndata: " + json.dumps({"message": "investigation_started"}) + "\n\n"
        response = await run_question_workflow_async(payload.question, current_user.role)
        yield "event: status\ndata: " + json.dumps(
            {
                "message": "answer_ready",
                "request_id": response.request_id,
                "cache_status": response.cache_status,
            }
        ) + "\n\n"

        for chunk in response.answer.split():
            yield "event: answer_chunk\ndata: " + json.dumps({"token": chunk + " "}) + "\n\n"
            await asyncio.sleep(0)

        yield "event: complete\ndata: " + json.dumps(response.model_dump()) + "\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
