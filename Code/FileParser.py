# -*- coding: utf-8 -*-
"""
Created on Thu Oct 31 15:28:47 2019

@author: ucasbwh
"""

### Master script that calls other functions. 
from pathlib import Path
from natsort import natsorted, ns

import Rover
import HaImageProc
import ImageRAWtoBrowse
import decodeRAW_HK

# Select Folder to Process
Top_DIR = Path(input("Type the path to the folder where the RAW log files are stored: "))

## Search for useful files
FILT_DIR = "STDRawOcds*.csv"
ROVER_TM = natsorted(Top_DIR.rglob(FILT_DIR), alg=ns.PATH)
print("Rover TM CSV Files Found: " + str(len(ROVER_TM)))

FILT_DIR = "STDChrono*.csv"
ROVER_TC = natsorted(Top_DIR.rglob(FILT_DIR), alg=ns.PATH)
print("Rover TC CSV Files Found: " + str(len(ROVER_TC)))

FILT_DIR = "*ha"
ROVER_HA = natsorted(Top_DIR.rglob(FILT_DIR), alg=ns.PATH)
print("Rover .ha Files Found: " + str(len(ROVER_HA)))

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
Proc_DIR = Top_DIR / 'PROC'
if Proc_DIR.is_dir():
    print("-'Processing' Directory already exists")
else:
    print("Generating 'Processing' directory")
    Proc_DIR.mkdir()

## Process primary files found
if len(ROVER_TM) != 0:
    Rover.TM_extract(ROVER_TM,Proc_DIR)

if len(ROVER_TC) != 0:
    Rover.TC_extract(ROVER_TC, Proc_DIR)

if len(ROVER_HA) != 0:
    ImageGen = HaImageProc.HaImageProc(ROVER_HA, Proc_DIR)

## Process secondary files
FILT_DIR = "*Unproc_TM.pickle"
if len(sorted(Proc_DIR.rglob(FILT_DIR))) != 0:
    decodeRAW_HK.decode(Proc_DIR)

FILT_DIR = "*.raw"
if len(sorted(Proc_DIR.rglob(FILT_DIR))) != 0:
    ImageRAWtoBrowse.Img_RAW_Browse(Proc_DIR)