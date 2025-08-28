# speech_recognizer.py

import whisper
import speech_recognition as sr
# import numpy as np
# import soundfile as sf

model = whisper.load_model("base")

def record_voice():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    try:
        with mic as source:
            print("请开始说话...")
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source, timeout=20)  
        with open("input.wav", "wb") as f:
            f.write(audio.get_wav_data())

        print("录音完成。")
        return "input.wav"
    except Exception as e:
        print(f"[ERROR] 录音失败: {e}")
        return None
    
def transcribe_audio():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("请开始说话...")
        audio = r.listen(source, timeout=5, phrase_time_limit=10)
    wav_path = "input.wav"

    with open(wav_path, "wb") as f:
        f.write(audio.get_wav_data())


    text = r.recognize_google(audio, language="zh-CN")
    return text

# 适合本地部署，不受网络限制
# def transcribe_audio(filename="input.wav"):
#     print("Whisper 开始识别音频中...")
#     result = model.transcribe(filename, language='en') 
#     print(f"Whisper 识别结果: {result['text']}")
#     return result['text']


# if __name__ == "__main__": 
#     audio_file = record_voice()
#     if audio_file:
#         text = transcribe_audio(audio_file)
#         print(f"识别文本: {text}")
#     else:
#         print("录音失败，无法进行语音识别。")


# def record_voice(filename="input.wav", duration=8, fs=16000):
#     try:
#         print("正在录音中，请讲话.../Recording in progress, please speak...")
#         recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
#         sd.wait()
#         sf.write(filename, recording, fs)
#         print("录音完成/Recording completed successfully.")
#     except Exception as e:
#         print(f"录音出错: {e}")
#         return None
#     return filename
