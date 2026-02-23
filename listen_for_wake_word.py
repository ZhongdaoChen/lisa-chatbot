"""
稳定版 Porcupine 唤醒词监听：
- 单独线程持续监听
- 唤醒后自动停止监听并释放麦克风
- 主线程处理完后可再次启动监听
- 不会卡死，不会资源泄露
"""

import pvporcupine
import pyaudio
import struct
import threading
import time

class WakeWordListener:
    def __init__(self, access_key, keyword_paths):
        self.access_key = access_key
        self.keyword_paths = keyword_paths

        self._thread = None
        self._running = False
        self._detected = False

    def _run(self):
        porcupine = pvporcupine.create(
            access_key=self.access_key,
            keyword_paths=self.keyword_paths
        )

        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length
        )

        print("Listening for wake word...")

        try:
            while self._running:
                pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
                result = porcupine.process(pcm)

                if result >= 0:
                    print("Wake word detected!")
                    self._detected = True
                    break

        finally:
            # 确保资源一定被释放，不会占着麦克风
            stream.stop_stream()
            stream.close()
            pa.terminate()
            porcupine.delete()

        self._running = False  # 线程退出

    def start(self):
        """开始监听（非阻塞）"""
        if self._running:
            return

        self._detected = False
        self._running = True

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """手动停止监听"""
        self._running = False
        if self._thread:
            self._thread.join()

    def detected(self):
        """是否检测到唤醒词"""
        return self._detected

