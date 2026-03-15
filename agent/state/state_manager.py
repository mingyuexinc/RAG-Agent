import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

from agent.orchestrator.executor import ExecutionContext
from infra.logs.logger_config import setup_logger

# 添加状态管理日志
logger = setup_logger("agent.state_manager")


@dataclass
class AgentState:
    # ===== 用户相关 =====
    session_id: str
    turn_id: int

    # ===== 记忆层 =====
    conversation_history:list   # 用户 & Agent 历史对话
    memory: dict[str, Any]                 # 长期 / 短期记忆
    working_context: ExecutionContext        # 本轮执行产生的中间上下文
    last_tool_results: dict[str, Any] | None = None

    def add_conversation_turn(self, query: str, response: str):
        logger.info(f"添加对话轮次 - session_id: {self.session_id}, turn_id: {self.turn_id}")
        logger.info(f"Query: {query[:100]}...")
        logger.info(f"Response: {response[:100]}...")
        
        self.conversation_history.append({
            "query": query,
            "response": response,
            "timestamp": datetime.now().isoformat()
        })

        if len(self.conversation_history) > 10:
            old_count = len(self.conversation_history)
            self.conversation_history = self.conversation_history[-10:]
            logger.info(f"对话历史截断：{old_count} -> {len(self.conversation_history)}")
        
        logger.info(f"当前对话历史轮数: {len(self.conversation_history)}")

    def _serialize(self, data: Any, pretty: bool = True) -> str:
        """统一的安全序列化方法"""
        try:
            if pretty:
                return json.dumps(data, ensure_ascii=False, indent=2)
            return json.dumps(data, ensure_ascii=False)
        except Exception:
            return str(data)

    def to_prompt_view(
            self,
            view_type: str,
            max_history_turns: int = 6,
            max_tool_chars: int = 2000
    ) -> Dict[str, str]:
        """
        根据不同模块生成不同的Prompt视图
        """

        if view_type == "planner":

            trimmed_history = self.conversation_history[-max_history_turns:]

            tool_results_str = self._serialize(self.last_tool_results)

            if len(tool_results_str) > max_tool_chars:
                tool_results_str = tool_results_str[:max_tool_chars] + "...(truncated)"

            return {
                "conversation_history": self._serialize(trimmed_history),
                "working_context": self._serialize(self.working_context.data),
                "last_tool_results": tool_results_str,
            }

        elif view_type == "context_analysis":

            return {
                "conversation_history": self._serialize(self.conversation_history[-5:]),
                "working_context": self._serialize(self.working_context.data),
            }

        elif view_type == "full":

            return {
                "conversation_history": self._serialize(self.conversation_history),
                "working_context": self._serialize(self.working_context.data),
                "last_tool_results": self._serialize(self.last_tool_results),
            }

        else:
            raise ValueError(f"Unknown prompt view type: {view_type}")

    # def to_prompt_dict(
    #     self,
    #     max_history_turns: int = 6,
    #     max_tool_chars: int = 2000
    # ) -> Dict[str, Any]:
    #     """
    #     只返回对 LLM 可见的状态字段。
    #     """
    #
    #     # 1️⃣ 截断对话历史，避免无限增长
    #     trimmed_history = self.conversation_history[-max_history_turns:]
    #
    #     # 2️⃣ 控制工具结果长度
    #     tool_results_str = str(self.last_tool_results)
    #     if len(tool_results_str) > max_tool_chars:
    #         tool_results_str = tool_results_str[:max_tool_chars] + "...(truncated)"
    #
    #     return {
    #         "conversation_history": trimmed_history,
    #         "working_context": self.working_context,
    #         "last_tool_results": tool_results_str,
    #     }


class AgentStateManager:
    def __init__(self):
        self.states: Dict[str, AgentState] = {}
        logger.info("AgentStateManager 初始化完成")

    def init(self, session_id: str) -> AgentState:
        """
        显式初始化一个新的 AgentState
        """
        logger.info(f"初始化AgentState，session_id: {session_id}")
        
        state = AgentState(
            session_id=session_id,
            turn_id=0,
            conversation_history=[],
            memory={},
            working_context=ExecutionContext(),
            last_tool_results={},
        )
        self.states[session_id] = state
        logger.info(f"AgentState初始化完成，当前状态数量: {len(self.states)}")
        return state

    def load(self, session_id: str) -> AgentState:
        state = self.states.get(session_id)
        if state:
            logger.info(f"加载AgentState成功，session_id: {session_id}, turn_id: {state.turn_id}")
        else:
            logger.warning(f"AgentState不存在，session_id: {session_id}")
        return state

    def save(self, state: AgentState):
        logger.info(f"保存AgentState，session_id: {state.session_id}, turn_id: {state.turn_id}")
        self.states[state.session_id] = state