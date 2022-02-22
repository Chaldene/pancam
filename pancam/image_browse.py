# -*- coding: utf-8 -*-
"""
Created on Thu Nov 14 12:01:04 2019

@author: ucasbwh
"""

# Convert pci_raw to viewable 8-bit .png and create appropriate label

from pathlib import Path
import numpy as np
import imageio
import json
import logging
import bitstruct
import colour
import pandas as pd

import pancam_fns
from image_hdr_raw import decodeRAW_ImgHDR

logger = logging.getLogger(__name__)
status = logging.getLogger('status')


class ImgRawBrError(Exception):
    """error for unexpected things"""
    pass


def Img_RAW_Browse(PROC_DIR, source, model=None, ptu_exists=False):

    # Constants
    BIN_RES = [1024, 512, 256, 128]

    logger.info("Generating Image Browse Products from RAW Images")

    # Search for pci_raw files in the process directory
    RAW_FILES = pancam_fns.Find_Files(PROC_DIR, r"IMG_RAW\*.pci_raw")
    if not RAW_FILES:
        logger.warning("No files found - ABORTING")
        return

    # Load ptu data
    if ptu_exists:

        pan_pik_file = pancam_fns.Find_Files(proc_dir, "ptu_pan.pickle", SingleFile=True)
        tilt_pik_file = pancam_fns.Find_Files(proc_dir, "ptu_tilt.pickle", SingleFile=True)

        if (not pan_pik_file) | (not tilt_pik_file):
            logger.warning("No PTU pickle files found but data was expected- ABORTING")

        pan_data = pd.read_pickle(pan_pik_file[0])
        tilt_data = pd.read_pickle(tilt_pik_file[0])
        pan = pan_data.set_index('DT')['REAL_PHYSICAL_VALUE'].rename('PAN')
        tilt = tilt_data.set_index('DT')['REAL_PHYSICAL_VALUE'].rename('TILT')

    # Create for loop here
    for curFile in RAW_FILES:
        logger.info("Reading %s", curFile.name)
        with open(curFile, 'rb') as file:
            img_rawheader = decodeRAW_ImgHDR(file.read(48), source, model)
            BrowseProps = {'RAW_Source': curFile.name}
            BrowseProps.update({'PNG Bit-Depth': "8"})

            # Determine resolution
            if img_rawheader['Cam'] != 3:
                res = BIN_RES[img_rawheader['W_Bin']]
                pad = img_rawheader['W_Pad_F']
            else:
                res = 1024
                pad = True

            if res != 1024:
                status.info("Non default image size: %s", res)

            if pad:
                raw_data = np.fromfile(file, dtype='>u2')
            else:
                status.info("Non padded image")
                read_data = []
                data = file.read(5)
                while len(data) == 5:
                    updata = bitstruct.unpack('u10u10u10u10', data)
                    read_data.extend([*updata])
                    data = file.read(5)
                raw_data = np.asarray(read_data)

            ig = raw_data.reshape(res, res)

            # Determine image rotation for preview
            if img_rawheader['Cam'] == 1:
                img = np.rot90(ig, k=3)
                BrowseProps.update({'Browse_Rotation': '-90'})
            elif img_rawheader['Cam'] == 2:
                img = np.rot90(ig, k=1)
                BrowseProps.update({'Browse_Rotation': '+90'})
            elif img_rawheader['Cam'] == 3:
                img = np.fliplr(ig)
                BrowseProps.update({'Browse_Transpose': "Left_Right"})
            else:
                img = ig
                BrowseProps.update({'Browse_Transform': 'None'})
                ImgRawBrError("Warning invalid CAM number")

            # Standard img for browse as normal
            img8 = img >> 2
            Br_img = colour.gamma_function(img8, 0.8)

            # Img for further processing
            img_anl = (img << 6).astype(np.uint16)

            # Create directory for Browse images of format IMG_Browse/SOL_RUN_TASK
            BRW_DIR = PROC_DIR / "IMG_Browse" / \
                f"S{img_rawheader['SOL']:02d}_R{img_rawheader['Task_RNO']:02d}_T{img_rawheader['Task_ID']:02d}"
            if not BRW_DIR.is_dir():
                logger.info("Generating 'Browse' directory")
                BRW_DIR.mkdir(parents=True)

            # Create 8-bit .png thumbnail
            write_filename = curFile.stem
            write_file = BRW_DIR / (write_filename + ".png")
            pancam_fns.exist_unlink(write_file)

            imageio.imwrite(write_file, Br_img)
            logger.info("Creating .png: %s", write_file.stem)

            # Read existing JSON file associated with RAW
            RAWJsonFile = curFile.with_suffix(".JSON")
            if not RAWJsonFile.exists():
                ImgRawBrError("Warning RAW JSON does not exist", RAWJsonFile)
            with open(RAWJsonFile, 'r') as read_file:
                RAWJson = json.load(read_file)

            # Append Browse Header information into dictionary for JSON file
            RAWJson.update({"Image Header RAW": img_rawheader})
            RAWJson['Processing Info'].update(
                {"Browse Properties": BrowseProps})

            # If ptu data determine positions whilst imaging and add to JSON file
            if ptu_exists:
                exp_start = pd.to_datetime(img_rawheader.get('Img_Start_Time'))
                exp_dur = pd.Timedelta(seconds=float(img_rawheader.get('Img_Exposure_sec')))
                exp_end = exp_start + exp_dur

                pan_valid = pan[(pan.index >= exp_start) & (pan.index <= exp_end)]
                if not pan_valid.empty:
                    pan_info = {
                        "samples": f"{pan_valid.count()}",
                        "mean": f"{pan_valid.mean():.4f}",
                        "std": f"{pan_valid.std():.4f}",
                        "min": f"{pan_valid.min():.4f}",
                        "max": f"{pan_valid.max():.4f}",
                        "samples_start_time": f"{pan_valid.index[0]}"[:-3],
                        "samples_end_time": f"{pan_valid.index[-1]}"[:-3]
                    }

                else:
                    pan_last = pan[pan.index <= exp_start].tail(1)
                    if not pan_last.empty:
                        pan_info = {
                            "samples": "0",
                            "last_known_value": f"{pan_last[0]:.4f}",
                            "sample_time": f"{pan_last.index[0]}"[:-3]
                        }
                    else:
                        pan_info = {
                            "samples": "0",
                            "last_known_value": "undetermined"
                        }

                tilt_valid = tilt[(tilt.index >= exp_start) & (tilt.index <= exp_end)]
                if not tilt_valid.empty:
                    tilt_info = {
                        "samples": f"{tilt_valid.count()}",
                        "mean": f"{tilt_valid.mean():.4f}",
                        "std": f"{tilt_valid.std():.4f}",
                        "min": f"{tilt_valid.min():.4f}",
                        "max": f"{tilt_valid.max():.4f}",
                        "samples_start_time": f"{tilt_valid.index[0]}"[:-3],
                        "samples_end_time": f"{tilt_valid.index[-1]}"[:-3]
                    }

                else:
                    tilt_last = tilt[tilt.index <= exp_start].tail(1)
                    if not tilt_last.empty:
                        tilt_info = {
                            "samples": "0",
                            "last_known_value": f"{tilt_last[0]:.4f}",
                            "sample_time": f"{pan_last.index[0]}"[:-3]
                        }
                    else:
                        tilt_info = {
                            "samples": "0",
                            "last_known_value": "undetermined"
                        }

                RAWJson.update({"PTU Pan": pan_info})
                RAWJson.update({"PTU Tilt": tilt_info})

            write_file = BRW_DIR / (write_filename + ".json")
            pancam_fns.exist_unlink(write_file)
            with open(write_file, 'w') as f:
                json.dump(RAWJson, f,  indent=4)

            # Create directory for Image analysis format
            ANL_DIR = PROC_DIR / "IMG_Analysis"
            if not ANL_DIR.is_dir():
                logger.info("Generating 'Analysis' directory")
                ANL_DIR.mkdir(parents=True)

            # Create 16-bit .png version
            write_filename = f"{img_rawheader['Pkt_CUC']}_{('_').join(curFile.stem.split('_')[1:])}_{img_rawheader['Cam']}"
            write_file = ANL_DIR / (write_filename + ".png")
            pancam_fns.exist_unlink(write_file)
            imageio.imwrite(write_file, img_anl)
            logger.info("Creating .png: %s", write_file.stem)

            write_file = ANL_DIR / (write_filename + ".json")
            pancam_fns.exist_unlink(write_file)
            with open(write_file, 'w') as f:
                json.dump(RAWJson, f,  indent=4)

    logger.info("Generating Image Browse Products from RAW Images Completed")


if __name__ == "__main__":
    proc_dir = Path(
        input("Type the path to the folder where the PROC folder is located: "))

    logger, status = pancam_fns.setup_logging()
    pancam_fns.setup_proc_logging(logger, proc_dir)

    logger.info('\n\n\n\n')
    logger.info("Running ImageRAWtoBrowse.py as main")
    logger.info("Reading directory: %s", proc_dir)

    Img_RAW_Browse(proc_dir, source='Rover', model='exm_gtm_ccs', ptu_exists=False)
