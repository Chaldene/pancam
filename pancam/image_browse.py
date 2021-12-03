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
            #img = ig >> 2
            img = colour.gamma_function(ig, 0.8)

            # Determine image rotation for preview
            if img_rawheader['Cam'] == 1:
                Br_img = np.rot90(img, k=3)
                BrowseProps.update({'Browse_Rotation': '-90'})
            elif img_rawheader['Cam'] == 2:
                Br_img = np.rot90(img, k=1)
                BrowseProps.update({'Browse_Rotation': '+90'})
            elif img_rawheader['Cam'] == 3:
                Br_img = np.fliplr(img)
                BrowseProps.update({'Browse_Transpose': "Left_Right"})
            else:
                Br_img = img
                BrowseProps.update({'Browse_Transform': 'None'})
                ImgRawBrError("Warning invalid CAM number")

            # Create directory for Browse images
            BRW_DIR = PROC_DIR / "IMG_Browse"
            if not BRW_DIR.is_dir():
                logger.info("Generating 'Processing' directory")
                BRW_DIR.mkdir()

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

            write_file = BRW_DIR / (write_filename + ".json")

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

    Img_RAW_Browse(proc_dir, source='Rover', model='exm_gtm_ccs', ptu_exists=True)
