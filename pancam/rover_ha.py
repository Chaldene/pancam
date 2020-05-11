"""
Created on Tue Nov 12 10:12:39 2019

Function to go through a folder of Rover .ha files and produce the .raw
binaries of the images and HK

@author: ucasbwh

"""

import numpy as np
import pandas as pd
import json
from collections import namedtuple
import binascii  # Used if wanting to output ascii to terminal
import math
import bitstruct
from datetime import datetime
from pathlib import Path
import logging

import pancam_fns

logger = logging.getLogger(__name__)
status = logging.getLogger('status')

# Global parameters
HaImageProcVer = {'HaImageProcVer': 0.5}
Found_IDS = {}
Buffer = {}
EndBuffer = {}
LDT_IDs = ["AB.TM.MRSS0697",
           "AB.TM.MRSS0698",
           "AB.TM.MRSS0699"]


class HaReadError(Exception):
    """error for unexpected things"""
    pass


class LDT_Properties(object):
    """Creates a LDT class for tracking those found"""

    def __init__(self, PKT_Bin):
        unpacked = bitstruct.unpack('u16u16u8u16u32u8u8', PKT_Bin[16:30])
        self.Unit_ID = unpacked[0]
        self.SEQ_No = unpacked[1]
        self.PART_ID = unpacked[2]
        self.FILE_ID = unpacked[3]
        self.FILE_SIZE = unpacked[4]
        self.FILE_TYPE = unpacked[5]
        self.SPARE = unpacked[6]

        # FileID definition given as part of LDT definition
        FID_unpack = bitstruct.unpack('u1u4u2u1u8', PKT_Bin[21:23])
        self.Identifier = FID_unpack[1]
        self.DataType = FID_unpack[2]
        self.TempFlag = FID_unpack[3]
        self.Counter = FID_unpack[4]

        # PanCam identifier is 0x5
        if self.Identifier == 5:
            self.PanCam = True
        else:
            logger.info("Not a PanCam file")
            self.PanCam = False

        # Check if a science type 0x2
        if self.DataType < 2:
            logger.info("Not a science packet")
            self.HK = True
        else:
            self.HK = False

        self.write = self.PanCam
        self.writtenLen = 0

    def setWriteFile(self, DIR, pkt_HD):
        # Determine FileName and check if exists
        write_filename = "PanCam_" + str(self.FILE_ID) + ".pci_raw.partial"
        self.write_file = DIR / write_filename
        pancam_fns.exist_unlink(self.write_file)
        logger.info("Creating file: %s", self.write_file.name)

    def updateWrite(self, Data):
        # Keep a running tally of the number of bytes written to file
        self.writtenLen += len(Data)

    def fileRename(self):
        # Once all parts of the file have been received then finish
        # Check written equals expected and rename file
        if self.writtenLen == self.FILE_SIZE:
            logger.info("Packet Length as expected - renaming")
            newFile = self.write_file.with_suffix("")
            self.write_file.replace(newFile)
            self.write_file = newFile
        else:
            logger.error("Warning written length: %d not equal to FILE_SIZE %d ",
                         self.writtenLen, self.FILE_SIZE)

    def moveHK(self):
        if self.DataType > 1:
            return
        elif self.DataType == 0:
            # HKNE
            newName = self.write_file.with_suffix(".HKNE_raw")
        elif self.DataType == 1:
            newName = self.write_file.with_suffix(".HKES_raw")
        logger.info("Moving HK Files")
        p = newName.absolute()
        # Move up a directory
        parent_dir = p.parents[1]
        self.write_file.replace(parent_dir / p.name)
        self.write_file = p / p.name

    def createJSON(self):
        if self.DataType < 2:
            return
        # Create dictionary of data to be written
        LDTSource = {
            'Source': 'Rover .ha files',
            'File ID': self.FILE_ID,
            'Unit ID': self.Unit_ID,
            'SEQ_No': self.SEQ_No,
            'PART_ID': self.PART_ID,
            'FILE_SIZE': self.FILE_SIZE,
            'Identifier': self.Identifier,
            'DataType': self.DataType,
            'Counter': self.Counter,
            'writtenLen': self.writtenLen
        }

        # Write LDT properties to a json file
        JSON_file = self.write_file.with_suffix(".json")
        TopLevDic = {"Processing Info": HaImageProcVer,
                     "LDT Information": LDTSource}
        pancam_fns.exist_unlink(JSON_file)
        with open(JSON_file, 'w') as f:
            json.dump(TopLevDic, f,  indent=4)


class LDT_Intermediate:
    """Creates a quick class for the LDT intermediate parts"""

    def __init__(self, PKT_Bin):
        unpacked = bitstruct.unpack('u16u16', PKT_Bin[16:20])
        self.Unit_ID = unpacked[0]
        self.SEQ_No = unpacked[1]


