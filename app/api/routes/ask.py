from fastapi import APIRouter

from app.schemas.ask import AskRequest, AskResponse
from app.services.workflow_service import run_question_workflow


router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest) -> AskResponse:
    return run_question_workflow(request.question, request.role)
