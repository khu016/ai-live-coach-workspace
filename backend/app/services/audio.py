"""从录像文件抽取音频轨（供语音转写使用）。

练习录像为 webm 视频（含 Opus 音频轨）。讯飞语音转写只收音频文件，
这里用 PyAV（内置 FFmpeg）把音频轨抽取并重采样为 16kHz / 单声道 / s16le WAV。
"""

import av


def extract_audio_to_wav(src: str, dst: str, sample_rate: int = 16000) -> None:
    input_container = av.open(src)
    try:
        audio_stream = next(
            (s for s in input_container.streams if s.type == "audio"), None
        )
        if audio_stream is None:
            raise RuntimeError("录像中没有音频轨，无法转写")

        resampler = av.AudioResampler(format="s16", layout="mono", rate=sample_rate)
        output = av.open(dst, "w", format="wav")
        try:
            out_stream = output.add_stream("pcm_s16le", rate=sample_rate)
            out_stream.layout = "mono"
            for frame in input_container.decode(audio_stream):
                for resampled in resampler.resample(frame):
                    for packet in out_stream.encode(resampled):
                        output.mux(packet)
            for packet in out_stream.encode(None):
                output.mux(packet)
        finally:
            output.close()
    finally:
        input_container.close()
