# -*- coding: utf-8 -*-
"""
Created on Thu Oct 31 17:18:02 2019

@author: ucasbwh
Parses Rover .ha and .csv files by extracting PanCam data.
"""

import pandas as pd
from pathlib import Path
from bitstruct import unpack_from as upf
import logging
import imageio
from datetime import datetime, timedelta

import pancam_fns

logger = logging.getLogger(__name__)
status = logging.getLogger('status')

# Variables for the script
name_hk_es = "AB.TM.TM_RMI000402"
name_hk_ne = "AB.TM.TM_RMI000401"

name_rov_ls = "AB.TM.MRSP8001"
name_rov_hs = "AB.TM.MRSP8002"

NAME_PAN_TM = "AB.TM.TRPR0479"
NAME_TILT_TM = "AB.TM.TRPL0480"


def TM_extract(ROV_DIR):
    """Searches for TM with Rover files and creates a binary array of each file found"""

    logger.info("Processing Rover TM Files")
    DF = pd.DataFrame()
    DRS = pd.DataFrame()
    DRT = pd.DataFrame()
    DG = pd.DataFrame()

    TMfiles = pancam_fns.Find_Files(ROV_DIR, "STDRawOcds*.csv")
    if not TMfiles:
        logger.warning("No files found - ABORTING")
        return False

    DF_es_entries = 0
    DF_ne_entries = 0

    # Read CSV files and parse
    for file in TMfiles:
        logger.info("Reading %s", file.name)
        DT = pd.read_csv(file, sep=';', header=0, index_col=False)

        # Search for PanCam housekeeping
        DF_es_entries += DT[DT['NAME'] == name_hk_es].shape[0]
        DF_ne_entries += DT[DT['NAME'] == name_hk_ne].shape[0]

        DL = DT[(DT['NAME'] == name_hk_es) | (
            DT['NAME'] == name_hk_ne)].copy()
        if not DL.empty:
            DL['RAW'] = DL.RAW_DATA.apply(lambda x: x[38: -4])
            DL['DT'] = pd.to_datetime(
                DL['GROUND_REFERENCE_TIME'], format='%d/%m/%Y %H:%M:%S.%f')
            DF = DF.append(DL[['RAW', 'DT']], ignore_index=True)

        # Rover HK both low and high speed
        DP = DT[(DT['NAME'] == name_rov_ls) | (
            DT['NAME'] == name_rov_hs)].copy()
        if not DP.empty:
            DG = DP.RAW_DATA.apply(lambda x: x[2:])
            DG = DG.apply(lambda x: bytearray.fromhex(x))
            # PanCam Current
            OffBy, OffBi, Len = 85, 4, 'u12'
            DP['RAW_Inst_Curr'] = DG.apply(
                lambda x: upf(Len, x, offset=8*OffBy+OffBi)[0])
            DP['Inst_Curr'] = DP['RAW_Inst_Curr'] * 1.1111/4095
            # PanCam Heater
            OffBy, OffBi, Len = 57, 4, 'u12'
            DP['RAW_HTR_Curr'] = DG.apply(
                lambda x: upf(Len, x, offset=8*OffBy+OffBi)[0])
            DP['HTR_Curr'] = DP['RAW_HTR_Curr'] * 1.1111/4095
            # PanCam Heater Status
            OffBy, OffBi, Len = 51, 2, 'u1'
            DP['HTR_ST'] = DG.apply(lambda x: upf(
                Len, x, offset=8*OffBy+OffBi)[0])
            # PanCam Power Status
            OffBy, OffBi, Len = 77, 1, 'u1'
            DP['PWR_ST'] = DG.apply(lambda x: upf(
                Len, x, offset=8*OffBy+OffBi)[0])
            DP['DT'] = pd.to_datetime(
                DP['GROUND_REFERENCE_TIME'], format='%d/%m/%Y %H:%M:%S.%f')
            DRS = DRS.append(DP, ignore_index=True)

        # Rover HK Thermistors Only contained within low speed HK
        DK = DT.loc[DT['NAME'] == name_rov_ls].copy()
        if not DK.empty:
            DW = DK.RAW_DATA.apply(lambda x: x[2:])
            DW = DW.apply(lambda x: bytearray.fromhex(x))
            DK['DT'] = pd.to_datetime(
                DK['GROUND_REFERENCE_TIME'], format='%d/%m/%Y %H:%M:%S.%f')

            # Get first entry and determine if to use old or new cal
            dtime0 = DK['DT'].iloc[0]
            # If after Feb 2020 use new Cal
            if dtime0 < datetime(2020, 2, 1):
                logger.info("Using old thermistor calibration 511,3 and 559,3")
                piu_loc = (511, 3, 'u13')
                dcdc_loc = (559, 3, 'u13')

            elif dtime0 < datetime(2021, 2, 1):
                logger.info("Using thermistor calibration 508,3 and 556,3")
                piu_loc = (508, 3, 's13')
                dcdc_loc = (556, 3, 's13')

            else:
                logger.info("Using new thermistor calibration 510,3 and 558,3")
                piu_loc = (510, 3, 's13')
                dcdc_loc = (558, 3, 's13')

            # PIU Temp
            (OffBy, OffBi, Len) = piu_loc
            DK['RAW_PIU_T'] = DW.apply(
                lambda x: upf(Len, x, offset=8*OffBy+OffBi)[0])
            # Calculated from thermistor curve provided
            DK['PIU_T'] = DK['RAW_PIU_T']*0.18640 - 259.84097
            # DCDC Temp
            OffBy, OffBi, Len = dcdc_loc
            DK['RAW_DCDC_T'] = DW.apply(
                lambda x: upf(Len, x, offset=8*OffBy+OffBi)[0])
            # Calculated from thermistor curve provided
            DK['DCDC_T'] = DK['RAW_DCDC_T']*0.18640 - 259.84097

            DRT = DRT.append(DK, ignore_index=True)

    if (DF_es_entries > 0):
        logger.info(f"Number of PanCam HK Ess found: {DF_es_entries}")
    else:
        logger.error(f"Rover TM_extract found no HK Ess")

    if (DF_ne_entries > 0):
        logger.info(f"Rover TM_extract total HK NonE found: {DF_ne_entries}")
    else:
        logger.error(f"Rover TM_extract found no HK NonE")

    logger.info("Number of PanCam TMs found: %d", DF.shape[0])
    logger.info("Number of Rover Status Entries found: %d", DRS.shape[0])
    logger.info("Number of Rover Temperature Entries found: %d", DRT.shape[0])

    if DF.shape[0] != 0:
        write_dts = DF['DT'].iloc[0].strftime('%y%m%d_%H%M%S_')
        DF['Source'] = "STDRawOcds.csv"
        DF.to_pickle(ROV_DIR / "PROC" / (write_dts + "csv_Unproc_HKTM.pickle"))
        logger.info("PanCam HKTM pickled.")

    if DRS.shape[0] != 0:
        write_dts = DRS['DT'].iloc[0].strftime('%y%m%d_%H%M%S_')
        DRS.to_pickle(ROV_DIR / "PROC" / (write_dts + "RoverStatus.pickle"))
        logger.info("Rover Status TM pickled.")

    if DRT.shape[0] != 0:
        write_dts = DRT['DT'].iloc[0].strftime('%y%m%d_%H%M%S_')
        DRT.to_pickle(ROV_DIR / "PROC" / (write_dts + "RoverTemps.pickle"))
        logger.info("Rover Temperatures TM pickled.")

    logger.info("Processing Rover TM Files Completed")

    return True


