# -*- coding: utf-8 -*-
"""
Created on Thu Oct 31 15:28:47 2019

@author: ucasbwh
"""

### Script to process files into the standard csv file format. 

import glob
import os
import Rover

# Pick folder of interest
TOP_DIR = input("Type the path to the folder where the RAW log files are stored: ")
#TOP_DIR = r"C:\Users\ucasbwh\OneDrive - University College London\PanCam Documents\Rover Level Testing\Data\190809 - PAN_FIT_01"

## Search for useful files
FILT_DIR = "\**\STDRawOcds*.csv"
ROVER_TM = glob.glob(TOP_DIR + FILT_DIR, recursive=True)
print("Rover TM CSV Files Found: " + str(len(ROVER_TM)))

FILT_DIR = "\**\STDChrono*.csv"
ROVER_TC = glob.glob(TOP_DIR + FILT_DIR, recursive=True)
print("Rover TC CSV Files Found: " + str(len(ROVER_TC)))

FILT_DIR = "\**\*.ha"
ROVER_HA = glob.glob(TOP_DIR + FILT_DIR, recursive=True)
print("Rover .ha Files Found: " + str(len(ROVER_HA)))

FILT_DIR = "\**\*HK*.txt"
LV_TM = glob.glob(TOP_DIR + FILT_DIR, recursive=True)
print("LabView TM Files Found: " + str(len(LV_TM)))

FILT_DIR = "\**\RMAP_CMD*.txt"
LV_TC = glob.glob(TOP_DIR + FILT_DIR, recursive=True)
print("LabView TC Files Found: " + str(len(LV_TC)))

FILT_DIR = "\**\*PSU*.txt"
LV_PSU = glob.glob(TOP_DIR + FILT_DIR, recursive=True)
print("LabView PSU Files Found: " + str(len(LV_PSU)))


## Test if processed directory folder exists, if not create it.
PROC_DIR = os.path.join(TOP_DIR, "PROC")
if os.path.isdir(PROC_DIR):
    print("-'Processing' Directory already exists")
else:
    print("Generating 'Processing' directory")
    os.mkdir(PROC_DIR)

## Process files found
if len(ROVER_TM) != 0:
    Rover.TM_convert(ROVER_TM,PROC_DIR)

## Process files found
if len(ROVER_TC) != 0:
    Rover.TC_convert(ROVER_TC, PROC_DIR)