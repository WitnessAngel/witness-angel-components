from pathlib import Path

from kivy.lang import Builder
from kivy.uix.screenmanager import Screen


Builder.load_file(str(Path(__file__).parent / 'container_store.kv'))


class ContainerStoreScreen(Screen):
    pass
