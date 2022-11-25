import logging
from pathlib import Path

from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty

from wacomponents.default_settings import EXTERNAL_EXPORTS_DIR
from wacomponents.i18n import tr
from wacomponents.screens.base import WAScreenName, WAScreenBase
from wacomponents.utilities import format_revelation_request_error, LINEBREAK
from wacomponents.widgets.layout_components import build_fallback_information_box
from wacryptolib.cryptainer import CRYPTAINER_DATETIME_FORMAT
from wacryptolib.utilities import get_utc_now_date

Builder.load_file(str(Path(__file__).parent / "cryptainer_decryption_result.kv"))

logger = logging.getLogger(__name__)


class DecryptionStatus:
    SUCCESS = tr._("SUCCESS")
    FAILURE = tr._("FAILURE")


class CryptainerDecryptionResultScreen(WAScreenBase):
    last_decryption_info = ObjectProperty(None, allownone=True)

    def go_to_previous_screen(self):
        self.manager.current = WAScreenName.cryptainer_decryption_process

    def display_revelation_request_error(self):  # FIXME rename

        logger.info("Displaying decryption attempt errors")

        self.ids.decryption_info_list.clear_widgets()

        if self.last_decryption_info is None:
            fallback_info_box = build_fallback_information_box(tr._("No decryption was performed"))
            self.ids.decryption_info_list.add_widget(fallback_info_box)

        else:
            decrypted_container_number, decryption_results = self.last_decryption_info

            layout = self.ids.decryption_info_list
            layout.bind(minimum_height=layout.setter("height"))

            # Selected Cryptainer decryption resume
            cryptainer_decryption_resume_label = tr._(
                "{decrypted_container} out of {selected_container} container(s) " "have been decrypted"
            ).format(decrypted_container=decrypted_container_number, selected_container=len(decryption_results))
            cryptainer_decryption_resume = Factory.MDLabel(
                text=cryptainer_decryption_resume_label, size_hint_y=None, height=60, font_style="H6", halign="center"
            )
            layout.add_widget(cryptainer_decryption_resume)

            for decryption_results_per_cryptainer in decryption_results:

                # Cryptainer decryption status(MDLabel)
                cryptainer_decryption_status = tr._(
                    "Decryption status for {cryptainer_name}: {decryption_status}"
                ).format(
                    cryptainer_name=decryption_results_per_cryptainer["cryptainer_name"],
                    decryption_status=DecryptionStatus.SUCCESS
                    if decryption_results_per_cryptainer["decryption_status"] == True
                    else DecryptionStatus.FAILURE,
                )

                cryptainer_decryption_status_label = Factory.DecryptionStatusLabel(
                    text=cryptainer_decryption_status, size_hint_y=None, height=40
                )
                layout.add_widget(cryptainer_decryption_status_label)

                # Cryptainer decryption error (WASelectable)
                if decryption_results_per_cryptainer["decryption_error"]:
                    error_report_text = ""
                    for error in decryption_results_per_cryptainer["decryption_error"]:
                        error_label = format_revelation_request_error(**error)
                        error_report_text += error_label + "\n\n"

                    datetime = get_utc_now_date()
                    from_ts = datetime.strftime(CRYPTAINER_DATETIME_FORMAT)
                    revelation_report_file = EXTERNAL_EXPORTS_DIR.joinpath(
                        str(decryption_results_per_cryptainer["cryptainer_name"])
                        + "_revelation_report"
                        + "_"
                        + from_ts
                        + ".txt"
                    )
                    dump_to_text_file(revelation_report_file, error_report_text)

                else:
                    error_report_text = tr._("No errors/warnings when decrypting the container")
                error_box = Factory.WASelectableLabel(
                    text=error_report_text + LINEBREAK, size_hint_y=None, full_height=False
                )
                layout.add_widget(error_box)


def dump_to_text_file(filepath, data):  # TODO To move in wacryptolib utilities
    with open(filepath, "w", encoding="utf8") as text_file:
        text_file.write(data)


def load_from_text_file(filepath):  # TODO To move in wacryptolib utilities
    with open(filepath, "r", encoding="utf8") as text_file:
        text = text_file.read()
    return text
