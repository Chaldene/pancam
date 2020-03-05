# decodeRAW_HK
#
# Barry Whiteside
# Mullard Space Science Laboratory - UCL
#
# PanCam Data Processing Tools

from datetime import datetime
from astropy.time import TimeDelta, Time
from astropy import units
import pandas as pd
import numpy as np
from pathlib import Path

import binascii
import logging

import pancam_fns
from pancam_fns import PandUPF

logger = logging.getLogger(__name__)


class decodeRAW_HK_Error(Exception):
    """error for unexpected things"""
    pass


def decode(PROC_DIR):
    """Takes the unprocessed telemetry and produces a RAW pandas array of all the PanCam parameters"""

    logger.info("---Processing RAW TM Files")

    # Search for PanCam unprocessed TM Files from ha source first
    PikFile = pancam_fns.Find_Files(
        PROC_DIR, "*Unproc_HKTM.pickle", SingleFile=True)
    if not PikFile:
        logger.warning("No files found - ABORTING")
        return

    RTM = pd.read_pickle(PikFile[0])

    try:
        Bin = RTM['RAW'].apply(lambda x: bytearray.fromhex(x))
    except TypeError:
        Bin = RTM['RAW']

    RTM = pancam_fns.ReturnCUC_RAW(RTM, Bin)

    TM = pd.DataFrame()
    verify = pd.DataFrame()
    err_df = pd.DataFrame()

    # Check for any blank HK
    verify['Blank'] = Bin.apply(len) == 0
    err_df = Bin[verify['Blank']]
    if not err_df.empty:
        for index in err_df.index.tolist():
            logging.error("Blank HK Entry Detected at line: %s", index)
            Bin = Bin.drop(index)

    # Time stamp data from CUC
    TM['DT'] = pd.to_datetime(CUCtoUTC_DT(RTM))

    TM, Bin = DecodeParam_HKHeader(TM, Bin)
    TM, Bin = DecodeParam_HKVoltTemps(TM, Bin)
    TM, Bin = DecodeParam_HKErrors(TM, Bin)
    TM, Bin = DecodeParam_HKFW(TM, Bin)

    # Byte 42-43 PIU Cam Status                          #From PAN_TM_PIU_HKN_PCS and PAN_TM_PIU_HK_PCS
    # PAN_TM_PIU_HKN_PCS_CE / PAN_TM_PIU_HK_PCS_CE
    TM['Stat_PIU_En'] = PandUPF(Bin, 'u8', 42, 0)
    # PAN_TM_PIU_HKN_PCS_PSS / PAN_TM_PIU_HK_PCS_PSS
    TM['Stat_PIU_Pw'] = PandUPF(Bin, 'u8', 43, 0)

    # Non-Essential Only HK
    TM = DecodeParam_HKNE(TM, Bin)

    # Camera Responses
    WACBin, HRCBin = Determ_CamRes(TM, Bin)

    if not WACBin.empty:
        TM = DecodeWAC_CamRes(TM, WACBin)
    del WACBin

    if not HRCBin.empty:
        TM = DecodeHRC_CamRes(TM, HRCBin)
    del HRCBin

    # Write a new file with RAW data
    write_file = PROC_DIR / \
        (PikFile[0].stem.split('Unproc')[0] + "RAW_HKTM.pickle")
    if write_file.exists():
        write_file.unlink()
        logger.info("Deleting file: %s", write_file.name)
    with open(write_file, 'w') as f:
        TM.to_pickle(write_file)
        logger.info("PanCam RAW TM pickled.")

    logger.info("---Processing RAW TM Files Completed")


def DecodeParam_HKHeader(TM, Bin):
    """Ensures the TM Header is consistent with what's expected
    So far checks include:
    - TM Data length matches length of Data
    - TM Type matches type ID
    """
    # Byte 0-10 TM Block Header
    TM['Block_Type'] = PandUPF(Bin, 'u1', 0, 0)
    TM['TM_Criticality'] = PandUPF(Bin, 'u2', 0, 1)
    TM['MMS_Dest'] = PandUPF(Bin, 'u1', 0, 3)
    TM['Instr_ID'] = PandUPF(Bin, 'u4', 0, 4)
    TM['TM_Type_ID'] = PandUPF(Bin, 'u6', 0, 8)
    TM['Seq_Flag'] = PandUPF(Bin, 'u2', 0, 14)
    TM['Pkt_CUC'] = PandUPF(Bin, 'u48', 0, 16)
    TM['Data_Len'] = PandUPF(Bin, 'u24', 0, 64)
    # Byte 11                                            #PAN_TM_PIU_HKN_RES and PAN_TM_PIU_HK_RES
    if True in (PandUPF(Bin, 'u8', 11, 0) != 0).unique():
        logger.error("TM Byte 11 not 0")

    # Verification checks
    # Check that the block type is always 0 for TM
    Data_Type_Mismatch = TM[(TM['Block_Type'] != 0)]
    if not Data_Type_Mismatch.empty:
        logging.error("Incorrect Block Type identified not a TM")
        TM, Bin = DropTM(Data_Type_Mismatch, TM, Bin)

    # Check that the Instr. ID is always 5
    if True in (TM['Instr_ID'] != 5).unique():
        logging.error("TM Instr. ID instance when not equal to 5")

    # Check that the TM Type is always 0 or 1
    Data_TMID_NotHK = TM[(TM['TM_Type_ID'] > 1)]
    if not Data_TMID_NotHK.empty:
        logging.error("TM Type ID expected 0 or 1, not a HK")
        TM, Bin = DropTM(Data_TMID_NotHK, TM, Bin)

    # Check that the data length matches that in binary
    Data_Len_Mismatch = TM[(Bin.apply(len)-11) != TM['Data_Len']]
    if not Data_Len_Mismatch.empty:
        logging.error(
            "Missing HK Data Detected - TM Data Len does not match actual length")
        TM, Bin = DropTM(Data_Len_Mismatch, TM, Bin)

    # Check that the TM Type has the correct length
    HK_Lengths = {0: 61, 1: 77}
    Data_TMType_Bool = TM[(TM['TM_Type_ID'].replace(
        HK_Lengths) != TM['Data_Len'])]
    if not Data_TMType_Bool.empty:
        logging.error("TM Type ID does not match TM Data Length in Header")
        TM, Bin = DropTM(Data_TMType_Bool, TM, Bin)

    return TM, Bin


