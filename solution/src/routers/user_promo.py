from fastapi import APIRouter, Depends, Query, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from starlette.responses import JSONResponse
from src.backend.db import get_db
from src.services.user_promo import PromoService
from src.schemas.user_promo import PromoForUser, Comment, CommentText, Author
from src.utils.get_company_or_user import get_current_user

router = APIRouter(prefix="/api/user")

@router.get("/feed", response_model=List[PromoForUser])
async def get_promos_feed(
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    service = PromoService(db)
    try:
        promos, total = await service.get_feed(current_user, limit, offset, category, active)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return JSONResponse(content=promos, headers={"X-Total-Count": str(total)})

@router.get("/promo/{id}", response_model=PromoForUser)
async def get_promo_by_id(
    id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = PromoService(db)
    try:
        promo = await service.get_promo(id, current_user)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    promo = {k: (str(v) if isinstance(v, UUID) else v) for k, v in promo.items()}
    return JSONResponse(content=promo)

@router.post("/promo/{id}/like", status_code=200)
async def like_promo(
    id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = PromoService(db)
    try:
        await service.like_promo(id, current_user)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    return JSONResponse(content={"status": "ok"})

@router.delete("/promo/{id}/like", status_code=200)
async def unlike_promo(
    id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = PromoService(db)
    try:
        await service.unlike_promo(id, current_user)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    return JSONResponse(content={"status": "ok"})

@router.post("/promo/{id}/comments", status_code=status.HTTP_201_CREATED)
async def create_comment(
    comment: CommentText,
    id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = PromoService(db)
    try:
        response = await service.create_comment(id, current_user, comment.text)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    return response

@router.get("/promo/{id}/comments")
async def get_comments(
    id: UUID = Path(...),
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = PromoService(db)
    try:
        comments, total = await service.get_comments(id, offset, limit)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    return JSONResponse(content=comments, headers={"X-Total-Count": str(total)})

@router.get("/promo/{id}/comments/{comment_id}")
async def get_comment_by_id(
    id: UUID = Path(...),
    comment_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = PromoService(db)
    try:
        comment = await service.get_comment(id, comment_id, current_user)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    return comment

@router.put("/promo/{id}/comments/{comment_id}")
async def edit_comment(
    comment_text: CommentText,
    id: UUID = Path(...),
    comment_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = PromoService(db)
    try:
        updated = await service.edit_comment(id, comment_id, current_user, comment_text.text)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return updated

@router.delete("/promo/{id}/comments/{comment_id}")
async def delete_comment(
    id: UUID = Path(...),
    comment_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = PromoService(db)
    try:
        await service.delete_comment(id, comment_id, current_user)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "ok"}
