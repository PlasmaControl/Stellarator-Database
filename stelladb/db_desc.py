import os
import numpy as np
import csv
import zipfile
from datetime import date

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from desc.equilibrium import Equilibrium, EquilibriaFamily
from desc.grid import LinearGrid
from desc.vmec_utils import ptolemy_identity_rev, zernike_to_fourier
from desc.io.hdf5_io import hdf5Reader
from desc.io.equilibrium_io import load

from .getters import get_hash_config, get_driver, get_hash_desc
from .device import device_or_concept_to_csv


def save_to_db_desc(  # pragma: no cover
    eq,
    config_name,
    user,
    description=None,
    provenance=None,
    deviceid=None,
    isDeviceNew=False,
    inputfile=False,
    inputfilename=None,
    config_class=None,
    current=True,
    initialization_method="surface",
    deviceNFP=1,
    deviceDescription=None,
    device_stell_sym=False,
    copy=False,
):
    """Load a DESC equilibrium and upload it to the database.

    Parameters
    ----------
    eq : str, Equilibrium or EquilibriumFamily
        file path of the output file without .h5 extension
        or the equilibrium to be uploaded
    config_name : str
        unique identifier for the configuration
    user : str
        user who created the equilibrium (must have an account on the database)
    description : str (Default: None)
        description of the configuration
    provenance : str (Default: None)
        where the configuration came from
    deviceid : str (Default: None)
        unique identifier for the device
    isDeviceNew : bool (Default: False)
        True if the device is new and should be uploaded to the database
    inputfile : bool (Default: False)
        True if the input file should be uploaded to the database
    inputfilename : str (Default: None)
        name of the input file corresponding to this configuration
    config_class : str (Default: None)
        class of configuration i.e. quasisymmetry (QA, QH, QP)
        or omnigenity (QI, OT, OH) or axisymmetry (AS)
    current : bool (Default: True)
        True if the equilibrium was solved with fixed current or not if False,
        was solved with fixed iota
    initialization_method : str (Default: 'surface')
        method used to initialize the equilibrium
    deviceNFP : int (Default: 1)
        number of field periods for the device
    deviceDescription : str (Default: None)
        description of the device
    device_stell_sym : bool (Default: False)
        stellarator symmetry of the device
    copy : bool (Default: False)
        True if the zip and csv files should be kept after uploading

    """
    if (
        eq == ""
        or eq is None
        or config_name == ""
        or config_name is None
        or user == ""
        or user is None
    ):
        raise ValueError("Please provide a valid input for eq, config_name, and user.")

    if isinstance(eq, str):
        if os.path.exists(eq + ".h5"):
            filename = eq
            eq = eq + ".h5"
        else:
            raise FileNotFoundError(f"{eq}.h5 does not exist.")
    elif isinstance(eq, Equilibrium):
        eq = eq
        filename = config_name
    elif isinstance(eq, EquilibriaFamily):
        eq = eq[-1]
        filename = config_name
    else:
        raise TypeError(
            "Expected type str, Equilibrium or EquilibriumFamily "
            + f"for eq, got type {type(eq)}"
        )
    if os.path.exists("auto_save.h5"):
        print("Removing auto_save.h5")
        os.remove("auto_save.h5")

    auto_input = False
    # Check input files, if there isn't any create automatically
    if inputfilename is None and inputfile:
        if os.path.exists(filename + "_input.txt"):
            print(
                f"Found an input file with name {filename}_input.txt and using that ..."
            )
            inputfilename = filename + "_input.txt"
        else:
            inputfilename = "auto_generated_" + filename + "_input.txt"
            from desc.input_reader import InputReader
            auto_input = True

            print("Auto-generating input file...")
            writer = InputReader()
            if isinstance(eq, str):
                writer.desc_output_to_input(inputfilename, eq)
            elif isinstance(eq, Equilibrium):
                eq.save("auto_save.h5")
                writer.desc_output_to_input(inputfilename, "auto_save.h5")
            elif isinstance(eq, EquilibriaFamily):
                eq[-1].save("auto_save.h5")
                writer.desc_output_to_input(inputfilename, "auto_save.h5")
    elif inputfilename is not None and os.path.exists(inputfilename) and not inputfile:
        inputfile = True

    # Zip the files
    print("Zipping files...")
    zip_filename = filename + ".zip"
    with zipfile.ZipFile(zip_filename, "w") as zipf:
        if os.path.exists(filename + ".h5"):
            zipf.write(filename + ".h5")
        elif isinstance(eq, Equilibrium):
            print("Saving equilibrium to .h5 file...")
            if not os.path.exists("auto_save.h5"):
                eq.save("auto_save.h5")
            zipf.write("auto_save.h5")
        elif isinstance(eq, EquilibriaFamily):
            print("Saving equilibrium to .h5 file...")
            if not os.path.exists("auto_save.h5"):
                eq[-1].save("auto_save.h5")
            zipf.write("auto_save.h5")
        if inputfilename is not None and inputfile:
            if os.path.exists(inputfilename):
                zipf.write(inputfilename)

    csv_filename = "desc_runs.csv"
    config_csv_filename = "configurations.csv"
    device_csv_filename = "devices_and_concepts.csv"
    if os.path.exists(csv_filename):
        os.remove(csv_filename)
        print(f"Previous {csv_filename} has been deleted.")
    if os.path.exists(config_csv_filename):
        os.remove(config_csv_filename)
        print(f"Previous {config_csv_filename} has been deleted.")
    if os.path.exists(device_csv_filename):
        os.remove(device_csv_filename)
        print(f"Previous {device_csv_filename} has been deleted.")

    print("Creating desc_runs.csv and configurations.csv...")
    desc_to_csv(
        eq, 
        name=config_name, 
        provenance=provenance,
        description=description,
        inputfilename=inputfilename,
        current=current,
        deviceid=deviceid,
        config_class=config_class,
        user_updated=user,
        user_created=user,
        initialization_method=initialization_method,
    )

    if isDeviceNew:
        if (
            deviceid is not None
            and config_class is not None
            and deviceDescription is not None
            and deviceNFP is not None
            and device_stell_sym is not None
            and config_name is not None
        ):
            print("Creating devices_and_concepts.csv...")
            device_or_concept_to_csv(
                name=config_name,
                device_class=config_class,
                NFP=deviceNFP,
                description=deviceDescription,
                stell_sym=device_stell_sym,
                deviceid=deviceid,
                user_created=user,
                user_updated=user,
            )
        else:
            raise ValueError(
                "If the device is new, device_name, config_class, deviceDescription, "
                + "deviceNFP, and device_stell_sym must be provided."
            )

    zip_upload_button_id = "zipToUpload"
    csv_upload_button_id = "descToUpload"
    cfg_upload_button_id = "configToUpload"
    device_upload_button_id = "deviceToUpload"
    confirm_button_id = "confirmDesc"

    print("Uploading to database...\n")
    driver = get_driver()
    driver.get("https://ye2698.mycpanel.princeton.edu/import-page/")

    try:
        # Upload the zip file
        file_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, zip_upload_button_id))
        )
        file_input.send_keys(os.path.abspath(zip_filename))

        # Upload the csv file for desc_runs
        file_input2 = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, csv_upload_button_id))
        )
        file_input2.send_keys(os.path.abspath(csv_filename))

        # Upload the csv file for configurations
        file_input3 = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, cfg_upload_button_id))
        )
        file_input3.send_keys(os.path.abspath(config_csv_filename))

        # Upload the csv file if the device is new
        if isDeviceNew:
            file_input4 = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, device_upload_button_id))
            )
            file_input4.send_keys(os.path.abspath(device_csv_filename))

        # Confirm the upload
        confirm_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, confirm_button_id))
        )
        confirm_button.click()

        # Wait for the messageContainer div to contain text
        WebDriverWait(driver, 10).until(
            lambda driver: driver.find_element(By.ID, "messageContainer").text.strip()
            != ""
        )

        # Extract and print the message
        message_element = driver.find_element(By.ID, "messageContainer")
        message = message_element.text
        print(message)
    except:  # noqa: E722
        # Extract and print the message
        message_element = driver.find_element(By.ID, "messageContainer")
        message = message_element.text
        print(message)

    finally:
        # Clean up resources
        driver.quit()
        if os.path.exists("auto_save.h5"):
            os.remove("auto_save.h5")
        if not copy:
            os.remove(zip_filename)
            os.remove(csv_filename)
            os.remove(config_csv_filename)
            if isDeviceNew:
                os.remove(device_csv_filename)
            if auto_input:
                os.remove(inputfilename)