def DecodeParam_HKVoltTemps(TM, Bin):
    """Decodes the HK Voltages and Temperatures"""
    # Byte 12-17 Voltages
    # PAN_TM_PIU_HKN_REFV and PAN_TM_PIU_HK_REFV
    TM['Volt_Ref'] = PandUPF(Bin, 'u16', 12, 0)
    # PAN_TM_PIU_HKN_6V0 and PAN_TM_PIU_HK_6V0
    TM['Volt_6V0'] = PandUPF(Bin, 'u16', 14, 0)
    # PAN_TM_PIU_HKN_1V5 and PAN_TM_PIU_HK_1V5
    TM['Volt_1V5'] = PandUPF(Bin, 'u16', 16, 0)

    # Byte 18-31 Temperatures
    # PAN_TM_PIU_HKN_LWACT and PAN_TM_PIU_HK_LFWT
    TM['Temp_LFW'] = PandUPF(Bin, 'u16', 18, 0)
    # PAN_TM_PIU_HKN_RWACT and PAN_TM_PIU_HK_RFWT
    TM['Temp_RFW'] = PandUPF(Bin, 'u16', 20, 0)
    # PAN_TM_PIU_HKN_HRCT and PAN_TM_PIU_HK_HRCT
    TM['Temp_HRC'] = PandUPF(Bin, 'u16', 22, 0)
    # PAN_TM_PIU_HKN_LWACT and PAN_TM_PIU_HK_LWACT
    TM['Temp_LWAC'] = PandUPF(Bin, 'u16', 24, 0)
    # PAN_TM_PIU_HKN_RWACT and PAN_TM_PIU_HK_RWACT
    TM['Temp_RWAC'] = PandUPF(Bin, 'u16', 26, 0)
    # PAN_TM_PIU_HKN_LDOT and PAN_TM_PIU_HK_LDOT
    TM['Temp_LDO'] = PandUPF(Bin, 'u16', 28, 0)
    # PAN_TM_PIU_HKN_HRCAT and PAN_TM_PIU_HK_HRCAT
    TM['Temp_HRCA'] = PandUPF(Bin, 'u16', 30, 0)

    # Byte 38-39 PIU Htr Status                          #From PAN_TM_PIU_HKN_TCS and PAN_TM_PIU_HK_TCS
    # PAN_TM_PIU_HKN_TCS_STAT / PAN_TM_PIU_HK_TCS_STAT
    TM['Stat_Temp_On'] = PandUPF(Bin, 'u1', 38, 0)
    # PAN_TM_PIU_HKN_TCS_MODE / PAN_TM_PIU_HK_TCS_MODE
    TM['Stat_Temp_Mo'] = PandUPF(Bin, 'u1', 38, 1)
    # PAN_TM_PIU_HKN_TCS_HEAT / PAN_TM_PIU_HK_TCS_HEAT
    TM['Stat_Temp_He'] = PandUPF(Bin, 'u2', 38, 2)
    # PAN_TM_PIU_HKN_TCS_SET / PAN_TM_PIU_HK_TCS_SET
    TM['Stat_Temp_Se'] = PandUPF(Bin, 'u12', 38, 4)

    return TM, Bin


