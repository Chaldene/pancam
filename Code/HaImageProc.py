# -*- coding: utf-8 -*-
"""
Created on Tue Nov 12 10:12:39 2019

Function to go through a folder of Rover .ha files and produce the .raw
binaries as well as a .jpg of all the images. 

@author: ucasbwh
"""
import bitstruct as bs



def HaImageProc(DIR, ROVER_HA):
    
    print("---Processing Rover TM Files")
    
    
    
if __name__ == "__main__":
    import glob
    
    DIR = r'C:\Users\ucasbwh\OneDrive - University College London\PanCam Documents\Rover Level Testing\Data\190809 - PAN_FIT_01'
    
    FILT_DIR = "\**\*.ha"
    ROVER_HA = glob.glob(DIR + FILT_DIR, recursive=True)
    print("Rover .ha Files Found: " + str(len(ROVER_HA)))
    
    if  len(ROVER_HA) != 0:
        HaImageProc(DIR, ROVER_HA)
    else:
        print("No .ha files found, cannot run HaImageProc")