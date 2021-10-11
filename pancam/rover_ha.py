"""
Created on Tue Nov 12 10:12:39 2019

Function to go through a folder of Rover .ha files and produce the .raw
binaries of the images and HK

@author: ucasbwh

"""

from re import split
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
ProcInfo = {'HaImageProcVer': 0.8}
Found_IDS = {}
Buffer = {}
EndBuffer = {}
LDT_IDs = ["AB.TM.MRSS0697",
           "AB.TM.MRSS0698",
           "AB.TM.MRSS0699"]
RMSW_VER = 2.0


class HaReadError(Exception):
    """error for unexpected things"""


class LdtProperties(object):
    """Creates a LDT class for tracking those found"""

    def __init__(self, PKT_Bin):
        unpacked = bitstruct.unpack('u16u16u8u16u32u8u8', PKT_Bin[16:30])
        self.unit_id = unpacked[0]
        self.seq_no = unpacked[1]
        self.part_id = unpacked[2]
        self.file_id = unpacked[3]
        self.file_size = unpacked[4]
        self.file_type = unpacked[5]
        self.spare = unpacked[6]

        # FileID definition given as part of LDT definition
        FID_unpack = bitstruct.unpack('u1u4u2u1u8', PKT_Bin[21:23])
        self.identifier = FID_unpack[1]
        self.data_type = FID_unpack[2]
        self.temp_flag = FID_unpack[3]
        self.counter = FID_unpack[4]

        # PanCam identifier is 0x5
        if self.identifier == 5:
            self.pancam = True
        else:
            logger.info("Not a PanCam file")
            self.pancam = False

        # Check if a science type 0x2
        if self.data_type < 2:
            logger.info("Not a science packet")
            self.hk = True
        else:
            self.hk = False

        self.write = True
        self.written_len = 0
        self.write_completed = False
        self.write_occurrence = 0

    def set_write_file(self, dir):
        """Generates a path for the file found either ldt_raw or nav_raw"""
        if self.pancam:
            # Create filename
            write_filename = "PanCam_" \
                + str(self.file_id) \
                + "_" \
                + str(self.write_occurrence).zfill(2) \
                + ".ldt_raw.partial"
            self.write_file = dir / 'IMG_RAW' / write_filename

        else:
            write_filename = 'LDT_' \
                + str(self.file_id) \
                + '_' \
                + str(self.write_occurrence).zfill(2) \
                + '.nav_raw.partial'
            self.write_file = dir / 'LDT_RAW' / write_filename

        pancam_fns.exist_unlink(self.write_file)
        logger.info("Creating file: %s", self.write_file.name)

    def update_write(self, Data):
        """The running tally of the number of bytes written to the file"""
        self.written_len += len(Data)

    def move_hk(self):
        """Moves PanCam HK to PROC directory and renames as appropriate for HKNE or HKES"""
        if not self.pancam:
            return
        if self.data_type > 1:
            return
        elif self.data_type == 0:
            # HKNE
            new_hk_filename = self.write_file.with_suffix(".HKNE_raw").name
        elif self.data_type == 1:
            # HKES
            new_hk_filename = self.write_file.with_suffix(".HKES_raw").name
        logger.info("Moving HK Files")
        # Move up a directory
        new_hk_dir = self.write_file.parents[1]
        pancam_fns.exist_unlink(new_hk_dir / new_hk_filename, logging.WARNING)

        logger.info("Moving file: %s up a dir", new_hk_filename)
        self.write_file.rename(new_hk_dir / new_hk_filename)
        self.write_file = new_hk_dir / new_hk_filename

    def verify_img(self):

        global RMSW_VER

        # Newer software has an extra 16bytes to account for image compression structure
        if RMSW_VER > 3:
            raw_img_sze = 2097200 + 14
        else:
            raw_img_sze = 2097200

        tm_pkt_hdr = pkt_identify(self.write_file)

        # Check for uncompressed files first
        # 1024 x 1024 pixels
        # each pixel 16-bit
        # plus 37 bytes of ancil header
        if (tm_pkt_hdr['data_len'] == (1024*1024*2 + 37)):
            logger.info("Restructuring to .pci_raw format")
            new_file = self.write_file.with_suffix(".pci_raw")
            pancam_fns.exist_unlink(new_file)
            with open(self.write_file, 'rb') as in_file:
                with open(new_file, 'wb') as out_file:
                    out_file.write(
                        in_file.read()[:2097200])
            self.write_file.unlink()
            self.write_file = new_file

        # Check if multiple files in the same packet
        elif self.written_len % raw_img_sze == 0:
            parts = self.written_len / raw_img_sze
            logger.info("LDT File likely contains %s images", parts)

            new_file = self.write_file.with_suffix(".pci_multiple")
            pancam_fns.exist_unlink(new_file)
            with open(self.write_file, 'rb') as in_file:
                with open(new_file, 'wb') as out_file:
                    out_file.write(in_file.read())
            self.write_file.unlink()
            self.write_file = new_file

        else:
            logger.info(
                "Image likely compressed - moving to compressed folder")

            # Move to a compressed folder
            new_dir = self.write_file.parents[1] / "COMPRESSED_IMG"
            new_file = self.write_file.with_suffix(".ldt_file_ccsds").name

            pancam_fns.exist_unlink(new_dir / new_file, logging.WARNING)

            self.write_file.rename(new_dir / new_file)
            self.write_file = new_dir / new_file

    def create_json(self):
        """Creates an accompanying JSON containing information of source LDT file"""
        # If HK ignore
        if self.data_type < 2:
            return

        # Create dictionary of data to be written
        LDTSource = {
            'Source': 'Rover .ha files',
            'File ID': self.file_id,
            'Unit ID': self.unit_id,
            'SEQ_No': self.seq_no,
            'PART_ID': self.part_id,
            'FILE_SIZE': self.file_size,
            'Identifier': self.identifier,
            'DataType': self.data_type,
            'Counter': self.counter,
            'writtenLen': self.written_len
        }

        # Write LDT properties to a json file
        json_file = self.write_file.with_suffix(".json")
        top_lvl_dict = {"Processing Info": ProcInfo,
                        "LDT Information": LDTSource}
        pancam_fns.exist_unlink(json_file)
        with open(json_file, 'w') as f:
            json.dump(top_lvl_dict, f,  indent=4)

    def complete_file(self):
        """Adds final part to LDT file and checks file length matches that in LDT header."""
        if self.write_completed:
            logger.error("%s unitID completed but attempt to complete again!", self.unit_id)
        else:
            self.write_completed = True
            logger.info("%s unitID now complete", self.unit_id)
            # Once all parts of the file have been received then finish

            if (self.pancam):
                if self.written_len == self.file_size:
                    logger.info("Packet Length as expected - renaming")
                    # Remove .partial from file name
                    newFile = self.write_file.with_suffix("")
                    pancam_fns.exist_unlink(newFile)
                    self.write_file.rename(newFile)
                    self.write_file = newFile

                    if self.hk:
                        self.move_hk()
                    else:
                        self.verify_img()

                else:
                    logger.error("Warning written length: %d not equal to FILE_SIZE %d ",
                                 self.written_len, self.file_size)

        self.navcam()
        self.create_json()

    def navcam(self):
        """Specific handler for NavCam images that are checked for size and made into a pgm file."""
        if self.pancam:
            return

        # Check if expected NavCam size just for 1024x1024
        if self.file_size == 1024*1024 + 68:
            logger.info(
                "FileID: %s Packet length matches NavCam", self.file_id)
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

    def setOccurrence(self, occurrence):
        self.write_occurrence = occurrence


