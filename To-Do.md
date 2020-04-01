# To-Do

## Prioties

* Make easier to read verification of HK by creating dedicated verificaiton modules
* Split data into activities so that it is easy to view HK etc.
* Check that all items from TC and TM plotter have been recreated in here.
* Be consistent with python style and capitalisation
* SWIS Verify that HK-Ess is generated at the right points
* Ensure all globals have Cpas and Underscore
* Don't define function types
* Use more lines for pandas long expressions
* Multi-line functions have closing bracket on new line
* Change console logging output to a STATUS Flag if possible
* Improve Docstrings and follow standard conventions

## Nice to haves

* swis.py: Rebuild TCs from SpW replie
* Look into the best use of the Pandas Int64 and how best to draw missing data.
* Decode Rover Variables, HRCWarm etc.
* Generate HK Ess and Non-Ess Calibrated for the rest of the variables
* Replace Temperature calibrations with a dictionary
* Read in calibraitons from files rather than stored in software
* Look into converting into archive database
* Plot points rather than lines
* Create a calculation array that stores useful temps, voltages, HRC etc.
* Look at creating a nice interface for it all
* Break into powered chunks that can be easily navigated
* Also look for PanCam service errors such as 5,2
* Automatically generated ICD from files
* Add liscense for project
* Check all liscenses are valid
* Update Readme
* For Plot labels add a white bounding box to stop overlap
* Plot calibrated WAC temperature along with PIU temperature
* Create a kind of WAC and HRC command history but not necessarily a plot
* Set FW numbers and colors to be consistent across WACs and FW plot
* Add borders around plot legends

## Completed

* Integrate with git and visual code
* Make pickle files have data and time tags error with first file created.
* Go through File Parser and make consolidated up to image processing
* For reading STDRaw files order is not sequential but 0, 1, 10, 11, 2, 20 etc.
* Generate HK Ess and Non-Ess RAW
* Ensure comments label all parameters
* Update decodeRAW_ImgHDR with new function
* Switch from os module to the new python path module
* Allow functions to check if a valid pickle file is found
* Generate HK Ess and Non-Ess Calibrated for Key Variables
* Change labels from 0,1,2,3 to WACL, WACR etc.
* Plot these results.
* A general log processing output that has all the text statements I've created stored in a log file.
* Save all plots
* Identify why there is data duplication in Rover TM '191022 - Post Accoustic'
* Check HaImageProc verifies that the last image is complete
* Check for end of LDT file
* Even if missing Start of LDT write to file anyway
* Make browse images as 8-bit png
* Filenames to be LDT File IDs
* Two folders, IMG_Browse and IMG_RAW
* Have JSON from image as multi-line rather than serial.
* Fix haImageProcEdit
* Preview to have same JSON as RAW with added details.
* Extract HK from .ha and plain binary files
* Convert CUC to a useful time
* HK as a simple binary
* Fix .ha extraction for problem files
* Check RestructureHK within HaProc
* Use PIU time rather than packet time
* Compare .ha generated output to csv output
* Create NAVCAM browse
* Add image generation to Overview plot
* FW plots adde
* swis.py: Generate raw science image from spw tms
* swis.py: Generate hk in raw pickle format
* Img Cnt plot to add y-axis
* Way to track data type and processing history
* Guareenteed way to distinguish between WAC and HRC CRs with just TM
* Logging to also stream to console if errors but otherwise ignore
* Hide x-axis labels on multi-stack, particularly for overview as can see extra numbers.
* Make H&S extract from SWIS TB compatible with H&S Checker written
* Is it possible to heavily compress raw data
* Make PSU Log
* Finish LabView processing:
* Make TC Extract
* Set errors between 0 and 1 for a clear view
* Split SWIS and NSVF into seperate modules
* Ensure SWIS checks science images are as expected
* swis.py: Adapt Sci compare for SWIS generated images.
* swis.py: Correct UNIX time calculation as reporting year is 1970
* Extract data from SWIS nsvf Router logs and run through analysis
* Make a list of required packages
* Reorganise into appropriate python structure.
* HRC and WAC plots to display only camera commands.
* Add the rest of the HRC and WAC plots
* Handle .tar.bz2 files
* WAC FW Plot limits set to 0 and 1
* If archive is active do not create a .ignore file
* Adjust x-scale to avoid clash
* Within HK Decode, stop passing bin around and change functions to only return relevant arrays
* Don't add instance names to SWIS products
