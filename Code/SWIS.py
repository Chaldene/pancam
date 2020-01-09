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

logger = logging.getLogger(__name__)
logging.getLogger().addHandler(logging.StreamHandler())  # To stream to console


def HK_extract(SWIS_DIR):
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
        DL['Unix'] = DT[0].apply(lambda x: x[11:-12])
        DL['DT'] = pd.to_datetime(DL['Unix'], unit='ms')

        # Create individual folders and save here
        curName = curfile.stem
        curDIR = SWIS_DIR / "PROC" / curName
        if curDIR.is_dir():
            logger.info("Instance Processing Directory already exists")
        else:
            logger.info("Generating Instance Processing Directory")
            curDIR.mkdir()
        DL.to_pickle(curDIR / (curName + "_Unproc_HKTM.pickle"))


if __name__ == "__main__":
    DIR = Path(
        input("Type the path to thefolder where the Rover files are stored: "))

    logging.basicConfig(filename=(DIR / 'processing.log'),
                        level=logging.INFO,
                        format='%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
    logger.info('\n\n\n\n')
    logger.info("Running Rover.py as main")
    logger.info("Reading directory: %s", DIR)

    PROC_DIR = DIR / "PROC"
    if PROC_DIR.is_dir():
        logger.info("Processing' Directory already exists")
    else:
        logger.info("Generating 'Processing' directory")
        PROC_DIR.mkdir()

    HK_extract(DIR)