def DecodeParam_HKErrors(TM, Bin):
    """Function to decode PIU reported errors"""
    # Byte 32-33 Error Codes
    # PAN_TM_ PIU_ HKN_ ERR1 and PAN_TM_PIU_ HK_ ERR1
    TM['ERR_1_CMD'] = PandUPF(Bin, 'u8', 32, 0)
    TM['ERR_1_FW'] = PandUPF(Bin, 'u8', 33, 0)
    # PAN_TM_ PIU_ HKN_ ERR2 and PAN_TM_PIU_ HK_ ERR2
    TM['ERR_2_LWAC'] = PandUPF(Bin, 'u8', 34, 0)
    TM['ERR_2_RWAC'] = PandUPF(Bin, 'u8', 34, 0)
    # PAN_TM_ PIU_ HKN_ ERR3 and PAN_TM_PIU_HK_ ERR3
    TM['ERR_3_HRC'] = PandUPF(Bin, 'u8', 36, 0)
    if True in (PandUPF(Bin, 'u8', 37, 0) != 0).unique():
        logging.error("TM HK Byte 37 not 0")

    # Check for any general errors but only report first occurance of each
    ERR = TM.ERR_1_CMD[TM['ERR_1_CMD'].diff() > 0]
    if not ERR.empty:
        logging.error("TM HK ERR1 CMD Detected")
        for index, row in ERR.items():
            logging.info("PanCam CMD Error Detected: %s", TM.ERR_1_CMD[index])

    ERR = TM.ERR_1_FW[TM['ERR_1_FW'].diff() > 0]
    if not ERR.empty:
        logging.error("TM HK ERR1 FW Detected")
        for index, row in ERR.items():
            logging.info("PanCam FW Error Detected: %s", TM.ERR_1_FW[index])

    ERR = TM.ERR_2_LWAC[TM['ERR_2_LWAC'].diff() > 0]
    if not ERR.empty:
        logging.error("TM HK ERR2 LWAC Detected")
        for index, row in ERR.items():
            logging.info("PanCam LWAC Error Detected: %s",
                         TM.ERR_2_LWAC[index])

    ERR = TM.ERR_2_RWAC[TM['ERR_2_RWAC'].diff() > 0]
    if not ERR.empty:
        logging.error("TM HK ERR2 RWAC Detected")
        for index, row in ERR.items():
            logging.info("PanCam RWAC Error Detected: %s",
                         TM.ERR_2_RWAC[index])

    ERR = TM.ERR_3_HRC[TM['ERR_3_HRC'].diff() > 0]
    if not ERR.empty:
        logging.error("TM HK ERR3 HRC Detected")
        for index, row in ERR.items():
            logging.info("PanCam HRC Error Detected: %s", TM.ERR_3_HRC[index])

    return TM, Bin


def DropTM(TM_ErrorFrame, TM, Bin):
    """Function to remove error entries. The TM_ErrorFrame must be
    a subset of the TM dataframe. TM and Bin are pandas dataframes
    of the same size.

    The function returns the reduced TM and Bin"""

    for index, row in TM_ErrorFrame.iterrows():
        logging.info("Packet removed: %s", binascii.hexlify(Bin[index]))
    newTM = TM.drop(TM_ErrorFrame.index)
    newBin = Bin.drop(TM_ErrorFrame.index)
    return newTM, newBin


def DecodeParam_HKFW(TM, Bin):
    """Decodes all filter wheel parameters"""

    # Byte 40-41 PIU FW Status                           #From PAN_TM_PIU_HKN_FWS and PAN_TM_PIU_HK_FWS
    # PAN_TM_PIU_HKN_FWS_LRES / PAN_TM_PIU_HK_FWS_LRES
    if True in (PandUPF(Bin, 'u1', 40, 0) != 0).unique():
        raise decodeRAW_HK_Error("TM Byte 40 bit 0 not 0")
    # PAN_TM_PIU_HKN_FWS_LOP / PAN_TM_PIU_HK_FWS_LOP
    TM['Stat_FWL_Op'] = PandUPF(Bin, 'u1', 40, 1)
    # PAN_TM_PIU_HKN_FWS_LHM / PAN_TM_PIU_HK_FWS_LHM
    TM['Stat_FWL_Ho'] = PandUPF(Bin, 'u1', 40, 2)
    # PAN_TM_PIU_HKN_FWS_LIDX / PAN_TM_PIU_HK_FWS_LIDX
    TM['Stat_FWL_Id'] = PandUPF(Bin, 'u1', 40, 3)
    # PAN_TM_PIU_HKN_FWS_LFN / PAN_TM_PIU_HK_FWS_LFN
    TM['Stat_FWL_Po'] = PandUPF(Bin, 'u4', 40, 4)
    # PAN_TM_PIU_HKN_FWS_RRES / PAN_TM_PIU_HK_FWS_RRES
    if True in (PandUPF(Bin, 'u1', 41, 0) != 0).unique():
        raise decodeRAW_HK_Error("TM Byte 41 bit 0 not 0")
    # PAN_TM_PIU_HKN_FWS_ROP / PAN_TM_PIU_HK_FWS_ROP
    TM['Stat_FWR_Op'] = PandUPF(Bin, 'u1', 41, 1)
    # PAN_TM_PIU_HKN_FWS_RHM / PAN_TM_PIU_HK_FWS_RHM
    TM['Stat_FWR_Ho'] = PandUPF(Bin, 'u1', 41, 2)
    # PAN_TM_PIU_HKN_FWS_RIDX / PAN_TM_PIU_HK_FWS_RIDX
    TM['Stat_FWR_Id'] = PandUPF(Bin, 'u1', 41, 3)
    # PAN_TM_PIU_HKN_FWS_RFN / PAN_TM_PIU_HK_FWS_RFN
    TM['Stat_FWR_Po'] = PandUPF(Bin, 'u4', 41, 4)

    # Byte 64-71 Filter Wheel
    # PAN_TM_PIU_HKN_LFWAS / PAN_TM_PIU_HK_LFWAS
    TM['FWL_ABS'] = PandUPF(Bin, 'u16', 64, 0)
    # PAN_TM_PIU_HKN_RFWAS and PAN_TM_PIU_HK_RFWAS
    TM['FWR_ABS'] = PandUPF(Bin, 'u16', 66, 0)
    # PAN_TM_PIU_HKN_LFWRS and PAN_TM_PIU_HK_LFWRS
    TM['FWL_REL'] = PandUPF(Bin, 'u16', 68, 0)
    # PAN_TM_PIU_HKN_RFWRS and PAN_TM_PIU_HK_RFWRS
    TM['FWR_REL'] = PandUPF(Bin, 'u16', 70, 0)

    return TM, Bin


