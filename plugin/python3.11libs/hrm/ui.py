"""界面与后台采样分离；所有窗口操作均在 Houdini 主线程执行。"""
import time
from PySide6 import QtCore, QtWidgets, QtGui
from .metrics import Sampler

NAME = 'houdini_resource_monitor_v001'


class MenuAnchor(QtCore.QObject):
    """只占用 Main 右侧空白区，不修改 Houdini 原生布局。"""
    def __init__(self, main, monitor):
        super().__init__(monitor)
        self.main = main
        self.monitor = monitor
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.sync)
        self.timer.start(250)
        self.sync()

    def sync(self):
        main, monitor = self.main, self.monitor
        if not main.isVisible() or main.isMinimized():
            monitor.hide()
            return
        import hou
        scale = hou.ui.scaledSize(100) / 100.
        left = int(monitor.settings.value('menu_left', round(640 * scale)))
        width = min(round(820 * scale), main.width()-left-round(12 * scale))
        if width < round(520 * scale):
            monitor.hide()
            return
        monitor.layout().itemAt(0).widget().hide()
        monitor.state.hide()
        monitor.layout().setContentsMargins(8, 1, 8, 1)
        monitor.layout().setSpacing(8)
        meter_width = (width-40)//4
        for meter in monitor.meters.values():
            meter.setFixedWidth(meter_width)
            label_width = max(round(28*scale), meter.label.fontMetrics().horizontalAdvance(meter.label.text())+4)
            meter.label.setFixedWidth(label_width)
            meter.bar.setFixedWidth(max(55,meter_width-label_width-13))
            meter.bar.setFixedHeight(round(18*scale))
        height = round(22 * scale)
        monitor.setFixedSize(width, height)
        monitor.move(left, 0)
        monitor.show()
        monitor.raise_()


def apply_appearance(monitor):
    """提供独立、不透明的底色，阻止原生菜单文字透过控件间隙。"""
    palette = monitor.palette()
    palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor('#303030'))
    palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor('#e8e8e8'))
    monitor.setPalette(palette)
    monitor.setAutoFillBackground(True)
    monitor.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground, False)
    monitor.setAttribute(QtCore.Qt.WidgetAttribute.WA_NativeWindow, True)
    monitor.update()


def attach_menu_row(main, monitor):
    """将单个监控控件嵌到菜单同排空白处，保留原生绘制区原位。"""
    for attr in ('_title_anchor', '_menu_anchor'):
        old = getattr(monitor, attr, None)
        if old is not None:
            old.timer.stop()
            old.deleteLater()
            delattr(monitor, attr)
    layout = main.layout()
    if layout is not None:
        layout.removeWidget(monitor)
        layout.activate()
    monitor.setParent(main, QtCore.Qt.WindowType.Widget)
    apply_appearance(monitor)
    monitor.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
    monitor._menu_anchor = MenuAnchor(main, monitor)
    return monitor


class Worker(QtCore.QThread):
    sampled = QtCore.Signal(object)

    def __init__(self, parent):
        super().__init__(parent)
        self.interval = 1.0

    def run(self):
        sampler = Sampler()
        while not self.isInterruptionRequested():
            started = time.monotonic()
            self.sampled.emit(sampler.sample())
            while not self.isInterruptionRequested() and time.monotonic()-started < self.interval:
                self.msleep(50)


class Meter(QtWidgets.QWidget):
    def __init__(self, title, color, parent):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(5)
        self.label = QtWidgets.QLabel(title)
        self.label.setFixedWidth(30)
        self.setFixedWidth(188)
        self.bar = QtWidgets.QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setFixedWidth(145)
        self.bar.setFixedHeight(20)
        self.bar.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.bar.setStyleSheet('QProgressBar {border:1px solid #555; border-radius:4px;'
            'background:#25282c;color:white;} QProgressBar::chunk {background:'+color+';border-radius:3px;}')
        layout.addWidget(self.label)
        layout.addWidget(self.bar)
        self.update_value(None, '采样中')

    def update_value(self, percent, text):
        self.bar.setValue(round(max(0, min(100, percent))*10) if percent is not None else 0)
        self.bar.setFormat(text)