def TC_extract(ROV_DIR):

    logger.info("Processing Rover TC Files")
    TC = pd.DataFrame()

    # Find all Rover TC files within folder and subfolders
    TCfiles = pancam_fns.Find_Files(ROV_DIR, "STDChrono*.csv")
    if not TCfiles:
        logger.error("No files found - ABORTING")
        return

    # Read CSV file and parse
    for file in TCfiles:
        logger.info("Reading %s", file.name)
        dt = pd.read_csv(file, sep=';', encoding="ISO-8859-1",
                         header=0, dtype=object, index_col=False)

        dp_rov_cmd = dt[dt['DESCRIPTION'].str.contains(
            "Pan Cam", na=False) & dt['NAME'].str.contains("CRM", na=False)].copy()

        dp_action_start = dt[dt['DESCRIPTION'].str.contains(
            "Pan Cam", na=False) & dt['NAME'].str.contains("RMI000331", na=False)].copy()

        if not dp_rov_cmd.empty:
            TC_rov = dp_rov_cmd[['NAME', 'DESCRIPTION', 'GROUND_REFERENCE_TIME']].copy()
            TC_rov['ACTION'] = dp_rov_cmd['DESCRIPTION'].map(lambda x: x.lstrip('Pan Cam'))
        else:
            TC_rov = pd.DataFrame()

        # TC_action = pd.DataFrame()
        if not dp_action_start.empty:
            dm_action_start = dp_action_start['VARIABLE_PART'].str.split(',', -1, expand=True).copy()
            dm_action_start['ACTION_CODE'] = dm_action_start[17]
            dm_action_start['ACTION'] = dm_action_start['ACTION_CODE'].map(lambda x: x[x.find('=')+1: x.find('|')])
            TC_action = pd.concat(
                [dp_action_start[['NAME', 'DESCRIPTION', 'GROUND_REFERENCE_TIME']], dm_action_start['ACTION']], axis=1)
        else:
            TC_action = pd.DataFrame()

        TC = pd.concat([TC_rov, TC_action])

        if not TC.empty:
            TC['DT'] = pd.to_datetime(
                TC['GROUND_REFERENCE_TIME'], format='%d/%m/%Y %H:%M:%S.%f')  # + pd.DateOffset(hours=2)
            TC['LEVEL'] = 1

    logger.info("Number of PanCam TCs found: %d", TC.shape[0])

    if TC.shape[0] != 0:
        write_dts = TC['DT'].iloc[0].strftime('%y%m%d_%H%M%S_')
        TC.to_pickle(ROV_DIR / "PROC" / (write_dts + "Unproc_TC.pickle"))
        logger.info("Rover TC pickled")

    logger.info("Processing Rover TC Files Completed")


