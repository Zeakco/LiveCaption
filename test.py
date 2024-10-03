import pyaudio


# 获取音频设备信息
def get_audio_devices():
    p = pyaudio.PyAudio()
    device_count = p.get_device_count()

    devices = []
    for i in range(device_count):
        device = p.get_device_info_by_index(i)
        devices.append(device)

    p.terminate()
    return devices


# 打开音频输入流
def open_audio_stream(device_index):
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, input_device_index=device_index)
    return p, stream


# 读取音频数据
def read_audio_data(stream, chunk_size=1024):
    data = stream.read(chunk_size)
    return data


# 停止并关闭输入流
def close_audio_stream(p, stream):
    stream.stop_stream()
    stream.close()
    p.terminate()


if __name__ == '__main__':
    devices = get_audio_devices()

    # 列出所有音频设备信息，打印更多详细信息
    for i, device in enumerate(devices):
        print(
            f"Device {i}: {device['name']} (input channels: {device['maxInputChannels']}, output channels: {device['maxOutputChannels']})")

    # 这里你可以手动选择设备索引
    device_index = int(input("请选择输入设备的索引: "))

    # 打开并读取音频数据
    p, stream = open_audio_stream(device_index)

    try:
        print("开始捕获音频数据... 按 Ctrl+C 停止")
        while True:
            data = read_audio_data(stream)
            print(f"音频数据长度: {len(data)}")
    except KeyboardInterrupt:
        print("停止捕获音频")

    # 关闭音频流
    close_audio_stream(p, stream)
