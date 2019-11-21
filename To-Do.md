# Prioties
-   Generate HK Ess and Non-Ess RAW
-   Generate HK Ess and Non-Ess Calibrated for Key Variables
-   Identify why there is data duplication in Rover TM '190809 - PAN_FIT_01'
-   Update decodeRAW_ImgHDR with new function
-   Plot these results. 

## Nice to haves
-   Generate HK Ess and Non-Ess Calibrated for the rest of the variables
-   Switch from os module to the new python path module
-	Allow functions to check if a valid pickle file is found
-	Look into converting into archive database
-	Is it possible to heavily compress raw data
-   Set errors between 0 and 1 for a clear view
-   Plot points rather than lines
-   Scroll bar for viewing
-   Save all plots
-   Change labels from 0,1,2,3 to WACL, WACR etc.
-   Create a calculation array that stores useful temps, voltages, HRC etc.
-   Look at creating a nice interface for it all
-   A general log processing output that has all the text statements I've created stored in a log file.
-   Break into powered chunks that can be easily navigated
-   Also look for PanCam service errors such as 5,2

-   Setup PEP8 tools and ensure code is up to standard. 

## Completed
-   Integrate with git and visual code
-   Make pickle files have data and time tags error with first file created.
-   Go through File Parser and make consolidated up to image processing
-   For reading STDRaw files order is not sequential but 0, 1, 10, 11, 2, 20 etc. 