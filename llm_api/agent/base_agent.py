import os
import sys
import uuid
from dataclasses import dataclass, field
from typing import Sequence
from venv import logger

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import END, START, StateGraph, add_messages
from typing_extensions import Annotated
from langchain_anthropic import ChatAnthropic

env_var_key = "ANTHROPIC_API_KEY"
api_key: str | None = os.getenv(env_var_key)

if not api_key:
    logger.fatal(f"Fatal Error: The '{env_var_key}' environment variable is missing.")
    sys.exit(1)


@dataclass
class AgentState:
    messages: Annotated[Sequence[AnyMessage], add_messages] = field(
        default_factory=list
    )


class BaseAgent:
    system_prompt: str = ""

    def __init__(self):
        self.llm: BaseChatModel = ChatAnthropic(model_name="claude-haiku-4-5-20251001")

    def _get_messages_with_prompt(
        self, messages: Sequence[BaseMessage]
    ) -> list[BaseMessage]:
        return [SystemMessage(content=self.system_prompt)] + list(messages)

    def _call_model(self, state: AgentState):
        messages = self._get_messages_with_prompt(state.messages)
        response: BaseMessage = self.llm.invoke(messages)
        return {"messages": [response]}

    def _build_graph(self):
        graph_builder = StateGraph(state_schema=AgentState)
        graph_builder.add_node("call_model", self._call_model)
        graph_builder.add_edge(START, "call_model")
        graph_builder.add_edge("call_model", END)
        return graph_builder.compile()

    async def _build_graph_and_invoke(
        self, message: str, config: RunnableConfig
    ) -> str:
        input_messages = [HumanMessage(message)]
        graph = self._build_graph()
        state = graph.invoke(AgentState(messages=input_messages), config)
        return state["messages"][-1].content

    def run(self, input_message: str):
        config: RunnableConfig = {"configurable": {"thread_id": str(uuid.uuid4())}}
        return self._build_graph_and_invoke(input_message, config)
