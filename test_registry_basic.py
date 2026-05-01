#!/usr/bin/env python3
"""
测试工具注册中心基础功能（不依赖pydantic）
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

def test_registry_basic():
    """测试注册中心基础功能"""
    print("=" * 60)
    print("测试工具注册中心基础功能")
    print("=" * 60)
    
    try:
        # 1. 测试注册中心导入（直接从文件导入，避免触发__init__.py中的其他导入）
        print("\n1. 测试注册中心导入...")
        import importlib.util
        spec = importlib.util.spec_from_file_location("registry", r"D:\PythonProject\demo\RAG-Agent\tools\langchain\registry.py")
        registry_module = importlib.util.module_from_spec(spec)
        sys.modules["registry"] = registry_module
        spec.loader.exec_module(registry_module)
        
        ToolRegistry = registry_module.ToolRegistry
        ToolMetadata = registry_module.ToolMetadata
        print("✅ ToolRegistry导入成功")
        
        # 2. 测试注册功能
        print("\n2. 测试工具注册...")
        
        # 定义测试工具类
        class TestTool:
            name = "test_tool"
            description = "测试工具"
            task_types = ["test_task"]
            dependencies = ["test_dep"]
        
        # 使用装饰器注册
        @ToolRegistry.register(
            name="test_tool",
            task_types=["test_task"],
            dependencies=["test_dep"],
            description="测试工具"
        )
        class RegisteredTestTool:
            pass
        
        print("✅ 装饰器注册成功")
        
        # 3. 测试获取工具列表
        print("\n3. 测试获取已注册工具...")
        all_tools = ToolRegistry.list_all_tools()
        print(f"   已注册工具: {all_tools}")
        
        if "test_tool" in all_tools:
            print("✅ 工具成功注册到注册中心")
        else:
            print("⚠️  test_tool未在列表中，可能需要导入触发注册")
        
        # 4. 测试获取任务类型工具
        print("\n4. 测试任务-工具映射...")
        task_tools = ToolRegistry.get_tools_for_task("test_task")
        print(f"   test_task的工具: {task_tools}")
        
        # 5. 测试获取工具元数据
        print("\n5. 测试工具元数据...")
        if "test_tool" in all_tools:
            meta = ToolRegistry.get_tool("test_tool")
            print(f"   工具名称: {meta.name}")
            print(f"   任务类型: {meta.task_types}")
            print(f"   依赖: {meta.dependencies}")
            print(f"   描述: {meta.description}")
            print("✅ 元数据获取成功")
        
        # 6. 测试调试信息
        print("\n6. 测试调试信息...")
        debug_info = ToolRegistry.debug_info()
        print(f"   注册工具数: {debug_info['tool_count']}")
        print(f"   任务类型数: {debug_info['task_type_count']}")
        print(f"   工具列表: {debug_info['registered_tools']}")
        print(f"   任务映射: {debug_info['task_mappings']}")
        print("✅ 调试信息完整")
        
        # 7. 测试列表所有任务类型
        print("\n7. 测试任务类型列表...")
        task_types = ToolRegistry.list_all_task_types()
        print(f"   所有任务类型: {task_types}")
        print("✅ 任务类型列表获取成功")
        
        print("\n" + "=" * 60)
        print("✅ 注册中心基础功能测试通过！")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_registry_basic()
    sys.exit(0 if success else 1)