def NavCamBrowse(ROV_DIR):
    """Searches for PGM files and creates an 8-bit .png to browse"""

    logger.info("Searching for NavCam .pgm files to generate browse")
    PGM_Files = pancam_fns.Find_Files(ROV_DIR, "*.pgm")

    for curFile in PGM_Files:
        image = imageio.imread(curFile)
        write_file = curFile.with_suffix(".png")

        # Check if file exists
        pancam_fns.exist_unlink(write_file)
        logger.info("Creating file: %s", write_file.name)
        imageio.imwrite(write_file, image)


def type(ROV_DIR):
    """Returns the Rover model"""

    # Constants
    sources = {1: 'exm_pfm_ccs', 2: 'exm_gtm_ccs'}

    logger.info("Searching for Rover model")

    # Find all Rover TC files within folder and subfolders
    TCfiles = pancam_fns.Find_Files(ROV_DIR, 'STDChrono*.csv')

    if TCfiles:
        # Read CSV file and parse to find model
        file = TCfiles[0]
        logger.info("Reading %s", file.name)
        dt = pd.read_csv(file, sep=';', encoding="ISO-8859-1",
                         header=0, dtype=object, index_col=False)
    else:
        logger.error("Unable to find details of Rover type")

    try:
        # Try to search logs for known entry
        dp = dt[dt['TEMPLATE'] == 'LG'].iloc[0]
        dm = dp['VARIABLE_PART']
        model = dm.split(',')[-3]
        if model not in sources.values():
            raise ValueError("Unrecognised Rover model")

    except:
        # If not found then ask user
        usr_ch = input(
            'Unable to determine Rover model, select as appropriate:\n'
            f'\t{sources[1]}: [1 = Default]\n'
            f'\t{sources[2]}: [2]\n\n'
            'Selection:  ')

        try:
            model = sources[int(usr_ch)]
        except:
            model = sources[1]

    return model


