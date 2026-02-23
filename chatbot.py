import threading
from openai import OpenAI
import os
import time
import logging
from gtts import gTTS
from recorder import record_audio_to_wav
import subprocess
from datetime import datetime
import queue
from speak_response_baidu import speak_response_baidu, speak_response_baidu_stream
import re
from listen_for_wake_word import WakeWordListener  # ← 使用你新的稳定唤醒模块
from pynput import keyboard as kb_module

timer = time.perf_counter

logging.basicConfig(filename="chatgpt_interaction.log",
                    level=logging.INFO,
                    format="%(asctime)s - %(message)s")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# ---------------------------
# OpenAI 调用
# ---------------------------
def call_openai(user_input):
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5.1",
        input=user_input
    )
    response_text = response.output[0].content[0].text
    return response_text


# ---------------------------
# 播放语音（Apple 内置）
# ---------------------------
def speak_response_apple(response_text):
    subprocess.run(['say', response_text])


# ---------------------------
# Whisper 语音识别
# ---------------------------
def recognize_wav_with_whisper_cli(model_path, wav_path, threads=4):
    cmd = [
        "/Users/peterchen/Desktop/LisaChatBot/whisper-cli",
        "-m", model_path,
        "-f", wav_path,
        "--threads", str(threads),
        "-l", "auto",        # 自动检测中文/英文
        "--beam-size", "5",  # 束搜索，提升准确率
        "--best-of", "5",    # 多次采样取最优
        "--no-timestamps",   # 不输出时间戳
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"whisper-cli error: {result.stderr}")

    return result.stdout.strip()


# ---------------------------
# 打印当前时间
# ---------------------------
def print_time():
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------
# 流式播放辅助
# ---------------------------
def stream_and_play(q, stop_event, process_holder):
    """后台线程：从队列中逐段取文件名并播放，支持随时打断"""
    while not stop_event.is_set():
        try:
            filename = q.get(timeout=0.5)
        except queue.Empty:
            continue
        if filename is None:
            process_holder[0] = None
            break
        if stop_event.is_set():
            break
        p = subprocess.Popen(["afplay", filename])
        process_holder[0] = p
        while p.poll() is None:
            if stop_event.is_set():
                p.terminate()
                break
            time.sleep(0.05)


# ---------------------------
# 主程序
# ---------------------------
def main():

    # 创建 唤醒词监听器（只会创建一次）
    listener = WakeWordListener(
        access_key="XUJ2i95zOyzEIspTpZUeqjQYn39SpMraZ5ck9TnLqL3gI/7sc8Iz2g==",
        keyword_paths=["/Users/peterchen/Desktop/LisaChatBot/Hello-robot_en_mac_v3_0_0/Hello-robot_en_mac_v3_0_0.ppn"]
    )

    # 流式播放控制
    process_holder = [None]   # 当前 afplay 进程
    stop_playback = threading.Event()

    # 空格键打断播放
    space_pressed = threading.Event()

    def on_press(key):
        if key == kb_module.Key.space:
            space_pressed.set()

    kb_listener = kb_module.Listener(on_press=on_press, daemon=True)
    kb_listener.start()

    while True:

        # -----------------------
        # 1) 启动唤醒检测线程
        # -----------------------
        space_pressed.clear()
        listener.start()
        print("🔊 正在监听唤醒词... (播放中可按空格键打断)")

        # 等待唤醒词触发，或空格键打断
        while not listener.detected() and not space_pressed.is_set():
            time.sleep(0.05)

        if space_pressed.is_set():
            # 空格键打断：停止播放，重新开始监听
            listener.stop()
            stop_playback.set()
            p = process_holder[0]
            if p and p.poll() is None:
                p.terminate()
                print("⏹ 播放已打断，重新监听唤醒词...")
            continue

        print("🚀 唤醒词已触发！")
        listener.stop()  # 释放麦克风（非常关键）

        # -----------------------
        # 2) 停掉之前的播放（如果还在）
        # -----------------------
        stop_playback.set()
        p = process_holder[0]
        if p and p.poll() is None:
            p.terminate()

        # -----------------------
        # 3) 提示用户提问
        # -----------------------
        speak_response_apple("Hello 你好呀，请说问题吧")

        # -----------------------
        # 4) 录音
        # -----------------------
        if not record_audio_to_wav("recorder_audio.wav"):
            speak_response_baidu("我好像什么都没有听到呢")
            continue

        threading.Thread(
            target=speak_response_apple,
            args=("让我思考思考～",),
            daemon=True
        ).start()

        # -----------------------
        # 5) Whisper 识别
        # -----------------------
        print("🎧 开始 Whisper 识别：" + print_time())

        text = recognize_wav_with_whisper_cli(
            "ggml-large-v3-q5_0.bin",
            "recorder_audio.wav"
        )

        # 清理时间戳
        print(text)
        text = re.sub(r'^\[.*?\]\s*', '', text).strip()

        logging.info("Text I hear: %s", text)
        print("识别完成：" + text)

        # -----------------------
        # 6) 调用 OpenAI
        # -----------------------
        print("🤖 开始调用 OpenAI：" + print_time())
        chatgpt_answer = call_openai(
            "请用简体中文回答以下问题，300字以内：" + text
        )
        logging.info("OpenAPI response: %s", chatgpt_answer)

        # -----------------------
        # 7) 流式 TTS + 播放（生成与播放并行）
        # -----------------------
        print("🔊 开始流式播放语音：" + print_time())
        q = speak_response_baidu_stream(chatgpt_answer)
        stop_playback.clear()
        threading.Thread(
            target=stream_and_play,
            args=(q, stop_playback, process_holder),
            daemon=True
        ).start()

        # -----------------------
        # 8) 回到循环，自动重新开始监听唤醒词
        # -----------------------


if __name__ == "__main__":
    main()
