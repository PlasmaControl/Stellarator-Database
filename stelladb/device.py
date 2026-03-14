import csv
import os
from datetime import date


def device_or_concept_to_csv(
    name=None,
    description=None,
):
    """Save device/concept info as a csv for database upload.

    Args
    ----
    name : str
        name of the device
    description : str
        description of the device/concept

    Returns
    -------
        None
    """
    devices_and_concepts = {}

    devices_csv_name = "devices_and_concepts.csv"

    devices_and_concepts["name"] = name
    devices_and_concepts["description"] = description

    today = date.today()
    devices_and_concepts["date_created"] = today
    devices_and_concepts["date_updated"] = today

    csv_columns = list(devices_and_concepts.keys())
    csv_columns.sort()
    csv_exists = os.path.isfile(devices_csv_name)

    try:
        with open(devices_csv_name, "a+") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
            if not csv_exists:
                writer.writeheader()  # only need header if file did not exist already
            writer.writerow(devices_and_concepts)
    except OSError:
        print("I/O error")

    return None
