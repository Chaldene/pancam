# -*- coding: utf-8 -*-
"""Created on Thu Dec 12 13:09 2019.

@author: ucasbwh
"""
# Converts outputs from the SWIS into readable format
# Seperate each session into a new Folder for checking

import pandas as pd
from pathlib import Path
import logging

import PC_Fns
import decodeRAW_HK
import Cal_HK
import Plotter

logger = logging.getLogger(__name__)


def HK_Extract(SWIS_DIR):
    """Searches for HK files and creates a binary for each file found"""

    logger.info("Processing SWIS HK")

    HKfiles = PC_Fns.Find_Files(SWIS_DIR, "*HK.txt")
    if not HKfiles:
        logger.error("No files found - ABORTING")
        return

    # Read text file for HK
    for curfile in HKfiles:
        DL = pd.DataFrame()
        logger.info("Reading %s", curfile.name)
        DT = pd.read_table(curfile, sep=']', header=None)

        DL['SPW_RAW'] = DT[1].apply(
            lambda x: x.replace('0x', '').replace(' ', ''))
        DL['RAW'] = DL.SPW_RAW.apply(lambda x: x[108-84:-2])
        DL['Source'] = 'SWIS'
        DL['Unix_Time'] = DT[0].apply(lambda x: x[11:-12])

        # Create individual folders and save here
        curName = curfile.stem
        curDIR = SWIS_DIR / "PROC" / curName
        if curDIR.is_dir():
            logger.info("Instance Processing Directory already exists")
        else:
            logger.info("Generating Instance Processing Directory")
            curDIR.mkdir()
        DL.to_pickle(curDIR / (curName + "_Unproc_HKTM.pickle"))


def HS_Extract(SWIS_DIR):
    """Searches through the typescript output .txt file and recreates a simple H&S.txt file"""

    logger.info("Processing SWIS H&S")

    txtFiles = PC_Fns.Find_Files(SWIS_DIR, "*.txt")
    HKFiles = PC_Fns.Find_Files(SWIS_DIR, "*HK.txt")
    SciFiles = PC_Fns.Find_Files(SWIS_DIR, '*SC.txt')
    HSFiles = list(set(txtFiles) - set(HKFiles) - set(SciFiles))

    # Read text file for H&S
    for curFile in HSFiles:

        # Create individual folders and save here
        curName = curFile.stem
        curDIR = SWIS_DIR / "PROC" / (curName + "_HK")
        if curDIR.is_dir():
            logger.info("Instance Processing Directory already exists")
        else:
            logger.info("Generating Instance Processing Directory")
            curDIR.mkdir()

        # New file within new folder
        writeFile = (curDIR / (curFile.stem + "_HS.txt"))
        if writeFile.exists():
            logger.info("HS.txt file already exists - deleting")
            writeFile.unlink()
        logger.info("Creating HS.txt file")
        wf = open(writeFile, 'w')

        # Scan through text log and save H&S lines
        with open(curFile, 'r') as f:
            logger.info("Reading %s", curFile.name)
            line = f.readline()
            while line != "":

                if "Requested" in line:
                    if "message with 45 bytes" in line:
                        wf.write(line)
                line = f.readline()
            wf.close()


if __name__ == "__main__":
    DIR = Path(
        input("Type the path to the folder where the Rover files are stored: "))

    PROC_DIR = DIR / "PROC"
    if PROC_DIR.is_dir():
        logger.info("Processing' Directory already exists")
    else:
        logger.info("Generating 'Processing' directory")
        PROC_DIR.mkdir()

    logging.basicConfig(filename=(PROC_DIR / 'processing.log'),
                        level=logging.INFO,
                        format='%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
    logger.info('\n\n\n\n')
    logger.info("Running SIWS.py as main")
    logger.info("Reading directory: %s", DIR)

    HK_Extract(DIR)
    HS_Extract(DIR)
    # Check_Sci(DIR)

    Unproc = PC_Fns.Find_Files(PROC_DIR, '*Unproc_HKTM.pickle')
    for curFile in Unproc:
        curDir = curFile.parent
        decodeRAW_HK.decode(curDir)
        Cal_HK.cal_HK(curDir)
        Plotter.HK_Overview(curDir)
    # Write function that compares the predicte image to the actual image