class Monitor(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName(NAME)
        self.settings = QtCore.QSettings('本地工具', 'Houdini顶部资源监控条')
        self.latest = {}
        self.samples = 0
        self.gpu_index = int(self.settings.value('gpu', 0))
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(8)
        title = QtWidgets.QLabel('资源监控')
        title.setToolTip('整台电脑的使用量，包含 Houdini 和其他程序。右键可调整刷新频率和显卡。')
        layout.addWidget(title)
        self.meters = {}
        for key, title, color in [('cpu','CPU','#258ba5'), ('gpu','GPU','#438b57'),
                                  ('ram','RAM','#8862ac'), ('vram','VRAM','#ac7736')]:
            self.meters[key] = Meter(title, color, self)
            layout.addWidget(self.meters[key])
        self.state = QtWidgets.QLabel('整机 · 每秒刷新')
        layout.addWidget(self.state)
        layout.addStretch()
        self.worker = Worker(self)
        self.worker.interval = float(self.settings.value('interval', 1.))
        if self.worker.interval not in (.5, 1., 2., 5.):
            self.worker.interval = 1.
        self.worker.sampled.connect(self.update_data)
        self.worker.start()
        QtWidgets.QApplication.instance().aboutToQuit.connect(self.stop)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.menu)

    def stop(self):
        self.worker.requestInterruption()
        self.worker.wait(3500)

    @QtCore.Slot(object)
    def update_data(self, data):
        self.latest = data
        self.samples += 1
        cpu = data.get('cpu')
        self.meters['cpu'].update_value(cpu, f'{cpu:.1f}%' if cpu is not None else '等待采样')
        mem = data.get('memory')
        if mem and mem['total']:
            self.meters['ram'].update_value(mem['used']/mem['total']*100,
                f"{mem['used']/2**30:.1f} / {mem['total']/2**30:.1f} GB")
        else:
            self.meters['ram'].update_value(None, '不可用')
        gpus = data.get('gpus', [])
        gpu = gpus[min(self.gpu_index, len(gpus)-1)] if gpus else None
        if gpu:
            value = gpu['load']
            self.meters['gpu'].update_value(value, f'{value:.0f}%' if value is not None else '不可用')
            used, total = gpu['used'], gpu['total']
            if used is not None and total:
                self.meters['vram'].update_value(used/total*100, f'{used/1024:.1f} / {total/1024:.1f} GB')
            else:
                self.meters['vram'].update_value(None, '不可用')
            tip = gpu['name'] + '\n驱动统计的整卡 GPU 利用率；与任务管理器的单引擎统计口径不同。'
            if gpu['temperature'] is not None:
                tip += f"\n显卡温度：{gpu['temperature']:.0f} ℃"
            self.meters['gpu'].setToolTip(tip)
            self.meters['vram'].setToolTip(gpu['name']+'\n整张显卡的已用显存 / 总显存')
        else:
            for key in ('gpu', 'vram'):
                self.meters[key].update_value(None, '不可用')
        errors = data.get('errors', [])
        self.state.setText('采样异常' if errors else f'整机 · {self.worker.interval:g}秒刷新')
        self.state.setToolTip('\n'.join(errors) if errors else '资源使用量为整机统计，并非 Houdini 单进程。')
        self.setToolTip('\n'.join(errors) if errors else '整机资源占用；右键调整刷新频率和监控条位置。')
        for key in ('cpu', 'ram'):
            self.meters[key].setToolTip('\n'.join(errors) if errors else '整机使用量')

    def menu(self, pos):
        menu = QtWidgets.QMenu(self)
        submenu = menu.addMenu('刷新频率')
        for seconds in (.5, 1., 2., 5.):
            action = submenu.addAction(f'每 {seconds:g} 秒')
            action.setCheckable(True)
            action.setChecked(self.worker.interval == seconds)
            action.triggered.connect(lambda checked=False, s=seconds: self.set_interval(s))
        submenu = menu.addMenu('选择显卡')
        for index, gpu in enumerate(self.latest.get('gpus', [])):
            action = submenu.addAction(gpu['name'])
            action.setCheckable(True)
            action.setChecked(self.gpu_index == index)
            action.triggered.connect(lambda checked=False, i=index: self.set_gpu(i))
        menu.addSeparator()
        menu.addAction('调整菜单行左侧留白…', self.adjust_menu_left)
        menu.addAction('说明：显示整机资源使用量').setEnabled(False)
        menu.exec(self.mapToGlobal(pos))

    def set_interval(self, seconds):
        self.worker.interval = seconds
        self.settings.setValue('interval', seconds)

    def adjust_menu_left(self):
        value, accepted = QtWidgets.QInputDialog.getInt(self, '监控条位置',
            '左侧为 Houdini 菜单保留的宽度（像素）：',
            int(self.settings.value('menu_left', 640)), 640, 4000)
        if accepted:
            self.settings.setValue('menu_left', value)
            self._menu_anchor.sync()

    def set_gpu(self, index):
        self.gpu_index = index
        self.settings.setValue('gpu', index)
        self.update_data(self.latest)


def install():
    import hou
    main = hou.qt.mainWindow()
    existing = main.findChild(QtWidgets.QWidget, NAME)
    if existing is not None:
        if not hasattr(existing, '_menu_anchor'):
            attach_menu_row(main, existing)
        existing.show()
        return existing
    monitor = Monitor(main)
    return attach_menu_row(main, monitor)
