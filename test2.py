import pyaudio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import wave

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 4096
# CHUNK = 1024
WAVE_OUTPUT_FILENAME = 'audio_output.wav'

# 获取内录设备序号,在windows操作系统上测试通过，hostAPI = 0 表明是MME设备
def findInternalRecordingDevice(p):
    # 要找查的设备名称中的关键字
    target = '立体声混音'
    # 逐一查找声音设备
    for i in range(p.get_device_count()):
        devInfo = p.get_device_info_by_index(i)
        print(devInfo)
        if devInfo['name'].find(target) >= 0 and devInfo['hostApi'] == 0:
            # print('已找到内录设备,序号是 ',i)
            return i
    print('无法找到内录设备!')
    return -1

# Initialize PyAudio
audio = pyaudio.PyAudio()

# 这里input_device_index的2就是系统内录设备索引
stream = audio.open(input_device_index=2,
                    format=FORMAT,
                    channels=1,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

plt.ion()
fig, ax = plt.subplots()
x = np.arange(0, CHUNK)
line, = ax.plot(x, np.zeros(CHUNK))
ax.set_xlim(0, CHUNK)
ax.set_ylim(-32768, 32767)

wave_output_file = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
wave_output_file.setnchannels(CHANNELS)
wave_output_file.setsampwidth(audio.get_sample_size(FORMAT))
wave_output_file.setframerate(RATE)

def update_plot(data):
    print(data)
    line.set_ydata(data)
    fig.canvas.draw()
    fig.canvas.flush_events()

def display_audio_waveform():
    while True:
        try:
            audio_data = np.frombuffer(stream.read(CHUNK), dtype=np.int16)
            # update_plot(audio_data*500)
            update_plot(audio_data)
            # wave_output_file.writeframes(audio_data)
        except KeyboardInterrupt:
            break

display_audio_waveform()

stream.stop_stream()
stream.close()
audio.terminate()

wave_output_file.close()
print('Audio saved to', WAVE_OUTPUT_FILENAME)