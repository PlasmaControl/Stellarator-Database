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
conda create --name db
conda activate db
pip install -r requirements.txt
```

## Sample usage
```python
from desc.examples import get
import stelladb

eq = get("HELIOTRON")
eq.save("test_output_HELIOTRON.h5")
save_to_db_desc("test_output_HELIOTRON", configid="HELIOTRON", user="username")
```
