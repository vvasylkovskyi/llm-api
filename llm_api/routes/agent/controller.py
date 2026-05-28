import logging
from fastapi import APIRouter, status
from pydantic import BaseModel
from llm_api.http.response import handle_response

from llm_api.agent.agent import Agent

logger = logging.getLogger(__name__)


agent_router = APIRouter(prefix="/agent", tags=["Agent"])


class Message(BaseModel):
    role: str
    content: str


class AgentRunRequest(BaseModel):
    messages: list[Message]


@agent_router.post("/run", status_code=status.HTTP_200_OK)
async def run_agent(payload: AgentRunRequest):
    agent = Agent()

    last_message = payload.messages[-1].content
    answer = await agent.run(last_message)

    return handle_response(
        data={"status": "OK", "response": answer},
        status_code=status.HTTP_200_OK,
    )
