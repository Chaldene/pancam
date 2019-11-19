# -*- coding: utf-8 -*-
"""
Created on Thu Nov 14 12:01:04 2019

@author: ucasbwh
"""

### Convert pci_raw to viewable .tiff and create appropriate label

import glob
import os
import numpy as np
from PIL import Image
import json

from decodeRAW_ImgHDR import decodeRAW_ImgHDR
from LID_Browse import LID_Browse

class ImgRawBrError(Exception):
    """error for unexpected things"""
    pass

def Img_RAW_Browse(PROC_DIR):

    print("---Generating Image Browse Products from RAW Images")

    ## Search for pci_raw files in the process directory
    FILT_DIR = r"\IMG_RAW\*.pci_raw"
    RAW_FILES = glob.glob(PROC_DIR + FILT_DIR, recursive=True)
    print("Number of Rover RAW processed images found: " + str(len(RAW_FILES)))

    if len(RAW_FILES) == 0:
        print("No complete Rover RAW images found")
        print("Searching for LabView EGSE files")    
        FILT_DIR = r"\IMG_RAW\*.bin"
        RAW_FILES = glob.glob(PROC_DIR + FILT_DIR, recursive=True)
        print("Number of LabView binary images found: " + str(len(RAW_FILES)))

    if len(RAW_FILES) == 0:
        raise ImgRawBrError("No complete RAW images found")

    ## Create for loop here
    for curFile in RAW_FILES:
        
        with open(curFile, 'rb') as file:
            img_rawheader = decodeRAW_ImgHDR(file.read(48))        
            raw_data = np.fromfile(file, dtype='>u2')
            
            img_rawheader['RAW_Source'] = os.path.basename(curFile)    
                        
            ig = raw_data.reshape(1024,1024)
            ig2 = ig*(2**8)/(2 **10-1)
            img = Image.fromarray(ig*2**6, mode='I;16')
            
            # Create directory for binary file
            BRW_DIR = os.path.join(PROC_DIR, "IMG_Browse")
            if not os.path.isdir(BRW_DIR):
                print("Generating 'Processing' directory")
                os.mkdir(BRW_DIR)
                
            # Generate filename
            write_filename = LID_Browse(img_rawheader, 'FM')
            file_dt = os.path.basename(curFile).split("_")
            write_filename += file_dt[0] + "-" + file_dt[1] + "Z"
            #write_filename = os.path.basename(curFile).split(".",1)[0] #Old name based on source
            
            # Create .tiff thumbnail
            write_file = os.path.join(BRW_DIR, write_filename + ".tiff")
            if os.path.isfile(write_file):
                os.remove(write_file)
                print("Deleting file: ", os.path.basename(write_file))
                
            if img_rawheader['Cam'] == 1:
                Br_img = img = img.rotate(angle=-90)
                img_rawheader['Browse_Rotation'] = -90
            elif img_rawheader['Cam'] == 2:
                Br_img = img.rotate(angle=90)
                img_rawheader['Browse_Rotation'] = +90
            elif img_rawheader['Cam'] == 3:
                Br_img = img.transpose(Image.FLIP_LEFT_RIGHT) 
                img_rawheader['Browse_Transpose'] = "Left_Right"
            else:
                ImgRawBrError("Warning invalid CAM number")
                
            Br_img.save(write_file)
            print("Creating .tiff: ", os.path.basename(write_file))
            
            # Write dictionary to a json file (for simplicity)
            write_file = os.path.join(BRW_DIR, write_filename + ".json")
            ancil = json.dumps(img_rawheader, separators=(',\n', ': '))
            if os.path.isfile(write_file):
                os.remove(write_file)
                print("Deleting file: ", os.path.basename(write_file))
            with open(write_file, 'w') as f:
                f.write(ancil)
    
    print("---Generating Image Browse Products from RAW Images - Completed")


    
if __name__ == "__main__":
    DIR= input("Type the path to the folder where the PROC folder is located: ")
    
    Img_RAW_Browse(DIR)