import os
import random
import subprocess
import platform
from typing import Optional, List

from qfluentwidgets import PrimaryPushButton, PushButton, DisplayLabel
from qframelesswindow import FramelessDialog, FramelessWindow

from .ClassWidgets.base import PluginBase, SettingsBase
from PyQt5 import uic
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QMouseEvent, QPalette, QColor
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QDialog,
    QVBoxLayout,
    QDesktopWidget
)


def read_names_from_file(file_path):
    """读取名单文件并返回处理后的名单列表"""
    if not os.path.exists(file_path):
        default_names = ["小明", "李华", "张四", "小五"]
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(default_names))
        return default_names

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            names = f.read().splitlines()
        return [name.strip() for name in names if name.strip()]
    except Exception as e:
        print(f"读取文件时出错: {e}")
        return []


class FloatingWindow(QWidget):
    closed = pyqtSignal()

    def __init__(self, method=None):
        super().__init__()
        self.method = method  # 保存method引用
        self.shuffled_names = []
        self.current_index = 0
        self.load_names()
        self.drag_pos = QPoint()
        self.mouse_press_pos = QPoint()
        self.init_ui()

    def init_ui(self):
        """初始化界面组件"""
        # 设置窗口标志实现全局置顶
        # 组合使用多种标志确保在所有系统上都能置顶
        self.setWindowFlags(
            Qt.FramelessWindowHint |  # 无边框
            Qt.WindowStaysOnTopHint |  # 始终置顶（最重要）
            Qt.Tool |  # 工具窗口（在任务栏不显示）
            Qt.WindowDoesNotAcceptFocus  # 不获取焦点，避免干扰其他窗口
        )
        
        # 设置窗口属性
        self.setAttribute(Qt.WA_TranslucentBackground)  # 透明背景
        self.setAttribute(Qt.WA_ShowWithoutActivating)  # 显示时不激活
        self.setWindowOpacity(0.8)  # 设置透明度

        self.label = QLabel("点名", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 0.8);
                font-family: 黑体;
                font-size: 16px;
                border-radius: 4px;
            }
        """)
        self.label.setFixedSize(50, 40)
        self.setFixedSize(50, 40)
        self.move_to_corner()
        
        # 设置鼠标追踪，确保鼠标事件正常工作
        self.setMouseTracking(True)

    def load_names(self):
        """加载名单并初始化洗牌队列"""
        file_path = os.path.join(os.path.dirname(__file__), "names.txt")
        self.names = read_names_from_file(file_path)
        self.reset_shuffle()

    def reset_shuffle(self):
        """执行洗牌算法重置队列"""
        self.shuffled_names = self.names.copy()
        random.shuffle(self.shuffled_names)
        self.current_index = 0

    def move_to_corner(self):
        """移动窗口到屏幕右下角"""
        screen = QDesktopWidget().availableGeometry()
        taskbar_height = 72
        x = screen.width() - self.width() - 50
        y = screen.height() - self.width() -200
        self.move(x, y)
        
        # 确保窗口在最顶层
        self.raise_()
        self.activateWindow()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.mouse_press_pos = event.globalPos()
            event.accept()
            
            # 点击时也确保窗口置顶
            self.raise_()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if (event.globalPos() - self.mouse_press_pos).manhattanLength() <= QApplication.startDragDistance():
                self.show_random_name()
            event.accept()

    def show(self):
        """重写show方法，确保窗口显示时置顶"""
        super().show()
        # 显示后立即置顶
        self.raise_()
        self.activateWindow()

    def show_random_name(self):
        """显示随机点名结果 - 通过发送通知的方式"""
        if not self.method:
            print("错误: 未提供method参数，无法发送通知")
            return
            
        name = self.get_next_name()
        
        # 获取插件目录，用于图标路径
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 构建图标路径
        icon_path = os.path.join(plugin_dir, "icon.png")
        
        # 如果图标文件不存在，可以尝试其他路径或使用默认值
        if not os.path.exists(icon_path):
            # 尝试查找其他可能的图标文件
            possible_icons = ["icon.png", "icon.jpg", "icon.jpeg", "icon.gif", "logo.png"]
            for icon_file in possible_icons:
                check_path = os.path.join(plugin_dir, icon_file)
                if os.path.exists(check_path):
                    icon_path = check_path
                    break
            else:
                # 如果都没有找到，可以使用空字符串或默认图标
                icon_path = ""  # 或者提供默认图标路径
        
        # 发送通知
        try:
            self.method.send_notification(
                state=4,  # 自定义通知
                lesson_name="",  # 自定义通知不需要课程名称
                title="随机点名",  # 通知标题
                subtitle="点名结果",  # 通知副标题
                content=f"{name}",  # 通知内容
                icon="",  # 图标路径
                duration=5000  # 通知显示5秒（5000毫秒）
            )
        except Exception as e:
            print(f"发送通知失败: {e}")
            # 如果发送通知失败，可以尝试备用方法（例如简单的对话框显示）
            self.show_fallback_dialog(name)

    def show_fallback_dialog(self, name):
        """发送通知失败时的备选方案"""
        try:
            from PyQt5.QtWidgets import QMessageBox
            msg_box = QMessageBox()
            msg_box.setWindowTitle("随机点名结果")
            msg_box.setText(f"本次点到的同学是：{name}")
            msg_box.setStandardButtons(QMessageBox.Ok)
            
            # 让弹窗也置顶显示
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
            msg_box.exec_()
        except:
            print(f"点名结果: {name}")

    def get_next_name(self):
        """获取下一个不重复的名字"""
        if not self.shuffled_names:
            return "名单为空"

        if self.current_index >= len(self.shuffled_names):
            self.reset_shuffle()

        name = self.shuffled_names[self.current_index]
        self.current_index += 1
        return name

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)


class Plugin(PluginBase):
    def __init__(self, cw_contexts, method):
        super().__init__(cw_contexts, method)
        self.floating_window = None
        self.plugin_dir = self.cw_contexts['PLUGIN_PATH']  # 保存插件目录

    def execute(self):
        """启动插件主功能"""
        if not self.floating_window:
            # 创建浮动窗口时传入method参数
            self.floating_window = FloatingWindow(method=self.method)
        self.floating_window.show()


class Settings(SettingsBase):
    def __init__(self, plugin_path, parent=None):
        super().__init__(plugin_path, parent)
        uic.loadUi(os.path.join(self.PATH, "settings.ui"), self)
        open_names_list = self.findChild(PrimaryPushButton, "open_names_list")
        open_names_list.clicked.connect(self.open_names_file)

    def open_names_file(self):
        """打开名单文件进行编辑"""
        file_path = os.path.join(self.PATH, "names.txt")
        
        try:
            if platform.system() == "Windows":
                os.startfile(file_path)
            elif platform.system() == "Linux":
                # 尝试多种Linux文件打开方式
                openers = ['xdg-open', 'gnome-open', 'kde-open', 'exo-open', 'gio-open']
                for opener in openers:
                    try:
                        subprocess.Popen([opener, file_path])
                        break
                    except FileNotFoundError:
                        continue
                else:
                    # 如果都没有，尝试使用编辑器
                    editors = ['gedit', 'kate', 'mousepad', 'pluma', 'xed']
                    for editor in editors:
                        try:
                            subprocess.Popen([editor, file_path])
                            break
                        except FileNotFoundError:
                            continue
            elif platform.system() == "Darwin":
                subprocess.Popen(['open', file_path])
        except Exception as e:
            print(f"打开文件失败: {e}")


# 独立运行时的测试代码
if __name__ == "__main__":
    import sys
    
    # 创建一个模拟的method对象用于测试
    class MockMethod:
        def send_notification(self, state, lesson_name, title, subtitle, content, icon, duration):
            print("\n" + "="*50)
            print("模拟通知发送:")
            print(f"状态: {state}")
            print(f"标题: {title}")
            print(f"副标题: {subtitle}")
            print(f"内容: {content}")
            print(f"图标: {icon}")
            print(f"持续时间: {duration}毫秒")
            print("="*50 + "\n")
    
    app = QApplication(sys.argv)
    
    # 创建一个模拟的cw_contexts字典
    mock_cw_contexts = {
        'PLUGIN_PATH': os.path.dirname(os.path.abspath(__file__))
    }
    
    # 创建插件实例
    plugin = Plugin(mock_cw_contexts, MockMethod())
    plugin.execute()
    
    sys.exit(app.exec_())