class LDT_End:
    """Creates a quick class for the LDT end part"""

    def __init__(self, PKT_Bin):
        unpacked = bitstruct.unpack('u16u16', PKT_Bin[16:20])
        self.Unit_ID = unpacked[0]
        self.SEQ_No = unpacked[1]


def HaScan(ROV_DIR):
    """Searches for .ha Rover files and creates raw binary files
    for each image found"""
    logger.info("Processing Rover .ha Files")

    # Find Files
    ROVER_HA = pancam_fns.Find_Files(ROV_DIR, "*.ha")
    if not ROVER_HA:
        logger.error("No files found - ABORTING")
        return

    # Create directory for binary file
    IMG_RAW_DIR = ROV_DIR / "PROC" / "IMG_RAW"
    if not IMG_RAW_DIR.is_dir():
        logger.info("Generating 'IMG_RAW' directory")
        IMG_RAW_DIR.mkdir()

    # Search through .ha files
    PKT_HD = [None] * 4

    for file in ROVER_HA:
        with open(file, 'r') as curFile:
            logger.info("Reading %s", file.name)
            # Read ha header and perform basic check
            HA_HEADER = [next(curFile) for x in range(5)]
            if HA_HEADER[4] != "<BEGIN_DATA_BLOCK>\n":
                raise HaReadError("<BEGIN_DATA_BLOCK>: Line not found")

            # Read first packet header and determine packet type
            PKT_HD[0] = next(curFile)
            while PKT_HD[0] != "<END_DATA_BLOCK>\n":
                PKT_HD[1:3] = [next(curFile) for x in range(3)]

                if PKT_HD[3][0:8] != "<LENGTH>":
                    raise HaReadError("<LENGTH>: Line not found")

                # Look for LDT Packets
                PKT_ID = PKT_HD[2][12:-1]
                # Determine number of lines in data entry
                PKT_LINES = math.ceil(pkt_Len(PKT_HD)/32)
                if PKT_ID in LDT_IDs:
                    # Read ha file using repeating pattern a packet head is 4 lines
                    HaPacketDecode(PKT_HD, PKT_ID, PKT_LINES,
                                   curFile, IMG_RAW_DIR)
                else:
                    for _ in range(PKT_LINES):
                        next(curFile)

                PKT_HD[0] = next(curFile)

    # Final buffer check
    # Merge buffers
    FinalBuf = {**Buffer, **EndBuffer}
    if len(FinalBuf) > 0:
        logger.info("Items remaining in buffers")
        for item in FinalBuf:
            logger.error(item)
            if item[0] in Found_IDS:
                Cur_LDT = Found_IDS.get(item[0])
                checkBuffers(Cur_LDT)
            else:
                logger.error(
                    "Initial LDT part not found for UnitID: %d", item[0])

    if len(Buffer) + len(EndBuffer) > 0:
        logger.info("Still %d items in buffer", len(Buffer)+len(EndBuffer))
    else:
        logger.info("LDT Buffer Empty")
    logger.info("Processing Rover .ha Files - Completed")


