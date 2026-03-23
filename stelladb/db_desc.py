import os
import shutil
import numpy as np
import csv
import zipfile
import time
from datetime import date

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.common.exceptions import TimeoutException

from desc.equilibrium import Equilibrium, EquilibriaFamily
from desc.grid import LinearGrid
from desc.vmec_utils import ptolemy_identity_rev, zernike_to_fourier
from desc.io.hdf5_io import hdf5Reader
from desc.io import load
from desc.profiles import *

from .getters import (
    get_driver,
    get_driver_for_download,
    get_file_in_directory,
    perform_login,
)
from .device import device_or_concept_to_csv
from .urls import HOME_PAGE

# ---------------------------------------------------------------------------
# Private File/Data Preparation Helpers
# ---------------------------------------------------------------------------


def _load_equilibrium(eq, config_name):
    """Resolve eq to an Equilibrium (or str path) and return (eq, filename)."""
    if os.path.exists(f"{config_name}_auto_save.h5"):
        print(f"Removing {config_name}_auto_save.h5")
        os.remove(f"{config_name}_auto_save.h5")

    if isinstance(eq, str):
        if os.path.exists(eq + ".h5"):
            return eq + ".h5", eq
        raise FileNotFoundError(f"{eq}.h5 does not exist.")
    elif isinstance(eq, Equilibrium):
        return eq, config_name
    elif isinstance(eq, EquilibriaFamily):
        return eq[-1], config_name
    raise TypeError(
        "Expected type str, Equilibrium or EquilibriumFamily "
        + f"for eq, got type {type(eq)}"
    )


def _prepare_input_file(eq, filename, inputfilename, inputfile):
    """Find or auto-generate the DESC input file."""
    auto_input = False
    if inputfilename is None and inputfile:
        if os.path.exists(filename + "_input.txt"):
            print(
                f"Found an input file with name {filename}_input.txt and using that ..."
            )
            inputfilename = filename + "_input.txt"
        else:
            from desc.input_reader import InputReader

            inputfilename = "auto_generated_" + filename + "_input.txt"
            auto_input = True
            print("Auto-generating input file...")
            writer = InputReader()
            if isinstance(eq, str):
                writer.desc_output_to_input(inputfilename, eq)
            else:
                eq.save(f"{filename}_auto_save.h5")
                writer.desc_output_to_input(inputfilename, f"{filename}_auto_save.h5")
    elif inputfilename is not None and os.path.exists(inputfilename) and not inputfile:
        inputfile = True
    return inputfilename, auto_input, inputfile


def _create_zip(eq, filename, inputfilename, inputfile):
    """Zip the equilibrium .h5 file and optional input file."""
    print("Zipping files...")
    zip_filename = filename + ".zip"
    with zipfile.ZipFile(zip_filename, "w") as zipf:
        if os.path.exists(filename + ".h5"):
            zipf.write(filename + ".h5")
        else:
            print("Saving equilibrium to .h5 file...")
            auto_save_name = f"{filename}_auto_save.h5"
            if not os.path.exists(auto_save_name):
                eq.save(auto_save_name)
            zipf.write(auto_save_name)
        if inputfilename is not None and inputfile and os.path.exists(inputfilename):
            zipf.write(inputfilename)
    return zip_filename


def _generate_desc_plots(eq, filename, config_name):
    """Generate and save surface, Boozer, and 3D plots."""
    from desc.plotting import plot_surfaces, plot_boozer_surface, plot_3d
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go

    if isinstance(eq, str):
        eq = load(eq)
        if isinstance(eq, EquilibriaFamily):
            eq = eq[-1]

    print("Plotting/saving surface, Boozer and 3D plots...")
    surface_filename = filename + "_surface.webp"
    boozer_filename = filename + "_boozer.webp"
    d3_filename = filename + "_3d.html"

    plot_surfaces(eq=eq, label=config_name)
    plt.savefig(surface_filename, dpi=90)
    plot_boozer_surface(eq)
    plt.savefig(boozer_filename, dpi=90)
    plt.close()

    fig = go.Figure()
    grid3d = LinearGrid(
        rho=1.0,
        theta=np.linspace(0, 2 * np.pi, 30),
        zeta=np.linspace(0, 2 * np.pi, max(140, int(20 * eq.NFP))),
    )
    plot_3d(eq, "|B|", fig=fig, grid=grid3d, cmap="plasma")
    fig.update_layout(
        width=1200,
        height=800,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgb(0, 0, 0)",
    )
    fig.write_html(
        d3_filename, include_plotlyjs=False, full_html=False, div_id="plot3d"
    )


