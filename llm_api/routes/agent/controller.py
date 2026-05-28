import logging
from fastapi import APIRouter, Header, status
from pydantic import BaseModel
from llm_api.http.response import handle_response

from llm_api.agent.base_agent import BaseAgent
from llm_api.agent.bark_agent import BarkAgent
from llm_api.agent.viktors_assistant_agent import ViktorsAssistantAgent

logger = logging.getLogger(__name__)

agent_router = APIRouter(prefix="/agent", tags=["Agent"])


class Message(BaseModel):
    role: str
    content: str


class AgentRunRequest(BaseModel):
    messages: list[Message]


def _resolve_agent(x_source: str | None) -> BaseAgent:
    if x_source == "viktor-portfolio":
        return ViktorsAssistantAgent()
    return BarkAgent()


@agent_router.post("/run", status_code=status.HTTP_200_OK)
async def run_agent(payload: AgentRunRequest, x_source: str | None = Header(default=None)):
    agent = _resolve_agent(x_source)

    last_message = payload.messages[-1].content
    answer = await agent.run(last_message)

    return handle_response(
        data={"status": "OK", "response": answer},
        status_code=status.HTTP_200_OK,
    )
