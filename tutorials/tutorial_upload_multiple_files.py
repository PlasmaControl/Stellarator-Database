"""
This script demonstrates how to upload multiple files that are located in the same folder
to the database quickly. The script will loop through all the files in the folder and
upload them to the database. 

Note: PLEASE DON'T RUN THIS SCRIPT WITH EXAMPLE DATA. USE IT FOR YOUR OWN DATA.
"""

# if you are using the repository, you should use the following import
# and chnage your absolute path to the repository path
import os
import sys

sys.path.insert(0, os.path.abspath("."))
sys.path.append(os.path.abspath("../"))

from stelladb import save_to_db_desc

folder_path = "./examples"  # Replace with the actual folder path

for file_name in os.listdir(folder_path):
    if file_name.endswith(".h5"):
        file_name_without_extension = os.path.splitext(file_name)[0]
        print(f"\n* * * Uploading {file_name_without_extension} * * *")
        config_name = file_name_without_extension.replace("_output", "")
        # upload to the equilibrium to database
        save_to_db_desc(
            os.path.abspath(folder_path) + "/" + file_name_without_extension,
            config_name=config_name,
            user="some-user-id",
            description="Upload multiple files tutorial",
            provenance="DESC examples folder",
            copy=False,
            inputfile=False,
        )
