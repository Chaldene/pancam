"""
Created on Tue Nov 12 10:12:39 2019

Function to go through a folder of Rover .ha files and produce the .raw
binaries of the images

@author: ucasbwh

To-Do:
Adapt for writing HK
"""

import PC_Fns
import TestFunctions
import math
import bitstruct
from datetime import datetime
from pathlib import Path
import logging
logger = logging.getLogger(__name__)
import binascii  # Used if wanting to output ascii to terminal

# Global parameters
# {LDT_Properties.Unit_ID: LDT_Properties.SEQ_No})
Found_IDS = {}
Buffer = {}
LDT_IDs = [ "AB.TM.MRSS0697",
            "AB.TM.MRSS0698",
            "AB.TM.MRSS0699"]  

class HaReadError(Exception):
    """error for unexpected things"""
    pass


class LDT_Properties:
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
        
        #FileID definition given as part of LDT definition
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
            logger.info("Not a science packet, skipping")
            self.Type = False
        else:
            self.Type = True

        self.write = self.PanCam & self.Type
        self.writtenLen = 0

    def setWriteFile(self, DIR, pkt_HD):
        # Determine FileName and check if exists
        write_dt = datetime.strptime(pkt_HD[1][16:-1], '%d/%m/%Y %H:%M:%S.%f')
        write_dts = write_dt.strftime('%y%m%d_%H%M%S_')
        write_filename = write_dts + str(self.Unit_ID) + ".pci_raw.partial"
        self.write_file = DIR / write_filename
        logger.info("Creating file: %s", self.write_file.name)
        if self.write_file.exists():
            self.write_file.unlink()
            logger.info("Deleting file: %s", self.write_file.name)

    def updateWrite(self, Data):
        # Keep a running tally of the number of bytes written to file
        self.writtenLen += len(Data)

    def completePacket(self):
        # Once all parts of the packet have been received then finish
        logger.info("End Packet Received")
        
        # Check written equals expected and rename file
        if self.writtenLen == self.FILE_SIZE:
            logger.info("Packet Length as expected - renaming")
            self.write_file.replace(self.write_file.with_suffix(""))


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

