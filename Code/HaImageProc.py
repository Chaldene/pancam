# -*- coding: utf-8 -*-
"""
Created on Tue Nov 12 10:12:39 2019

Function to go through a folder of Rover .ha files and produce the .raw
binaries of the images

@author: ucasbwh
"""

import PC_Fns
import math
import bitstruct
from collections import namedtuple
from datetime import datetime
from pathlib import Path
import logging
logger = logging.getLogger(__name__)
# import binascii  # Used if wanting to output ascii to terminal


class HaReadError(Exception):
    """error for unexpected things"""
    pass


def pkt_Len(PKT_HD):
    return int(PKT_HD[3][8:])


def HaImageProc(ROV_DIR):
    """Searches for .ha Rover files and creates raw binary files
    for each image found"""

    logger.info("Processing Rover .ha Files")

    # Define useful parameters
    LDT_HDR = namedtuple('LDT_HDR', ['Unit_ID', 'SEQ'])
    SCI_PC = {}
    SCI_IDS = {}
    LDTO = 16  # Offset before TM structure appear
    write_file = Path()

    Sci_Len = (0,)
    written_bytes = 0

    ROVER_HA = PC_Fns.Find_Files(ROV_DIR, "*.ha")
    if not ROVER_HA:
        logger.error("No files found - ABORTING")
        return

    for file in ROVER_HA:
        with open(file, 'r') as curFile:
            logger.info("Reading %s", file.name)

            # Check header of ha file matches that expected
            HA_HEADER = [next(curFile) for x in range(5)]
            if HA_HEADER[4] != "<BEGIN_DATA_BLOCK>\n":
                raise HaReadError("<BEGIN_DATA_BLOCK>: Line not found")

            # Read first packet header and determine packet type
            PKT_HD = [next(curFile)]
            while PKT_HD[0] != "<END_DATA_BLOCK>\n":
                # Packet header is made of 4 line entries
                # Determine packet length
                PKT_HD = PKT_HD + list(next(curFile) for x in range(3))
                if PKT_HD[3][0:8] != "<LENGTH>":
                    raise HaReadError("<LENGTH>: Line not found")

                # Look for first part of a LDT
                # Each data line can contain 32 bytes of data
                PKT_LINES = math.ceil(pkt_Len(PKT_HD)/32)
                if PKT_HD[2][12:-1] == "AB.TM.MRSS0697":
                    logger.info("New LDT part found")

                    # Read data as binary and decode LDT properties
                    TXT_Data = [next(curFile)[:-1] for x in range(PKT_LINES)]
                    PKT_Bin = bytes.fromhex(''.join(TXT_Data))
                    unpacked = bitstruct.unpack('u16u16', PKT_Bin[16:20])
                    Sci_ldt_hdr = LDT_HDR(*unpacked)

                    # Check to see if ID already exists if not add to dict
                    if Sci_ldt_hdr.Unit_ID in SCI_IDS:
                        #raise HaReadError("Two packets with same ID")
                        logger.warning("2 packets with the same ID found")
                    else:
                        SCI_IDS.update({Sci_ldt_hdr.Unit_ID: Sci_ldt_hdr.SEQ})

                    # print(binascii.hexlify(PKT_Bin[21:23]))
                    FileID = bitstruct.unpack('u1u4u2u1u8', PKT_Bin[21:23])
                    # PanCam identifier is 0x5
                    if not FileID[1] == 5:
                        logger.info("Not a PanCam file")
                        SCI_PC.update({Sci_ldt_hdr.Unit_ID: False})

                    # Filter for only science packets
                    elif not (FileID[2] & 0x2) == 0x2:
                        logger.info("Not a science packet, skipping")
                        SCI_PC.update({Sci_ldt_hdr.Unit_ID: False})

                    else:
                        # Check old length
                        if Sci_Len[0] != written_bytes:
                            write_file.replace(write_file.with_suffix(".part"))
                            logger.warning("Missing data")
                            logger.warning("Expected Write: %d", Sci_Len[0])
                            logger.warning("Actual Write: %d", written_bytes)
                            logger.warning("Packet ID: %s", PKT_HD[1])
                            logger.warning("Next LDT Unit ID: %s",
                                           str(Sci_ldt_hdr.Unit_ID))
                            logger.warning("Next LDT Seq ID: %s",
                                           str(Sci_ldt_hdr.SEQ))

                        # Get new length
                        SCI_PC.update({Sci_ldt_hdr.Unit_ID: True})
                        Sci_Len = bitstruct.unpack('u32', PKT_Bin[23:27])

                        # Create directory for binary file
                        IMG_RAW_DIR = ROV_DIR / "PROC" / "IMG_RAW"
                        if not IMG_RAW_DIR.is_dir():
                            logger.info("Generating 'IMG_RAW' directory")
                            IMG_RAW_DIR.mkdir()

                        # Write science data to binary file
                        write_dt = datetime.strptime(
                            PKT_HD[1][16:-1], '%d/%m/%Y %H:%M:%S.%f')
                        write_dts = write_dt.strftime('%y%m%d_%H%M%S_')
                        write_filename = write_dts + \
                            str(Sci_ldt_hdr.Unit_ID) + ".pci_raw"
                        write_file = IMG_RAW_DIR / write_filename
                        if write_file.exists():
                            write_file.unlink()
                            logger.info("Deleting file: %s", write_file.name)
                            # Need to add handling this case and raise exception
                        with open(write_file, 'wb') as wf:
                            logger.info("Creating file: %s", write_file.name)
                            wf.write(PKT_Bin[29:-2])
                            written_bytes = len(PKT_Bin[29:-2])

                # Second chunk of an LDT
                elif PKT_HD[2][12:-1] == "AB.TM.MRSS0698":

                    # Read data as binary and decode LDT properties
                    TXT_Data = [next(curFile)[:-1] for x in range(PKT_LINES)]
                    PKT_TXT = ''.join(TXT_Data)
                    PKT_Bin = bytes.fromhex(''.join(TXT_Data))
                    unpacked = bitstruct.unpack('u16u16', PKT_Bin[16:20])
                    Sci_ldt_hdr = LDT_HDR(*unpacked)

                    # Check to see if ID already exists if not add to dict
                    if not Sci_ldt_hdr.Unit_ID in SCI_IDS:
                        logger.error("New Packet without first part")
                        SCI_IDS.update({Sci_ldt_hdr.Unit_ID: Sci_ldt_hdr.SEQ})

                    # Check if PanCam file
                    if SCI_PC.get(Sci_ldt_hdr.Unit_ID):

                        # Verify sequence is correct
                        if SCI_IDS.get(Sci_ldt_hdr.Unit_ID)+1 != Sci_ldt_hdr.SEQ:
                            logger.warning("LDT parts not sequential")
                            logger.warning("Expected: %d", SCI_IDS.get(
                                Sci_ldt_hdr.Unit_ID)+1)
                            logger.warning("Got: %d", Sci_ldt_hdr.SEQ)
                            #raise HaReadError("LDT parts not sequential.")
                        SCI_IDS = {Sci_ldt_hdr.Unit_ID: Sci_ldt_hdr.SEQ}

                        # Write new data
                        with open(write_file, 'ab') as wf:
                            wf.write(PKT_Bin[20:-2])
                            written_bytes = written_bytes + len(PKT_Bin[20:-2])

                # Else skip the number of lines associated with the packet
                else:
                    for x in range(PKT_LINES):
                        next(curFile)
                PKT_HD = [next(curFile)]

    logger.info("Processing Rover .ha Files - Completed")


if __name__ == "__main__":
    DIR = Path(
        input("Type the path to the folder where the .ha log files are stored: "))

    logging.basicConfig(filename=(DIR / 'processing.log'),
                        level=logging.INFO,
                        format='%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
    logger.info('\n\n\n\n')
    logger.info("Running HaImageProc.py as main")
    logger.info("Reading directory: %s", DIR)

    PROC_DIR = DIR / "PROC"
    if PROC_DIR.is_dir():
        logger.info("Processing' Directory already exists")
    else:
        logger.info("Generating 'Processing' directory")
        PROC_DIR.mkdir()

    HaImageProc(DIR)
