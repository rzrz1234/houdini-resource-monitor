"""延迟到 Houdini 主事件循环再安装界面。"""
import sys
from pathlib import Path
import hou
_modules = str(next(Path(p) / 'python3.11libs' for p in hou.houdiniPath()
                    if (Path(p) / 'python3.11libs' / 'hrm').is_dir()))
if _modules not in sys.path:
    sys.path.insert(0, _modules)
if hou.isUIAvailable():
    import hdefereval
    from hrm.startup import start
    hdefereval.executeDeferred(start)
