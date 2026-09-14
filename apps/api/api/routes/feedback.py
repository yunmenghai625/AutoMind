from typing import Annotated

from fastapi import APIRouter, Depends, status

from apps.api.aigc.repository import UsageSubject
from apps.api.api.dependencies import get_feedback_service, get_usage_subject
from apps.api.core.errors import AppError
from apps.api.product.schemas import FeedbackRequest, FeedbackView
from apps.api.product.service import FeedbackService, ProductNotFoundError

router = APIRouter()


@router.post("", response_model=FeedbackView, status_code=status.HTTP_201_CREATED)
async def save_feedback(
    payload: FeedbackRequest,
    subject: Annotated[UsageSubject, Depends(get_usage_subject)],
    service: Annotated[FeedbackService, Depends(get_feedback_service)],
) -> FeedbackView:
    try:
        return await service.save(subject, payload)
    except ProductNotFoundError as exc:
        raise AppError(
            "FEEDBACK_TARGET_NOT_FOUND",
            "Feedback target was not found",
            status_code=404,
        ) from exc


@router.get("", response_model=list[FeedbackView])
async def list_feedback(
    subject: Annotated[UsageSubject, Depends(get_usage_subject)],
    service: Annotated[FeedbackService, Depends(get_feedback_service)],
) -> list[FeedbackView]:
    return await service.list(subject)