def _append_to_csv(filename, data):
    """Append a dict as one row to a CSV file, writing the header if new."""
    file_exists = os.path.isfile(filename)
    fieldnames = sorted(data.keys())
    try:
        with open(filename, "a", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(data)
    except OSError as e:
        print(f"I/O error writing to {filename}: {e}")


def _clean_stale_csvs(verbose=True):
    """Removes standard CSVs if they already exist in the directory."""
    files_to_check = ["desc_runs.csv", "configurations.csv", "devices_and_concepts.csv"]
    for f in files_to_check:
        if os.path.exists(f):
            os.remove(f)
            if verbose:
                print(f"Previous {f} has been deleted.")


def _prepare_all_artifacts(
    eq,
    config_name,
    description,
    provenance,
    deviceid,
    isDeviceNew,
    inputfile,
    inputfilename,
    config_class,
    initialization_method,
    deviceDescription,
    uploadPlots,
):
    """Handles all local file generation, zipping, and plotting before upload or storage."""
    eq, filename = _load_equilibrium(eq, config_name)
    inputfilename, auto_input, inputfile = _prepare_input_file(
        eq, filename, inputfilename, inputfile
    )
    _create_zip(eq, filename, inputfilename, inputfile)

    _clean_stale_csvs()

    print("Creating desc_runs.csv and configurations.csv...")
    desc_to_csv(
        eq,
        name=config_name,
        provenance=provenance,
        description=description,
        inputfilename=inputfilename,
        deviceid=deviceid,
        config_class=config_class,
        initialization_method=initialization_method,
    )

    if isDeviceNew:
        print("Creating devices_and_concepts.csv...")
        device_or_concept_to_csv(name=config_name, description=deviceDescription)

    if uploadPlots:
        _generate_desc_plots(eq, filename, config_name)

    return filename, auto_input


def _upload_desc_files(driver, filename, isDeviceNew, uploadPlots):
    """Fill the upload form with all prepared files and return the server response."""

    def send(element_id, filepath):
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, element_id))
        ).send_keys(os.path.abspath(filepath))

    send("zipToUpload", f"{filename}.zip")
    send("descToUpload", "desc_runs.csv")
    send("configToUpload", "configurations.csv")

    if uploadPlots:
        send("surfaceToUpload", f"{filename}_surface.webp")
        send("boozerToUpload", f"{filename}_boozer.webp")
        send("plot3dToUpload", f"{filename}_3d.html")

    if isDeviceNew:
        send("deviceToUpload", "devices_and_concepts.csv")

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "confirmDesc"))
    ).click()
    WebDriverWait(driver, 30).until(
        lambda d: d.find_elements(By.CSS_SELECTOR, ".success-div, .error-div")
    )
    return driver.find_element(By.CSS_SELECTOR, ".success-div, .error-div").text


def _cleanup_local_files(filename, auto_input, uploadPlots, keep_artifacts):
    """Handles deletion of locally generated files if `keep_artifacts` is False."""
    if os.path.exists(f"{filename}_auto_save.h5"):
        os.remove(f"{filename}_auto_save.h5")

    if not keep_artifacts:
        if os.path.exists(f"{filename}.zip"):
            os.remove(f"{filename}.zip")

        _clean_stale_csvs(verbose=False)

        if auto_input:
            auto_input_file = f"auto_generated_{filename}_input.txt"
            if os.path.exists(auto_input_file):
                os.remove(auto_input_file)

        if uploadPlots:
            for f in [
                f"{filename}_surface.webp",
                f"{filename}_boozer.webp",
                f"{filename}_3d.html",
            ]:
                if os.path.exists(f):
                    os.remove(f)