def HaPacketDecode(PKT_HD, PKT_ID, PKT_LINES, curFile, IMG_RAW_DIR):
    """Decodes the first packet"""

    TXT_Data = [next(curFile)[:-1] for x in range(PKT_LINES)]
    PKT_Bin = bytes.fromhex(''.join(TXT_Data))

    # First LDT Part
    if PKT_ID == LDT_IDs[0]:
        LDT_Cur_Pkt = LDT_Properties(PKT_Bin)
        if LDT_Cur_Pkt.PanCam:
            logger.info("New PanCam LDT part found with file ID: %s, and unitID %s",
                        LDT_Cur_Pkt.FILE_ID, LDT_Cur_Pkt.Unit_ID)

        # If write is True, check to see if ID already exists

        # Check to see if ID already exists if not add to dict
        if (LDT_Cur_Pkt.Unit_ID in Found_IDS) and LDT_Cur_Pkt.PanCam:
            logger.error(
                "2 initial packets with the same ID found, first ignored.")

        # Write data then add to dictionary
        if LDT_Cur_Pkt.write:
            LDT_Cur_Pkt.setWriteFile(IMG_RAW_DIR, PKT_HD)
            writeBytesToFile(LDT_Cur_Pkt, PKT_Bin[29:-2])
        Found_IDS.update({LDT_Cur_Pkt.Unit_ID: LDT_Cur_Pkt})

    # Second LDT Part
    elif PKT_ID == LDT_IDs[1]:
        IntP = LDT_Intermediate(PKT_Bin)

        # Check to see if Unit ID already started if not add to buffer
        if IntP.Unit_ID not in Found_IDS:
            logger.info("New Packet without first part - adding to buffer")
            Buffer.update({(IntP.Unit_ID, IntP.SEQ_No): PKT_Bin[20:-2]})

        else:
            Cur_LDT = Found_IDS.get(IntP.Unit_ID)

            # Check file should be written
            if Cur_LDT.write:
                # Verify SEQ number is as expected
                Expected_SEQ = (Cur_LDT.Unit_ID, Cur_LDT.SEQ_No + 1)
                if Expected_SEQ == (IntP.Unit_ID, IntP.SEQ_No):
                    writeBytesToFile(Cur_LDT, PKT_Bin[20:-2])
                    Cur_LDT.SEQ_No += 1
                    Found_IDS.update({IntP.Unit_ID: Cur_LDT})

                # Else add to buffer and try to rebuild
                else:
                    logger.warning("LDT parts not sequential")
                    logger.warning("Expected: %d", Expected_SEQ[1])
                    logger.warning("Got: %d", IntP.SEQ_No)
                    Buffer.update(
                        {(IntP.Unit_ID, IntP.SEQ_No): PKT_Bin[20:-2]})
                    logger.warning(
                        "Added LDT part to buffer: %d", IntP.SEQ_No)
                    checkBuffers(Cur_LDT)

    elif PKT_ID == LDT_IDs[2]:
        # Check end of file and rename properly
        EndP = LDT_End(PKT_Bin)
        logger.info("End Packet Received with unitID: %d", EndP.Unit_ID)

        # Check to see if Unit ID already started if not add to dict
        if EndP.Unit_ID not in Found_IDS:
            logger.error("End Packet without first part - adding to EndBuffer")
            EndBuffer.update({(EndP.Unit_ID, EndP.SEQ_No): PKT_Bin[20:-2]})

        else:
            Cur_LDT = Found_IDS.get(EndP.Unit_ID)

            # Check file should be written
            if Cur_LDT.write:
                # Verify SEQ number is as expected
                Expected_SEQ = (Cur_LDT.Unit_ID, Cur_LDT.SEQ_No + 1)
                if Expected_SEQ == (EndP.Unit_ID, EndP.SEQ_No):
                    Cur_LDT.SEQ_No += 1
                    CompleteTelemetry(Cur_LDT)
                    Found_IDS.update({EndP.Unit_ID: Cur_LDT})

                else:
                    logger.warning("END LDT not sequential")
                    logger.warning("Expected: %d", Expected_SEQ[1])
                    logger.warning("Got: %d", EndP.SEQ_No)
                    EndBuffer.update(
                        {(EndP.Unit_ID, EndP.SEQ_No): PKT_Bin[20:-2]})
                    logger.warning(
                        "Added End part to buffer: %d, %d", EndP.Unit_ID, EndP.SEQ_No)
                    checkBuffers(Cur_LDT)


def checkBuffers(Cur_LDT):
    """Function checks the LDT part buffer and end buffer to add parts already found out of sequence"""

    Expected_SEQ = (Cur_LDT.Unit_ID, Cur_LDT.SEQ_No + 1)

    # First partial buffer
    # Check if expected SEQ_No packets already exists in the buffer
    while Expected_SEQ in Buffer:
        # Write to file the value in the buffer found
        writeBytesToFile(Cur_LDT, Buffer[Expected_SEQ])
        Buffer.pop(Expected_SEQ)
        logger.warning(
            "Wrote LDT part from buffer: %d", Expected_SEQ[1])
        Cur_LDT.SEQ_No += 1
        Found_IDS.update({Cur_LDT.Unit_ID: Cur_LDT})
        Expected_SEQ = (Expected_SEQ[0], Expected_SEQ[1] + 1)

    # Then End Buffer
    # Determine if the end packet has been found
    if Expected_SEQ in EndBuffer:
        logger.warning("End LDT now fits: %d", Expected_SEQ[1])
        Cur_LDT.SEQ_No += 1
        CompleteTelemetry(Cur_LDT)
        EndBuffer.pop(Expected_SEQ)
        Found_IDS.update({Cur_LDT.Unit_ID: Cur_LDT})


def pkt_Len(PKT_HD):
    return int(PKT_HD[3][8:])


def writeBytesToFile(CurLDT, Bytes):
    """Funtion for writing to data file"""
    with open(CurLDT.write_file, 'ab') as wf:
        wf.write(Bytes)
        CurLDT.writtenLen += len(Bytes)
    return


