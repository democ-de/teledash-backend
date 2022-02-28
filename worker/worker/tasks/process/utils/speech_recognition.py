import json
import subprocess
import time
from pathlib import Path
from typing import Union
from urllib import request

from celery.utils.log import get_task_logger
from vosk import KaldiRecognizer, Model, SetLogLevel

logger = get_task_logger(__name__)

# Pre-trained language models provided by vosk
# See: https://alphacephei.com/vosk/models
PRETRAINED_VOSK_MODELS = [
    "vosk-model-small-en-us-0.15",
    "vosk-model-en-us-0.22",
    "vosk-model-en-us-0.22-lgraph",
    "vosk-model-en-us-daanzu-20200905",
    "vosk-model-en-us-daanzu-20200905-lgraph",
    "vosk-model-en-us-librispeech-0.2",
    "vosk-model-small-en-us-zamia-0.5",
    "vosk-model-en-us-aspire-0.2",
    "vosk-model-en-us-0.21",
    "vosk-model-en-in-0.4",
    "vosk-model-small-en-in-0.4",
    "vosk-model-cn-0.1",
    "vosk-model-small-cn-0.3",
    "vosk-model-cn-kaldi-multicn-2",
    "vosk-model-cn-kaldi-multicn-2-lgraph",
    "vosk-model-cn-kaldi-cvte-2",
    "vosk-model-ru-0.22",
    "vosk-model-small-ru-0.22",
    "vosk-model-ru-0.10",
    "vosk-model-small-fr-0.22",
    "vosk-model-fr-0.22",
    "vosk-model-small-fr-pguyot-0.3",
    "vosk-model-fr-0.6-linto-2",
    "vosk-model-de-0.21",
    "vosk-model-small-de-zamia-0.3",
    "vosk-model-small-de-0.15",
    "vosk-model-small-es-0.3",
    "vosk-model-small-pt-0.3",
    "vosk-model-el-gr-0.7",
    "vosk-model-small-tr-0.3",
    "vosk-model-small-vn-0.3",
    "vosk-model-small-it-0.4",
    "vosk-model-nl-spraakherkenning-0.6",
    "vosk-model-nl-spraakherkenning-0.6-lgraph",
    "vosk-model-small-ca-0.4",
    "vosk-model-ar-mgb2-0.4",
    "vosk-model-small-fa-0.4",
    "vosk-model-fa-0.5",
    "vosk-model-small-fa-0.5",
    "vosk-model-tl-ph-generic-0.6",
    "vosk-model-small-uk-v3-nano",
    "vosk-model-small-uk-v3-small",
    "vosk-model-uk-v3",
    "vosk-model-small-kz-0.15",
    "vosk-model-kz-0.15",
    "vosk-model-small-sv-rhasspy-0.15",
    "vosk-model-small-ja-0.22",
    "vosk-model-small-eo-0.22",
    "vosk-model-spk-0.4",
]

WAV_SAMPLE_RATE = 16000


def get_duration(media):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            media,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return float(result.stdout)


def load_model_speech_recognition(model_name: str):
    # Loglevel for Vosk / Kaldi:
    # 0 - default value to print info and error messages but no debug
    # less than 0 - don't print info messages
    # greather than 0 - more verbose mode
    SetLogLevel(-1)

    model = None
    model_dir = Path.cwd().joinpath("worker/models/vosk")
    model_path = model_dir.joinpath(model_name)

    # language model file does not exist locally
    if not model_path.is_dir():
        if model_name not in PRETRAINED_VOSK_MODELS:
            logger.error(f"Model {model_path} does not exist at this location")
            return

        # download language model if pretrained model exists
        model_file_name = model_name + ".zip"
        model_file_path = model_dir.joinpath(model_file_name)
        model_url = f"https://alphacephei.com/vosk/models/{model_file_name}"

        logger.info(
            f"Downloading model from {model_url}. This can take a few minuntes..."
        )

        try:
            model_dir.mkdir(parents=True, exist_ok=True)
            request.urlretrieve(model_url, model_file_path)
        except Exception:
            logger.error(
                f"Failed downloading language model from {model_url}",
                exc_info=True,
            )

        # unpack zipped model
        logger.info(
            f"Unpackung model {model_file_path}. This can also take a few minuntes..."
        )
        try:
            import zipfile

            with zipfile.ZipFile(model_file_path, "r") as zip_ref:
                zip_ref.extractall(model_dir)
            model_file_path.unlink()

        except Exception:
            logger.error(
                f"Failed unpacking model {model_file_path}",
                exc_info=True,
            )

    try:
        start_time = time.time()
        model = Model(model_path.as_posix())
        end_time = round(time.time() - start_time, 2)
        logger.info(f"Loading model '{model_name}' took {end_time} s")
        return model

    except Exception:
        logger.error(f"Failed loading model {model_path}", exc_info=True)


def recognize_speech(audio: str, model: Model) -> Union[str, None]:
    # TODO: implement vosk-server (docker) for large models

    # transcode audio
    try:
        process = subprocess.Popen(
            [
                "ffmpeg",
                "-loglevel",
                "quiet",
                "-i",  # input
                audio,
                "-ar",  # audio sampling frequency
                str(WAV_SAMPLE_RATE),
                "-ac",  # number of audio channels
                "1",  # 1 channel (mono)
                "-f",  # force input or output file format
                "s16le",  # PCM signed 16-bit little-endian
                "-",
            ],
            stdout=subprocess.PIPE,
        )
    except Exception:
        logger.error(
            f"Can't read audio file {audio}",
            exc_info=True,
        )
        return

    try:
        start_time = time.time()
        recognizer = KaldiRecognizer(model, WAV_SAMPLE_RATE)
        result = []

        while True:
            data = process.stdout.read(4000)
            # TODO: stop recognition if no voice detected after first few seconds

            if len(data) == 0:
                break
            if recognizer.AcceptWaveform(data):
                partial_result = json.loads(recognizer.Result())
                result.append(partial_result["text"])

        final = json.loads(recognizer.FinalResult())
        result.append(final["text"])

        end_time = round(time.time() - start_time, 2)

        duration = get_duration(audio)
        logger.info(f"ASR of {round(duration)}s audio using took {end_time} s")

        text = "\n".join(result)

        return text

    except Exception:
        logger.error(
            f"Speech recognition for {audio} failed",
            exc_info=True,
        )
