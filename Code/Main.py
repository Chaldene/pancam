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

# First check if SWIS as multiple folders
instances = swis.create_instances(top_dir)
if instances:
    for inst in instances:
        proc_dir = inst / "PROC"
        logger.error("Analysing %s", inst.name)
        swis.hk_extract(inst)
        swis.hs_extract(inst)
        hs.decode(proc_dir, True)
        hs.verify(inst)
        decodeRAW_HK.decode(proc_dir)
        Cal_HK.cal_HK(proc_dir)
        Plotter.all_plots(proc_dir)
        swis.sci_extract(inst)
        swis.sci_compare(inst)

else:
    # LabView Files
    arc_logs = True
    if labview.hk_extract(top_dir, archive=arc_logs):
        labview.hs_extract(top_dir, archive=arc_logs)
        hs.decode(proc_dir)
        hs.verify(proc_dir)
        labview.tc_extract(top_dir)
        labview.sci_extract(top_dir, archive=arc_logs)
        labview.bin_move(top_dir, archive=arc_logs)
        labview.psu_extract(top_dir, archive=arc_logs)
        if arc_logs:
            labview.create_archive(top_dir)

    # Rover files
    # Process primary files found
    # Rover.TM_extract(top_dir)
    # Rover.TC_extract(top_dir)
    # Rover.NavCamBrowse(top_dir)
    # HaProc.HaScan(top_dir)
    # HaProc.RestructureHK(proc_dir)
    # HaProc.compareHaCSV(proc_dir)

    elif swis.nsvf_parse(top_dir):
        swis.hk_extract(proc_dir)
        hs.decode(proc_dir)
        hs.verify(proc_dir)
        swis.sci_extract(proc_dir, True)
        swis.sci_compare(proc_dir)

    # Process secondary files
    decodeRAW_HK.decode(proc_dir)
    ImageRAWtoBrowse.Img_RAW_Browse(proc_dir)
    Cal_HK.cal_HK(proc_dir)

    # Produce Plots
    Plotter.all_plots(proc_dir)

logger.info("main.py completed")