def _format_array(arr):
    """Format an array of floats as a comma-separated string in scientific notation."""
    return ", ".join(f"{v:.2e}" for v in arr)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def desc_to_csv(
    eq,
    name=None,
    provenance=None,
    description=None,
    inputfilename=None,
    initialization_method="surface",
    **kwargs,
):
    """Save DESC equilibrium data to CSV files for database upload.

    Computes scalar metrics, profile arrays, surface geometry, and stability
    quantities from the equilibrium and writes them to ``desc_runs.csv`` and
    ``configurations.csv`` in the current working directory.

    Parameters
    ----------
    eq : str or Equilibrium or EquilibriaFamily
        DESC equilibrium to save. If str, treated as a path to an ``.h5`` file
        (without extension). If EquilibriaFamily, the last element is used.
    name : str, optional
        Configuration name stored in the ``configurations`` table.
    provenance : str, optional
        Free-text provenance note (e.g. paper reference or run description).
    description : str, optional
        Free-text description of the equilibrium.
    inputfilename : str, optional
        Path to the DESC input file used to produce this equilibrium.
    initialization_method : str, optional
        Method used to initialize the equilibrium (default ``"surface"``).
    **kwargs
        Extra fields passed directly into the CSV rows, e.g. ``deviceid``,
        ``config_class``, ``publicationid``, ``date_created``.
    """
    descruns = {"outputfile": f"{name}_auto_save.h5"}

    if isinstance(eq, str) and os.path.exists(eq):
        descruns["outputfile"] = os.path.basename(eq)
        reader = hdf5Reader(eq)
        version = reader.read_dict().get("__version__", "unknown")
        eq = load(eq)
    else:
        import desc

        version = desc.__version__

    if type(eq).__name__ == "EquilibriaFamily":
        eq = eq[-1]

    if type(eq).__name__ != "Equilibrium":
        raise TypeError(
            f"Expected str, Equilibrium or EquilibriaFamily for eq, got {type(eq)}"
        )

    nfp = eq.NFP
    rho = np.linspace(0, 1.0, 10, endpoint=True)
    rho[0] = 1e-12
    rho_grid = LinearGrid(rho=rho, M=eq.M_grid, N=eq.N_grid, NFP=nfp)

    eq_data = eq.compute(
        [
            "R0/a",
            "a",
            "R0",
            "V",
            "<|B|>_vol",
            "<beta>_vol",
            "R",
            "Z",
            "a_major/a_minor",
            "|F|_normalized",
        ]
    )
    data_rho = eq.compute(["current", "iota"], grid=rho_grid)
    p_iota = rho_grid.compress(data_rho["iota"])
    p_curr = rho_grid.compress(data_rho["current"])

    today = kwargs.get("date_created", date.today())

    descruns.update(
        {
            "provenance": provenance,
            "description": description,
            "version": version,
            "inputfilename": inputfilename,
            "initialization_method": initialization_method,
            "l_rad": int(eq.L),
            "l_grid": int(eq.L_grid),
            "m_pol": int(eq.M),
            "m_grid": int(eq.M_grid),
            "n_tor": int(eq.N),
            "n_grid": int(eq.N_grid),
            "profile_rho": _format_array(rho),
            "pressure_profile": _format_array(eq.pressure(rho)),
            "pressure_max": round(float(np.max(eq.pressure(rho))), 3),
            "pressure_min": round(float(np.min(eq.pressure(rho))), 3),
            "iota_profile": _format_array(p_iota),
            "iota_max": round(float(np.max(np.abs(p_iota))), 3),
            "iota_min": round(float(np.min(np.abs(p_iota))), 3),
            "current_profile": _format_array(p_curr),
            "spectral_indexing": eq.spectral_indexing,
            "sym": bool(eq.sym),
            "date_created": today,
            "publicationid": kwargs.get("publicationid"),
            "max_normalized_F_error": round(
                float(np.max(np.abs(eq_data["|F|_normalized"]))), 3
            ),
        }
    )

    descruns["current_specification"] = "iota" if eq.iota else "net enclosed current"

    rho_grid_mercier = LinearGrid(
        rho=np.linspace(0.1, 1.0, 10, endpoint=True), M=0, N=0, NFP=nfp
    )
    d_merc = eq.compute("D_Mercier", grid=rho_grid_mercier)["D_Mercier"]
    descruns.update(
        {
            "D_Mercier_max": round(float(np.max(d_merc)), 3),
            "D_Mercier_min": round(float(np.min(d_merc)), 3),
            "D_Mercier": _format_array(d_merc),
            "vacuum": bool(
                np.allclose(eq.pressure.params, 0)
                and np.allclose(data_rho["current"], 0)
            ),
        }
    )

    config = {
        "name": name,
        "NFP": int(nfp),
        "stell_sym": bool(eq.sym),
        "deviceid": kwargs.get("deviceid"),
        "provenance": provenance,
        "description": description,
        "toroidal_flux": round(float(eq.Psi), 3),
        "aspect_ratio": round(float(eq_data["R0/a"]), 3),
        "minor_radius": round(float(eq_data["a"]), 3),
        "major_radius": round(float(eq_data["R0"]), 3),
        "volume": round(float(eq_data["V"]), 3),
        "volume_averaged_B": round(float(eq_data["<|B|>_vol"]), 3),
        "volume_averaged_beta": round(float(eq_data["<beta>_vol"]), 3),
        "total_toroidal_current": round(float(f"{np.max(np.abs(p_curr)):1.2e}"), 3),
        "R_excursion": round(
            float(f'{np.max(eq_data["R"]) - np.min(eq_data["R"]):1.4e}'), 3
        ),
        "Z_excursion": round(
            float(f'{np.max(eq_data["Z"]) - np.min(eq_data["Z"]):1.4e}'), 3
        ),
        "average_elongation": round(
            float(f'{np.mean(eq_data["a_major/a_minor"]):1.4e}'), 3
        ),
        "classification": "AS" if eq.N == 0 else kwargs.get("config_class"),
        "current_specification": descruns.get("current_specification"),
        "pressure_profile": descruns["pressure_profile"],
        "iota_profile": descruns["iota_profile"],
        "current_profile": descruns["current_profile"],
        "date_created": today,
    }

    def get_surface_geometry(lmn, basis):
        val = np.ones_like(lmn)
        val[basis.modes[:, 1] < 0] *= -1
        m, n, x_mn = zernike_to_fourier(val * lmn, basis=basis, rho=np.array([1.0]))
        return ptolemy_identity_rev(m, n, x_mn)

    xm, xn, s_R, c_R = get_surface_geometry(eq.R_lmn, eq.R_basis)
    _, _, s_Z, c_Z = get_surface_geometry(eq.Z_lmn, eq.Z_basis)

    config.update(
        {
            "m": xm,
            "n": xn,
            "RBC": c_R[0, :],
            "RBS": np.zeros(c_R.shape[1]) if eq.sym else s_R[0, :],
            "ZBS": s_Z[0, :],
            "ZBC": np.zeros(s_Z.shape[1]) if eq.sym else c_Z[0, :],
        }
    )

    _append_to_csv(
        "desc_runs.csv", {k: v for k, v in descruns.items() if v is not None}
    )
    _append_to_csv(
        "configurations.csv",
        {k: v for k, v in config.items() if v is not None},
    )
    return None


