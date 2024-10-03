import sys
import pyaudio
import json
from PyQt5.QtGui import QPalette, QColor, QFont, QCursor
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QMenu, QWidget
from PyQt5.QtCore import QTimer, Qt, QThread, QPoint
from vosk import Model, KaldiRecognizer
from PyQt5.QtWidgets import QScrollBar

# 设置音频流参数
RATE = 44100  # 采样率
CHUNK = 2048  # 每次读取的音频块大小

class SubtitleWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.history = []
        self.transcription = ""
        self.is_dragging = False
        self.setMouseTracking(True)  # 启用鼠标跟踪
        self.is_in_edit_mode = False
        self.is_resizing = False  # 标识是否在调整大小
        self.drag_start_pos = QPoint(0, 0)
        self.is_scrolling = False  # 新增标志，指示用户是否在手动滚动
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(400, 800, 800, 300)

        self.text_edit = QTextEdit(self)
        self.text_edit.setGeometry(0, 0, 800, 300)
        self.text_edit.setReadOnly(True)

        font = QFont("Arial", 16)
        self.text_edit.setFont(font)

        palette = QPalette()
        palette.setColor(QPalette.Base, QColor(0, 0, 0, 150))
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        self.text_edit.setPalette(palette)

        self.text_edit.setAlignment(Qt.AlignLeft)
        self.text_edit.setWordWrapMode(True)

        self.set_display_mode()

        # 监听滚动条的 valueChanged 信号
        self.text_edit.verticalScrollBar().valueChanged.connect(self.on_scrollbar_value_changed)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_subtitle)
        self.timer.start(500)

    def on_scrollbar_value_changed(self):
        scrollbar = self.text_edit.verticalScrollBar()
        # 当滚动条不在底部时，说明用户正在手动滚动
        if scrollbar.value() != scrollbar.maximum():
            self.is_scrolling = True
        else:
            self.is_scrolling = False

    def set_display_mode(self):
        self.text_edit.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setCursor(QCursor(Qt.ArrowCursor))
        self.is_in_edit_mode = False
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def set_edit_mode(self):
        self.text_edit.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setCursor(QCursor(Qt.IBeamCursor))
        self.is_in_edit_mode = True
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def update_subtitle(self):
        # 获取滚动条对象
        scrollbar: QScrollBar = self.text_edit.verticalScrollBar()

        # 如果滚动条在最底部，允许自动滚动
        is_at_bottom = scrollbar.value() == scrollbar.maximum()

        # 只在有新的文字生成时更新
        if self.transcription or (self.history and self.history[-1] != self.transcription):
            # 增量更新字幕
            if self.transcription:
                self.text_edit.append(self.transcription)
            else:
                self.text_edit.append(self.history[-1])

        # 如果滚动条在最底部，保持自动滚动
        if is_at_bottom:
            scrollbar.setValue(scrollbar.maximum())


    def resizeEvent(self, event):
        self.text_edit.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            rect = self.rect()
            pos = event.pos()
            margin = 40  # 扩大边缘检测范围

            if rect.right() - margin <= pos.x() <= rect.right():
                if rect.bottom() - margin <= pos.y() <= rect.bottom():
                    self.is_resizing = "bottom_right"
                    self.drag_start_pos = event.globalPos()
                    self.setCursor(QCursor(Qt.SizeFDiagCursor))
                else:
                    self.is_resizing = "right"
                    self.drag_start_pos = event.globalPos()
                    self.setCursor(QCursor(Qt.SizeHorCursor))
            elif rect.bottom() - margin <= pos.y() <= rect.bottom():
                self.is_resizing = "bottom"
                self.drag_start_pos = event.globalPos()
                self.setCursor(QCursor(Qt.SizeVerCursor))
            else:
                self.is_dragging = True
                self.drag_start_pos = event.globalPos() - self.frameGeometry().topLeft()
                self.setCursor(QCursor(Qt.OpenHandCursor))
            event.accept()

            # 当鼠标按下时，用户开始滚动，标记正在滚动状态
            if self.text_edit.verticalScrollBar().isVisible():
                self.is_scrolling = True

    def mouseMoveEvent(self, event):
        rect = self.rect()
        pos = event.pos()
        margin = 40  # 边缘检测范围

        if self.is_dragging:
            self.move(event.globalPos() - self.drag_start_pos)
            event.accept()
        elif self.is_resizing:
            if self.is_resizing == "right":
                new_width = event.globalPos().x() - self.frameGeometry().x()
                if new_width > 200:
                    self.resize(new_width, self.height())
                self.setCursor(QCursor(Qt.SizeHorCursor))
            elif self.is_resizing == "bottom":
                new_height = event.globalPos().y() - self.frameGeometry().y()
                if new_height > 150:
                    self.resize(self.width(), new_height)
                self.setCursor(QCursor(Qt.SizeVerCursor))
            elif self.is_resizing == "bottom_right":
                new_width = event.globalPos().x() - self.frameGeometry().x()
                new_height = event.globalPos().y() - self.frameGeometry().y()
                if new_width > 200 and new_height > 150:
                    self.resize(new_width, new_height)
                self.setCursor(QCursor(Qt.SizeFDiagCursor))
            event.accept()
        else:
            # 根据鼠标位置判断是否靠近边缘并改变光标样式
            if rect.right() - margin <= pos.x() <= rect.right():
                if rect.bottom() - margin <= pos.y() <= rect.bottom():
                    self.setCursor(QCursor(Qt.SizeFDiagCursor))
                else:
                    self.setCursor(QCursor(Qt.SizeHorCursor))
            elif rect.bottom() - margin <= pos.y() <= rect.bottom():
                self.setCursor(QCursor(Qt.SizeVerCursor))
            else:
                self.setCursor(QCursor(Qt.ArrowCursor))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            self.is_resizing = False
            self.setCursor(QCursor(Qt.ArrowCursor))
            event.accept()

            # 当鼠标释放时，用户结束滚动，取消滚动状态
            self.is_scrolling = False

    def mouseDoubleClickEvent(self, event):
        if not self.is_in_edit_mode:
            self.set_edit_mode()
        event.accept()

    def focusOutEvent(self, event):
        if self.is_in_edit_mode:
            self.set_display_mode()
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        if self.is_in_edit_mode and event.key() == Qt.Key_Escape:
            self.set_display_mode()
            self.setCursor(QCursor(Qt.ArrowCursor))
            event.accept()

# 识别线程继承自 QThread
class RecognitionThread(QThread):
    def __init__(self, window):
        super().__init__()
        self.window = window

    def run(self):
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
                    result = rec.Result()
                    result_json = json.loads(result)

                    final_text = result_json.get('text', '').replace(" ", "")
                    if final_text:
                        self.window.history.append(final_text)
                        self.window.transcription = ""
                        print(f"Stored full sentence: {final_text}")

                else:
                    partial_result = rec.PartialResult()
                    partial_text = json.loads(partial_result).get('partial', '').replace(" ", "")
                    self.window.transcription = partial_text
                    print(f"Partial result: {partial_text}")

        except KeyboardInterrupt:
            print("录音结束")

        stream.stop_stream()
        stream.close()
        p.terminate()

def findInternalRecordingDevice(p):
    target = '立体声混音'
    for i in range(p.get_device_count()):
        devInfo = p.get_device_info_by_index(i)
        if target in devInfo['name'] and devInfo['maxInputChannels'] > 0:
            return i
    return -1

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SubtitleWindow()
    window.show()

    recognition_thread = RecognitionThread(window)
    recognition_thread.start()

    sys.exit(app.exec_())
