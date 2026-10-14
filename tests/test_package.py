from importlib.metadata import version


def test_package_is_installed_and_importable():
    import trm_engine

    assert trm_engine.__doc__
    assert version("trm-engine") == "0.1.0"
