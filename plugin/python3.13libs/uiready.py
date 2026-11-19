"""界面就绪后加载监控条，不依赖场景文件。"""
import sys
from pathlib import Path
import hou
_modules = str(next(Path(p) / 'python3.11libs' for p in hou.houdiniPath()
                    if (Path(p) / 'python3.11libs' / 'hrm').is_dir()))
if _modules not in sys.path:
    sys.path.insert(0, _modules)
from hrm.startup import start
start()