def RestructureHK(ROV_DIR):
    """Searches for .HKNE_raw and .HKES_raw generated from HaScan, produces the a single Unrpoc_HKTM pickle file"""
    logger.info("Processing any .ha HK that has been created")

    # Find Files
    RAW_ES = pancam_fns.Find_Files(ROV_DIR, "*.HKES_raw")
    if not RAW_ES:
        logger.info("No .ha generated HK files found")
        return

    RAW_NE = pancam_fns.Find_Files(ROV_DIR, "*.HKNE_raw")
    if not RAW_NE:
        logger.info("No .ha generated HK files found")

    ES = pd.DataFrame(columns=['RAW'])
    NE = pd.DataFrame(columns=['RAW'])
    raw_data = []

    es_line_len = 72
    ne_line_len = 88

    # Read files
    for curfile in RAW_ES:
        # Ignore if not all packets are complete
        if curfile.stat().st_size % es_line_len != 0:
            target = curfile.with_suffix('.HKES_raw.ignore')
            pancam_fns.exist_unlink(target)
            curfile.rename(target)
            continue

        with open(curfile, 'rb') as f:
            logger.info("Reading %s", f.name)
            line = f.read(es_line_len)
            while len(line) == es_line_len:
                raw_data.append(line)
                line = f.read(es_line_len)

    ES['RAW'] = raw_data
    raw_data = []

    for curfile in RAW_NE:
        # Ignore if not all packets are complete
        if curfile.stat().st_size % ne_line_len != 0:
            target = curfile.with_suffix('.HKNE_raw.ignore')
            pancam_fns.exist_unlink(target)
            curfile.rename(target)
            continue

        with open(curfile, 'rb') as f:
            logger.info("Reading %s", f.name)
            line = f.read(ne_line_len)
            while len(line) == ne_line_len:
                raw_data.append(line)
                line = f.read(ne_line_len)

    NE['RAW'] = raw_data

    # Combine HK data into a single dataframe
    RTM = pd.concat([ES, NE], axis=0, join='outer')
    RTM = pancam_fns.ReturnCUC_RAW(RTM, RTM['RAW'])
    RTM['Source'] = '.ha'
    RTM = RTM.sort_values(by='Pkt_CUC').reset_index(drop=True)

    # Then save file
    curName = (RAW_ES + RAW_NE)[0].stem
    RTM.to_pickle(ROV_DIR / (curName + "_ha_Unproc_HKTM.pickle"))


def CompleteTelemetry(Cur_LDT):
    """Once a telemetry has been fully reassembled, rename and create JSON"""
    Cur_LDT.fileRename()
    Cur_LDT.moveHK()
    Cur_LDT.createJSON()
    Found_IDS.pop(Cur_LDT.Unit_ID)


def compareHaCSV(ProcDir):
    """Looks for HK generated by .csv and .ha and compares the two. 
    The majority of the time the .ha files contain more data."""

    logger.info("Comparing .ha generated HK to .csv generated HK")
    # Find Files
    RAW_ha = pancam_fns.Find_Files(
        ProcDir, "*_ha_Unproc_HKTM.pickle", SingleFile=True)
    if not RAW_ha:
        logger.info("No .ha generated HK files found")
        return

    RAW_csv = pancam_fns.Find_Files(
        ProcDir, "*_csv_Unproc_HKTM.pickle", SingleFile=True)
    if not RAW_csv:
        logger.info("No .csv generated HK files found")
        return

    ha_bin = pd.read_pickle(RAW_ha[0])
    csv = pd.read_pickle(RAW_csv[0])
    csv_bin = pd.DataFrame()
    csv_bin['RAW'] = csv['RAW'].apply(lambda x: bytearray.fromhex(x))
    csv_bin = pancam_fns.ReturnCUC_RAW(csv_bin, csv_bin['RAW'])

    result = pd.merge(ha_bin, csv_bin, on=['Pkt_CUC'], how='right')
    comp = result['RAW_x'] != result['RAW_y']
    mismatch = result[comp]

    if (len(result)-len(csv_bin)) > 0:
        # First check that all the CUC entries within csv_bin are in ha_bin
        logger.error(
            "HK Data contained entries within .csv HK not present in .ha HK")

    elif len(mismatch) > 0:
        # Next confirm that the RAW is equivalent, if so delete .csv HK
        logger.error(
            "HK Data in .ha file did not match that of .csv with same CUC times")

    else:
        logger.info("HK Data matches")
        logger.info("Removing .csv HK file: %s", RAW_csv[0].name)
        Path.unlink(RAW_csv[0])


if __name__ == "__main__":

    dir = Path(
        input("Type the path to the folder where the .ha log files are stored: "))

    proc_dir = dir / "PROC"
    if proc_dir.is_dir():
        status.info("Processing' Directory already exists")
    else:
        status.info("Generating 'Processing' directory")
        proc_dir.mkdir()

    logger, status = pancam_fns.setup_logging()
    pancam_fns.setup_proc_logging(logger, proc_dir)

    logger.info('\n\n\n\n')
    logger.info("Running HaImageProc.py as main")
    logger.info("Reading directory: %s", proc_dir)

    HaScan(dir)
    RestructureHK(proc_dir)
    compareHaCSV(proc_dir)