def DecodeParam_HKNE(TM, Bin):
    """Decodes all the non-essential HK parameters not included in the essential HK."""

    NEBin = Bin[TM['TM_Type_ID'] == 1]
    if not NEBin.empty:
        # Byte 72-77 Image ID                            #From PAN_TM_PIU_HKN_IID[1:3]
        TM['IMG_SOL'] = PandUPF(NEBin, 'u12', 72, 0)  # PAN_TM_PIU_HKN_SIID_SOL
        # PAN_TM_PIU_HKN_SIID_TID
        TM['IMG_Task_ID'] = PandUPF(NEBin, 'u7', 73, 4)
        TM['IMG_Task_RNO'] = PandUPF(
            NEBin, 'u7', 74, 3)  # PAN_TM_PIU_HKN_SIID_TRN
        TM['IMG_Cam'] = PandUPF(NEBin, 'u2', 75, 2)  # PAN_TM_PIU_HKN_SIID_PC
        TM['IMG_FW'] = PandUPF(NEBin, 'u4', 75, 4)  # PAN_TM_PIU_HKN_SIID_FW
        TM['IMG_No'] = PandUPF(NEBin, 'u8', 76, 0)  # PAN_TM_PIU_HKN_SIID_IN
        if True in (PandUPF(NEBin, 'u1', 77, 0) != 0).unique():  # PAN_TM_PIU_HKN_SIID_RES
            raise decodeRAW_HK_Error("TM Byte 77 not 0")

        # Byte 78-79 PIU Version
        TM['PIU_Ver'] = PandUPF(NEBin, 'u16', 78, 0)  # PAN_TM_PIU_HKN_VER
        allowed_PIU_Ver = [288, np.nan]
        if (set(TM.PIU_Ver.unique()) - set(allowed_PIU_Ver)):
            logger.error("Illegal PIU Version Detected!")

        # Byte 80-87 FW Config                           #From PAN_TM_PIU_HKN_FWMS and PAN_TM_PIU_HKN_SLF
        TM['FWL_RTi'] = PandUPF(NEBin, 'u8',  80, 0)
        TM['FWL_Spe'] = PandUPF(NEBin, 'u4',  81, 0)
        TM['FWR_Spe'] = PandUPF(NEBin, 'u4',  81, 4)
        TM['FWL_Cur'] = PandUPF(NEBin, 'u16', 82, 0)  # PAN_TM_PIU_HKN_LFWCS
        TM['FWR_Cur'] = PandUPF(NEBin, 'u16', 84, 0)  # PAN_TM_PIU_HKN_RFWCS
        TM['FWR_RTi'] = PandUPF(NEBin, 'u8',  86, 0)
        TM['FWL_StL'] = PandUPF(NEBin, 'u4',  87, 0)
        TM['FWR_StR'] = PandUPF(NEBin, 'u4',  87, 4)
        del NEBin

    return TM


def Determ_CamRes(TM, Bin):
    """Sort camera responses for each camera, only change cam if a new Cam response is received"""

    # Byte 44-63 Camera Responses                   #PAN_TM_PIU_HKN_CR[1:10] / PAN_TM_PIU_HK_CR[1:10]
    CamResSeries = Bin.apply(lambda x: x[44: 64])
    # Determine if Cam Response has changed
    camres_chg = CamResSeries != CamResSeries.shift(1)
    # Ignore first entry if all 0x0s
    if CamResSeries[0] == bytes([0x0]*20):
        camres_chg[0] = False

    WACBin = Bin[camres_chg & (TM['Stat_PIU_Pw'].between(1, 2))]
    HRCBin = Bin[camres_chg & (TM['Stat_PIU_Pw'] == 3)]

    # Verify NulBin is empty
    NulBin = CamResSeries[camres_chg & (TM['Stat_PIU_Pw'] == 0)]
    if not NulBin.shape[0] == 0:
        resetbin = NulBin[NulBin == bytes([0x0]*20)]
        undefbin = NulBin[NulBin != bytes([0x0]*20)]

        if not resetbin.shape[0] == 0:
            logger.warning("PanCam likely reset %d, times", resetbin.shape[0])
            logger.info("\n%s", TM['DT'].iloc[resetbin.index])

        if not undefbin.shape[0] == 0:
            logger.error(
                "Warning CamRes change during unpowered state, %d occurances.", undefbin.shape[0])
            logger.info("\n%s", TM['DT'].iloc[undefbin.index])

    # Verify No Overlap between WACBin and HRCBin
    union = WACBin.to_frame().join(HRCBin.to_frame(), lsuffix='WAC',
                                   rsuffix='HRC', how='inner')
    if union.shape[0] != 0:
        logger.error("Common entries for WACBin and HRCBin")

    return WACBin, HRCBin


