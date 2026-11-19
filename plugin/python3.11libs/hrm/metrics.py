"""通过 Windows 和 NVIDIA 驱动读取整机资源，无需第三方采样库。"""
import ctypes
from ctypes import wintypes
import csv
import shutil
import subprocess


class MemoryStatus(ctypes.Structure):
    _fields_ = [('length', wintypes.DWORD), ('load', wintypes.DWORD)] + [
        (name, ctypes.c_ulonglong) for name in (
            'total_phys', 'avail_phys', 'total_page', 'avail_page',
            'total_virtual', 'avail_virtual', 'avail_extended')]


class Sampler:
    def __init__(self):
        self.previous = None
        self.smi = shutil.which('nvidia-smi')

    def sample(self):
        result = {'cpu': None, 'memory': None, 'gpus': [], 'errors': []}
        try:
            times = [wintypes.FILETIME() for _ in range(3)]
            if not ctypes.windll.kernel32.GetSystemTimes(*(ctypes.byref(t) for t in times)):
                raise OSError('无法读取处理器时间')
            now = tuple((t.dwHighDateTime << 32) | t.dwLowDateTime for t in times)
            if self.previous:
                idle, kernel, user = (a-b for a, b in zip(now, self.previous))
                total = kernel + user
                if total > 0:
                    result['cpu'] = max(0., min(100., 100. * (total-idle) / total))
            self.previous = now
            mem = MemoryStatus()
            mem.length = ctypes.sizeof(mem)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
                raise OSError('无法读取物理内存')
            result['memory'] = {'used': mem.total_phys-mem.avail_phys, 'total': mem.total_phys}
        except Exception as exc:
            result['errors'].append('系统采样失败：' + str(exc))
        try:
            if not self.smi:
                raise OSError('未找到 NVIDIA 驱动查询程序')
            run = subprocess.run([self.smi,
                '--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu',
                '--format=csv,noheader,nounits'], capture_output=True, text=True,
                encoding='utf-8', errors='replace', timeout=2,
                creationflags=subprocess.CREATE_NO_WINDOW, check=True)
            for row in csv.reader(run.stdout.splitlines(), skipinitialspace=True):
                if len(row) != 6:
                    continue
                def number(value):
                    try:
                        return float(value.strip())
                    except ValueError:
                        return None
                result['gpus'].append(dict(zip(
                    ('index', 'name', 'load', 'used', 'total', 'temperature'),
                    [row[0], row[1]] + [number(x) for x in row[2:]])))
            if not result['gpus']:
                raise OSError('驱动没有返回可用显卡')
        except Exception as exc:
            result['errors'].append('显卡采样失败：' + str(exc))
        return result
