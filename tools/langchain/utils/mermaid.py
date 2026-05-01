"""
Mermaid流程图生成工具函数
"""
import base64


def generate_flowchart(content: str) -> str:
    """生成Mermaid流程图代码"""
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    nodes = [line[:60] + "..." if len(line) > 60 else line for line in lines[:15]]
    mermaid_code = "graph TD\n"

    for i, node in enumerate(nodes):
        node_id = chr(65 + i)
        clean_node = node.replace('"', "").replace("'", "")
        mermaid_code += f"    {node_id}[{clean_node}]\n"
        if i > 0:
            prev_node_id = chr(65 + i - 1)
            mermaid_code += f"    {prev_node_id} --> {node_id}\n"

    return mermaid_code


def generate_mermaid_image_url(mermaid_code: str) -> str:
    """生成Mermaid图片URL"""
    encoded = base64.urlsafe_b64encode(mermaid_code.encode("utf-8")).decode("utf-8").rstrip("=")
    return f"https://mermaid.ink/img/{encoded}"
