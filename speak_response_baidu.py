import subprocess
from urllib.request import urlopen
from urllib.request import Request
from urllib.parse import urlencode
from urllib.parse import quote_plus
from get_baidu_access_token import get_baidu_access_token
from pydub import AudioSegment
import os
import queue
import threading


def split_text(text, max_len=300):
    """把长文本按 max_len 拆分"""
    return [text[i:i+max_len] for i in range(0, len(text), max_len)]

def tts_request(text, index=0):

    # 语音列表文档：https://ai.baidu.com/ai-doc/SPEECH/Rluv3uq3d
    PER = 4189
    # 语速，取值0-15，默认为5中语速
    SPD = 5
    # 音调，取值0-15，默认为5中语调
    PIT = 5
    # 音量，取值0-9，默认为5中音量
    VOL = 5
    # 下载的文件格式, 3：mp3(default) 4： pcm-16k 5： pcm-8k 6. wav
    AUE = 3
    FORMATS = {3: "mp3", 4: "pcm", 5: "pcm", 6: "wav"}
    FORMAT = FORMATS[AUE]
    CUID = "123456PYTHON"
    TTS_URL = 'http://tsn.baidu.com/text2audio'
    token = get_baidu_access_token()
    tex = quote_plus(text)  # 此处TEXT需要两次urlencode
    print(tex)
    params = {'tok': token, 'tex': tex, 'per': PER, 'spd': SPD, 'pit': PIT, 'vol': VOL, 'aue': AUE, 'cuid': CUID,
              'lan': 'zh', 'ctp': 1}  # lan ctp 固定参数
    data = urlencode(params)
    req = Request(TTS_URL, data.encode('utf-8'))
    f = urlopen(req)
    result = f.read()
    headers = dict((name.lower(), value) for name, value in f.headers.items())

    has_error = ('content-type' not in headers.keys() or headers['content-type'].find('audio/') < 0)
    filename = f"part_{index}.{FORMAT}" if not has_error else f"error_{index}.txt"
    with open(filename, 'wb') as of:
        of.write(result)

    return filename if not has_error else None


def speak_response_baidu_stream(text):
    """流式合成：后台线程逐段生成，通过队列传出文件名，None 表示全部完成"""
    q = queue.Queue()
    parts = split_text(text, 300)

    def _produce():
        for i, part in enumerate(parts):
            print(f"正在生成第 {i+1}/{len(parts)} 段语音...")
            filename = tts_request(part, i)
            if filename:
                q.put(filename)
            else:
                print(f"第 {i+1} 段生成失败，跳过。")
        q.put(None)  # 生成完毕信号

    threading.Thread(target=_produce, daemon=True).start()
    return q


def speak_response_baidu(text):
    """支持长文本自动分段合成，并拼接成 result.mp3"""
    parts = split_text(text, 300)
    audio_segments = []

    for i, part in enumerate(parts):
        print(f"正在生成第 {i+1}/{len(parts)} 段语音...")
        filename = tts_request(part, i)
        if filename:
            seg = AudioSegment.from_mp3(filename)
            audio_segments.append(seg)
        else:
            print(f"第 {i+1} 段生成失败，跳过。")

    if audio_segments:
        final_audio = sum(audio_segments[1:], audio_segments[0])
        final_audio.export("result.mp3", format="mp3")
        print("已生成完整语音 result.mp3")
        # 播放（可选）
        # subprocess.Popen(["afplay", "result.mp3"])
    else:
        print("全部语音生成失败！")