def sw_ver(ROV_DIR):
    """Returns the rover module software version RMSW"""

    logger.info("Searching for RMSW_Ver")

    user_ch = input("Input Rover Module Software Version [Default = 2.0]: ")

    if user_ch == '':
        user_ch = 2.0

    rmsw_ver = float(user_ch)

    return rmsw_ver


def ptu_extract(ROV_DIR):
    """Searches for a STDParamAnalysis.csv and if found extracts all PTU TMs into a pickle file

    Args:
        ROV_DIR ([pathlib]): Rover directory containing STDParamAnalysis.csv in a subfolder

    Returns:
        bool: True if file found and processed, otherwise False

    Generates:
        PTU_DATA.pickle: A pickle file containing PTU information with duplicate entries removed.
    """

    logger.info("Processing PTU Files")

    std_files = pancam_fns.Find_Files(ROV_DIR, "STDParamAnalysis*.csv")
    if not std_files:
        logger.warning("No STDParamAnalysis*.csv files found - Skipping PTU parsing")
        return False

    raw_pan = pd.DataFrame()
    raw_tilt = pd.DataFrame()

    # Read top of first file to get column names
    # Necessary as a mix of ';' and ',' are used as seperators

    for file in std_files:
        logger.info("Reading %s", file.name)

        # Import from CSV, drop duplicates (as coming from multiple packets)
        raw_ptufile = pd.read_csv(file, sep=';|,', header=0, index_col=False, engine='python')
        raw_ptufile.drop_duplicates(subset=["NAME", "ON_BOARD_TIME", "RAW_DATA"], inplace=True)
        #raw_ptufile[~raw_ptufile.duplicated(subset=["NAME", "ON_BOARD_TIME", "RAW_DATA"])]
        raw_ptufile['DT'] = pd.to_datetime(raw_ptufile['ON_BOARD_TIME'], format='%d/%m/%Y %H:%M:%S.%f')

        # Remove RAW zero values
        raw_ptufile = raw_ptufile[raw_ptufile.RAW_DATA > 0]

        raw_pan = raw_pan.append(raw_ptufile[raw_ptufile.NAME == NAME_PAN_TM])
        raw_tilt = raw_tilt.append(raw_ptufile[raw_ptufile.NAME == NAME_TILT_TM])

    pan_entries = raw_pan.shape[0]
    tilt_entries = raw_tilt.shape[0]

    if (pan_entries > 0):
        logger.info(f"Number of unique PTU Pan positions found: {pan_entries}")
        raw_pan.to_pickle(ROV_DIR / "PROC" / "ptu_pan.pickle")
        logger.info("Rover PTU Pan pickled.")
    else:
        logger.error(f"Rover ptu_extract found no Pan entries despite ParamAnalysis file.")

    if (tilt_entries > 0):
        logger.info(f"Number of unique PTU Tilt positions found: {tilt_entries}")
        raw_tilt.to_pickle(ROV_DIR / "PROC" / "ptu_tilt.pickle")
        logger.info("Rover PTU tilt pickled.")
    else:
        logger.error(f"Rover ptu_extract found no Tilt entries despite ParamAnalysis file.")

    return True


if __name__ == "__main__":
    dir = Path(
        input("Type the path to thefolder where the Rover files are stored: "))

    proc_dir = dir / "PROC"
    if proc_dir.is_dir():
        status.info("Processing' Directory already exists")
    else:
        status.info("Generating 'Processing' directory")
        proc_dir.mkdir()

    logger, status = pancam_fns.setup_logging()
    pancam_fns.setup_proc_logging(logger, proc_dir)

    logger.info('\n\n\n\n')
    logger.info("Running rover.py as main")
    logger.info("Reading directory: %s", proc_dir)

    # RoverType(dir)
    # sw_ver(dir)
    TM_extract(dir)
    TC_extract(dir)
    NavCamBrowse(dir)
    ptu_extract(dir)
