# This file is part of Witness Angel Components
# SPDX-FileCopyrightText: Copyright Prolifik SARL
# SPDX-License-Identifier: GPL-2.0-or-later

EPAPER_TYPES = ["waveshare_2.7_epaper", "waveshare_2.13_epaper_v3", "dfrobot_2.13_epaper_v2"]


def get_epaper_instance(epaper_type):
    if epaper_type == EPAPER_TYPES[0]:
        from ._waveshare_epaper import WaveshareEpaperStatusDisplay2in7

        return WaveshareEpaperStatusDisplay2in7()
    elif epaper_type == EPAPER_TYPES[1]:
        from ._waveshare_epaper import WaveshareEpaperStatusDisplay2in13V3

        return WaveshareEpaperStatusDisplay2in13V3()
    elif epaper_type == EPAPER_TYPES[2]:
        from ._dfrobot_epaper import DfrobotEpaperStatusDisplay2in13v2

        return DfrobotEpaperStatusDisplay2in13v2()
    else:
        raise ValueError("Unknown e-paper type %r" % epaper_type)