def desc_to_csv(  # noqa
    eq,
    name=None,
    provenance=None,
    description=None,
    inputfilename=None,
    initialization_method="surface",
    user_created=None,
    user_updated=None,
    output_csv_name_desc="desc_runs.csv",
    output_csv_name_config="configurations.csv",
    **kwargs,
):
    """Save DESC output file as a csv with relevant information.

    Parameters
    ----------
        eq : str, Equilibrium or EquilibriumFamily
            file path of the output file without .h5 extension
            or the equilibrium to be uploaded
        name : str
            name of configuration (and desc run)
        provenance : str
            where this configuration (and desc run) came from, e.g. DESC github repo
        description : str
            description of the configuration (and desc run)
        inputfilename : str
            name of the input file corresponding to this configuration (and desc run)
        initialization_method : str
            how the DESC equilibrium solution was initialized
            one of "surface", "NAE", or the name of a .nc or .h5 file
            corresponding to a VMEC (if .nc) or DESC (if .h5) solution

    Kwargs
    ------
        date_created : str
            when the DESC run was created, defaults to current day
        publicationid : str
            unique ID for a publication which this DESC output file is associated with.
        deviceid : str
            unique ID for a device/concept which this configuration is associated with.
        config_class : str
            class of configuration i.e. quasisymmetry (QA, QH, QP)
            or omnigenity (QI, OT, OH) or axisymmetry (AS).
            Defaults to None for a stellarator and (AS) for a tokamak
            #TODO: can we attempt to automatically detect this for QS configs?
            maybe with a threshold on low QS, then if passes that, classify
            based on largest Boozer mode? can add a flag to the table like
            "automatically labelled class" if this occurs
            to be transparent about source of the class if it was not a human

    Returns
    -------
        None
    """
    # data dicts for each table
    data_desc_runs = {}
    data_configurations = {}

    desc_runs_csv_name = output_csv_name_desc
    configurations_csv_name = output_csv_name_config

    if isinstance(eq, str) and os.path.exists(eq):
        data_desc_runs["outputfile"] = os.path.basename(eq)
        reader = hdf5Reader(eq)
        version = reader.read_dict()["__version__"]
        eq = load(eq)
        if isinstance(eq, EquilibriaFamily):
            eq = eq[-1]
    elif isinstance(eq, Equilibrium):
        import desc

        version = desc.__version__
        data_desc_runs["outputfile"] = "auto_save.h5"
    elif isinstance(eq, EquilibriaFamily):
        import desc

        eq = eq[-1]
        version = desc.__version__
        data_desc_runs["outputfile"] = "auto_save.h5"
    else:
        raise TypeError(
            "Expected type str, Equilibrium or EquilibriumFamily "
            + f"for eq, got type {type(eq)}"
        )

    ############ DESC_runs Data Table ############
    if name is not None:
        data_desc_runs["config_name"] = name
    if provenance is not None:
        data_desc_runs["provenance"] = provenance
    if description is not None:
        data_desc_runs["description"] = description

    data_desc_runs["version"] = (
        version  # this is basically redundant with git commit I think
    )
    if inputfilename is not None:
        data_desc_runs["inputfilename"] = inputfilename

    data_desc_runs["initialization_method"] = initialization_method

    data_desc_runs["l_rad"] = eq.L
    data_desc_runs["l_grid"] = eq.L_grid
    data_desc_runs["m_pol"] = eq.M
    data_desc_runs["m_grid"] = eq.M_grid
    data_desc_runs["n_tor"] = eq.N
    data_desc_runs["n_grid"] = eq.N_grid

    data_desc_runs["bdry_ratio"] = (
        1.0  # this is not a equilibrium property, so should not be saved
    )

    # save profiles

    rho = np.linspace(0, 1.0, 11, endpoint=True)
    rho_grid = LinearGrid(rho=rho, M=0, N=0, NFP=eq.NFP)
    data_desc_runs["profile_rho"] = rho
    rho_dense = np.linspace(0, 1.0, 101, endpoint=True)
    rho_grid_dense = LinearGrid(rho=rho_dense, M=0, N=0, NFP=eq.NFP)

    rho_grid.nodes[0, 0] = 1e-12  # bc we dont have axis limit right now
    rho_grid_dense.nodes[0, 0] = 1e-12  # bc we dont have axis limit right now

    if eq.iota:
        data_desc_runs["iota_profile"] = eq.iota(rho)  # sohuld name differently
        data_desc_runs["iota_max"] = np.max(eq.iota(rho_dense))

        data_desc_runs["iota_min"] = np.min(eq.iota(rho_dense))

        data_desc_runs["current_profile"] = round(
            eq.compute("current", grid=rho_grid)["current"], ndigits=14
        )  # round to make sure any 0s are actually zero
        data_configurations["current_specification"] = "iota"
        data_desc_runs["current_specification"] = "iota"
    elif eq.current:
        data_desc_runs["current_profile"] = eq.current(rho)
        data_desc_runs["iota_profile"] = round(
            eq.compute("iota", grid=rho_grid)["iota"], ndigits=14
        )
        data_desc_runs["iota_max"] = np.max(
            eq.compute("iota", grid=rho_grid_dense)["iota"]
        )
        data_desc_runs["iota_min"] = np.min(
            eq.compute("iota", grid=rho_grid_dense)["iota"]
        )
        data_configurations["current_specification"] = "net enclosed current"
        data_desc_runs["current_specification"] = "net enclosed current"
    Dmerc = eq.compute("D_Mercier", grid=rho_grid)["D_Mercier"]
    data_desc_runs["D_Mercier_max"] = np.max(Dmerc)
    data_desc_runs["D_Mercier_min"] = np.min(Dmerc)
    data_desc_runs["D_Mercier"] = Dmerc

    data_desc_runs["iota_min"] = np.min(eq.compute("iota", grid=rho_grid_dense)["iota"])
    data_desc_runs["pressure_profile"] = eq.pressure(rho)
    data_desc_runs["pressure_max"] = np.max(eq.pressure(rho_dense))
    data_desc_runs["pressure_min"] = np.min(eq.pressure(rho_dense))

    today = date.today()
    data_desc_runs["date_created"] = kwargs.get("date_created", today)
    data_desc_runs["date_updated"] = kwargs.get("date_updated", today)
    if user_created is not None:
        data_desc_runs["user_created"] = user_created
    if user_updated is not None:
        data_desc_runs["user_updated"] = user_updated
    if kwargs.get("publicationid", None) is not None:
        data_desc_runs["publicationid"] = kwargs.get("publicationid", None)

    ############ configuration Data Table ############
    data_configurations["name"] = name
    data_configurations["NFP"] = eq.NFP
    data_configurations["stell_sym"] = bool(eq.sym)

    if kwargs.get("deviceid", None) is not None:
        data_configurations["deviceid"] = kwargs.get("deviceid", None)
    if provenance is not None:
        data_configurations["provenance"] = provenance
    if description is not None:
        data_configurations["description"] = description

    data_configurations["toroidal_flux"] = eq.Psi
    data_configurations["aspect_ratio"] = eq.compute("R0/a")["R0/a"]
    data_configurations["minor_radius"] = eq.compute("a")["a"]
    data_configurations["major_radius"] = eq.compute("R0")["R0"]
    data_configurations["volume"] = eq.compute("V")["V"]
    data_configurations["volume_averaged_B"] = eq.compute("<|B|>_vol")["<|B|>_vol"]
    data_configurations["volume_averaged_beta"] = eq.compute("<beta>_vol")["<beta>_vol"]
    data_configurations["total_toroidal_current"] = float(
        f'{eq.compute("current")["current"][-1]:1.2e}'
    )
    position_data = eq.compute(["R", "Z", "a_major/a_minor"])
    data_configurations["R_excursion"] = float(
        f'{np.max(position_data["R"])-np.min(position_data["R"]):1.4e}'
    )
    data_configurations["Z_excursion"] = float(
        f'{np.max(position_data["Z"])-np.min(position_data["Z"]):1.4e}'
    )
    data_configurations["average_elongation"] = float(
        f'{np.mean(position_data["a_major/a_minor"]):1.4e}'
    )
    if kwargs.get("config_class", None) is not None:
        data_configurations["class"] = kwargs.get("config_class", None)
    if eq.N == 0:  # is axisymmetric
        data_configurations["class"] = "AS"

    # surface geometry
    # currently saving as VMEC format but I'd prefer if we could do DESC format...

    r1 = np.ones_like(eq.R_lmn)
    r1[eq.R_basis.modes[:, 1] < 0] *= -1
    m, n, x_mn = zernike_to_fourier(
        r1 * eq.R_lmn, basis=eq.R_basis, rho=np.array([1.0])
    )
    xm, xn, s, c = ptolemy_identity_rev(m, n, x_mn)

    data_configurations["m"] = xm
    data_configurations["n"] = xn

    data_configurations["RBC"] = c[0, :]
    if not eq.sym:
        data_configurations["RBS"] = s[0, :]
    else:
        data_configurations["RBS"] = np.zeros_like(c)
    # Z
    z1 = np.ones_like(eq.Z_lmn)
    z1[eq.Z_basis.modes[:, 1] < 0] *= -1
    m, n, x_mn = zernike_to_fourier(
        z1 * eq.Z_lmn, basis=eq.Z_basis, rho=np.array([1.0])
    )
    xm, xn, s, c = ptolemy_identity_rev(m, n, x_mn)
    data_configurations["ZBS"] = s
    if not eq.sym:
        data_configurations["ZBC"] = c
    else:
        data_configurations["ZBC"] = np.zeros_like(s)

    # profiles
    # TODO: make dict of different classes of Profile and
    # the corresponding type of profile, to support more than just
    # power series
    data_configurations["pressure_profile_type"] = "power_series"
    data_configurations["pressure_profile_data1"] = eq.pressure.basis.modes[
        :, 0
    ]  # these are the mode numbers
    data_configurations["pressure_profile_data2"] = (
        eq.pressure.params
    )  # these are the coefficients

    if eq.current:
        data_configurations["current_profile_type"] = "power_series"
        data_configurations["current_profile_data1"] = eq.current.basis.modes[
            :, 0
        ]  # these are the mode numbers
        data_configurations["current_profile_data2"] = (
            eq.current.params
        )  # these are the coefficients

    elif eq.iota:
        data_configurations["iota_profile_type"] = "power_series"
        data_configurations["iota_profile_data1"] = eq.iota.basis.modes[
            :, 0
        ]  # these are the mode numbers
        data_configurations["iota_profile_data2"] = (
            eq.iota.params
        )  # these are the coefficients

    data_configurations["date_created"] = kwargs.get("date_created", today)
    data_configurations["date_updated"] = kwargs.get("date_updated", today)
    if user_created is not None:
        data_configurations["user_created"] = user_created
    if user_updated is not None:
        data_configurations["user_updated"] = user_updated

    data_configurations["configid"] = get_hash_config(data_configurations)
    data_desc_runs["hashkey"] = get_hash_desc(
        eq, data_desc_runs, data_configurations["configid"]
    )

    csv_columns_desc_runs = list(data_desc_runs.keys())
    csv_columns_desc_runs.sort()
    desc_runs_csv_exists = os.path.isfile(desc_runs_csv_name)

    try:
        with open(desc_runs_csv_name, "a+") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns_desc_runs)
            if not desc_runs_csv_exists:
                writer.writeheader()  # only need header if file did not exist already
            writer.writerow(data_desc_runs)
    except OSError:
        print("I/O error")
    csv_columns_configurations = list(data_configurations.keys())
    csv_columns_configurations.sort()

    configurations_csv_exists = os.path.isfile(configurations_csv_name)
    try:
        with open(configurations_csv_name, "a+") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns_configurations)
            if not configurations_csv_exists:
                writer.writeheader()  # only need header if file did not exist already
            writer.writerow(data_configurations)
    except OSError:
        print("I/O error")

    return None
