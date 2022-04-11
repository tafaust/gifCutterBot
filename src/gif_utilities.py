from PIL.Image import Image


# credits: https://www.codespeedy.com/find-the-duration-of-gif-image-in-python/
def get_gif_duration(image: Image) -> float:
    image.seek(0)  # move to the start of the gif, frame 0
    total_duration_milliseconds = 0
    # loop through the frames until EndOfFileError
    while True:
        try:
            frame_duration_milliseconds = image.info['duration']
            total_duration_milliseconds += frame_duration_milliseconds
            # now move to the next frame of the gif
            image.seek(image.tell() + 1)  # image.tell() = current frame
        except EOFError:
            return total_duration_milliseconds / 1000


# def cut_gif(img: Image, start: int, end: int = None, watermark=noop_image):
#     gif = unpack_gif(img)
#     gif_duration = get_gif_duration(img)
#     start = max(start, 0)
#     end = min(end or math.inf, gif_duration)
#     target_duration = end - start
#     # sanity check
#     assert 0 < target_duration < gif_duration and end <= gif_duration
#     print(f'Cutting GIF from {start} to {end}')  # todo log debug
#     frames_out = []
#     append = False
#     cum_duration = 0
#     for frame in gif:
#         if not append and cum_duration >= start:
#             # start to append when the cumulative duration is beyond the start
#             append = True
#         if append and cum_duration <= end:
#             # append to out_frames as long as the cumulative duration is not beyond the end marker
#             frames_out.append(watermark(frame))
#         else:
#             append = False
#         cum_duration += frame.info['duration']
#     assert len(frames_out) > 0
#     return frames_out, target_duration/len(frames_out)


# def unpack_gif(image: Image) -> List[Image]:
#     frames = []
#     disposal = []
#     for gifFrame in ImageSequence.Iterator(image):
#         disposal.append(gifFrame.disposal_method)
#         frames.append(gifFrame.convert('P'))
#     output = []
#     last_frame = None
#     for i, loadedFrame in enumerate(frames):
#         this_frame = loadedFrame
#         if disposal[i] == 2:
#             if i != 0:
#                 last_frame.paste(this_frame, mask=this_frame.convert('RGBA'))
#                 output.append(last_frame)
#             else:
#                 output.append(this_frame)
#         elif disposal[i] == 1 or disposal[i] == 0:
#             output.append(this_frame)
#         else:
#             raise ValueError('Disposal Methods other than '
#                              '2: Restore to Background, '
#                              '1: Do Not Dispose, and '
#                              '0: No Disposal are supported at this time')
#         last_frame = loadedFrame
#     return output
