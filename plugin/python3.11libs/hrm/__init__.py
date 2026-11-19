"""Houdini 顶部资源监控条入口。"""
def install():
    from .ui import install as start
    return start()
