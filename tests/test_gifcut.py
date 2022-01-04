from tempfile import NamedTemporaryFile

import pytest as pytest
from PIL import Image

from src.gif_utilities import cut_gif as cut_gif_func
from src.gif_utilities import get_total_duration_milliseconds


@pytest.fixture(params=[(0, 250), (350, 450), (1250, 934823)])
def yield_params(request):
    params = {
        'img': Image.open('tests/cat.gif'),
        'start': request.param[0],
        'end': request.param[1]
    }
    yield params


def test_cutgif_length(yield_params):
    cut_gif, target_duration = cut_gif_func(**yield_params)
    with NamedTemporaryFile(mode='w+b', suffix='.gif') as gif:
        cut_gif[0].save(
            gif,
            save_all=True,
            append_images=cut_gif[1:],
            optimize=False,
            duration=target_duration,
            loop=0
        )
        # test that there is no more deviation than 5ms per frame
        cut_gif_duration = target_duration * len(cut_gif)
        assert 0 <= abs(cut_gif_duration - get_total_duration_milliseconds(image=Image.open(gif))) <= (5 * len(cut_gif))
