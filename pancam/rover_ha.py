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
ProcInfo = {'HaImageProcVer': 0.7}
Found_IDS = {}
Buffer = {}
EndBuffer = {}
LDT_IDs = ["AB.TM.MRSS0697",
           "AB.TM.MRSS0698",
           "AB.TM.MRSS0699"]
RMSW_VER = 2.0


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

        self.write = True
        self.writtenLen = 0
        self.write_completed = False
        self.write_occurance = 0

    def setWriteFile(self, DIR, pkt_HD):
        if self.PanCam:
            # Create filename
            write_filename = "PanCam_" \
                + str(self.FILE_ID) \
                + "_" \
                + str(self.write_occurance).zfill(2) \
                + ".ldt_raw.partial"
            self.write_file = DIR / 'IMG_RAW' / write_filename

        else:
            write_filename = 'LDT_' \
                + str(self.FILE_ID) \
                + '_' \
                + str(self.write_occurance).zfill(2) \
                + '.nav_raw.partial'
            self.write_file = DIR / 'LDT_RAW' / write_filename

        pancam_fns.exist_unlink(self.write_file)
        logger.info("Creating file: %s", self.write_file.name)

    def updateWrite(self, Data):
        # Keep a running tally of the number of bytes written to file
        self.writtenLen += len(Data)

    def moveHK(self):
        if not self.PanCam:
            return
        if self.DataType > 1:
            return
        elif self.DataType == 0:
            # HKNE
            newName = self.write_file.with_suffix(".HKNE_raw").name
        elif self.DataType == 1:
            # HKES
            newName = self.write_file.with_suffix(".HKES_raw").name
        logger.info("Moving HK Files")
        # Move up a directory
        newDir = self.write_file.parents[1]
        pancam_fns.exist_unlink(newDir / newName, logging.WARNING)

        logger.info("Moving file: %s up a dir", newName)
        self.write_file.rename(newDir / newName)
        self.write_file = newDir / newName

    def verifyImg(self):

        global RMSW_VER

        # Newer software has an extra 16bytes to account for image compression structure
        if RMSW_VER > 3:
            raw_img_sze = 2097200 + 14
        else:
            raw_img_sze = 2097200

        # Check written equals expected and rename file
        if self.writtenLen == raw_img_sze:
            logger.info("Restructuring to .pci_raw format")
            newFile = self.write_file.with_suffix(".pci_raw")
            pancam_fns.exist_unlink(newFile)
            with open(self.write_file, 'rb') as in_file:
                with open(newFile, 'wb') as out_file:
                    out_file.write(
                        in_file.read()[:2097200])
            self.write_file.unlink()
            self.write_file = newFile

        # Check if multiple files in the same packet
        elif self.writtenLen % raw_img_sze == 0:
            parts = self.writtenLen / raw_img_sze
            logger.info("LDT File likely contains {parts} images")

            newFile = self.write_file.with_suffix(".pci_multiple")
            pancam_fns.exist_unlink(newFile)
            with open(self.write_file, 'rb') as in_file:
                with open(newFile, 'wb') as out_file:
                    out_file.write(in_file.read())
            self.write_file.unlink()
            self.write_file = newFile

        else:
            logger.info(
                "Image likely compressed - renaming")
            newFile = self.write_file.with_suffix(
                ".ldt_raw.ignore")
            pancam_fns.exist_unlink(newFile)
            self.write_file.rename(newFile)
            self.write_file = newFile

    def createJSON(self):
        # If HK ignore
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
        TopLevDic = {"Processing Info": ProcInfo,
                     "LDT Information": LDTSource}
        pancam_fns.exist_unlink(JSON_file)
        with open(JSON_file, 'w') as f:
            json.dump(TopLevDic, f,  indent=4)

    def complete_file(self):

        if self.write_completed:
            logger.error("%s unitID completed but attempt to complete again!")
        else:
            self.write_completed = True
            logger.info("%s unitID now complete", self.Unit_ID)
            # Once all parts of the file have been received then finish

            if (self.PanCam):
                if self.writtenLen == self.FILE_SIZE:
                    logger.info("Packet Length as expected - renaming")
                    # Remove .partial from file name
                    newFile = self.write_file.with_suffix("")
                    pancam_fns.exist_unlink(newFile)
                    self.write_file.rename(newFile)
                    self.write_file = newFile

                    if self.HK:
                        self.moveHK()
                    else:
                        self.verifyImg()

                else:
                    logger.error("Warning written length: %d not equal to FILE_SIZE %d ",
                                 self.writtenLen, self.FILE_SIZE)

        self.navcam()
        self.createJSON()

    def navcam(self):
        if self.PanCam:
            return

        # Check if expected NavCam size just for 1024x1024
        if self.FILE_SIZE == 1024*1024 + 68:
            logger.info(
                "FileID: %s Packet length matches NavCam", self.FILE_ID)
            name_new = self.write_file.with_suffix('.pgm').name
            dir_nav = self.write_file.parents[1] / 'NAVCAM'
            file_targ = dir_nav / name_new
            pancam_fns.exist_unlink(file_targ)

            logger.info('Creating pgm file: %s', name_new)
            pgm_hdr = bytes('P5\n1024 1024 255\n', 'utf8')
            src = open(self.write_file, 'rb')
            src.read(68)

            # Write file to NavCam
            with open(file_targ, 'wb') as f:
                f.write(pgm_hdr)
                f.write(src.read())

            src.close()

    def setOccurance(self, occurance):
        self.write_occurance = occurance


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

    global Found_IDS
    global RMSW_VER

    # Find Files
    ROVER_HA = pancam_fns.Find_Files(ROV_DIR, "*.ha")
    if not ROVER_HA:
        logger.error("No files found - ABORTING")
        return

    # Determine RMSW Version
    config_files = pancam_fns.Find_Files(
        ROV_DIR, "config.json", SingleFile=True)
    if not config_files:
        logger.error(
            f"No config.json file found. Assuming RMSW Version is {RMSW_VER}")
    else:
        with open(config_files[0], 'r') as curfile:
            config = json.load(curfile)
            RMSW_VER = config['Source Details']['RMSW Ver']
            status.info(f"Using structure for RMSW_Ver {RMSW_VER}")

    # Update Processing info
    ProcInfo.update({'RMSW Version': RMSW_VER})

    # Create directories
    dir_proc = ROV_DIR / "PROC"
    if not dir_proc.is_dir():
        logger.info("Generating 'PROC' directory")
        dir_proc.mkdir()

    IMG_RAW_DIR = dir_proc / "IMG_RAW"
    if not IMG_RAW_DIR.is_dir():
        logger.info("Generating 'IMG_RAW' directory")
        IMG_RAW_DIR.mkdir()

    LDT_RAW_DIR = dir_proc / 'LDT_RAW'
    if not LDT_RAW_DIR.is_dir():
        logger.info("Generating 'LDT_RAW' directory")
        LDT_RAW_DIR.mkdir()

    dir_nav = dir_proc / "NAVCAM"
    if not dir_nav.is_dir():
        logger.info("Generating 'NAVCAM' directory")
        dir_nav.mkdir()

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
                                   curFile, dir_proc)
                else:
                    for _ in range(PKT_LINES):
                        next(curFile)

                PKT_HD[0] = next(curFile)

    # Final buffer check
    # Merge buffers
    FinalBuf = {**Buffer, **EndBuffer}
    if len(FinalBuf) > 0:
        logger.error("Items remaining in buffers")
        for item in FinalBuf:
            logger.info(item)
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
        status.info("LDT Buffer Now Empty")

    if len(Found_IDS) > 0:
        msg = (f"Found the following PanCam LDT files: \n")
        for _, value in Found_IDS.items():
            msg += f"\t\t{value.FILE_ID}\n"
        status.info(msg)

    # Clean up directories if empty
    if not (any(IMG_RAW_DIR.iterdir())):
        IMG_RAW_DIR.rmdir()
        logger.info(f"No files found in IMG_RAW dir. Removing")

    if not (any(LDT_RAW_DIR.iterdir())):
        LDT_RAW_DIR.rmdir()
        logger.info(f"No files found in LDT_RAW dir. Removing")

    if not (any(dir_nav.iterdir())):
        dir_nav.rmdir()
        logger.info(f"No files found in NAVCAM dir. Removing")

    logger.info("Processing Rover .ha Files - Completed")


