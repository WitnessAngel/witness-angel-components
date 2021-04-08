
def setup_generic_app(package):
    """Setup for both gui and console apps."""
    import os
    if os.getenv("WACLIENT_ENABLE_TYPEGUARD"):
        from typeguard.importhook import install_import_hook
        install_import_hook(package)
