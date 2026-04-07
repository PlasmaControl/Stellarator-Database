# Stellarator-Database
Includes the functions required to upload DESC results to the stellarator database. You can access the database [here](https://www.stellarator-database.org/).

This is still a work in progress. VMEC and coil data upload functions will be implemented soon!

## Install using pip
If you are on Linux, WSL or MacOS, you should be able to install `stelladb` directly from PyPi.
```bash
pip install stelladb
```

This package will be used along with DESC or SIMSOPT. You should install them separately to your environment.

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

If you just want to upload DESC results, follow these steps for creating conda environment,
```bash
conda create --name db 'python>=3.9, <=3.12'
conda activate db
pip install desc-opt selenium
```
Then, you can upload to database inside the repo, or anywhere where you can access the module `stelladb`. You can either git clone the whole repository or you can just get the `stelladb` folder of the repo and copy it to where you want to call the functions from.

## Sample usage

For more detailed explanation, refer to the notebooks in `tutorials` subfolder in the [repo](https://github.com/PlasmaControl/Stellarator-Database/blob/main/tutorials/tutorial_basics.ipynb).


## Installing Chrome on WSL2

The automated upload functions relies on `selenium` which opens a web browser on the background. To be able to use this package, you should have a web browser. On WSL, the system cannot use the browser installed on the Windows, you should install one to Linux subsystem too.

```
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google-chrome-stable_current_amd64.deb -y
google-chrome --version
```