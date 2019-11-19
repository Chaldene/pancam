# -*- coding: utf-8 -*-
"""
Created on Thu Oct 31 15:28:47 2019

@author: ucasbwh
"""

### Master script that calls other functions. 

import glob
import os
import Rover
import HaImageProc
import ImageRAWtoBrowse

# Select Folder to Process
TOP_DIR = input("Type the path to the folder where the RAW log files are stored: ")

## Search for useful files
FILT_DIR = r"\**\STDRawOcds*.csv"
ROVER_TM = glob.glob(TOP_DIR + FILT_DIR, recursive=True)
print("Rover TM CSV Files Found: " + str(len(ROVER_TM)))

FILT_DIR = r"\**\STDChrono*.csv"
ROVER_TC = glob.glob(TOP_DIR + FILT_DIR, recursive=True)
print("Rover TC CSV Files Found: " + str(len(ROVER_TC)))

FILT_DIR = r"\**\*.ha"
ROVER_HA = glob.glob(TOP_DIR + FILT_DIR, recursive=True)
print("Rover .ha Files Found: " + str(len(ROVER_HA)))

FILT_DIR = r"\**\*HK*.txt"
LV_TM = glob.glob(TOP_DIR + FILT_DIR, recursive=True)
print("LabView TM Files Found: " + str(len(LV_TM)))

FILT_DIR = r"\**\RMAP_CMD*.txt"
LV_TC = glob.glob(TOP_DIR + FILT_DIR, recursive=True)
print("LabView TC Files Found: " + str(len(LV_TC)))

FILT_DIR = r"\**\*PSU*.txt"
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

if len(ROVER_HA) != 0:
    HaImageProc.HaImageProc(ROVER_HA, PROC_DIR)
    ImageGen = True

if ImageGen:
    ImageRAWtoBrowse.Img_RAW_Browse(PROC_DIR)