# PanCam-Data-Processing-Tools

A set of tools developed to aid processing of all PanCam produced data. So far support has been developed to decode Rover ".ha" and ".csv" files and extracts all relevant PanCam telemetry along with telecommands if available.

Generally the script Main.py should be run and the directory containing the PanCam files should be input. The script will then search through the folder contents to find data it recognises. Subsequent scripts are then called depending on what was found, the output should be any generated RAW images along with HK plots and several pickle files of the data.

## Installation Instructions

This software uses Python 3.7 with pipenv used to manage module dependancies and versions. 

To duplicate the enviornment as intended first install pipenv using the command `pip install pipenv` using the terminal/powershell.

Next navigate to the folder containing a copy of this repo above and type `pipenv shell` to create an environment for this program.

Install all the dependencies by simply running `pipenv install` this will use the pipfile.lock to capture the same configuration as I have. (The command `pipenv install --dev` can be used to also install development modules).

Finally, run the main.py and paste the location of the files in the terminal/powershell and it will process everything it finds. 
