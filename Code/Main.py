# -*- coding: utf-8 -*-
"""
main.py

Barry Whiteside
Mullard Space Science Laboratory - UCL

PanCam Data Processing Tools
Created 31 Oct 2019
"""

from pathlib import Path
import logging

import Plotter
import Cal_HK
import decodeRAW_HK
import ImageRAWtoBrowse
import HaProc
import Rover
import swis
import hs

logger = logging.getLogger(__name__)


# Select Folder to Process
top_dir = Path(
    input("Type the path to the folder where the RAW log files are stored: "))

# Test if processed directory folder exists, if not create it.
proc_dir = top_dir / 'PROC'
if not proc_dir.is_dir():
    MakeDir = True
    proc_dir.mkdir()

# logging file will be stored in processing directory
logging.basicConfig(filename=(proc_dir / 'processing.log'),
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
Rover.TM_extract(top_dir)
Rover.TC_extract(top_dir)
Rover.NavCamBrowse(top_dir)
HaProc.HaScan(top_dir)
HaProc.RestructureHK(proc_dir)
HaProc.compareHaCSV(proc_dir)

if swis.nsvf_parse(top_dir):
    hs.decode(proc_dir)
    hs.verify(proc_dir)
    swis.sci_extract(proc_dir)
    swis.sci_compare(proc_dir)

# Process secondary files
decodeRAW_HK.decode(proc_dir)
ImageRAWtoBrowse.Img_RAW_Browse(proc_dir)
Cal_HK.cal_HK(proc_dir)

# Produce Plots
Plotter.HK_Overview(proc_dir)
Plotter.HK_Voltages(proc_dir)
Plotter.HK_Temperatures(proc_dir)
Plotter.Rover_Power(proc_dir)
Plotter.Rover_Temperatures(proc_dir)

logger.info("FileParser.py completed")