class LdtIntermediate:
    """Creates a quick class for the LDT intermediate parts"""

    def __init__(self, PKT_Bin):
        unpacked = bitstruct.unpack('u16u16', PKT_Bin[16:20])
        self.unit_id = unpacked[0]
        self.seq_no = unpacked[1]


class LdtEnd:
    """Creates a quick class for the LDT end part"""

    def __init__(self, PKT_Bin):
        unpacked = bitstruct.unpack('u16u16', PKT_Bin[16:20])
        self.unit_id = unpacked[0]
        self.seq_no = unpacked[1]


def ha_scan(ROV_DIR):
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

    dir_comp_img = dir_proc / "COMPRESSED_IMG"
    if not dir_comp_img.is_dir():
        logger.info("Generating 'COMPRESSED_IMG' directory")
        dir_comp_img.mkdir()

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
                    ha_pkt_decode(PKT_HD, PKT_ID, PKT_LINES,
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
                check_buffers(Cur_LDT)
            else:
                logger.error(
                    "Initial LDT part not found for UnitID: %d", item[0])

    if len(Buffer) + len(EndBuffer) > 0:
        logger.info("Still %d items in buffer", len(Buffer)+len(EndBuffer))
    else:
        logger.info("LDT Buffer Empty")
        status.info("LDT Buffer Now Empty")

    if len(Found_IDS) > 0:
        msg = ("Found the following PanCam LDT files: \n")
        for _, value in Found_IDS.items():
            msg += f"\t\t{value.file_id}\n"
        status.info(msg)

    # Clean up directories if empty
    if not (any(IMG_RAW_DIR.iterdir())):
        IMG_RAW_DIR.rmdir()
        logger.info("No files found in IMG_RAW dir. Removing")

    if not (any(LDT_RAW_DIR.iterdir())):
        LDT_RAW_DIR.rmdir()
        logger.info("No files found in LDT_RAW dir. Removing")

    if not (any(dir_nav.iterdir())):
        dir_nav.rmdir()
        logger.info("No files found in NAVCAM dir. Removing")

    if not (any(dir_comp_img.iterdir())):
        dir_comp_img.rmdir()
        logger.info("No files found in COMPRESSED_IMG dir. Removing")
    else:
        split_comp_files(dir_comp_img)

    logger.info("Processing Rover .ha Files - Completed")


def ha_pkt_decode(PKT_HD, PKT_ID, PKT_LINES, curFile, dir_proc):
    """Decodes the first packet"""

    global Found_IDS

    TXT_Data = [next(curFile)[:-1] for x in range(PKT_LINES)]
    PKT_Bin = bytes.fromhex(''.join(TXT_Data))

    # First LDT Part
    if PKT_ID == LDT_IDs[0]:
        LDT_Cur_Pkt = LdtProperties(PKT_Bin)

        if LDT_Cur_Pkt.pancam:
            log_message = 'New PanCam LDT part'

        else:
            log_message = '----Other LDT part'

        logger.info('%s found with file ID: %s, and unitID %s',
                    log_message, LDT_Cur_Pkt.file_id, LDT_Cur_Pkt.unit_id)

        # If write is True, check to see if ID already exists
        if LDT_Cur_Pkt.write and (LDT_Cur_Pkt.unit_id in Found_IDS):
            status.info(
                "Multiple initial packets with the same ID found.")
            prev_count = Found_IDS.get(LDT_Cur_Pkt.unit_id).write_occurrence
            LDT_Cur_Pkt.setOccurrence(prev_count + 1)

            # Check to see if previous ID was not already completed
            if not Found_IDS.get(LDT_Cur_Pkt.unit_id).write_completed:
                logger.error(
                    "Previous FileID not completed, now adding to second FileID")

        # Write packet contents to file
        if LDT_Cur_Pkt.write:
            LDT_Cur_Pkt.set_write_file(dir_proc)
            write_bytes2file(LDT_Cur_Pkt, PKT_Bin[29:-2])

        Found_IDS.update({LDT_Cur_Pkt.unit_id: LDT_Cur_Pkt})

    # Second LDT Part
    elif PKT_ID == LDT_IDs[1]:
        IntP = LdtIntermediate(PKT_Bin)

        # Check to see if Unit ID already started if not add to buffer
        if IntP.unit_id not in Found_IDS:
            logger.info("New Packet without first part - adding to buffer")
            Buffer.update({(IntP.unit_id, IntP.seq_no): PKT_Bin[20:-2]})

        else:
            Cur_LDT = Found_IDS.get(IntP.unit_id)

            # Check file should be written
            if Cur_LDT.write:
                # Verify SEQ number is as expected
                Expected_SEQ = (Cur_LDT.unit_id, Cur_LDT.seq_no + 1)
                if Expected_SEQ == (IntP.unit_id, IntP.seq_no):
                    write_bytes2file(Cur_LDT, PKT_Bin[20:-2])
                    Cur_LDT.seq_no += 1
                    Found_IDS.update({IntP.unit_id: Cur_LDT})

                # Else add to buffer and try to rebuild
                else:
                    logger.warning("LDT parts not sequential")
                    logger.warning("Expected: %d", Expected_SEQ[1])
                    logger.warning("Got: %d", IntP.seq_no)
                    Buffer.update(
                        {(IntP.unit_id, IntP.seq_no): PKT_Bin[20:-2]})
                    logger.warning(
                        "Added LDT part to buffer: %d", IntP.seq_no)
                    check_buffers(Cur_LDT)

    elif PKT_ID == LDT_IDs[2]:
        # Check end of file and rename properly
        EndP = LdtEnd(PKT_Bin)
        logger.info("End Packet Received with unitID: %d", EndP.unit_id)

        # Check to see if Unit ID already started if not add to dict
        if EndP.unit_id not in Found_IDS:
            logger.error("End Packet without first part - adding to EndBuffer")
            EndBuffer.update({(EndP.unit_id, EndP.seq_no): PKT_Bin[20:-2]})

        else:
            Cur_LDT = Found_IDS.get(EndP.unit_id)

            # Check file should be written
            if Cur_LDT.write:
                # Verify SEQ number is as expected
                Expected_SEQ = (Cur_LDT.unit_id, Cur_LDT.seq_no + 1)
                if Expected_SEQ == (EndP.unit_id, EndP.seq_no):
                    Cur_LDT.seq_no += 1
                    Found_IDS.update({EndP.unit_id: Cur_LDT})
                    Cur_LDT.complete_file()

                else:
                    logger.warning("END LDT not sequential")
                    logger.warning("Expected: %d", Expected_SEQ[1])
                    logger.warning("Got: %d", EndP.seq_no)
                    EndBuffer.update(
                        {(EndP.unit_id, EndP.seq_no): PKT_Bin[20:-2]})
                    logger.warning(
                        "Added End part to buffer: %d, %d", EndP.unit_id, EndP.seq_no)
                    check_buffers(Cur_LDT)


def check_buffers(cur_ldt):
    """Function checks the LDT part buffer and end buffer to add parts already found out of sequence"""

    global Found_IDS

    Expected_SEQ = (cur_ldt.unit_id, cur_ldt.seq_no + 1)

    # First partial buffer
    # Check if expected SEQ_No packets already exists in the buffer
    while Expected_SEQ in Buffer:
        # Write to file the value in the buffer found
        write_bytes2file(cur_ldt, Buffer[Expected_SEQ])
        Buffer.pop(Expected_SEQ)
        logger.warning(
            "Wrote LDT part from buffer: %d", Expected_SEQ[1])
        cur_ldt.seq_no += 1
        Found_IDS.update({cur_ldt.unit_id: cur_ldt})
        Expected_SEQ = (Expected_SEQ[0], Expected_SEQ[1] + 1)

    # Then End Buffer
    # Determine if the end packet has been found
    if Expected_SEQ in EndBuffer:
        logger.warning("End LDT now fits: %d", Expected_SEQ[1])
        cur_ldt.seq_no += 1
        Found_IDS.update({cur_ldt.unit_id: cur_ldt})
        cur_ldt.complete_file()
        EndBuffer.pop(Expected_SEQ)


def pkt_Len(PKT_HD):
    return int(PKT_HD[3][8:])


def write_bytes2file(CurLDT, Bytes):
    """Function for writing to data file"""
    with open(CurLDT.write_file, 'ab') as wf:
        wf.write(Bytes)
        CurLDT.written_len += len(Bytes)
    return


def hkraw2unproc_pickle(ROV_DIR):
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
            target = curfile.with_suffix('.HKES_raw.incomplete')
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
            target = curfile.with_suffix('.HKNE_raw.incomplete')
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


def compare_ha2csv(ProcDir):
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


def pkt_identify(pkt):
    tm_pkt_hdr_names = ['block_type', 'tm_crit', 'mms_dest',
                        'instr_id', 'tm_type', 'seq_fl', 'cuc_s',  'cuc_ms', 'data_len']
    # sci_hdr_names = namedtuple('sci_hdr_names', ['ancil_len', 'pad',
    #                                              'sol', 'task_id', 'task_run', 'cam', 'filt', 'img_no'])

    # Read TM packet header, split if multiples
    if isinstance(pkt, Path):
        with open(pkt, "rb") as tm_pkt:
            tm_header = tm_pkt.read(11)
            # sci_header = tm_pkt.read(7)
            # tm_pkt.read(36)
            # comp_header = tm_pkt.read(10)

        # unpacked = bitstruct.unpack('u8u8u12u7u7u2u4u8', sci_header)
        # tm_sci_hdr = sci_hdr_names(*unpacked)
        # unpacked = bitstruct.unpack('u8u8u8u16u16u1u1u1', comp_header)
        # tm_comp_hdr = comp_hdr_names(*unpacked)

    else:
        tm_header = pkt

    tm_pkt_hdr = bitstruct.unpack_dict('u1u2u1u4u6u2r32r16u24', tm_pkt_hdr_names, tm_header)
    # tm_pkt_hdr = tm_pkt_hdr_names(*unpacked)
    tm_pkt_hdr['cuc_s'] = "0x" + str(tm_pkt_hdr.get('cuc_s').hex())
    tm_pkt_hdr['cuc_ms'] = "0x" + str(tm_pkt_hdr.get('cuc_ms').hex())

    return tm_pkt_hdr


def pkt_comp_hdr_decode(pkt):
    comp_hdr_names = ['algo', 'bit_depth',
                      'data_type', 'img_width', 'img_height', 'ratio', 'min_ratio', 'pad']

    tm_comp_hdr = bitstruct.unpack_dict('u8u8u8u16u16u1u1u1', comp_hdr_names, pkt)

    return tm_comp_hdr


def split_comp_files(CompDir):
    """Searches through the compressed images folder, and splits files depending on header contents."""

    comp_files = pancam_fns.Find_Files(CompDir, "*.ldt_file_ccsds")

    for file in comp_files:
        pkt = 00
        with open(file, "rb") as tm_pkt:
            tm_hdr_bytes = tm_pkt.read(11)

            # Read associated JSON file
            json_file = file.with_suffix(".JSON")
            with open(json_file, 'r') as read_file:
                ldt_json = json.load(read_file)

            # Next loop through each tm packet
            while tm_hdr_bytes:
                file_part = file.with_name(file.stem + f"_{pkt:02d}.tm_pkt_ccsds")
                new_file = open(file_part, 'wb')

                tm_pkt_hdr = pkt_identify(tm_hdr_bytes)

                ancil_hdr_bytes = tm_pkt.read(43)
                new_file.write(ancil_hdr_bytes)

                compr_hdr_bytes = tm_pkt.read(10)
                compr_hdr = pkt_comp_hdr_decode(compr_hdr_bytes)
                new_file.write(compr_hdr_bytes)

                # Read the number of packets set in the header and write to new file
                new_file.write(tm_pkt.read(tm_pkt_hdr.get('data_len')-53))
                new_file.close()

                # Create associated json
                # Add pkt part as well and maybe other stuff such as comp header etc.
                pkt_info = {"TM packet number within file": pkt}
                pkt_info.update({"TM Packet Header": tm_pkt_hdr})
                pkt_info.update({"Compression Header": compr_hdr})

                pkt_json = {**ldt_json, **pkt_info}

                new_json_file = file_part.with_suffix(".json")
                pancam_fns.exist_unlink(new_json_file)
                with open(new_json_file, 'w') as f:
                    json.dump(pkt_json, f, indent=4)

                # Continue Loop
                pkt += 1
                tm_hdr_bytes = tm_pkt.read(11)


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

    ha_scan(dir)
    hkraw2unproc_pickle(proc_dir)
    compare_ha2csv(proc_dir)
    split_comp_files(proc_dir / "COMPRESSED_IMG")
