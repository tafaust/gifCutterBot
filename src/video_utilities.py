import shlex
import subprocess as sp
from io import BytesIO
from tempfile import NamedTemporaryFile


# def cut_video(
#         stream: BytesIO, start: int, end: Optional[int] = None, watermark=noop_image, ext: Optional[str] = None,
#         duration: Optional[int] = None
# ) -> Tuple[List[Image.Image], float]:
#     if duration is None:
#         duration = get_vid_duration(stream)
#     start = max(start, 0)
#     # end = min(end or math.inf, vid_duration)
#
#     start, end = fix_start_end_swap(start=start, end=end)
#
#     fps = get_frame_rate(stream)
#
#     target_duration = end - start
#     # sanity check
#     # assert 0 < target_duration < vid_duration and end <= vid_duration
#     ffmpeg = 'ffmpeg'
#     # https://stackoverflow.com/questions/18444194/cutting-the-videos-based-on-start-and-end-time-using-ffmpeg
#     # #comment51400781_18449609
#     cut_cmd = shlex.split(
#             f'{ffmpeg} -ss {start / 1000} -t {(end - start) / 1000} -i pipe:0 -filter_complex "fps={fps},'
#             f'split[a][b];[a]palettegen[p];[b][p]paletteuse" -y -loop 0 -f gif pipe:1'
#     )
#     # https://stackoverflow.com/questions/20321116/can-i-pipe-a-io-bytesio-stream-to-subprocess-popen-in-python
#     # #comment30326992_20321129
#     proc = sp.Popen(cut_cmd, stdout=sp.PIPE, stdin=sp.PIPE, stderr=sp.PIPE)
#     stream.seek(0)
#     out, err = proc.communicate(input=stream.read())
#     proc.wait()
#     response = err.decode()
#
#     if 'partial file' in response:
#         with NamedTemporaryFile('wb', suffix=f'.{ext}') as f:
#             stream.seek(0)
#             f.write(stream.read())
#             cut_cmd[6] = f.name
#             proc = sp.Popen(cut_cmd, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
#             out, _ = proc.communicate()
#             proc.wait()
#
#     gif = Image.open(BytesIO(out))
#
#     frames_out = []
#     for frame in ImageSequence.Iterator(gif):
#         frame = frame.convert('RGB')
#         frames_out.append(watermark(frame))
#     assert len(frames_out) > 0
#     return frames_out, target_duration / len(frames_out)


def get_vid_duration(stream: BytesIO):
    # len_cmd = shlex.split('ffprobe -i - -show_entries format=duration -v quiet -of csv="p=0"')
    # # proc = sp.Popen(len_cmd, stdout=sp.PIPE, stdin=sp.PIPE)
    # stream.seek(0)
    # proc = sp.Popen(len_cmd, stdout=sp.PIPE, stdin=sp.PIPE)
    # out = proc.communicate(input=stream.read())[0]
    # proc.wait()
    # #vid_duration = float(sp.run(len_cmd, input=stream.read(), check=True, capture_output=True, text=True).stdout)
    # * 1000
    # # proc.wait()
    with NamedTemporaryFile(mode='wb') as vid:
        vid.write(stream.getvalue())
        len_cmd = shlex.split(f'ffprobe -show_entries format=duration -v quiet -of csv="p=0" -i {vid.name}')
        vid_duration = float(
                sp.run(len_cmd, input=None, shell=True, capture_output=True, check=True, text=True).stdout
        ) * 1000
    return vid_duration


def get_frame_rate(stream: BytesIO):
    # out = sp.check_output(
    #     [ffprobe, '/dev/stdin', "-v", "0", "-select_streams", "v", "-print_format", "flat", "-show_entries",
    #      "stream=r_frame_rate"],
    #     input=stream.read(), text=False)
    # sp.check_output(cmd, input=stream.read()).decode('utf-8')
    ffprobe = 'ffprobe'
    cmd = shlex.split(f'{ffprobe} -i pipe:0 -v 0 -select_streams v -of flat -show_entries stream=r_frame_rate')
    proc = sp.Popen(cmd, stdout=sp.PIPE, stdin=sp.PIPE, stderr=sp.PIPE)
    stream.seek(0)
    out, _ = proc.communicate(input=stream.read())
    proc.wait()
    rate = out.decode('utf-8').split('=')[1].strip()[1:-1].split('/')
    if len(rate) == 1:
        return float(rate[0])
    if len(rate) == 2:
        return float(rate[0]) / float(rate[1])
    return -1
