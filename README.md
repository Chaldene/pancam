# PanCam-Data-Processing-Tools

A set of tools developed to aid processing of all PanCam produced data. So far support has been developed to decode Rover ".ha" and ".csv" files and extracts all relevant PanCam telemetry along with telecommands if available.

Generally the script Main.py should be run and the directory containing the PanCam files should be input. The script will then search through the folder contents to find data it recognises. Subsequent scripts are then called depending on what was found, the output should be any generated RAW images along with HK plots and several pickle files of the data.

## Note

I've still yet to package this up properly but as a quick solution I have included a requirements.txt file of everything installed within my conda environment. 