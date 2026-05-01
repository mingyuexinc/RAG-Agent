# LangChain Tools Integration

## Overview

RAG Agent has been migrated to use LangChain's official tool integration framework, providing better compatibility, type safety, and standardized tool definitions.

## Architecture

### Tool Structure

The new tool integration is located in `/tools/langchain/`:

```
tools/langchain/
|-- __init__.py              # Tool exports
|-- official_tools.py        # LangChain tool implementations
```

### Available Tools

#### 1. Knowledge Search Tool (`knowledge_search`)
- **Purpose**: Retrieve relevant documents from vector knowledge base
- **Input**: `query` (string) - User query question
- **Output**: List of documents with content, metadata, and relevance scores
- **Dependencies**: Vector store (FAISS or Pinecone)

#### 2. Summarizer Tool (`summarizer`)
- **Purpose**: Generate summaries from retrieved documents
- **Input**: `documents` (List[Dict]) - Retrieved document list
- **Output**: Summarized text content
- **Dependencies**: LLM model for summarization

#### 3. Chart Generation Tool (`chart_gen`)
- **Purpose**: Generate flowchart from summarized text
- **Input**: `summarized_text` (string) - Text to visualize
- **Output**: Mermaid chart code and image URL
- **Dependencies**: Mermaid.ink service for chart rendering

## Implementation Details

### Tool Builder Pattern

Each tool is implemented using the builder pattern:

```python
def build_knowledge_search_tool(vector_store) -> StructuredTool:
    def _search(query: str) -> Dict[str, Any]:
        # Tool implementation
        return ToolResult(success=True, data=result_data).to_dict()
    
    return StructuredTool.from_function(
        func=_search,
        name="knowledge_search",
        description="...",
        args_schema=KnowledgeSearchInput,
        metadata={...}
    )
```

### Input Validation

All tools use Pydantic models for input validation:

```python
class KnowledgeSearchInput(BaseModel):
    query: str = Field(..., min_length=1, description="User query question")
```

### Error Handling

Tools implement comprehensive error handling with standardized response format:

```python
try:
    # Tool logic
    return ToolResult(success=True, data=result_data).to_dict()
except Exception as exc:
    logger.error(f"Tool failed: {exc}", exc_info=True)
    return ToolResult(success=False, error=str(exc), data={}).to_dict()
```

## Integration Points

### Container Configuration

The `AppContainer` class in `/infra/container.py` manages tool initialization:

```python
from tools.langchain.official_tools import TOOL_BUILDERS

# Tool builders are registered and instantiated based on configuration
tools = {
    name: builder(vector_db) 
    for name, builder in TOOL_BUILDERS.items()
}
```

### Task-Tool Mapping

Task types and their required tools are defined in `/infra/config/executor_config.py`:

```python
TASK_TOOL_CONSTRAINTS = {
    "knowledge_qa": ["knowledge_search"],
    "flowchart_generation": ["knowledge_search", "summarizer", "chart_gen"],
    "summary": ["knowledge_search", "summarizer"],
    "context_analysis": []
}
```

## Migration from Old Tools

### Removed Directories
- `/tools/generation/` - Old flowchart generation tools
- `/tools/knowledge/` - Old knowledge search and summarizer tools

### Key Differences
1. **Type Safety**: New tools use Pydantic for input validation
2. **Standardization**: All tools follow LangChain's `StructuredTool` interface
3. **Metadata**: Rich metadata support for tool discovery and configuration
4. **Error Handling**: Consistent error handling across all tools

### Compatibility
- Old tool names are preserved for backward compatibility
- Task configurations remain the same
- Agent orchestration continues to work without changes

## Usage Examples

### Direct Tool Usage

```python
from tools.langchain.official_tools import build_knowledge_search_tool

# Initialize tool
tool = build_knowledge_search_tool(vector_store)

# Execute tool
result = tool.invoke({"query": "What is RAG?"})
```

### Container-based Usage

```python
from infra.container import AppContainer

# Get agent with tools
agent = AppContainer.get_doc_agent()

# Execute task (automatically uses appropriate tools)
result = agent.execute_with_session(plan, session_id)
```

## Development Guidelines

### Adding New Tools

1. Create input schema using Pydantic:
```python
class NewToolInput(BaseModel):
    parameter: str = Field(..., description="Parameter description")
```

2. Implement tool function:
```python
def build_new_tool() -> StructuredTool:
    def _execute(parameter: str) -> Dict[str, Any]:
        # Tool logic
        return ToolResult(success=True, data=result).to_dict()
    
    return StructuredTool.from_function(
        func=_execute,
        name="new_tool",
        description="Tool description",
        args_schema=NewToolInput,
        metadata={...}
    )
```

3. Register in `TOOL_BUILDERS`:
```python
TOOL_BUILDERS = {
    "knowledge_search": build_knowledge_search_tool,
    "summarizer": build_summarizer_tool,
    "chart_gen": build_chart_gen_tool,
    "new_tool": build_new_tool,  # Add new tool
}
```

### Best Practices

- Always use `ToolResult` for consistent response format
- Include comprehensive error handling with logging
- Use descriptive field descriptions in Pydantic models
- Add relevant metadata for tool discovery
- Keep tool functions focused and single-purpose

## Testing

Tools are tested in `/tests/test_doc_agent_langchain_tools.py`:

```python
class DocAgentLangChainToolTests(unittest.TestCase):
    def test_knowledge_search(self):
        # Test knowledge search tool
        pass
    
    def test_summarizer(self):
        # Test summarizer tool
        pass
    
    def test_chart_gen(self):
        # Test chart generation tool
        pass
```

## Future Enhancements

1. **Async Support**: Add async tool implementations
2. **Streaming**: Support for streaming responses in LLM tools
3. **Caching**: Tool result caching for performance
4. **Monitoring**: Tool usage metrics and performance monitoring
5. **Dynamic Loading**: Runtime tool registration and discovery
