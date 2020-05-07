# -*- coding: utf-8 -*-
"""Where applicable applies calibration to the processed RAW HK pickle file.

This module applies the predetermined calibrations and generates a new
calibrated pickle file:
    - HK Voltages
    - HK Temperatures

:copyright: (c) 2020 by Barry J Whiteside. Mullard Space Science Laboratory - UCL

:license: GPLv3, see LICENSE for more details.
"""

import pandas as pd
from pathlib import Path
import logging

import pancam_fns

logger = logging.getLogger(__name__)
status = logging.getLogger('status')


def cal_HK(proc_dir):
    """Reads processed telemetery and outputs calibrated pandas pickle file.

    Arguments:
        proc_dir {pathlib.dir()} -- Folder containing processed TM pickle file.

    Generates:
        Cal_HKTM.pickle -- A pandas pickle file containing calibrated values.

    """

    logger.info("Calibrating TM HK Files")

    # Search for PanCam Processed Files
    pik_file = pancam_fns.Find_Files(proc_dir, "*RAW_HKTM.pickle")
    if not pik_file:
        logger.warning("No files found - ABORTING")
        return

    # Read RAW TM pickle file
    raw = pd.read_pickle(pik_file[0])
    ctm = pd.DataFrame()
    ctm['DT'] = raw['DT'].copy()

    # Voltages
    ratio = 4096*1.45914

    ctm['Volt_Ref'] = ratio / raw['Volt_Ref']
    ctm['Volt_6V0'] = ctm['Volt_Ref'] / 4096 * 6.4945 * raw['Volt_6V0']
    ctm['Volt_1V5'] = ctm['Volt_Ref'] * raw['Volt_1V5']/4096

    # Temperatures
    # Cal_A = {"LFW":306.90, "RFW":308.57, "HRC":313.57, "LWAC":307.91, "RWAC":307.17, "LDO":310.42, "ACT":304.15}
    # Cal_B = {"LFW":-268.21, "RFW":-268.14, "HRC":-274.94, "LWAC":-267.41, "RWAC":-266.71, "LDO":-270.04, "ACT":-264.52}
    cal_a = [306.90, 308.57, 313.57, 307.91, 307.17, 310.42, 304.15]
    cal_b = [-268.21, -268.14, -274.94, -267.41, -266.71, -270.04, -264.52]

    ctm['Temp_LFW'] = raw['Temp_LFW'] * cal_a[0] / raw['Volt_Ref'] + cal_b[0]
    ctm['Temp_RFW'] = raw['Temp_RFW'] * cal_a[1] / raw['Volt_Ref'] + cal_b[1]
    ctm['Temp_HRC'] = raw['Temp_HRC'] * cal_a[2] / raw['Volt_Ref'] + cal_b[2]
    ctm['Temp_LWAC'] = raw['Temp_LWAC'] * cal_a[3] / raw['Volt_Ref'] + cal_b[3]
    ctm['Temp_RWAC'] = raw['Temp_RWAC'] * cal_a[4] / raw['Volt_Ref'] + cal_b[4]
    ctm['Temp_LDO'] = raw['Temp_LDO'] * cal_a[5] / raw['Volt_Ref'] + cal_b[5]
    ctm['Temp_HRCA'] = raw['Temp_HRCA'] * cal_a[6] / raw['Volt_Ref'] + cal_b[6]

    write_file = proc_dir / "Cal_HKTM.pickle"
    if write_file.exists():
        write_file.unlink()
        logger.info("Deleting file: %s", write_file.stem)
    with open(write_file, 'w'):
        ctm.to_pickle(write_file)
        logger.info("PanCam Cal HK TM pickled.")


if __name__ == "__main__":
    proc_dir = Path(
        input("Type the path to the PROC folder where the processed files are stored: "))

    logger, status = pancam_fns.setup_logging()
    pancam_fns.setup_proc_logging(logger, proc_dir)

    logger.info('\n\n\n\n')
    logger.info("Running Cal_HK.py as main")
    logger.info("Reading directory: %s", proc_dir)

    cal_HK(proc_dir)
    status.info("Completed")
