
EPAPER_TYPES = ["waveshare_2.7_epaper", "dfrobot_2.13_epaper"]

def get_epaper_instance(epaper_type):
    if epaper_type == EPAPER_TYPES[0]:
        from ._waveshare_epaper import WaveshareEpaperStatusDisplay
        return WaveshareEpaperStatusDisplay()
    elif epaper_type == EPAPER_TYPES[1]:
        from ._dfrobot_epaper import DfrobotEpaperStatusDisplay
        return DfrobotEpaperStatusDisplay()
    else:
        raise ValueError("Unknown e-paper type %r" % epaper_type)
