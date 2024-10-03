from vosk import Model

try:
    model = Model("vosk-model-cn-0.22")
    print("Model loaded successfully")
except Exception as e:
    print(f"Error: {e}")


import sys
import pyaudio
import json
from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit
from PyQt5.QtCore import QTimer, Qt, QThread, QPoint
from vosk import Model, KaldiRecognizer
from PyQt5.QtWidgets import QScrollBar

# 设置音频流参数
RATE = 44100  # 采样率
CHUNK = 2048  # 每次读取的音频块大小

class SubtitleWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.history = []  # 用于存储历史字幕
        self.transcription = ""  # 实时显示的部分句子
        self.is_dragging = False
        self.drag_start_pos = QPoint(0, 0)
        self.initUI()

    def initUI(self):
        # 创建可拖动和调整大小的窗口
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)  # 添加无边框
        self.setAttribute(Qt.WA_TranslucentBackground)  # 透明背景
        self.setGeometry(400, 800, 800, 300)  # 增加窗口高度以显示更多字幕

        # 字幕标签
        self.text_edit = QTextEdit(self)
        self.text_edit.setGeometry(0, 0, 800, 300)  # 调整高度
        self.text_edit.setReadOnly(True)  # 设置为只读，避免修改内容

        # 设置字体样式和大小
        font = QFont("Arial", 16)  # 设置字体为 Arial，大小为 16
        self.text_edit.setFont(font)

        # 设置背景颜色和字体颜色
        palette = QPalette()
        palette.setColor(QPalette.Base, QColor(0, 0, 0, 150))  # 半透明黑色背景
        palette.setColor(QPalette.Text, QColor(255, 255, 255))  # 设置字体为白色
        self.text_edit.setPalette(palette)

        self.text_edit.setAlignment(Qt.AlignLeft)  # 左对齐并靠上对齐
        self.text_edit.setWordWrapMode(True)  # 启用自动换行

        # 定时器用于定时更新字幕
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_subtitle)
        self.timer.start(500)

    def update_subtitle(self):
        # 获取滚动条对象
        scrollbar: QScrollBar = self.text_edit.verticalScrollBar()

        # 保存滚动条是否在最底部
        is_at_bottom = scrollbar.value() == scrollbar.maximum()

        # 将所有历史字幕拼接并显示
        all_history_text = "\n".join(self.history)
        self.text_edit.setPlainText(all_history_text + "\n" + self.transcription)  # 在最后一行显示当前句子

        # 如果滚动条在最底部，保持自动滚动
        if is_at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def resizeEvent(self, event):
        # 在窗口大小变化时，调整字幕标签的宽度
        self.text_edit.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    # 鼠标按下事件，记录开始位置
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.drag_start_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    # 鼠标移动事件，实现窗口拖动
    def mouseMoveEvent(self, event):
        if self.is_dragging:
            self.move(event.globalPos() - self.drag_start_pos)
            event.accept()

    # 鼠标释放事件，停止拖动
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            event.accept()

# 识别线程继承自 QThread
class RecognitionThread(QThread):
    def __init__(self, window):
        super().__init__()
        self.window = window

    def run(self):
        # 实时语音识别逻辑
        p = pyaudio.PyAudio()
        device_index = findInternalRecordingDevice(p)
        if device_index == -1:
            print("没有找到内录设备，程序终止。")
            return

        model = Model("vosk-model-cn-0.22")
        rec = KaldiRecognizer(model, RATE)

        stream = p.open(input_device_index=device_index,
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)

        try:
            while True:
                data = stream.read(CHUNK, exception_on_overflow=False)

                if rec.AcceptWaveform(data):
                    # 完整结果：只在这里进行存储
                    result = rec.Result()
                    result_json = json.loads(result)

                    # 检查是否有文本返回
                    final_text = result_json.get('text', '').replace(" ", "")
                    if final_text:
                        self.window.history.append(final_text)  # 将完整句子存入历史
                        self.window.transcription = ""  # 清空部分句子
                        print(f"Stored full sentence: {final_text}")  # 仅用于调试，打印完整句子

                else:
                    # 部分结果：仅用于实时显示，不存储
                    partial_result = rec.PartialResult()
                    partial_text = json.loads(partial_result).get('partial', '').replace(" ", "")  # 去除空格
                    self.window.transcription = partial_text  # 实时显示但不存储
                    print(f"Partial result: {partial_text}")  # 仅用于调试，打印部分结果

        except KeyboardInterrupt:
            print("录音结束")

        stream.stop_stream()
        stream.close()
        p.terminate()

def findInternalRecordingDevice(p):
    target = '立体声混音'
    for i in range(p.get_device_count()):
        devInfo = p.get_device_info_by_index(i)
        if devInfo['name'].find(target) >= 0 and devInfo['hostApi'] == 0:
            return i
    print('无法找到内录设备!')
    return -1

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SubtitleWindow()
    window.show()

    # 启动识别线程
    rec_thread = RecognitionThread(window)
    rec_thread.start()

    sys.exit(app.exec_())