def save_to_db_desc(
    eq,
    config_name,
    username,
    password,
    uploadPlots=False,
    description=None,
    provenance=None,
    deviceid=None,
    isDeviceNew=False,
    inputfile=False,
    inputfilename=None,
    config_class=None,
    initialization_method="surface",
    deviceDescription=None,
    keep_artifacts=False,
):
    """Upload a DESC equilibrium to the stellarator database.

    Prepares all required files (zip archive, CSV metadata, optional plots),
    logs in to the website, and submits the upload form automatically.
    Local files are cleaned up afterwards unless ``keep_artifacts=True``.

    Parameters
    ----------
    eq : str or Equilibrium or EquilibriaFamily
        DESC equilibrium to upload. If str, treated as a path to an ``.h5``
        file (without extension). If EquilibriaFamily, the last element is used.
    config_name : str
        Name used for the configuration entry and to derive all output filenames.
    username : str
        Username for the database website.
    password : str
        Password for the database website.
    uploadPlots : bool, optional
        If True, generate and upload surface, Boozer, and 3-D plots (default False).
    description : str, optional
        Free-text description stored with the run and configuration.
    provenance : str, optional
        Free-text provenance note (e.g. paper reference or run description).
    deviceid : int, optional
        Database ID of the device this configuration belongs to.
    isDeviceNew : bool, optional
        If True, also create and upload a new device entry using ``config_name``
        and ``deviceDescription`` (default False).
    inputfile : bool, optional
        If True, include the DESC input file in the upload. A file named
        ``{config_name}_input.txt`` is used if it exists; otherwise one is
        auto-generated (default False).
    inputfilename : str, optional
        Explicit path to the DESC input file. Implies ``inputfile=True`` when
        provided and the file exists.
    config_class : str, optional
        Configuration class label (e.g. ``"QA"``, ``"QH"``). Ignored for
        axisymmetric equilibria, which are always classified as ``"AS"``.
    initialization_method : str, optional
        Initialization method stored in the run metadata (default ``"surface"``).
    deviceDescription : str, optional
        Description for the new device entry. Only used when ``isDeviceNew=True``.
    keep_artifacts : bool, optional
        If True, keep all locally generated files after upload (default False).
    """

    filename, auto_input = _prepare_all_artifacts(
        eq,
        config_name,
        description,
        provenance,
        deviceid,
        isDeviceNew,
        inputfile,
        inputfilename,
        config_class,
        initialization_method,
        deviceDescription,
        uploadPlots,
    )

    print("Uploading to database...\n")
    driver = get_driver()
    perform_login(driver, username, password)
    driver.get(f"{HOME_PAGE}/upload/")
    try:
        message = _upload_desc_files(driver, filename, isDeviceNew, uploadPlots)
        print(message)
    except Exception as e:
        print(f"An error occurred during upload: {e}")
    finally:
        driver.quit()
        _cleanup_local_files(filename, auto_input, uploadPlots, keep_artifacts)