def DecodeWAC_CamRes(TM, WACBin):
    """Function that accepts the WACBin and decodes the Camera Response and appends them to the TM dataframe"""

    # PAN_TM_WAC_IA_CID / PAN_TM_WAC_HK_CID / PAN_TM_WAC_DT_CID / PAN_TM_WAC_NK_CID
    TM['WAC_CID'] = PandUPF(WACBin, 'u2', 44, 0)
    # PAN_TM_WAC_IA_MK / PAN_TM_WAC_HK_MK / PAN_TM_WAC_DT_MK / PAN_TM_WAC_NK_MK
    if True in (PandUPF(WACBin, 'u1', 44, 2) != 1).unique():
        raise decodeRAW_HK_Error("TM Byte 44 bit 2 not 0 for WAC")
        logger.error("Warning likely mixed WAC and HRC Cam responses.")
    # PAN_TM_WAC_IA_WID / PAN_TM_WAC_HK_WID / PAN_TM_WAC_DT_WID / PAN_TM_WAC_NK_WID
    TM['WAC_WID'] = PandUPF(WACBin, 'u3', 44, 5)
    # PAN_TM_WAC_IA_WTS / PAN_TM_WAC_HK_WTS / PAN_TM_WAC_DT_WTS / PAN_TM_WAC_NK_WTS
    TM['WAC_WTS'] = PandUPF(WACBin, 'u48', 51, 0)
    # PAN_TM_WAC_IA_SUM / PAN_TM_WAC_HK_SUM / PAN_TM_WAC_NK_SUM
    TM['WAC_SUM'] = PandUPF(WACBin, 'u8', 59, 0)
    # Set WAC DT Checksums to 0 as don't exist
    TM.WAC_SUM[TM['WAC_CID'] == 2] = np.NaN

    # WAC IA
    WIA = WACBin[TM['WAC_CID'] == 0]
    if not WIA.empty:
        TM['WAC_IAS'] = PandUPF(WIA, 'u2', 44, 3)  # PAN_TM_WAC_IA_IAS
        if True in (PandUPF(WIA, 'u48', 45, 0) != 0).unique():  # PAN_TM_WAC_IA_RES1
            raise decodeRAW_HK_Error("TM Bytes 45-50 not 0 for WAC IA")
        if True in (PandUPF(WIA, 'u16', 57, 0) != 0).unique():  # PAN_TM_WAC_IA_RES2
            raise decodeRAW_HK_Error("TM Bytes 57-58 not 0 for WAC IA")
        if True in (PandUPF(WIA, 'u32', 60, 0) != 0).unique():  # PAN_TM_WAC_IA_RES3
            raise decodeRAW_HK_Error("TM Bytes 60-63 not 0 for WAC IA")
    del WIA

    # WAC HK
    WHK = WACBin[TM['WAC_CID'] == 1]
    if not WHK.empty:
        TM['WAC_HK_MCK'] = PandUPF(WHK, 'u2', 44, 3)  # PAN_TM_WAC_HK_MS
        TM['WAC_HK_TAT'] = PandUPF(WHK, 'u48', 45, 0)  # PAN_TM_WAC_HK_TAT
        TM['WAC_HK_LTP'] = PandUPF(WHK, 'u12', 57, 0)  # PAN_TM_WAC_HK_TP
        TM['WAC_HK_INH'] = PandUPF(WHK, 'u1', 58, 4)  # PAN_TM_WAC_HK_INH
        TM['WAC_HK_IAO'] = PandUPF(WHK, 'u1', 58, 5)  # PAN_TM_WAC_HK_IAO
        TM['WAC_HK_TAO'] = PandUPF(WHK, 'u1', 58, 6)  # PAN_TM_WAC_HK_TAO
        TM['WAC_HK_MCO'] = PandUPF(WHK, 'u1', 58, 7)  # PAN_TM_WAC_HK_MCO
        if True in (PandUPF(WHK, 'u32', 60, 0) != 0).unique():
            raise decodeRAW_HK_Error("TM Bytes 60-63 not 0 for WAC HK")
    del WHK

    # WAC DT
    WDT = WACBin[TM['WAC_CID'] == 2]
    if not WDT.empty:
        TM['WAC_DT_BIN'] = PandUPF(WDT, 'u2', 44, 3)  # PAN_TM_WAC_DT_BIN
        TM['WAC_DT_ITS'] = PandUPF(WDT, 'u48', 45, 0)  # PAN_TM_WAC_DT_ITS
        TM['WAC_DT_INT'] = PandUPF(WDT, 'u20', 57, 0)  # PAN_TM_WAC_DT_IT
        TM['WAC_DT_STP'] = PandUPF(WDT, 'u12', 59, 4)  # PAN_TM_WAC_DT_STP
        TM['WAC_DT_INH'] = PandUPF(WDT, 'u1',  61, 0)  # PAN_TM_WAC_DT_INH
        TM['WAC_DT_AE'] = PandUPF(WDT, 'u1',  61, 1)  # PAN_TM_WAC_DT_AE
        TM['WAC_DT_PAD'] = PandUPF(WDT, 'u1',  61, 2)  # PAN_TM_WAC_DT_PAD
        TM['WAC_DT_GAS'] = PandUPF(WDT, 'u2',  61, 3)  # PAN_TM_WAC_DT_GAS
        TM['WAC_DT_DD'] = PandUPF(WDT, 'u1',  61, 5)  # PAN_TM_WAC_DT_DD
        TM['WAC_DT_AES'] = PandUPF(WDT, 'u1',  61, 6)  # PAN_TM_WAC_DT_AESF
        if True in (PandUPF(WDT, 'u1', 61, 7) != 0).unique():  # PAN_TM_WAC_DT_RES
            raise decodeRAW_HK_Error("TM Byte 71 bit 7 not 0 for WAC DT")
        TM['WAC_DT_CRC'] = PandUPF(WDT, 'u16', 62, 0)  # PAN_TM_WAC_DT_CRC
    del WDT

    # WAC NAK
    WNK = WACBin[TM['WAC_CID'] == 3]
    if not WNK.empty:
        if True in (PandUPF(WNK, 'u2', 44, 3) != 0).unique():  # PAN_TM_WAC_NK_RES1
            raise decodeRAW_HK_Error(
                "TM Byte 44 bits 3-4 not 0 for WAC NAK")
        TM['WAC_NK_ERR'] = PandUPF(WNK, 'u8', 45, 0)  # PAN_TM_WAC_NK_ERR
        if True in (PandUPF(WNK, 'u40', 46, 0) != 0).unique():  # PAN_TM_WAC_NK_RES1
            raise decodeRAW_HK_Error("TM Bytes 46-50 not 0 for WAC NAK")
        if True in (PandUPF(WNK, 'u16', 57, 0) != 0).unique():  # PAN_TM_WAC_NK_RES3
            raise decodeRAW_HK_Error("TM Bytes 57-58 not 0 for WAC NAK")
        if True in (PandUPF(WNK, 'u32', 60, 0) != 0).unique():  # PAN_TM_WAC_HK_RES4
            raise decodeRAW_HK_Error("TM Bytes 60-63 not 0 for WAC NAK")
    del WNK

    return TM


