from pathlib import Path

from kivy.lang import Builder
from kivy.uix.screenmanager import Screen


Builder.load_file(str(Path(__file__).parent / 'authentication_device_store.kv'))


class AuthenticationDeviceStoreScreen(Screen):
    pass
