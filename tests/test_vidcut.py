import io
import itertools
import os
import shutil

import pytest


# from src.video_utilities import cut_video as cut_video_func


# 934823
# 'test.mp4',
@pytest.fixture(params=itertools.product([0, 350, 1250], [250, 450, 3000], ['test.mov', 'test.webm']))
def yield_params(request):
    f = open(f'test_data/{request.param[2]}', 'r+b')
    # f.seek(0)
    my_bytes_io = io.BytesIO()
    shutil.copyfileobj(f, my_bytes_io)
    # my_bytes_io.seek(0)
    params = {
        'stream': my_bytes_io,
        'start': request.param[0],
        'end': request.param[1],
        'ext': os.path.splitext(request.param[2])[-1][1:],  # [:1] to skip the initial dot
    }
    yield params
    # f.close()
    # my_bytes_io.close()


def test_cutvideo_length(yield_params):
    assert True  # todo video cut tests
    # cut_gif, target_duration = cut_video_func(**yield_params)
    # with NamedTemporaryFile(mode='w+b', suffix='.gif') as gif:
    #     cut_gif[0].save(
    #         gif,
    #         save_all=True,
    #         append_images=cut_gif[1:],
    #         optimize=False,
    #         duration=target_duration,
    #         loop=0
    #     )
    #     # test that there is no more deviation than 5ms per frame
    #     cut_gif_duration = target_duration * len(cut_gif)
    #     assert 0 <= abs(cut_gif_duration - get_gif_duration(image=Image.open(gif))) <= (5 * len(cut_gif))
