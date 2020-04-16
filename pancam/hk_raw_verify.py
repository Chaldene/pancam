# -*- coding: utf-8 -*-
"""
hk_raw_verify.py
For verifying the structure and contents of PanCam hk_raw.

Barry Whiteside
Mullard Space Science Laboratory - UCL

PanCam Data Processing Tools
Created 24 Mar 2020
"""

import pandas as pd
import logging
import numpy as np

import pancam_fns
from pancam_fns import DropTM
from pancam_fns import PandUPF

logger = logging.getLogger(__name__)


def blanks(rtm, bin):
    """
    Performs checks on the following:
        - bin line is not empty

    Arguments:
        rtm {pd.DataFrame} -- raw unprocessed HK tm
        bin {bytearray} -- raw HK tm data

    Returns:
        rtm -- with removed blank entries
        bin -- with removed blank entries
    """

    verify = pd.DataFrame()
    err_df = pd.DataFrame()

    logger.info("Verifying no blank HK lines")

    # Check for blank entries in bin
    verify['Blank'] = bin.apply(len) == 0
    err_df = rtm[verify['Blank']]
    if not err_df.empty:
        logging.error("Blank HK Entry Detected")
        rtm, bin = DropTM(err_df, rtm, bin)

    return rtm, bin


def hkheader(tm, bin):
    """
    Performs checks on the following:
        - Byte 11 is empty
        - Block type is always 0 for TM
        - Instr. ID is always 5 for PanCam
        - TM Type is always 0 or 1
        - TM Header Data Length matches len(bin)
        - TM Header Data Length is one of two expected lengths

    Arguments:
        tm {pd.DataFrame} -- decoded tm header.
        bin {bytearray} -- raw HK tm data

    Returns:
        tm -- with removed entries that do not match expected
        bin -- with removed entries that do not match expected
    """

    verify = pd.DataFrame()
    err_df = pd.DataFrame()

    logger.info("Verifying HK RAW TM Header")

    # Byte 11                                            #PAN_TM_PIU_HKN_RES and PAN_TM_PIU_HK_RES
    if True in (PandUPF(bin, 'u8', 11, 0) != 0).unique():
        logger.error("TM Byte 11 not 0")

    # Check that the block type is always 0 for TM
    verify['Block_Type'] = tm['Block_Type'] != 0
    err_df = tm[verify['Block_Type']]
    if not err_df.empty:
        logging.error("Incorrect Block Type identified not a TM")
        tm, bin = DropTM(err_df, tm, bin)
        verify = verify.drop(err_df.index)

    # Check that the Instr. ID is always 5
    if True in (tm['Instr_ID'] != 5).unique():
        logging.error("TM Instr. ID instance when not equal to 5")

    # Check that the TM Type is always 0 or 1
    verify['TM_Type_ID'] = tm['TM_Type_ID'] > 1
    err_df = tm[verify['TM_Type_ID']]
    if not err_df.empty:
        logging.error("TM Type ID expected 0 or 1, not a HK")
        tm, bin = DropTM(err_df, tm, bin)
        verify = verify.drop(err_df.index)

    # Check that the data length matches that in binary
    verify['Data_Len'] = (bin.apply(len)-11) != tm['Data_Len']
    err_df = tm[verify['Data_Len']]
    if not err_df.empty:
        logging.error(
            "Missing HK Data Detected - TM Data Len does not match actual length")
        tm, bin = DropTM(err_df, tm, bin)
        verify = verify.drop(err_df.index)

    # Check that the TM Type has the correct length
    hk_lengths = {0: 61, 1: 77}
    verify['TM_Type_ID'] = tm['TM_Type_ID'].replace(
        hk_lengths) != tm['Data_Len']
    err_df = tm[verify['TM_Type_ID']]
    if not err_df.empty:
        logging.error("TM Type ID does not match TM Data Length in Header")
        tm, bin = DropTM(err_df, tm, bin)
        verify = verify.drop(err_df.index)

    # Calculate the time delta between HK
    tm['Pkt_CUC_Delta'] = tm['Pkt_CUC'].diff()
    verify['Pkt_CUC_Delta'] = tm['Pkt_CUC_Delta'] != 0x10000  # Not a gap of 1s

    err_df = tm[verify['Pkt_CUC_Delta']]
    if not err_df.empty:
        logging.warning("TM CUC Delta not equal to 1s")
        logger.info("\n%s", err_df[['Pkt_CUC_Delta', 'TM_Type_ID']])

    verify['LRG_Delta'] = ~tm['Pkt_CUC_Delta'].between(
        0xCCCD, 0x17FFF)  # Not between 0.8s and 1.5s
    verify['LRG_Delta'].iloc[0] = False
    err_df = tm[verify['LRG_Delta']]
    if not err_df.empty:
        logger.error("TM CUC Delta not between 0.8 and 1.5s")
        logger.error("Values: %s\n", verify['LRG_Delta'].value_counts())

    # Ensure the time delta between Ess-HK is < 10s
    ess_tm = tm[tm['TM_Type_ID'] == 0].copy()
    ess_tm['Ess_CUC_Delta'] = ess_tm['Pkt_CUC'].diff()
    verify = pd.DataFrame()  # As different size for just ess_tm
    verify['Ess_Delta'] = ess_tm['Ess_CUC_Delta'] > 0xA0000
    err_df = ess_tm[verify['Ess_Delta']]
    if not err_df.empty:
        logger.error("Instances of Ess HK TM CUC Delta not less than 10s")
        logger.info("\n%s", err_df[['Ess_CUC_Delta', 'Pkt_CUC']])

    return tm, bin


