from fastapi import APIRouter, Depends

from app.core.auth import AuthenticatedUser, get_current_user
from app.schemas.ask import AskRequest, AskResponse
from app.services.workflow_service import run_question_workflow


router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AskResponse)
def ask_question(
    payload: AskRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AskResponse:
    return run_question_workflow(payload.question, current_user.role)