def generate_files_desc(
    eq,
    config_name,
    uploadPlots=False,
    description=None,
    provenance=None,
    deviceid=None,
    isDeviceNew=False,
    inputfile=False,
    inputfilename=None,
    config_class=None,
    initialization_method="surface",
    deviceDescription=None,
):
    """Generate and collect all database upload files into a local folder.

    Performs the same file preparation as ``save_to_db_desc`` but instead of
    uploading, moves everything into a folder named ``{config_name}/`` in the
    current working directory. The folder can later be uploaded with
    ``upload_files_desc``.

    Parameters
    ----------
    eq : str or Equilibrium or EquilibriaFamily
        DESC equilibrium to process. If str, treated as a path to an ``.h5``
        file (without extension). If EquilibriaFamily, the last element is used.
    config_name : str
        Name used for the configuration entry, output folder, and all filenames.
    uploadPlots : bool, optional
        If True, generate surface, Boozer, and 3-D plot files (default False).
    description : str, optional
        Free-text description stored with the run and configuration.
    provenance : str, optional
        Free-text provenance note (e.g. paper reference or run description).
    deviceid : int, optional
        Database ID of the device this configuration belongs to.
    isDeviceNew : bool, optional
        If True, also create a device CSV for a new device entry (default False).
    inputfile : bool, optional
        If True, include the DESC input file. A file named
        ``{config_name}_input.txt`` is used if it exists; otherwise one is
        auto-generated (default False).
    inputfilename : str, optional
        Explicit path to the DESC input file. Implies ``inputfile=True`` when
        provided and the file exists.
    config_class : str, optional
        Configuration class label (e.g. ``"QA"``, ``"QH"``). Ignored for
        axisymmetric equilibria, which are always classified as ``"AS"``.
    initialization_method : str, optional
        Initialization method stored in the run metadata (default ``"surface"``).
    deviceDescription : str, optional
        Description for the new device entry. Only used when ``isDeviceNew=True``.
    """
    if not all([eq, config_name]):
        raise ValueError("Please provide a valid input for eq and config_name.")

    filename, auto_input = _prepare_all_artifacts(
        eq,
        config_name,
        description,
        provenance,
        deviceid,
        isDeviceNew,
        inputfile,
        inputfilename,
        config_class,
        initialization_method,
        deviceDescription,
        uploadPlots,
    )

    folder_name = filename
    print(f"Creating folder {folder_name}...")
    os.makedirs(folder_name, exist_ok=True)
    print("Moving files to the folder...")

    for f in [f"{filename}.zip", "desc_runs.csv", "configurations.csv"]:
        shutil.move(f, os.path.join(folder_name, f))

    if isDeviceNew and os.path.exists("devices_and_concepts.csv"):
        shutil.move(
            "devices_and_concepts.csv",
            os.path.join(folder_name, "devices_and_concepts.csv"),
        )
    if auto_input:
        auto_input_file = f"auto_generated_{filename}_input.txt"
        if os.path.exists(auto_input_file):
            shutil.move(auto_input_file, os.path.join(folder_name, auto_input_file))
    if uploadPlots:
        for f in [
            f"{filename}_surface.webp",
            f"{filename}_boozer.webp",
            f"{filename}_3d.html",
        ]:
            if os.path.exists(f):
                shutil.move(f, os.path.join(folder_name, f))

    auto_save_name = f"{filename}_auto_save.h5"
    if os.path.exists(auto_save_name):
        os.remove(auto_save_name)


