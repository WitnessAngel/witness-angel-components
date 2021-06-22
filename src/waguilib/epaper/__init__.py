
try:
    from ._dfrobot_epaper import DfrobotEpaperStatusDisplay as EpaperStatusDisplay
except ModuleNotFoundError:
    from ._waveshare_epaper import WaveshareEpaperStatusDisplay as EpaperStatusDisplay


__all__ = ["EpaperStatusDisplay"]
