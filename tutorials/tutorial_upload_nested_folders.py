"""
This script demonstrates how to upload multiple files that are located in the same folder
structure. The script will loop through all the folders in the current folder and
loop through each .h5 file inside those folders, then upload them to the database. 

- Current folder:
    - Folder 1:
        - file1.h5
        - file2.h5
        - text1.txt
    - Folder 2:
        - file3.h5
        - file4.h5
        - text1.txt

Note: The output file names must be different. Or you can change the script to 
change the config_name

Note: PLEASE DON'T RUN THIS SCRIPT WITH EXAMPLE DATA. USE IT FOR YOUR OWN DATA.
"""

# if you are using the repository, you should use the following import
# and chnage your absolute path to the repository path
import os
import sys

sys.path.insert(0, os.path.abspath("."))
sys.path.append(os.path.abspath("../"))

from stelladb import save_to_db_desc

# Get the current folder path
current_folder_path = os.getcwd()

# Loop through all the folders in the current folder
for folder_name in os.listdir(current_folder_path):
    # Create the folder path
    folder_path = os.path.join(current_folder_path, folder_name)

    # Check if the path is a directory
    if os.path.isdir(folder_path):
        # Loop through all the files in the folder
        for file_name in os.listdir(folder_path):
            # Check if the file ends with .h5
            if file_name.endswith(".h5"):
                file_path = os.path.join(folder_path, file_name)
                file_name_without_extension = os.path.splitext(file_name)[0]
                print(f"\n* * * Uploading {file_name_without_extension} * * *")
                config_name = file_name_without_extension
                # upload to the equilibrium to database
                save_to_db_desc(
                    os.path.join(folder_path, file_name_without_extension),
                    config_name=config_name,
                    user="test-user-id",
                    description="Test for Rahul's database",
                    provenance="test",
                    copy=False,
                    inputfile=False,
                )