def upload_files_desc(folder_path, username, password, verbose=1):
    """Upload a pre-generated folder of DESC files to the database.

    Scans ``folder_path`` for the expected files (zip archive, CSV metadata,
    optional plots) and submits them via the website upload form. Use this
    after ``generate_files_desc`` to separate file preparation from upload.

    Parameters
    ----------
    folder_path : str
        Path to the folder produced by ``generate_files_desc``. Must contain
        at minimum a ``.zip`` archive, ``desc_runs.csv``, and
        ``configurations.csv``.
    username : str
        Username for the database website.
    password : str
        Password for the database website.
    verbose : int, optional
        Verbosity level. ``0`` suppresses all output, ``1`` prints a status
        line (default), ``2`` also lists the files being uploaded.
    """
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"{folder_path} does not exist.")

    uploadPlots = False
    isDeviceNew = False
    files = {
        "zipToUpload": None,
        "descToUpload": None,
        "configToUpload": None,
        "deviceToUpload": None,
        "surfaceToUpload": None,
        "boozerToUpload": None,
        "plot3dToUpload": None,
    }

    for file in os.listdir(folder_path):
        full_path = os.path.join(folder_path, file)
        if file.endswith(".zip"):
            files["zipToUpload"] = full_path
        elif file.endswith(".csv"):
            if "desc_runs" in file:
                files["descToUpload"] = full_path
            elif "configurations" in file:
                files["configToUpload"] = full_path
            elif "devices_and_concepts" in file:
                files["deviceToUpload"] = full_path
                isDeviceNew = True
        elif file.endswith(".webp"):
            if "surface" in file:
                files["surfaceToUpload"] = full_path
            elif "boozer" in file:
                files["boozerToUpload"] = full_path
        elif file.endswith(".html") and "3d" in file:
            files["plot3dToUpload"] = full_path
            uploadPlots = True

    if verbose > 0:
        print(f"Uploading contents of {folder_path} to database...\n")
    if verbose > 1:
        print(f"Files to upload: {[f for f in files.values() if f is not None]}")

    driver = get_driver()
    perform_login(driver, username, password)
    driver.get(f"{HOME_PAGE}/upload/")

    try:

        def wait_and_send(element_id, filepath):
            if filepath:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, element_id))
                ).send_keys(os.path.abspath(filepath))

        wait_and_send("zipToUpload", files["zipToUpload"])
        wait_and_send("descToUpload", files["descToUpload"])
        wait_and_send("configToUpload", files["configToUpload"])

        if uploadPlots:
            wait_and_send("surfaceToUpload", files["surfaceToUpload"])
            wait_and_send("boozerToUpload", files["boozerToUpload"])
            wait_and_send("plot3dToUpload", files["plot3dToUpload"])

        if isDeviceNew:
            wait_and_send("deviceToUpload", files["deviceToUpload"])

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "confirmDesc"))
        ).click()
        WebDriverWait(driver, 30).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, ".success-div, .error-div")
        )
        print(driver.find_element(By.CSS_SELECTOR, ".success-div, .error-div").text)
    except Exception as e:
        print(f"Upload failed: {e}")
    finally:
        driver.quit()


