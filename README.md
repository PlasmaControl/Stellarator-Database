# Stellarator-Database
Includes the functions required to upload DESC or VMEC results to the stellarator database. You can access the database [here](https://ye2698.mycpanel.princeton.edu/).

This is still a work in progress.

## Install using pip
```bash
pip install stelladb
```

## Install using GIT

### Clone GIT repo
```bash
git clone https://github.com/PlasmaControl/Stellarator-Database.git
```
Once you get the files,
```bash
cd Stellarator-Database
```

### Building conda environment
```bash
conda create --name db 'python>=3.9, <=3.12'
conda activate db
pip install -r requirements.txt
```

## Sample usage
```python
from desc.examples import get
from stelladb import save_to_db_desc

eq = get("HELIOTRON")

# if you are using DESC, you can directly upload Equilibrium or 
# EquilibriumFamily objects. For EquilibriumFamily, only the last
# Equilibrium will be uploaded.
save_to_db_desc(eq, configid="HELIOTRON", user="username")

# if you have an outfile, supply the name of it without extension
# For DESC example, we need to save it first to get the .h5 file
eq.save("test_output_HELIOTRON.h5")
save_to_db_desc("test_output_HELIOTRON", configid="HELIOTRON", user="username")

# use copy parameter, if you want the local copy of the files that are uploaded
# default value is False
save_to_db_desc(eq, configid="HELIOTRON", user="username", copy=True)
```
