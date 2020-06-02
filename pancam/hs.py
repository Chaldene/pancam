# -*- coding: utf-8 -*-
"""
hs.py

Barry Whiteside
Mullard Space Science Laboratory - UCL

PanCam Data Processing Tools
Created 14 Feb 2020
"""

from pathlib import Path
from bitstruct import unpack_from as upf
import pandas as pd
import logging

import pancam_fns
from pancam_fns import PandUPF

logger = logging.getLogger(__name__)
status = logging.getLogger('status')


def decode(proc_dir: Path, spw_header: bool = False):
    """Searches the proc_dir for hs_raw.pickle and decodes PanCam parameters generating a new pickle file

    Arguments:
        proc_dir {Path} -- Folder path to the hs_raw.pickle file.

    Keyword Arguments:
        spw_header {bool} -- Set to true if RAW data includes spacewire header. (default: {False})

    Generates:
        hs.pickle -- H+S pandas dataframe with decoding parameters columns and raw.
    """

    logger.info("Running H+S decode")
    logger.info("Searching for hs_raw.pickle file")
    hs_file = pancam_fns.Find_Files(
        proc_dir, "hs_raw.pickle", SingleFile=True)[0]
    hs = pd.read_pickle(hs_file)

    raw = hs['RAW'].apply(lambda x: bytearray.fromhex(x))

    if spw_header:
        spw_offset = 12
        logging.info("Spacewire header offset added to H&S %d", spw_offset)
    else:
        logging.info("No spacewire header offset used.")
        spw_offset = 0

    # HS Decode
    hs['HK_Addr'] = PandUPF(raw, 'u32',  0+spw_offset, 0)
    hs['HK_Len'] = PandUPF(raw, 'u16',  4+spw_offset, 0)
    hs['HK_Cnt'] = PandUPF(raw, 'u16',  6+spw_offset, 0)
    hs['Sci_Addr'] = PandUPF(raw, 'u32',  8+spw_offset, 0)
    hs['Sci_Len'] = PandUPF(raw, 'u24', 12+spw_offset, 0)
    hs['LDT'] = PandUPF(raw, 'u8', 15+spw_offset, 0)
    hs['Sci_Cnt'] = PandUPF(raw, 'u16', 16+spw_offset, 0)

    logger.info("Writing H+S decoded to pickle file")
    hs.to_pickle(proc_dir / "hs.pickle")
    logger.info("PanCam H+S decoded pickled.")

    logger.info("--Parsing HS decode completed.")


