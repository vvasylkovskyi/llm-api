from fastapi import APIRouter, HTTPException, status

from llm_api.databases.relational_database.database_manager import DatabaseEngineManager
from llm_api.databases.vector_database.database_manager import VectorDatabaseEngineManager
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


@health_check_router.get("/vector-db")
async def health_check_vector_db():
    try:
        if await VectorDatabaseEngineManager.ping():
            return {"status": "ok", "vector_db": "reachable", "pgvector": "enabled"}
        raise HTTPException(status_code=500, detail="pgvector extension not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector DB error: {str(e)}") from e