def DecodeHRC_CamRes(TM, HRCBin):
    """Function to decode the HRC camera response passed as a bytearray from HRCBin and then added to the TM datafrmae."""

    # PAN_TM_HRC_HK_CA / PAN_TM_HRC_RB1_CA / PAN_TM_HRC_RB2_CA / PAN_TM_HRC_RB3_CA / PAN_TM_HRC_RB4_CA / PAN_TM_HRC_HMD_CA / PAN_TM_HRC_RES_CA2
    TM['HRC_ACK'] = PandUPF(HRCBin, 'u8', 51, 0)
    Res = PandUPF(HRCBin, 'u32', 52, 0) + PandUPF(HRCBin,
                                                  'u32', 56, 0) + PandUPF(HRCBin, 'u32', 60, 0)
    # PAN_TM_HRC_HK_RES1 / PAN_TM_HRC_RB1_RES1 / PAN_TM_HRC_RB2_RES4 / PAN_TM_HRC_RB3_RES2 / PAN_TM_HRC_RB4_RES2 / PAN_TM_HRC_HMD_RES3 / PAN_TM_HRC_RES_RES2
    if True in (Res != 0):
        logging.error("TM Bytes 52-63 not 0 for HRC HK")
    del Res

    # HRC HK
    HHK = HRCBin[TM['HRC_ACK'] == 0x02]
    if not HHK.empty:
        HRCBin = HRCBin.drop(HHK.index.values)
        TM['HRC_CS'] = PandUPF(HHK, 'u16', 44, 0)  # PAN_TM_HRC_ HK_CS
        TM['HRC_TP'] = PandUPF(HHK, 'u10', 46, 0)  # PAN_TM_HRC_HK_TP
        TM['HRC_ENC'] = PandUPF(HHK, 'u10', 47, 3)  # PAN_TM_HRC_HK_ENC
        TM['HRC_EPF'] = PandUPF(HHK, 'u1', 48, 4)  # PAN_TM_HRC_HK_EP
        TM['HRC_AIF'] = PandUPF(HHK, 'u1', 48, 5)  # PAN_TM_HRC_HK_AI
        TM['HRC_AFF'] = PandUPF(HHK, 'u1', 48, 6)  # PAN_TM_HRC_HK_AF
        TM['HRC_MMF'] = PandUPF(HHK, 'u1', 48, 7)  # PAN_TM_HRC_HK_MM
        TM['HRC_IFC'] = PandUPF(HHK, 'u8', 49, 0)  # PAN_TM_HRC_HK_IFC
        TM['HRC_GA'] = PandUPF(HHK, 'u2', 50, 0)  # PAN_TM_HRC_HK_GA
        TM['HRC_ESF'] = PandUPF(HHK, 'u1', 50, 2)  # PAN_TM_HRC_HK_ES
        TM['HRC_EIF'] = PandUPF(HHK, 'u1', 50, 3)  # PAN_TM_HRC_HK_EI
        # if True in (PandUPF(HHK, 'u1', 50, 4) != 0).unique():  # PAN_TM_HRC_HK_RES2
        #     raise decodeRAW_HK_Error("TM Byte 50 bit 4 not 0 for HRC HK")
        TM['HRC_ERR_EN'] = PandUPF(HHK, 'u1', 50, 5)  # PAN_TM_HRC_HK_ERENC
        TM['HRC_ERR_AI'] = PandUPF(HHK, 'u1', 50, 6)  # PAN_TM_HRC_HK_ERAI
        TM['HRC_ERR_AF'] = PandUPF(HHK, 'u1', 50, 7)  # PAN_TM_HRC_HK_ERAF

    del HHK

    # HRC RB1
    HR1 = HRCBin[TM['HRC_ACK'] == 0x0C]
    if not HR1.empty:
        HRCBin = HRCBin.drop(HR1.index.values)
        TM['HRC_R1_MS'] = PandUPF(HR1, 'u16', 44, 0)  # PAN_TM_HRC_RB1_MS
        TM['HRC_R1_MAI'] = PandUPF(HR1, 'u16', 46, 0)  # PAN_TM_HRC_RB1_MAI
        TM['HRC_R1_MII'] = PandUPF(HR1, 'u16', 48, 0)  # PAN_TM_HRC_RB1_MII
        TM['HRC_R1_FDV'] = PandUPF(HR1, 'u3', 50, 0)  # PAN_TM_HRC_RB1_FDV
        TM['HRC_R1_CMV'] = PandUPF(HR1, 'u5', 50, 3)  # PAN_TM_HRC_RB1_CMV
    del HR1

    # HRC RB2
    HR2 = HRCBin[TM['HRC_ACK'] == 0x0D]
    if not HR2.empty:
        HRCBin = HRCBin.drop(HR2.index.values)
        if True in (PandUPF(HR2, 'u4', 44, 0) != 0).unique():  # PAN_TM_HRC_RB2_RES1
            raise decodeRAW_HK_Error(
                "TM Byte 44 bits 0-4 not 0 for HRC RB2")
        TM['HRC_R2_INT'] = PandUPF(HR2, 'u20', 44, 4)  # PAN_TM_HRC_RB2_IT
        TM['HRC_R2_FXC'] = PandUPF(HR2, 'u10', 47, 0)  # PAN_TM_HRC_RB2_FXC
        TM['HRC_R2_FYC'] = PandUPF(HR2, 'u10', 48, 2)  # PAN_TM_HRC_RB2_FYC
        if True in (PandUPF(HR2, 'u1', 49, 4) != 0).unique():  # PAN_TM_HRC_RB2_RES2
            raise decodeRAW_HK_Error("TM Byte 49 bit 4 not 0 for HRC RB2")
        TM['HRC_R2_SFS'] = PandUPF(HR2, 'u1', 49, 5)  # PAN_TM_HRC_RB2_RES2
        TM['HRC_R2_FWZ'] = PandUPF(HR2, 'u2', 49, 6)  # PAN_TM_HRC_RB2_FWZ
        # PAN_TM_HRC_RB2_RES3 and PAN_TM_HRC_RB2_RES5
        if True in (PandUPF(HR2, 'u8', 50, 0) != 0).unique():
            raise decodeRAW_HK_Error("TM Byte 50 not 0 for HRC RB2")
    del HR2

    # HRC RB3
    HR3 = HRCBin[TM['HRC_ACK'] == 0x10]
    if not HR3.empty:
        HRCBin = HRCBin.drop(HR3.index.values)
        if True in (PandUPF(HR3, 'u6', 44, 0) != 0).unique():  # PAN_TM_HRC_RB3_RES1
            raise decodeRAW_HK_Error(
                "TM Byte 44 bits 0-5 not 0 for HRC RB3")
        TM['HRC_R3_LRS'] = PandUPF(HR3, 'u10', 44, 6)  # PAN_TM_HRC_RB3_LRS
        TM['HRC_R3_DPN'] = PandUPF(HR3, 'u16', 46, 0)  # PAN_TM_HRC_RB3_DPN
        TM['HRC_R3_TOL'] = PandUPF(HR3, 'u8', 48, 0)  # PAN_TM_HRC_RB3_TOL
        TM['HRC_R3_MSC'] = PandUPF(HR3, 'u16', 49, 0)  # PAN_TM_HRC_RB3_MSC
    del HR3

    # HRC RB4
    HR4 = HRCBin[TM['HRC_ACK'] == 0x0E]
    if not HR4.empty:
        HRCBin = HRCBin.drop(HR4.index.values)
        TM['HRC_R4_CRC'] = PandUPF(HR4, 'u16', 44, 0)  # PAN_TM_HRC_RB4_CRC
        TM['HRC_R4_SHR'] = PandUPF(HR4, 'u16', 46, 0)  # PAN_TM_HRC_RB4_SHR
        TM['HRC_R4_AIT1'] = PandUPF(
            HR4, 'u10', 48, 0)  # PAN_TM_HRC_RB4_AIT1
        TM['HRC_R4_AIT2'] = PandUPF(
            HR4, 'u10', 49, 2)  # PAN_TM_HRC_RB4_AIT2
        TM['HRC_R4_AIT3'] = PandUPF(
            HR4, 'u1', 50, 4)  # PAN_TM_HRC_RB4_AIT3
        TM['HRC_R4_AIT4'] = PandUPF(
            HR4, 'u1', 50, 5)  # PAN_TM_HRC_RB4_AIT4
        TM['HRC_R4_AIT5'] = PandUPF(
            HR4, 'u1', 50, 6)  # PAN_TM_HRC_RB4_AIT5
        TM['HRC_R4_AIT6'] = PandUPF(
            HR4, 'u1', 50, 7)  # PAN_TM_HRC_RB4_AIT6
    del HR4

    # HRC MetaData in HK
    HRM = HRCBin[TM['HRC_ACK'] == 0xB5]
    if not HRM.empty:
        HRCBin = HRCBin.drop(HRM.index.values)
        TM['HRC_MD_STP'] = PandUPF(HRM, 'u10', 44, 0)  # PAN_TM_HRC_HMD_STP
        if True in (PandUPF(HRM, 'u2', 45, 2) != 0).unique():  # PAN_TM_HRC_HMD_RES1
            raise decodeRAW_HK_Error(
                "TM Byte 44 bits 2-3 not 0 for HRC MetaData")
        TM['HRC_MD_INT'] = PandUPF(HRM, 'u20', 45, 4)  # PAN_TM_HRC_HMD_IT
        TM['HRC_MD_FXC'] = PandUPF(HRM, 'u10', 48, 0)  # PAN_TM_HRC_HMD_FXC
        TM['HRC_MD_FYC'] = PandUPF(HRM, 'u10', 49, 2)  # PAN_TM_HRC_HMD_FYC
        if True in (PandUPF(HRM, 'u1', 50, 4) != 0).unique():  # PAN_TM_HRC_HMD_RES2
            raise decodeRAW_HK_Error(
                "TM Byte 50 bit 4 not 0 for HRC MetaData")
        TM['HRC_MD_SFS'] = PandUPF(HRM, 'u1', 50, 5)  # PAN_TM_HRC_HMD_SFS
        TM['HRC_MD_FWZ'] = PandUPF(HRM, 'u2', 50, 6)  # PAN_TM_HRC_HMD_FWZ
    del HRM

    # Command Response Packet
    TM['HRC_Res_CA'] = PandUPF(HRCBin, 'u8', 44, 0)  # PAN_TM_HRC_RES_CA1
    if True in (PandUPF(HRCBin, 'u48', 45, 0) != 0).unique():
        raise decodeRAW_HK_Error("TM Bytes 45-50 not 0 for HRC CMD Response")
        logger.warning("Likely mixed WAC and HRC Cam responses.")

    return TM


