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

import pancam_fns
from pancam_fns import DropTM
from pancam_fns import PandUPF

logger = logging.getLogger(__name__)


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
        tm {pd.DataFrame} -- pandas dataframe containing already decoded tm header.
        bin {bytearray} -- bytearray of raw HK tm data

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

    # Check that the Instr. ID is always 5
    if True in (tm['Instr_ID'] != 5).unique():
        logging.error("TM Instr. ID instance when not equal to 5")

    # Check that the TM Type is always 0 or 1
    verify['TM_Type_ID'] = tm['TM_Type_ID'] > 1
    err_df = tm[verify['TM_Type_ID']]
    if not err_df.empty:
        logging.error("TM Type ID expected 0 or 1, not a HK")
        tm, bin = DropTM(err_df, tm, bin)

    # Check that the data length matches that in binary
    verify['Data_Len'] = (bin.apply(len)-11) != tm['Data_Len']
    err_df = tm[verify['Data_Len']]
    if not err_df.empty:
        logging.error(
            "Missing HK Data Detected - TM Data Len does not match actual length")
        tm, bin = DropTM(err_df, tm, bin)

    # Check that the TM Type has the correct length
    hk_lengths = {0: 61, 1: 77}
    verify['TM_Type_ID'] = tm['TM_Type_ID'].replace(
        hk_lengths) != tm['Data_Len']
    err_df = tm[verify['TM_Type_ID']]
    if not err_df.empty:
        logging.error("TM Type ID does not match TM Data Length in Header")
        tm, bin = DropTM(err_df, tm, bin)

    return tm, bin