def HaPacketDecode(PKT_HD, PKT_ID, PKT_LINES, curFile, dir_proc):
    """Decodes the first packet"""

    global Found_IDS

    TXT_Data = [next(curFile)[:-1] for x in range(PKT_LINES)]
    PKT_Bin = bytes.fromhex(''.join(TXT_Data))

    # First LDT Part
    if PKT_ID == LDT_IDs[0]:
        LDT_Cur_Pkt = LDT_Properties(PKT_Bin)

        if LDT_Cur_Pkt.PanCam:
            log_message = 'New PanCam LDT part'

        else:
            log_message = '----Other LDT part'

        logger.info(log_message + ' found with file ID: %s, and unitID %s',
                    LDT_Cur_Pkt.FILE_ID, LDT_Cur_Pkt.Unit_ID)

        # If write is True, check to see if ID already exists
        if LDT_Cur_Pkt.write and (LDT_Cur_Pkt.Unit_ID in Found_IDS):
            status.info(
                "Multiple initial packets with the same ID found.")
            prev_count = Found_IDS.get(LDT_Cur_Pkt.Unit_ID).write_occurance
            LDT_Cur_Pkt.setOccurance(prev_count + 1)

            # Check to see if previous ID was not already completed
            if not Found_IDS.get(LDT_Cur_Pkt.Unit_ID).write_completed:
                logger.error(
                    "Previous FileID not completed, now adding to second FileID")

        # Write packet contents to file
        if LDT_Cur_Pkt.write:
            LDT_Cur_Pkt.setWriteFile(dir_proc, PKT_HD)
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
                    Found_IDS.update({EndP.Unit_ID: Cur_LDT})
                    Cur_LDT.complete_file()

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

    global Found_IDS

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
        Found_IDS.update({Cur_LDT.Unit_ID: Cur_LDT})
        Cur_LDT.complete_file()
        EndBuffer.pop(Expected_SEQ)


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

    ES = pd.DataFrame()
    NE = pd.DataFrame()
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
    csv_bin['RAW'] = csv['RAW'].apply(lambda x: bytes.fromhex(x))
    csv_bin = pancam_fns.ReturnCUC_RAW(csv_bin, csv_bin['RAW'])

    result = pd.merge(ha_bin, csv_bin, on=['Pkt_CUC'], how='inner')
    comp = result['RAW_x'] != result['RAW_y']
    mismatch = result[comp]

    if (len(result)-len(csv_bin)) < 0:
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