def CUCtoUTC_DT(RAW):
    """Function that takes the 4,2 CUC and converts it to a datetime object"""

    Sources = RAW['Source'].value_counts().index.tolist()
    if len(Sources) > 1:
        logger.error(
            "More than one data source found within HK. Using the most common source")

    elif len(Sources) == 0:
        logger.error("No HK source column found! ABORTING")
        return

    MajSource = Sources[0]

    # First calculate the fractional seconds
    RAW['CUCfrac'] = RAW['Pkt_CUC'].apply(lambda x: (x & 0xFFFF)/0x10000)

    if MajSource == 'SWIS':
        CalcTime = pd.to_datetime(RAW['Unix_Time'], unit='ms')

    elif MajSource == 'LabView':
        RAW['DT'] = pd.to_datetime(RAW['Time'], format='%Y-%m-%d\t%H:%M:%S.%f')
        RAW['Year'] = RAW['DT'].dt.year
        RAW['Month'] = RAW['DT'].dt.month

        # LabView provides the CUC time as the # seconds from the first day
        # of the month, minus an extra day.
        CalcTime = RAW.apply(lambda row:
                             (Time(datetime(row['Year'], row['Month'], 1, 0, 0, 0))
                              - TimeDelta(1, format='jd')
                              + TimeDelta((row['Pkt_CUC'] >> 16)*units.s)
                              + TimeDelta(row['CUCfrac'], format='sec')
                              ).iso, axis=1)

    else:
        # Rover uses time since Mid-day of the year 2000 minues 12 hours
        CalcTime = RAW.apply(lambda row:
                             (Time(2000, format='jyear')
                              + TimeDelta((row['Pkt_CUC'] >> 16)*units.s)
                              # To deal with 12-hour Rover offset
                              - TimeDelta(12*60*60, format='sec')
                              + TimeDelta(row['CUCfrac'], format='sec')
                              ).iso, axis=1)

    return CalcTime


if __name__ == "__main__":
    DIR = Path(
        input("Type the path to the PROC folder where the processed files are stored: "))

    logging.basicConfig(filename=(DIR / 'processing.log'),
                        level=logging.INFO,
                        format='%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
    logger.info('\n\n\n\n')
    logger.info("Running decodeRAW_HK.py as main")
    logger.info("Reading directory: %s", DIR)

    decode(DIR)
