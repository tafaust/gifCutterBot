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
