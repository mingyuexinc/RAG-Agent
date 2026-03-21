import uuid
import time
from copy import deepcopy
from typing import Dict, Any, Optional

from agent.orchestrator.executor import ExecutionPlan, ExecutionResult, ExecutionContext
from agent.state.session_manager import SessionManager
from agent.state.state_manager import AgentStateManager
from infra.config.app_config import AppConfig
from infra.logs.logger_config import get_logger

from llm.model import ModelManager
from tools.base import BaseTool

# 添加agent模块日志
logger = get_logger("agent.orchestrator")


class DocAgent:
    def __init__(self,tools:Dict[str,BaseTool]):
        self.tools = tools
        self.max_steps = AppConfig.agent.MAX_STEPS
        self.max_retries = AppConfig.agent.MAX_RETRIES
        self.max_content_size = AppConfig.agent.MAX_CONTENT_SIZE
        self.max_execution_time = 60  # 60秒超时

        self.session_manager = SessionManager()
        self.state_manager = AgentStateManager()

    def ensure_session(self, session_id: Optional[str]) -> str:
        logger.info(f"确保会话存在，session_id: {session_id}")
        
        # first request
        if not session_id:
            session_id = str(uuid.uuid4())
            logger.info(f"创建新会话: {session_id}")
            self.session_manager.create_session(session_id)
            self.state_manager.init(session_id)
            logger.info(f"新会话初始化完成: {session_id}")
            return session_id

        session = self.session_manager.get_session(session_id)
        if session is None:  # expired
            logger.info(f"会话已过期，重新创建: {session_id}")
            self.session_manager.create_session(session_id)
            self.state_manager.init(session_id)
            logger.info(f"过期会话重新初始化完成: {session_id}")
        else:
            logger.info(f"使用现有会话: {session_id}")

        return session_id

    def execute_with_session(self, plan:ExecutionPlan,session_id:str)-> ExecutionResult:
        logger.info(f"开始执行计划，session_id: {session_id}")
        logger.info(f"执行计划: {plan.task_type}, 工具: {plan.tools}")

        start_time = time.time()
        
        state = self.state_manager.load(session_id)
        if state is None:
            logger.error(f"状态未初始化，session_id: {session_id}")
            raise RuntimeError(
                f"State not initialized for session_id={session_id}"
            )

        # 记录当前状态
        logger.info(f"当前会话状态 - turn_id: {state.turn_id}")
        logger.info(f"对话历史轮数: {len(state.conversation_history)}")
        logger.info(f"工作上下文大小: {len(state.working_context.data)}")
        logger.info(f"上次工具结果: {list(state.last_tool_results.keys()) if state.last_tool_results else 'None'}")
        
        # 详细记录对话历史
        if state.conversation_history:
            logger.info("=== 对话历史 ===")
            for i, turn in enumerate(state.conversation_history[-3:]):  # 只显示最近3轮
                logger.info(f"第{i+1}轮 - Query: {turn['query'][:100]}...")
                logger.info(f"第{i+1}轮 - Response: {turn['response'][:100]}...")
        else:
            logger.info("对话历史为空")
        
        # 详细记录工作上下文
        logger.info("=== 工作上下文 ===")
        for key, value in state.working_context.data.items():
            value_str = str(value)
            if len(value_str) > 200:
                value_str = value_str[:200] + "..."
            logger.info(f"上下文[{key}]: {value_str}")

        executed_tools = []
        tool_results = {}
        step_count = 0

        try:
            for tool_name in plan.tools:
                # 检查超时
                if time.time() - start_time > self.max_execution_time:
                    logger.error(f"执行超时: {time.time() - start_time:.1f}s > {self.max_execution_time}s")
                    raise ValueError(f"Execution timeout after {self.max_execution_time} seconds")
                
                if step_count >= self.max_steps:
                    logger.error(f"超过最大执行步数: {self.max_steps}")
                    raise ValueError(f"Exceeded maximum execution steps: {self.max_steps}")

                logger.info(f"执行工具: {tool_name} (步骤 {step_count + 1}/{self.max_steps})")

                state_snapshot = {
                    "executed_tools": executed_tools.copy(),
                    "tool_results": deepcopy(tool_results),
                    "context": deepcopy(state.working_context)
                }

                retry_count = 0
                success = False

                while retry_count < self.max_retries and not success:
                    try:
                        if tool_name not in self.tools:
                            logger.error(f"未知工具: {tool_name}")
                            raise ValueError(f"Unknown tool: {tool_name}")
                        tool = self.tools[tool_name]

                        raw_params = plan.tool_params.get(tool_name, {})
                        logger.info(f"工具参数: {raw_params}")
                        
                        resolved_params = self._resolve_params(raw_params, state.working_context)
                        logger.info(f"解析后参数: {resolved_params}")
                        
                        # 检查解析后的参数是否有效
                        if tool_name == "summarizer":
                            documents = resolved_params.get("documents")
                            if not documents or len(documents) == 0:
                                logger.error(f"summarizer工具缺少documents参数或参数为空: {resolved_params}")
                                raise ValueError("summarizer tool requires non-empty documents parameter")
                        
                        if tool_name == "knowledge_search":
                            set_tool = True
                        else:
                            set_tool = False
                        
                        logger.info(f"执行工具 {tool_name}...")
                        result = tool.run(resolved_params, state.working_context, set_tool)
                        
                        if not isinstance(result, dict):
                            logger.error(f"工具返回结果格式错误: {type(result)}")
                            result = {"success": False, "error": "Invalid result format"}
                        
                        success = result.get("success", False)
                        logger.info(f"工具 {tool_name} 执行结果: {success}")
                        logger.info(f"工具 {tool_name} 返回结果: {result}")

                        executed_tools.append(tool_name)
                        tool_results[tool_name] = result

                        state.last_tool_results = tool_results
                        
                        if success:
                            logger.info(f"工具 {tool_name} 执行成功")
                        else:
                            logger.error(f"工具 {tool_name} 执行失败: {result.get('error', 'Unknown error')}")
                            logger.error(f"工具 {tool_name} 将进行重试，当前重试次数: {retry_count}/{self.max_retries}")
                        
                    except Exception as e:
                        logger.error(f"工具 {tool_name} 执行失败 (重试 {retry_count + 1}/{self.max_retries}): {e}")
                        retry_count += 1
                        if retry_count >= self.max_retries:
                            logger.error(f"工具 {tool_name} 执行失败，超过最大重试次数")
                            raise ValueError(f"Failed to execute tool: {tool_name} after {self.max_retries} retries: {str(e)}")
                        else:
                            logger.info(f"恢复到执行前状态并重试工具 {tool_name}")
                            executed_tools = state_snapshot["executed_tools"].copy()
                            tool_results = state_snapshot["tool_results"].copy()
                            state.working_context = deepcopy(state_snapshot["context"])
                step_count += 1

            execution_time = time.time() - start_time
            logger.info(f"计划执行成功，执行工具: {executed_tools}, 耗时: {execution_time:.1f}s")
            return ExecutionResult(
                success=True,
                task_type=plan.task_type,
                executed_tools=executed_tools,
                tool_results=tool_results,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"计划执行失败: {e}, 耗时: {execution_time:.1f}s")
            return ExecutionResult(
                success=False,
                task_type=plan.task_type,
                executed_tools=executed_tools,
                tool_results=tool_results,
                error=str(e)
            )

    def _resolve_params(self,params:Dict[str,Any],context:ExecutionContext) -> Dict[str,Any]:
        resolved = {}
        for key,value in params.items():
            if isinstance(value, str) and "." in value:
                resolved_value = context.get_by_path(value)
                if resolved_value is None:
                    raise ValueError(f"Missing dependency: {value}")
                resolved[key] = resolved_value

            else:
                resolved[key] = value
        return resolved


    def generate_response(self, prompt:str) -> str:
        model_manager = ModelManager(timeout=30)
        response = model_manager.invoke_with_timeout(prompt)
        return response.content.strip()





