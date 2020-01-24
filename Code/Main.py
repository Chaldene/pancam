# -*- coding: utf-8 -*-
"""Created on Thu Oct 31 15:28:47 2019.

@author: ucasbwh

This is the master script that calls all the other functions.
Normally this script can be run and pointed at a useful folder. 
"""

from pathlib import Path
import logging

import Plotter
import Cal_HK
import decodeRAW_HK
import ImageRAWtoBrowse
import HaProc
import Rover

logger = logging.getLogger(__name__)


# Select Folder to Process
Top_DIR = Path(
    input("Type the path to the folder where the RAW log files are stored: "))

# Test if processed directory folder exists, if not create it.
Proc_DIR = Top_DIR / 'PROC'
if not Proc_DIR.is_dir():
    MakeDir = True
    Proc_DIR.mkdir()

# logging file will be stored in processing directory
logging.basicConfig(filename=(Proc_DIR / 'processing.log'),
                    level=logging.INFO,
                    format='%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
logger.info('\n\n\n\n')
logger.info("Running FileParser.py")

# Still to-do
#LV_TM = natsorted(Top_DIR.rglob(FILT_DIR), alg=ns.PATH)
#LV_TC = natsorted(Top_DIR.rglob(FILT_DIR), alg=ns.PATH)
#LV_PSU = natsorted(Top_DIR.rglob(FILT_DIR), alg=ns.PATH)
# SWIS Files

# Process primary files found
Rover.TM_extract(Top_DIR)
Rover.TC_extract(Top_DIR)
Rover.NavCamBrowse(Top_DIR)
HaProc.HaScan(Top_DIR)
HaProc.RestructureHK(Proc_DIR)
HaProc.compareHaCSV(Proc_DIR)

# Process secondary files
decodeRAW_HK.decode(Proc_DIR)
ImageRAWtoBrowse.Img_RAW_Browse(Proc_DIR)
Cal_HK.cal_HK(Proc_DIR)

# Produce Plots
Plotter.HK_Overview(Proc_DIR)
Plotter.HK_Voltages(Proc_DIR)
Plotter.HK_Temperatures(Proc_DIR)
Plotter.Rover_Power(Proc_DIR)
Plotter.Rover_Temperatures(Proc_DIR)

logger.info("FileParser.py completed")
