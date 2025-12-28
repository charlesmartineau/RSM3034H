import logging
from typing import List, Union

import matplotlib.pyplot as plt


def configure_pyplot(
    usetex: bool = True,
    font_family: str = "serif",
    font_serif: Union[str, List[str]] = "Computer Modern Roman",
    font_sans_serif: Union[str, List[str]] = "Helvetica",
):
    logging.info("Setting up matplotlib configuration")

    plt.rcParams.update(
        {
            "text.usetex": usetex,
            "font.family": font_family,
            "font.sans-serif": font_serif,
            "font.serif": font_sans_serif,
        }
    )
