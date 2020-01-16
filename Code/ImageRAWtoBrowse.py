# -*- coding: utf-8 -*-
"""
Created on Thu Nov 14 12:01:04 2019

@author: ucasbwh
"""

### Convert pci_raw to viewable .tiff and create appropriate label

from pathlib import Path
import numpy as np
import imageio
import json
import logging
logger = logging.getLogger(__name__)

from decodeRAW_ImgHDR import decodeRAW_ImgHDR
import PC_Fns

class ImgRawBrError(Exception):
    """error for unexpected things"""
    pass

def Img_RAW_Browse(PROC_DIR):

    logger.info("Generating Image Browse Products from RAW Images")

    ## Search for pci_raw files in the process directory
    RAW_FILES = PC_Fns.Find_Files(PROC_DIR, "IMG_RAW\*.pci_raw")
    if not RAW_FILES:
        logger.error("No files found - ABORTING")  

    ## Create for loop here
    for curFile in RAW_FILES:
        logger.info("Reading %s", curFile.name)
        with open(curFile, 'rb') as file:
            img_rawheader = decodeRAW_ImgHDR(file.read(48))        
            raw_data = np.fromfile(file, dtype='>u2')
            
            img_rawheader['RAW_Source'] = curFile.stem
                        
            ig = raw_data.reshape(1024,1024)
            img = ig >> 2
            
            # Create directory for binary file
            BRW_DIR = PROC_DIR / "IMG_Browse"
            if not BRW_DIR.is_dir():
                logger.info("Generating 'Processing' directory")
                BRW_DIR.mkdir()
                
            # Generate filename
            #write_filename = PC_Fns.LID_Browse(img_rawheader, 'FM')
            #file_dt = (curFile.stem.split("_"))
            #write_filename += file_dt[0] + "-" + file_dt[1] + "Z"
            write_filename = curFile.stem
            
            # Create .tiff thumbnail
            write_file = BRW_DIR / (write_filename + ".png")
            if write_file.exists():
                write_file.unlink()
                logger.info("Deleting file: %s", write_file.stem)
                
            if img_rawheader['Cam'] == 1:
                Br_img = np.rot90(img, k=3)
                img_rawheader['Browse_Rotation'] = -90
            elif img_rawheader['Cam'] == 2:
                Br_img = np.rot90(img, k=1)
                img_rawheader['Browse_Rotation'] = +90
            elif img_rawheader['Cam'] == 3:
                Br_img = np.fliplr(img) 
                img_rawheader['Browse_Transpose'] = "Left_Right"
            else:
                ImgRawBrError("Warning invalid CAM number")

            imageio.imwrite(write_file, Br_img)
            logger.info("Creating .png: %s", write_file.stem)
            
            # Write dictionary to a json file (for simplicity)
            write_file = BRW_DIR / (write_filename + ".json")
            ancil = json.dumps(img_rawheader, separators=(',\n', ': '))
            if write_file.exists():
                write_file.unlink()
                logger.info("Deleting file: %s", write_file.stem)
            with open(write_file, 'w') as f:
                f.write(ancil)
    
    logger.info("Generating Image Browse Products from RAW Images Completed")


    
if __name__ == "__main__":
    DIR= Path(input("Type the path to the folder where the PROC folder is located: "))

    logging.basicConfig(filename=(DIR / 'processing.log'),
                        level=logging.INFO,
                        format='%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
    logger.info('\n\n\n\n')
    logger.info("Running ImageRAWtoBrowse.py as main")
    logger.info("Reading directory: %s", DIR)
    
    Img_RAW_Browse(DIR)