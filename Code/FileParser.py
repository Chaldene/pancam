# -*- coding: utf-8 -*-
"""
Created on Thu Oct 31 15:28:47 2019

@author: ucasbwh
"""

### Master script that calls other functions. 
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

import Rover
import HaImageProc
import ImageRAWtoBrowse
import decodeRAW_HK
import Cal_HK
import Plotter

# Select Folder to Process
Top_DIR = Path(input("Type the path to the folder where the RAW log files are stored: "))

## Search for useful files
FILT_DIR = "*HK*.txt"
LV_TM = natsorted(Top_DIR.rglob(FILT_DIR), alg=ns.PATH)
print("LabView TM Files Found: " + str(len(LV_TM)))

FILT_DIR = "RMAP_CMD*.txt"
LV_TC = natsorted(Top_DIR.rglob(FILT_DIR), alg=ns.PATH)
print("LabView TC Files Found: " + str(len(LV_TC)))

FILT_DIR = "*PSU*.txt"
LV_PSU = natsorted(Top_DIR.rglob(FILT_DIR), alg=ns.PATH)
print("LabView PSU Files Found: " + str(len(LV_PSU)))

## Test if processed directory folder exists, if not create it.
PROC_DIR = Top_DIR / 'PROC'
if PROC_DIR.is_dir():
    print("-'Processing' Directory already exists")
else:
    print("Generating 'Processing' directory")
    PROC_DIR.mkdir()

## Process primary files found
if len(ROVER_TM) != 0:
    Rover.TM_extract(ROVER_TM,Proc_DIR)

if len(ROVER_TC) != 0:
    Rover.TC_extract(ROVER_TC, Proc_DIR)

if len(ROVER_HA) != 0:
    ImageGen = HaImageProc.HaImageProc(ROVER_HA, Proc_DIR)

## Process secondary files
decodeRAW_HK.decode(Proc_DIR)

ImageRAWtoBrowse.Img_RAW_Browse(Proc_DIR)

Cal_HK.cal_HK(Proc_DIR)

## Produce Plots
Plotter.HK_Overview(Proc_DIR)
Plotter.HK_Voltages(Proc_DIR)
Plotter.HK_Temperatures(Proc_DIR)
Plotter.Rover_Power(Proc_DIR)
Plotter.Rover_Temperatures(Proc_DIR)
