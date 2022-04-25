import shlex
import subprocess
from io import BytesIO


def get_vid_duration(stream: BytesIO) -> float:
    """Returns the video duration in seconds.
    """
    len_cmd = shlex.split(f'ffprobe -i pipe:0 -show_entries format=duration -v quiet -of csv="p=0"')
    proc = subprocess.Popen(len_cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    stream.seek(0)
    out, err = proc.communicate(input=stream.read())
    proc.wait()
    if err:
        raise ValueError('Unable to get video duration.')
    return float(out)