def HaProc(ROV_DIR):
    """Searches for .ha Rover files and creates raw binary files
    for each image found"""
    logger.info("Processing Rover .ha Files")

    #Find Files
    ROVER_HA = PC_Fns.Find_Files(ROV_DIR, "*.ha")
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
                    HaPacketDecode(PKT_HD, PKT_ID, PKT_LINES, curFile, IMG_RAW_DIR)
                else:
                    for x in range(PKT_LINES): next(curFile)
                
                PKT_HD[0] = next(curFile)

    if len(Buffer) > 0:
        logger.error("Data remaining in buffer. Entries = ", len(Buffer))
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
        logger.info("New LDT part found with file ID: %s", LDT_Cur_Pkt.FILE_ID)
        
        # Check to see if ID already exists if not add to dict
        if LDT_Cur_Pkt.Unit_ID in Found_IDS:
            logger.warning("2 initial packets with the same ID found")
        else:
            #Write Data then add to dictionary
            if LDT_Cur_Pkt.write:
                LDT_Cur_Pkt.setWriteFile(IMG_RAW_DIR, PKT_HD)
                writeBytesToFile(LDT_Cur_Pkt, PKT_Bin[29:-2])
        Found_IDS.update({LDT_Cur_Pkt.Unit_ID: LDT_Cur_Pkt})

    # Second LDT Part
    elif PKT_ID == LDT_IDs[1]:
        IntP = LDT_Intermediate(PKT_Bin)
        
        # Check to see if Unit ID already started if not add to dict
        if IntP.Unit_ID in Found_IDS:
            Cur_LDT = Found_IDS.get(IntP.Unit_ID)               
        else:
            logger.error("New Packet without first part - adding to buffer")
            Buffer.update({IntP.SEQ_No: PKT_Bin[20:-2]})

        #Check file should be written            
        if Cur_LDT.write:
            # Verify SEQ number is as expected
            Expected_SEQ = Cur_LDT.SEQ_No + 1
            if Expected_SEQ == IntP.SEQ_No:
                writeBytesToFile(Cur_LDT, PKT_Bin[20:-2])
                Cur_LDT.SEQ_No += 1
            else:                    
                logger.warning("LDT parts not sequential")
                logger.warning("Expected: %d", Expected_SEQ)
                logger.warning("Got: %d", IntP.SEQ_No)

                #First check if expected SEQ_No already exists in the buffer
                if Expected_SEQ in Buffer:
                    #Write to file the value in the buffer found
                    writeBytesToFile(Cur_LDT, Buffer[Expected_SEQ])
                    del Buffer[Expected_SEQ]
                    logger.warning("Wrote LDT part from buffer: %d", Expected_SEQ)
                    Cur_LDT.SEQ_No += 1
                    Expected_SEQ += 1

                #Then check if the current packet is as expected
                if Expected_SEQ == IntP.SEQ_No:
                    writeBytesToFile(Cur_LDT, PKT_Bin[20:-2])
                    logger.warning("Current LDT part now fits: %d", Expected_SEQ)
                    Cur_LDT.SEQ_No += 1 

                #If not then add to buffer
                else:
                    Buffer.update({Cur_LDT.SEQ_No: PKT_Bin[20:-2]})
            
        Found_IDS.update({IntP.Unit_ID: Cur_LDT})                              

    elif PKT_ID == LDT_IDs[2]:
        #Check end of file and rename properly
        EndP = LDT_End(PKT_Bin)

        # Check to see if Unit ID already started if not add to dict
        if EndP.Unit_ID in Found_IDS:
            Cur_LDT = Found_IDS.get(EndP.Unit_ID)               
        else:
            logger.error("End Packet without first part - adding to buffer")
            Buffer.update({EndP.SEQ_No: PKT_Bin[20:-2]})

        #Check file should be written            
        if Cur_LDT.write:
            # Verify SEQ number is as expected
            Expected_SEQ = Cur_LDT.SEQ_No + 1
            if Expected_SEQ == EndP.SEQ_No:
                Cur_LDT.SEQ_No += 1
                Cur_LDT.completePacket()
                Found_IDS.pop(EndP.Unit_ID)                
            else:                    
                logger.warning("END LDT not sequential")
                logger.warning("Expected: %d", Expected_SEQ)
                logger.warning("Got: %d", EndP.SEQ_No)

                #First check if expected SEQ_No already exists in the buffer
                if Expected_SEQ in Buffer:
                    #Write to file the value in the buffer found
                    writeBytesToFile(Cur_LDT, Buffer[Expected_SEQ])
                    del Buffer[Expected_SEQ]
                    logger.warning("Wrote LDT part from buffer: %d", Expected_SEQ)
                    Cur_LDT.SEQ_No += 1
                    Expected_SEQ += 1

                #Then check if the current packet is as expected
                if Expected_SEQ == EndP.SEQ_No:
                    logger.warning("End LDT now fits: %d", Expected_SEQ)
                    Cur_LDT.SEQ_No += 1 
                    Cur_LDT.completePacket()
                    Buffer.pop(EndP.SEQ_No) 

                #If not then add to buffer
                else:
                    Buffer.update({Cur_LDT.SEQ_No: PKT_Bin[20:-2]})
            
        Found_IDS.update({EndP.Unit_ID: Cur_LDT})                              

def pkt_Len(PKT_HD):
    return int(PKT_HD[3][8:])


def writeBytesToFile(CurLDT, Bytes):
    """Funtion for writing to data file"""
    with open(CurLDT.write_file, 'ab') as wf:
        wf.write(Bytes)
        CurLDT.writtenLen += len(Bytes)
    return


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

    HaProc(DIR)
