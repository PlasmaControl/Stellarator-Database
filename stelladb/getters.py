import warnings
from selenium import webdriver
from desc.equilibrium import Equilibrium


def get_hash_desc(eq, data_desc_runs, config_hash):
    """Get a unique identifier for a DESC equilibrium."""
    if not isinstance(eq, Equilibrium):
        warnings.warn(f"Expected type Equilibrium for eq, got type {type(eq)}")

    unique_id = (
        f"{eq.L}{eq.M}{eq.N}{eq.NFP}{config_hash}{data_desc_runs['current_profile']}"
        + f"{data_desc_runs['iota_profile']}{data_desc_runs['pressure_profile']}{eq.params_dict}"
    )

    return hash(unique_id)


def get_hash_config(data_configurations):
    """Get a unique identifier for configuration."""

    unique_id = ""
    for key in data_configurations.keys():
        if key not in [
            "config_name",
            "name",
            "provenance",
            "description",
            "device_name",
            "date_created",
            "date_updated",
            "user_created",
            "user_updated",
        ]:
            unique_id += f"{data_configurations[key]}"

    return hash(unique_id)


def get_hash_device(devices_and_concepts):
    """Get a unique identifier for configuration."""

    unique_id = ""
    for key in devices_and_concepts.keys():
        if key not in [
            "date_created",
            "date_updated",
            "user_created",
            "user_updated",
        ]:
            unique_id += f"{devices_and_concepts[key]}"

    return hash(unique_id)


def get_driver():  # pragma: no cover
    """Initialize a webdriver for use in uploading to the database."""

    try:
        options = webdriver.ChromeOptions()
        options.headless = True
        return webdriver.Chrome(options=options)
    except:  # noqa: E722
        pass

    try:
        options = webdriver.FirefoxOptions()
        options.headless = True
        return webdriver.Firefox(options=options)
    except:  # noqa: E722
        pass

    try:
        return webdriver.Safari()
    except:  # noqa: E722
        pass

    try:
        options = webdriver.EdgeOptions()
        options.use_chromium = True
        options.add_argument("headless")
        return webdriver.Edge(options=options)
    except:  # noqa: E722
        warnings.warn(
            "Failed to initialize any webdriver! Consider installing "
            + "Chrome, Safari, Firefox, or Edge."
        )

    # If no browser was successfully initialized, return None
    return None
