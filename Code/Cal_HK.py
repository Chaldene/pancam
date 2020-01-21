# Cal_HK.py
#
# Barry Whiteside
# Mullard Space Science Laboratory - UCL
#
# PanCam Data Processing Tools

import pandas as pd
import numpy as np
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

import PC_Fns

class cal_HK_Error(Exception):
    """error for unexpected things"""
    pass

def cal_HK(PROC_DIR):
    """Takes the processed telemetery and produces calibrated HK pandas array"""

    logger.info("Calibrating TM HK Files")

    ## Search for PanCam Processed Files
    PikFile = PC_Fns.Find_Files(PROC_DIR, "*RAW_HKTM.pickle")
    if not PikFile:
        logger.error("No files found - ABORTING")
        return

    ## Read RAW TM pickle file
    RAW = pd.read_pickle(PikFile[0])
    CalTM = pd.DataFrame()
    CalTM['DT'] = RAW['DT'].copy()

    ## Voltages
    ratio = 4096*1.45914

    CalTM['Volt_Ref'] = ratio / RAW['Volt_Ref']
    CalTM['Volt_6V0'] = CalTM['Volt_Ref'] / 4096 * 6.4945 * RAW['Volt_6V0']
    CalTM['Volt_1V5'] = CalTM['Volt_Ref'] * RAW['Volt_1V5']/4096

    ## Temperatures
    #Cal_A = {"LFW":306.90, "RFW":308.57, "HRC":313.57, "LWAC":307.91, "RWAC":307.17, "LDO":310.42, "ACT":304.15}
    #Cal_B = {"LFW":-268.21, "RFW":-268.14, "HRC":-274.94, "LWAC":-267.41, "RWAC":-266.71, "LDO":-270.04, "ACT":-264.52}
    Cal_A = [306.90, 308.57, 313.57, 307.91, 307.17, 310.42, 304.15]
    Cal_B = [-268.21, -268.14, -274.94, -267.41, -266.71, -270.04, -264.52]

    CalTM['Temp_LFW']  = RAW['Temp_LFW']  * Cal_A[0] / RAW['Volt_Ref'] + Cal_B[0]
    CalTM['Temp_RFW']  = RAW['Temp_RFW']  * Cal_A[1] / RAW['Volt_Ref'] + Cal_B[1]
    CalTM['Temp_HRC']  = RAW['Temp_HRC']  * Cal_A[2] / RAW['Volt_Ref'] + Cal_B[2]
    CalTM['Temp_LWAC'] = RAW['Temp_LWAC'] * Cal_A[3] / RAW['Volt_Ref'] + Cal_B[3]
    CalTM['Temp_RWAC'] = RAW['Temp_RWAC'] * Cal_A[4] / RAW['Volt_Ref'] + Cal_B[4]
    CalTM['Temp_LDO']  = RAW['Temp_LDO']  * Cal_A[5] / RAW['Volt_Ref'] + Cal_B[5]
    CalTM['Temp_HRCA'] = RAW['Temp_HRCA'] * Cal_A[6] / RAW['Volt_Ref'] + Cal_B[6]
    
    write_file = PROC_DIR / (PikFile[0].stem.split('_RAW')[0] + "_Cal_HKTM.pickle")
    if write_file.exists():
        write_file.unlink()
        logger.info("Deleting file: %s", write_file.stem)
    with open(write_file, 'w') as f:
        CalTM.to_pickle(write_file)
        logger.info("PanCam Cal HK TM pickled.") 

if __name__ == "__main__":
    DIR = Path(input("Type the path to the PROC folder where the processed files are stored: "))

    logging.basicConfig(filename=(DIR / 'processing.log'),
                        level=logging.INFO,
                        format='%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
    logger.info('\n\n\n\n')
    logger.info("Running Cal_HK.py as main")
    logger.info("Reading directory: %s", DIR)

    cal_HK(DIR)