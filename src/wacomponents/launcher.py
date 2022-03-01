import importlib
import os
import sys


def launch_app_or_service_with_crash_handler(main_module: str, client_type: str):
    """
    Launcher used both for main app or service, depending on parameters, and
    uplaod a crash report if an abormal exception occurs on mobile platform.
    """

    assert client_type in ("SERVICE", "APPLICATION"), client_type
    os.environ["WACLIENT_TYPE"] = client_type

    try:
        module = importlib.import_module(main_module)  # NOW ONLY we trigger conf loading
        module.main()
    except Exception:
        if 'ANDROID_ARGUMENT' not in os.environ:
            raise  # Dev should not be impacted
        print(">> FATAL ERROR IN %s LAUNCHER ON MOBILE PLATFORM, SENDING CRASH REPORT <<" % client_type)
        exc_info = sys.exc_info()
        target_url = "https://api.witnessangel.com/support/crashdumps/"  # HARDCODED - Can't access common config safely here
        from wacomponents.logging.crashdumps import generate_and_send_crashdump  # Should be mostly safe to import
        report = generate_and_send_crashdump(exc_info=exc_info, target_url=target_url)
        print(report)  # Not to stderr for now, since it is hooked by Kivy logging
        raise
