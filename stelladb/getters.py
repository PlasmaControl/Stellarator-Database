import os
import warnings
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from desc.equilibrium import Equilibrium
from .urls import HOME_PAGE


def get_driver():
    """Initialize a webdriver for use in uploading to the database."""

    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        return webdriver.Chrome(options=options)
    except:
        pass

    try:
        options = webdriver.FirefoxOptions()
        options.add_argument("--headless")
        return webdriver.Firefox(options=options)
    except:
        pass

    try:
        options = webdriver.SafariOptions()
        options.add_argument("--headless")
        return webdriver.Safari(options=options)
    except:
        pass

    try:
        options = webdriver.EdgeOptions()
        options.use_chromium = True
        options.add_argument("--headless")
        return webdriver.Edge(options=options)
    except:
        warnings.warn(
            "Failed to initialize any webdriver! Consider installing "
            + "Chrome, Safari, Firefox, or Edge."
        )

    # If no browser was successfully initialized, return None
    return None


def get_driver_for_download(download_directory):
    """Initialize a webdriver configured to save downloads to download_directory."""
    abs_dir = os.path.abspath(download_directory)
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": abs_dir,
                "download.prompt_for_download": False,
            },
        )
        return webdriver.Chrome(options=options)
    except Exception:
        pass
    try:
        options = webdriver.FirefoxOptions()
        options.add_argument("--headless")
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.manager.showWhenStarting", False)
        options.set_preference("browser.download.dir", abs_dir)
        options.set_preference(
            "browser.helperApps.neverAsk.saveToDisk", "application/zip"
        )
        return webdriver.Firefox(options=options)
    except Exception:
        pass
    return get_driver()


def get_file_in_directory(directory, prefix, suffix):
    """Get the first file in the given directory with the given prefix and suffix."""
    # List all files in the given directory
    for file_name in os.listdir(directory):
        # Check if the file name starts with the given prefix
        # and ends with the given suffix
        if file_name.startswith(prefix) and file_name.endswith(suffix):
            return os.path.join(
                directory, file_name
            )  # Return the full path to the file
    return None  # Return None if no matching file is found


def perform_login(driver, username, password):
    """Log in to the database website if not already authenticated.

    Parameters
    ----------
    driver : selenium.webdriver
        The webdriver instance to use.
    username : str
        Username for the database website.
    password : str
        Password for the database website.
    """
    login_url = HOME_PAGE + "/login/"
    driver.get(login_url)

    # If the site redirected away from the login page, already authenticated
    if "login" not in driver.current_url:
        return

    # Fill in and submit the login form
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "username"))
    ).send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    # Wait for redirect away from login page
    WebDriverWait(driver, 10).until(lambda d: "login" not in d.current_url)

    # If still on login page, credentials were rejected
    if "login" in driver.current_url:
        driver.quit()
        raise ValueError("Login failed. Please check your username and password.")
