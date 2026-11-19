"""跨版本启动入口，兼容较早版本未执行 uiready 的情况。"""
_started = False

def start():
    global _started
    if _started:
        return
    try:
        from . import install
        install()
        _started = True
    except Exception as exc:
        import hou
        from PySide6 import QtWidgets
        QtWidgets.QMessageBox.warning(hou.qt.mainWindow(), '资源监控条加载失败', str(exc))
        return