def hkne(tm, bin):
    """
    Performs checks on the following:
        - Reported PIU version is within the list of allowed values
        - filter wheel recirculation time has not changed
        - filter wheel speed has not changed
        - filter wheel current has not changed
        - filter wheel step level factor has not changed

    Arguments:
        tm {pd.DataFrame} -- decoded tm header.
        bin {bytearray} -- raw HK tm data

    Returns:
        tm -- same as input with nothing removed (placeholder)
        bin -- same as input with nothing removed, (placeholder)
    """

    allowed_PIU_Ver = [288, np.nan]

    logger.info("Verifying HKNE Contents")

    # Check PIU version
    if (set(tm.PIU_Ver.unique()) - set(allowed_PIU_Ver)):
        logger.error("Illegal PIU Version Detected!")

    # Check recirculation time
    if (tm['FWL_RTi'].nunique() != 1) or (tm['FWR_RTi'].nunique() != 1):
        logger.error("Filter Wheel recirculation time change detected!")

    # Check speed
    if (tm['FWL_Spe'].nunique() != 1) or (tm['FWR_Spe'].nunique() != 1):
        logger.error("Filter Wheel speed change detected")

    # Check current
    if (tm['FWL_Cur'].nunique() != 1) or (tm['FWR_Cur'].nunique() != 1):
        logger.error("Filter Wheel current change detected")

    # Check step level factor
    if (tm['FWL_StL'].nunique() != 1) or (tm['FWR_StR'].nunique() != 1):
        logger.error("Filter Wheel step level factor change detected")

    return tm, bin


def gen_wac_crc_tab():
    """Generates a CRC lookup table using the WAC algorithm.

    Returns:
        bytes -- A lookup table with the 256 entries for the WAC algorithm.
    """

    poly = 0x4D
    table = []

    for byte in range(256):
        crc = 0
        for _ in range(8):
            if (byte ^ crc) & 0x80:
                crc = (crc << 1) ^ poly
            else:
                crc <<= 1
            byte <<= 1
            crc &= 0xFF

        table.append(crc)
    return table


def calc_wac_crc(crc_tab, bin_data):
    """Calculates the CRC of the bin_data using the WAC algorithm

    Arguments:
        crc_tab {bytes} -- Precomputed CRC lookup table for WAC algorithm
        bin_data {bytes} -- Data CRC is to be calculated

    Returns:
        int -- Returns value of CRC or 0x0 if WAC response is a DT.
    """

    if (bin_data[0] & 0xC0) == 0x80:
        return 0x00

    incr = 0xFF

    for inbyte in bin_data:
        incr = crc_tab[incr ^ inbyte]

    return incr


def wac(tm, wacbin):
    """
    Performs checks on the following:
        - WAC TMs begin with with a '0x1' start marker
        - Reports if a memory check has been performed, raises error if failed
        - Response CRC matches for all except DT 

    Arguments:
        tm {pd.DataFrame} -- decoded tm header.
        wacbin {bytearray} -- raw HK tm data containing just wac rows

    Returns:
        tm -- same as input with nothing removed (placeholder)
        wacbin -- same as input with nothing removed, (placeholder)
    """

    logger.info("Verifying WAC Contents")

    verify = pd.DataFrame()
    err_df = pd.DataFrame()

    # Check that the start marker is always 1
    verify['MKR'] = PandUPF(wacbin, 'u1', 44, 2) != 1
    err_df = wacbin[verify['MKR']]
    if not err_df.empty:
        logging.error("WAC start marker not always 0x1")
        logging.info("Marker error at: \n%s", err_df.index.values)

    # Memory check
    mc = tm['WAC_HK_MCK']
    if 1 in mc.values:
        logging.error("Memory check performed and successful")
    if 2 in mc.values:
        logging.error("Memory check performed and failed!")
    if any(x > 3 for x in mc.values):
        logging.error("Memory check invalid value")

    # Response CRC
    crc_tab = gen_wac_crc_tab()
    verify['CRC'] = wacbin.apply(lambda x: calc_wac_crc(crc_tab, x[44:60]))
    err_df = wacbin[verify['CRC'] != 0]
    if not err_df.empty:
        logging.error("WAC response CRC mismatch!")
        logging.info("WAC CRC errors at: \n%s", err_df.index.values)

    return tm, wacbin
