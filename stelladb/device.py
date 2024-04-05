import csv
import os
from datetime import date
from .getters import get_hash_device


def device_or_concept_to_csv(  # noqa
    deviceid,
    name=None,
    device_class=None,
    NFP=None,
    description=None,
    stell_sym=False,
    user_created=None,
    user_updated=None,
):
    """Save DESC as a csv with relevant information.

    Args
    ----
        deviceid : str
            short name of the device
        name : str
            name of the device
        device_class (str):
            class of device i.e. quasisymmetry (QA, QH, QP)
            or omnigenity (QI, OT, OH) or axisymmetry (AS).
        NFP : (int)
            (Nominal) number of field periods for the device/concept
        description : (str)
            description of the device/concept
        stell_sym : (bool)
            (Nominal) stellarator symmetry of the device
            (stellarator symmetry defined as R(theta, zeta) = R(-theta,-zeta)
            and Z(theta, zeta) = -Z(-theta,-zeta))

    Returns
    -------
        None
    """
    # data dicts for each table
    devices_and_concepts = {}

    devices_csv_name = "devices_and_concepts.csv"

    devices_and_concepts["deviceid"] = deviceid
    devices_and_concepts["name"] = name if name is not None else deviceid
    devices_and_concepts["class"] = device_class

    devices_and_concepts["NFP"] = NFP
    devices_and_concepts["stell_sym"] = bool(stell_sym)

    devices_and_concepts["description"] = description
    if user_created is not None:
        devices_and_concepts["user_created"] = user_created
    if user_updated is not None:
        devices_and_concepts["user_updated"] = user_updated

    today = date.today()
    devices_and_concepts["date_created"] = today
    devices_and_concepts["date_updated"] = today

    devices_and_concepts["hashkey"] = get_hash_device(devices_and_concepts)

    csv_columns_desc_runs = list(devices_and_concepts.keys())
    csv_columns_desc_runs.sort()
    desc_runs_csv_exists = os.path.isfile(devices_csv_name)

    try:
        with open(devices_csv_name, "a+") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns_desc_runs)
            if not desc_runs_csv_exists:
                writer.writeheader()  # only need header if file did not exist already
            writer.writerow(devices_and_concepts)
    except OSError:
        print("I/O error")

    return None