def get_desc_by_id(
    id,
    download_directory=None,
    delete_zip=False,
    return_names=False,
):
    """Download and extract a DESC equilibrium from the database by its ID.

    Queries the database for the given run ID, downloads the associated zip
    archive, and extracts its contents into the current working directory.

    Parameters
    ----------
    id : int
        The ``descrunid`` of the run to retrieve.
    download_directory : str, optional
        Directory where the browser saves the downloaded zip file. Defaults to
        the current working directory. The browser is also configured to download
        directly to this path, so no manual browser setup is needed.
    delete_zip : bool, optional
        If True, delete the downloaded zip file after extraction (default False).
    return_names : bool, optional
        If True, return a list of filenames that were extracted from the zip.
        Returns ``None`` otherwise (default False).

    Returns
    -------
    list of str or None
        Names of the extracted files if ``return_names=True``, otherwise ``None``.
        Also returns ``None`` if the ID does not exist or an error occurs.
    """
    if download_directory is None:
        download_directory = os.getcwd()
    print("Searching in the database...")
    driver = get_driver_for_download(download_directory)
    driver.get(f"{HOME_PAGE}/query/")

    try:
        timeout = 10

        # Select table — triggers AJAX to populate qfin and qfout
        Select(
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.ID, "qtable"))
            )
        ).select_by_value("desc_runs")

        # Wait for qfin options to be populated by AJAX, then select
        WebDriverWait(driver, timeout).until(
            lambda d: len(Select(d.find_element(By.ID, "qfin")).options) > 1
        )
        Select(driver.find_element(By.ID, "qfin")).select_by_value("descrunid")

        driver.find_element(By.ID, "qthr").send_keys(f"={id}")

        # Wait for qfout options, then select desc_runs.descrunid
        WebDriverWait(driver, timeout).until(
            lambda d: len(Select(d.find_element(By.ID, "qfout")).options) > 0
        )
        Select(driver.find_element(By.ID, "qfout")).select_by_value(
            "desc_runs.descrunid"
        )

        driver.find_element(By.ID, "submit").click()
        print("Query submitted successfully!")

        try:
            download_link = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.NAME, "download-button-each"))
            )
            download_link.click()
            print("Download completed successfully!")
        except TimeoutException:
            print(
                f"Error: The download button did not appear. Most likely, id {id} does not exist."
            )
            return None

        time.sleep(1)

        filename = get_file_in_directory(download_directory, f"desc-eq-id{id}", ".zip")

        with zipfile.ZipFile(filename, "r") as zip_ref:
            print(f"Extracting files: {zip_ref.namelist()}")
            zip_ref.extractall()
            print(f"Extracted all files to {os.getcwd()}")

        if delete_zip:
            os.remove(filename)
            print(f"Deleted {filename}")

    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    finally:
        driver.quit()

    if return_names:
        return zip_ref.namelist()
    return None
