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

import pancam_fns
from image_hdr_raw import decodeRAW_ImgHDR

logger = logging.getLogger(__name__)


class ImgRawBrError(Exception):
    """error for unexpected things"""
    pass


def Img_RAW_Browse(PROC_DIR):

    logger.info("Generating Image Browse Products from RAW Images")

    # Search for pci_raw files in the process directory
    RAW_FILES = pancam_fns.Find_Files(PROC_DIR, "IMG_RAW\*.pci_raw")
    if not RAW_FILES:
        logger.warning("No files found - ABORTING")
        return

    # Create for loop here
    for curFile in RAW_FILES:
        logger.info("Reading %s", curFile.name)
        with open(curFile, 'rb') as file:
            img_rawheader = decodeRAW_ImgHDR(file.read(48))
            raw_data = np.fromfile(file, dtype='>u2')
            BrowseProps = {'RAW_Source': curFile.name}
            BrowseProps.update({'PNG Bit-Depth': "8"})

            ig = raw_data.reshape(1024, 1024)
            img = ig >> 2

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
            if write_file.exists():
                write_file.unlink()
                logger.info("Deleting file: %s", write_file.stem)

            imageio.imwrite(write_file, Br_img)
            logger.info("Creating .png: %s", write_file.stem)

            # Read existing JSON file associated with RAW
            RAWJsonFile = curFile.with_suffix(".JSON")
            if not RAWJsonFile.exists():
                ImgRawBrError("Warning RAW JSon does not exist", RAWJsonFile)
            with open(RAWJsonFile, 'r') as read_file:
                RAWJson = json.load(read_file)

            # Append Browse Header information into dictionary for JSON file
            RAWJson.update({"Image Header RAW": img_rawheader})
            RAWJson['Processing Info'].update(
                {"Browse Properties": BrowseProps})

            write_file = BRW_DIR / (write_filename + ".json")

            if write_file.exists():
                write_file.unlink()
                logger.info("Deleting file: %s", write_file.stem)
            with open(write_file, 'w') as f:
                json.dump(RAWJson, f,  indent=4)

    logger.info("Generating Image Browse Products from RAW Images Completed")


if __name__ == "__main__":
    DIR = Path(
        input("Type the path to the folder where the PROC folder is located: "))

    logging.basicConfig(filename=(DIR / 'processing.log'),
                        level=logging.INFO,
                        format='%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
    logger.info('\n\n\n\n')
    logger.info("Running ImageRAWtoBrowse.py as main")
    logger.info("Reading directory: %s", DIR)

    Img_RAW_Browse(DIR)
