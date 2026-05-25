"""
Graph 包
"""


def create_graph(*args, **kwargs):
    from agent.graph.builder import create_graph as _create_graph
    return _create_graph(*args, **kwargs)


__all__ = ["create_graph"]
