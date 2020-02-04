# To-Do

## Prioties

- Add the rest of the HRC, WAC and FW plots
- SWIS read XML that generates data?
- Split data into activities so that it is easy to view HK etc.
- Hide x-axis labels on multi-stack, particularly for overview as can see extra numbers.
- Way to track data type and processing history
- Within HK Decode, stop passing bin around and change functions to only return relevant arrays

## Nice to haves

- Look into the best use of the Pandas Int64 and how best to draw missing data.
- Decode Rover Variables, HRCWarm etc.
- Generate HK Ess and Non-Ess Calibrated for the rest of the variables
- Replace Temperature calibrations with a dictionary
- Read in calibraitons from files rather than stored in software
- Guareenteed way to distinguish between WAC and HRC CRs with just TM
- Look into converting into archive database
- Is it possible to heavily compress raw data
- Set errors between 0 and 1 for a clear view
- Plot points rather than lines
- Scroll bar for viewing
- Create a calculation array that stores useful temps, voltages, HRC etc.
- Look at creating a nice interface for it all
- Break into powered chunks that can be easily navigated
- Also look for PanCam service errors such as 5,2
- Automatically generated ICD from files
- More checks of the data integrity
- Setup PEP8 tools and ensure code is up to standard.
- Add liscense for project
- Check all liscenses are valid
- Update Readme
- Make a list of required packages
- Make reading csv Rover file output similar to that of .ha and other sources

## Completed

- Integrate with git and visual code
- Make pickle files have data and time tags error with first file created.
- Go through File Parser and make consolidated up to image processing
- For reading STDRaw files order is not sequential but 0, 1, 10, 11, 2, 20 etc.
- Generate HK Ess and Non-Ess RAW
- Ensure comments label all parameters
- Update decodeRAW_ImgHDR with new function
- Switch from os module to the new python path module
- Allow functions to check if a valid pickle file is found
- Generate HK Ess and Non-Ess Calibrated for Key Variables
- Change labels from 0,1,2,3 to WACL, WACR etc.
- Plot these results.
- A general log processing output that has all the text statements I've created stored in a log file.
- Save all plots
- Identify why there is data duplication in Rover TM '191022 - Post Accoustic'
- Check HaImageProc verifies that the last image is complete
- Check for end of LDT file
- Even if missing Start of LDT write to file anyway
- Make browse images as 8-bit png
- Filenames to be LDT File IDs
- Two folders, IMG_Browse and IMG_RAW
- Have JSON from image as multi-line rather than serial.
- Fix haImageProcEdit
- Preview to have same JSON as RAW with added details.
- Extract HK from .ha and plain binary files
- Convert CUC to a useful time
- HK as a simple binary
- Fix .ha extraction for problem files
- Check RestructureHK within HaProc
- Use PIU time rather than packet time
- Compare .ha generated output to csv output
- Create NAVCAM browse
- Add image generation to Overview plot