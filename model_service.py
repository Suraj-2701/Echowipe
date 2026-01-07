import subprocess
import sys
import re

MODEL_PATH = r"model_detection.pth"
EVAL_SCRIPT = r"eval.py"

def detect_voice(audio_path):
    command = [
        sys.executable,
        EVAL_SCRIPT,
        "--input_path", audio_path,
        "--model_path", MODEL_PATH
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout
        print("MODEL OUTPUT:\n", output)

        fake = float(re.search(r"fake:\s*([0-9.]+)", output).group(1))
        real = float(re.search(r"real:\s*([0-9.]+)", output).group(1))

        return fake, real, output

    except subprocess.CalledProcessError as e:
        print("❌ MODEL ERROR OUTPUT:\n", e.stdout)
        print("❌ MODEL STDERR:\n", e.stderr)
        raise RuntimeError(e.stderr)
