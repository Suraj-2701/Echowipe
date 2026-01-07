import subprocess
import sys
import re

MODEL_PATH = r"D:\Echowipe\Model\model_detection.pth"
EVAL_SCRIPT = "D:\Echowipe\Model\eval.py"

def detect_voice(audio_path: str):
    """
    Run model on audio file and return fake/real probabilities.
    """
    command = [
        sys.executable,
        EVAL_SCRIPT,
        "--input_path", audio_path,
        "--model_path", MODEL_PATH
    ]

    result = subprocess.check_output(
        command,
        stderr=subprocess.STDOUT,
        text=True
    )

    fake_match = re.search(r"fake:\s*([0-9.eE+-]+)", result)
    real_match = re.search(r"real:\s*([0-9.eE+-]+)", result)

    if not fake_match or not real_match:
        return None, None, result

    fake = float(fake_match.group(1))
    real = float(real_match.group(1))

    return fake, real, result
