# -*- coding: utf-8 -*-
"""Created on Thu Dec 12 13:09 2019.

@author: ucasbwh
"""
# Converts outputs from the SWIS into readable format
# Seperate each session into a new Folder for checking

import pandas as pd
from pathlib import Path
import logging
import csv
import re

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


def nsvf_parse(packet_log: Path):
    """Searches through the NSVF generated packet_log and generates new files from any found PanCam telemetry.

    Arguments:
        packet_log {File Path} -- File Path of .txt file to search through for telemetry.

    Generates:
        H+S.txt -- ASCII txt file of all PanCam health and status.
        HK.txt  -- ASCII file of the PanCam HK telemetry
        Sci.txt -- ASCII file of the PanCam Sci telemetry.
        TC.txt  -- ASCII file of the PanCam TC responses.

        hs.pickle -- Pandas pickle file of H+S in the standard format for this tool.
    """

    # Function Constants

    # Regular expressions for log format
    in_re = re.compile(r"^\[IN=[0-9]+\]$")
    sz_re = re.compile(r"^\[SZ=[0-9]+\]$")

    # PanCam logical address
    pc_log_addr = 0x41
    pc_hs_rowlen = 45

    logger.info("Processing SWIS NSVF log")

    if not packet_log.exists():
        logger.error("nsvf_file %s does not exist", packet_log)
        return

    # Create a PROC directory if does not already exist
    proc_dir = packet_log.parent / 'PROC'
    if not proc_dir.is_dir():
        proc_dir.mkdir()

    # Next prepare files to be written
    file = {}
    f_acc = {}
    f_wri = {}

    file['hs'] = proc_dir / 'H+S.txt'
    file['hk'] = proc_dir / 'HK.txt'
    file['tc'] = proc_dir / 'TC.txt'
    file['sc'] = proc_dir / 'Sci.txt'

    for key, value in file.items():
        if value.exists():
            value.unlink()
            logger.info("Deleting file: %s", value.name)
        f_acc[key] = open(value, 'w')
        f_wri[key] = csv.writer(f_acc[key], delimiter=' ', lineterminator='\r')

    # Open file and check format is as expcted
    # Contains ..[IN=..].. and ..[SZ=..].., ..[EOP] at the end of each line

    with open(packet_log) as logfile:
        reader = csv.reader(logfile, delimiter=' ')
        logger.info("Reading file %s", packet_log.name)
        for row in reader:
            # First check that row ends in [EOP]
            if row[-1] != '[EOP]':
                logger.error("Row does not end in '[EOP]': %s", row)
                continue

            # Verify row contains [IN=..] in correct position
            if not in_re.match(row[1]):
                logger.error("Row no match for '[IN..]': %s", row)
                continue

            # Verify row contains [SZ=..] in correct position
            if not sz_re.match(row[2]):
                logger.error("Row no match for '[SZ..]': %s", row)
                continue

            # Verify row size matches that stated in [SZ=..]
            row_size = int(row[2][4:-1])
            if row_size != len(row[4:-1]):
                logger.error(
                    "Row row does not match expected length %d bytes: %s", row_size, row)
                continue

            # Filter by Logical address
            log_addr = int(row[8], 16)

            if log_addr == pc_log_addr:
                # Assume 45 byte lines are H+S
                if row_size == pc_hs_rowlen:
                    row_red = row
                    row_red[1:4] = []
                    row_red[-1:] = []
                    row_red[0] += ';'
                    f_wri['hs'].writerow(row_red)

                # If 8 byte line assume TC
                elif row_size == 8:
                    f_wri['tc'].writerow(row)

                # If 85 or 101 byte line assume HK
                elif (row_size == 85) | (row_size == 101):
                    f_wri['hk'].writerow(row)

                # Else assume Sci
                else:
                    f_wri['sc'].writerow(row)

    for key, value in f_acc.items():
        value.close()

    # Create a H&S Pickle File
    hs_head = ['Time', 'RAW']
    hs = pd.read_csv(file['hs'], sep=';', header=None, names=hs_head)
    hs.to_pickle(proc_dir / "hs_raw.pickle")
    logger.info("PanCam H+S pickled.")

    logger.info("--Parsing SWIS NSVF log completed.")


if __name__ == "__main__":
    dir = Path(
        input("Type the path to the folder where the Rover files are stored: "))

    proc_dir = dir / "PROC"
    if proc_dir.is_dir():
        logger.info("Processing' Directory already exists")
    else:
        logger.info("Generating 'Processing' directory")
        proc_dir.mkdir()

    logging.basicConfig(filename=(proc_dir / 'processing.log'),
                        level=logging.INFO,
                        format='%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
    logger.info('\n\n\n\n')
    logger.info("Running SIWS.py as main")
    logger.info("Reading directory: %s", dir)

    routeA = PC_Fns.Find_Files(dir, 'Router_A_packet.log', SingleFile=True)[0]
    nsvf_parse(routeA)

    # HK_Extract(DIR)
    # HS_Extract(DIR)
    # # Check_Sci(DIR)

    # Unproc = PC_Fns.Find_Files(PROC_DIR, '*Unproc_HKTM.pickle')
    # for curFile in Unproc:
    #     curDir = curFile.parent
    #     decodeRAW_HK.decode(curDir)
    #     Cal_HK.cal_HK(curDir)
    #     Plotter.HK_Overview(curDir)
    # Write function that compares the predicte image to the actual image
