from kivy.utils import platform

from ._osc_transport import get_osc_client, get_osc_server  # Must come BEFORE service controller

if platform == "android":
    from ._android_service_controller import ServiceController
else:
    from ._subprocess_service_controller import ServiceController
