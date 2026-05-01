#!/usr/bin/env python3
"""
测试工具注册中心功能
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

def test_registry():
    """测试注册中心功能"""
    print("=" * 60)
    print("测试工具注册中心 (ToolRegistry)")
    print("=" * 60)
    
    try:
        # 1. 测试注册中心导入和工具自动注册
        print("\n1. 测试导入和自动注册...")
        from tools.langchain import ToolRegistry
        from tools.langchain.knowledge import KnowledgeSearchTool
        from tools.langchain.summarizer import SummarizerTool
        from tools.langchain.chart_gen import ChartGenTool
        print("✅ 工具类和注册中心导入成功")
        
        # 2. 测试已注册的工具列表
        print("\n2. 测试已注册的工具列表...")
        all_tools = ToolRegistry.list_all_tools()
        print(f"   已注册工具: {all_tools}")
        assert "knowledge_search" in all_tools, "knowledge_search 未注册"
        assert "summarizer" in all_tools, "summarizer 未注册"
        assert "chart_gen" in all_tools, "chart_gen 未注册"
        print("✅ 所有工具已正确注册")
        
        # 3. 测试任务类型映射
        print("\n3. 测试任务-工具映射...")
        for task_type in ["knowledge_qa", "flowchart_generation", "summary", "context_analysis"]:
            tools_for_task = ToolRegistry.get_tools_for_task(task_type)
            print(f"   {task_type}: {tools_for_task}")
        
        # 验证特定任务的映射
        qa_tools = ToolRegistry.get_tools_for_task("knowledge_qa")
        assert "knowledge_search" in qa_tools, "knowledge_qa 应该包含 knowledge_search"
        print("✅ 任务-工具映射正确")
        
        # 4. 测试工具元数据
        print("\n4. 测试工具元数据...")
        knowledge_meta = ToolRegistry.get_tool("knowledge_search")
        print(f"   工具名称: {knowledge_meta.name}")
        print(f"   任务类型: {knowledge_meta.task_types}")
        print(f"   依赖项: {knowledge_meta.dependencies}")
        print(f"   描述: {knowledge_meta.description}")
        assert knowledge_meta.name == "knowledge_search"
        assert "vector_store" in knowledge_meta.dependencies
        print("✅ 工具元数据正确")
        
        # 5. 测试工具构建
        print("\n5. 测试工具构建...")
        # 注意：这里没有vector_db，所以knowledge_search构建会失败
        # 但summarizer和chart_gen应该可以成功
        summarizer_tool = ToolRegistry.build_tool("summarizer")
        chart_tool = ToolRegistry.build_tool("chart_gen")
        print(f"   summarizer工具类型: {type(summarizer_tool)}")
        print(f"   chart_gen工具类型: {type(chart_tool)}")
        print("✅ 无依赖工具构建成功")
        
        # 6. 测试调试信息
        print("\n6. 测试调试信息...")
        debug_info = ToolRegistry.debug_info()
        print(f"   注册工具数: {debug_info['tool_count']}")
        print(f"   任务类型数: {debug_info['task_type_count']}")
        print(f"   所有工具: {debug_info['registered_tools']}")
        print("✅ 调试信息完整")
        
        # 7. 测试向后兼容
        print("\n7. 测试向后兼容 (TOOL_BUILDERS)...")
        from tools.langchain import TOOL_BUILDERS
        print(f"   TOOL_BUILDERS keys: {list(TOOL_BUILDERS.keys())}")
        assert "knowledge_search" in TOOL_BUILDERS
        assert "summarizer" in TOOL_BUILDERS
        assert "chart_gen" in TOOL_BUILDERS
        print("✅ 向后兼容正常")
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！工具注册中心工作正常")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_registry()
    sys.exit(0 if success else 1)
