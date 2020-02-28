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
import labview
import PC_Fns

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# create console handler logger
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
ch_formatter = logging.Formatter(
    '%(module)s.%(funcName)s - %(levelname)s - %(message)s')
ch.setFormatter(ch_formatter)

# Select Folder to Process
top_dir = Path(
    input("Type the path to the folder where the RAW log files are stored: "))

# Test if processed directory folder exists, if not create it.
proc_dir = top_dir / 'PROC'
if not proc_dir.is_dir():
    MakeDir = True
    proc_dir.mkdir()

# create file handler logger
fh = logging.FileHandler(proc_dir / 'processing.log')
fh.setLevel(logging.INFO)
fh_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(module)s.%(funcName)s - %(message)s')
fh.setFormatter(fh_formatter)
logger.addHandler(fh)
logger.addHandler(ch)

logger.info('\n\n\n\n')
logger.info("main.py")

# LabView Files
arc_logs = True
if labview.hk_extract(top_dir, archive=arc_logs):
    labview.hs_extract(top_dir, archive=arc_logs)
    hs.decode(proc_dir)
    hs.verify(proc_dir)
    labview.sci_extract(top_dir, archive=arc_logs)
    labview.bin_move(top_dir, archive=arc_logs)
    if arc_logs:
        labview.create_archive(top_dir)
# LV_TC = natsorted(Top_DIR.rglob(FILT_DIR), alg=ns.PATH)
# LV_PSU = natsorted(Top_DIR.rglob(FILT_DIR), alg=ns.PATH)

# Process primary files found
# Rover.TM_extract(top_dir)
# Rover.TC_extract(top_dir)
# Rover.NavCamBrowse(top_dir)
# HaProc.HaScan(top_dir)
# HaProc.RestructureHK(proc_dir)
# HaProc.compareHaCSV(proc_dir)

# SWIS Files
elif swis.hk_extract(top_dir):
    # Several instance files generated
    unproc = PC_Fns.Find_Files(top_dir, '*Unproc_HKTM.pickle')
    swis.hs_extract(top_dir)
    for cur_file in unproc:
        logger.error("Analysing %s", cur_file.name)
        cur_dir = cur_file.parent
        hs.decode(cur_dir, True)
        hs.verify(cur_dir)
        decodeRAW_HK.decode(cur_dir)
        Cal_HK.cal_HK(cur_dir)
        Plotter.HK_Overview(cur_dir)
        Plotter.HK_Voltages(cur_dir)
        Plotter.HK_Temperatures(cur_dir)
        Plotter.FW(cur_dir)

        # Check_Sci(DIR)

elif swis.nsvf_parse(top_dir):
    swis.hk_extract(proc_dir)
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
Plotter.FW(proc_dir)
Plotter.Rover_Power(proc_dir)
Plotter.Rover_Temperatures(proc_dir)

logger.info("main.py completed")
