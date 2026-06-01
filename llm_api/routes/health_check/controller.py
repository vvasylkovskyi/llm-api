from fastapi import APIRouter, HTTPException, status

from llm_api.database.database import DatabaseEngineManager
from llm_api.http.response import handle_response

health_check_router = APIRouter(prefix="/health-check")


@health_check_router.get("/")
async def health_check():
    return handle_response(data={"status": "OK"}, status_code=status.HTTP_200_OK)


@health_check_router.get("/db")
async def health_check_db():
    try:
        if await DatabaseEngineManager.ping():
            return {"status": "ok", "db": "reachable"}
        raise HTTPException(status_code=500, detail="DB ping failed")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}") from e