def verify(proc_dir: Path):
    """Finds the decoded HS.pickle and runs the following checks on the data:
        - HK Address is constant
        - HK Length is a valid value
        - HK counter is either the same or increasing
        - Sci address is constant
        - Sci length is constant
        - LDT Ctrl is always <7
        - Sci counter is either the same or increasing

    Arguments:
        proc_dir {Path} -- Folder path to the hs.pickle file
    """

    # Constants
    pc_hk_addr = 0x80000000
    pc_hk_lens = [0, 72, 88]
    pc_sci_addr = 0xC0000000
    pc_sci_len = [0x0, 0x200030]

    # Searches folder for hs.pickle and then verifies hs data is as expected
    logger.info("Running H+S verify")

    logger.info("Searching for hs.pickle file")
    hs_file = pancam_fns.Find_Files(proc_dir, "hs.pickle", SingleFile=True)[0]
    hs = pd.read_pickle(hs_file)

    verify = pd.DataFrame()
    err_df = pd.DataFrame()

    # Verify HK Address is always 0x80 00 00 00
    # Check first value is as expected
    verify['HK_Addr'] = ~(hs['HK_Addr'] == pc_hk_addr)
    err_df = hs[verify['HK_Addr']]
    if err_df.shape[0] != 0:
        logger.error(
            "HS HK Address not as expected %d occurances.", err_df.shape[0])
        logger.info("\n %s \n", err_df)

    # Verify the HK Length is either 72 or 88 bytes
    verify['HK_Len'] = ~hs['HK_Len'].isin(pc_hk_lens)
    err_df = hs[verify['HK_Len']]
    if err_df.shape[0] != 0:
        logger.error("HS HK unexpected length %d occurances.",
                     err_df.shape[0])
        logger.info("\n %s \n", err_df)

    # Verify HK counter is always increasing
    verify['HK_Cnt'] = hs['HK_Cnt'].diff() < 0
    err_df = hs[verify['HK_Cnt']]
    if err_df.shape[0] != 0:
        logger.error("HS HK Count not increasing, %d occurances.",
                     err_df.shape[0])
        for row in err_df.index.values:
            logger.info("Occurance")
            logger.info("\n %s \n", hs.iloc[row-1:row+2])

    # Verify Sci Address is always 0xC0 00 00 00
    # Check first value is as expected
    verify['Sci_Addr'] = ~(hs['Sci_Addr'] == pc_sci_addr)
    err_df = hs[verify['Sci_Addr']]
    if err_df.shape[0] != 0:
        logger.error(
            "HS Sci Address not as expected %d occurances.", err_df.shape[0])
        logger.info("\n %s \n", err_df)

    # Verify the Sci Length is always 2,097,200 bytes
    verify['Sci_Len'] = ~hs['Sci_Len'].isin(pc_sci_len)
    err_df = hs[verify['Sci_Len']]
    if err_df.shape[0] != 0:
        logger.error("HS Sci unexpected length %d occurances.",
                     err_df.shape[0])
        logger.info("\n %s \n", err_df)

    # Verify the LDT Ctrl is always <7
    verify['LDT'] = ~(hs['LDT'] < 8)
    err_df = hs[verify['LDT']]
    if err_df.shape[0] != 0:
        logger.error("HS LDT not in expected range of 0 to 7, %d occurances",
                     err_df.shape[0])
        logger.info("\n %s \n", err_df)

    # Check that the Sci counter is always increasing
    verify['Sci_Cnt'] = hs['Sci_Cnt'].diff() < 0
    err_df = hs[verify['Sci_Cnt']]
    if err_df.shape[0] != 0:
        logger.error("HS Sci count not increasing, %d occurances",
                     err_df.shape[0])
        for row in err_df.index.values:
            logger.info("Occurance")
            logger.info("\n %s \n", hs.iloc[row-1:row+2])

    logger.info("--HS Verify Completed.")


def sci_cnt(proc_dir: Path):
    """Calculates the number of science images generated as reported in HS

    Arguments:
        proc_dir {Path} -- Folder path to the hs.pickle file

    Returns:
        int -- The image count
    """

    logger.info("Generating expected number of science images from HS")
    logger.info("Searching for hs.pickle file")
    hs_file = pancam_fns.Find_Files(proc_dir, "hs.pickle", SingleFile=True)[0]
    hs = pd.read_pickle(hs_file)

    # First find last count entry
    img_cnt = hs['Sci_Cnt'].iloc[-1]

    # Find all instances where it has reset and add to total
    cnt_rst = hs.Sci_Cnt[hs['Sci_Cnt'].diff(-1) > 0]
    img_cnt += cnt_rst.sum()
    logger.info("A total of %d images generated over session", img_cnt)

    return img_cnt


def all_default_image_dim(proc_dir):
    """Returns false if any entries in hs Sci_Len not 0 or default size.

    Arguments:
        proc_dir {Path} -- Folder path to the hs.pickle file

    Returns:
        bool -- False if any enties are not 0 or 2,097,200 bytes.
    """

    # Constants
    NORM_BYTE_LENS = {0, 2097200}

    logger.info("Verifying all science images are default dimensions")
    logger.info("Searching for hs.pickle file")
    hs_file = pancam_fns.Find_Files(proc_dir, "hs.pickle", SingleFile=True)[0]
    hs = pd.read_pickle(hs_file)

    verify = pd.DataFrame()
    verify['Sci_Len'] = ~hs['Sci_Len'].isin(NORM_BYTE_LENS)
    err_df = hs[verify['Sci_Len']]
    if err_df.shape[0] != 0:
        status.info(
            "Non-Default image dimensions found, not rebuilding from SpW packets and only using saved .bin")
        return False

    return True


if __name__ == "__main__":
    proc_dir = Path(
        input("Type the path to thefolder where the hs.pickle files are stored: "))

    logger, status = pancam_fns.setup_logging()
    pancam_fns.setup_proc_logging(logger, proc_dir)

    logger.info('\n\n\n\n')
    logger.info("Running hs.py as main")
    logger.info("Reading directory: %s", proc_dir)

    decode(proc_dir)
    verify(proc_dir)
    status.info("Sci_Cnt: %s", sci_cnt(proc_dir))
