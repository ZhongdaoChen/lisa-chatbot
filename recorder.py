import pyaudio
import wave
import numpy as np
import time


def record_audio_to_wav(filename,threshold=200, silence_limit=3, rate=16000, chunk=1024, wait_timeout=10):
    """
    录音并去除静音段，保存到指定文件

    参数：
    - filename: 保存的 wav 文件名
    - threshold: 静音判断阈值，越大越不容易判为静音
    - silence_limit: 连续静音多少秒后结束录音
    - rate: 采样率
    - chunk: 每次读取的帧数
    """

    def is_silent(data):
        #print(str(np.abs(np.frombuffer(data, dtype=np.int16)).mean()) + '\n\n\n\n')
        return np.abs(np.frombuffer(data, dtype=np.int16)).mean() < threshold


    p = pyaudio.PyAudio()

    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=rate,
                    input=True,
                    frames_per_buffer=chunk)

    print("开始录音，可以先沉默再说话...")
    for _ in range(6):
        stream.read(chunk)      #丢弃五个chunk避免唤醒词后打招呼的干扰

    frames = []
    silent_chunks = 0
    recording_started = False
    start_time = time.time()

    while True:
        data = stream.read(chunk)
        if not is_silent(data):   #如果有声音，这录音
            frames.append(data)
            recording_started = True
            #print("录音打开\n")
            silent_chunks = 0
        else:       #如果没声音
            if recording_started:
                frames.append(data)  # 保留停顿，维持词间自然间隔
                silent_chunks += 1
                if silent_chunks > silence_limit * rate / chunk:
                    # 去掉末尾多余的静音段，只保留0.3秒收尾
                    tail_keep = int(0.3 * rate / chunk)
                    frames = frames[:-silent_chunks + tail_keep]
                    print("检测到持续静音，录音结束。")
                    break
            else:
                # 开头沉默，检查等待超时
                if wait_timeout > 0 and time.time() - start_time > wait_timeout:
                    print("等待超时，未检测到说话。")
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                    return False


    stream.stop_stream()
    stream.close()
    p.terminate()
    wf = wave.open(filename, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    wf.setframerate(rate)
    wf.writeframes(b''.join(frames))
    wf.close()

    print("录音已保存")
    return True