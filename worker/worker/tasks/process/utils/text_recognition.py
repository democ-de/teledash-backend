import time
from pathlib import Path
from typing import List, Literal, Union
from urllib import request

import pytesseract
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

# Languages supported by tesseract as ISO 639-2/T codes
# Reference: https://tesseract-ocr.github.io/tessdoc/Data-Files
SUPPORTED_LANGUAGES_TESSERACT = (
    "afr",
    "amh",
    "ara",
    "asm",
    "aze",
    "bel",
    "ben",
    "bod",
    "bos",
    "bul",
    "cat",
    "ceb",
    "ces",
    "chr",
    "cym",
    "dan",
    "deu",
    "dzo",
    "ell",
    "eng",
    "enm",
    "epo",
    "est",
    "eus",
    "fas",
    "fin",
    "fra",
    "frk",
    "frm",
    "gle",
    "glg",
    "grc",
    "guj",
    "hat",
    "heb",
    "hin",
    "hrv",
    "hun",
    "iku",
    "ind",
    "isl",
    "ita",
    "jav",
    "jpn",
    "kan",
    "kat",
    "kaz",
    "khm",
    "kir",
    "kor",
    "kur",
    "lao",
    "lat",
    "lav",
    "lit",
    "mal",
    "mar",
    "mkd",
    "mlt",
    "msa",
    "mya",
    "nep",
    "nld",
    "nor",
    "ori",
    "pan",
    "pol",
    "por",
    "pus",
    "ron",
    "rus",
    "san",
    "sin",
    "slk",
    "slv",
    "spa",
    "sqi",
    "srp",
    "swa",
    "swe",
    "syr",
    "tam",
    "tel",
    "tgk",
    "tgl",
    "tha",
    "tir",
    "tur",
    "uig",
    "ukr",
    "urd",
    "uzb",
    "vie",
)


def clean_text(text: str) -> Union[str, None]:
    # return None if string is whitespace or newline
    if not text.strip():
        return

    lines = text.split("\n")  # convert string to list
    lines = [line for line in lines if line.strip()]  # remove empty lines
    text = "\n".join(lines)  # convert list to string
    return text


def recognize_text(
    image: str,
    languages: List[str],
    model_type: Literal["fast", "best", "custom"] = "fast",
) -> Union[str, None]:
    text = None
    matched_languages = []
    for language in languages:
        # match incoming ISO 639-1 language code with ISO 639-2/T language code
        # (tesseract needs three character language codes)
        # reference: https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
        match = [s for s in SUPPORTED_LANGUAGES_TESSERACT if language == s[:2]]
        matched_languages.append(match[0])

    # language is not supported by text recognition
    if not matched_languages:
        logger.warn(f"Text recognition for language(s) '{*languages,}' not supported")
        return

    model_dir = Path.cwd().joinpath("worker/models/tessdata", model_type)

    # Reference: https://tesseract-ocr.github.io/tessdoc/tess3/ControlParams.html
    custom_config = f"--tessdata-dir '{model_dir}'"
    # TODO: test new "thresholding_method": 1 = LeptonicaOtsu or 2 = Sauvola
    # TODO: test disabling dictionary: set load_system_dawg and load_freq_dawg to false
    # TODO: specify "user-patterns" (e.g. for URLs) and "user-words" for frequent words

    for language in matched_languages:
        model_file_name = language + ".traineddata"
        model_path = model_dir.joinpath(model_file_name)

        # language model file does not exist locally
        if not model_path.is_file():

            if model_type == "custom":
                logger.error(
                    f"Custom model {model_path} does not exist at this location"
                )
                return

            # download language model if type is "fast" or "best"
            remote_model_url = f"https://raw.githubusercontent.com/tesseract-ocr/tessdata_{model_type}/main/{language}.traineddata"  # noqa: E501

            logger.info(f"Downloading language model from '{remote_model_url}'")

            try:
                model_dir.mkdir(parents=True, exist_ok=True)
                request.urlretrieve(remote_model_url, model_path)
            except Exception:
                logger.error(
                    f"Failed downloading language model from '{remote_model_url}'",
                    exc_info=True,
                )

    start_time = time.time()
    model_langs = "+".join(matched_languages)
    try:
        # run text recognition
        text = pytesseract.image_to_string(
            image, lang=model_langs, config=custom_config
        )
    except FileNotFoundError:
        logger.error(f"File {image} not found", exc_info=True)
    except Exception:
        logger.error(
            f"Text recognition for {image} failed",
            exc_info=True,
        )
    end_time = round(time.time() - start_time, 2)
    logger.info(f"OCR using '{model_langs}/{model_type}' took {end_time} s")

    text = clean_text(text) if text else None

    return text
