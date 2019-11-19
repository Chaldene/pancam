# -*- coding: utf-8 -*-
"""
Created on Fri Nov 15 10:24:38 2019

@author: ucasbwh
"""

class LID_Browse_Error(Exception):
    """error for unexpected things"""
    pass

def LID_Browse(RawHDR_Dict, Model):
    """returns a string to name the browse images
    
    Standard format:
   
    <cam_ID><filter_ID>_<taskID>_<taskRun>_<img_no.>_ <temp>_<exposure>_<date-time>.ext
    
    """
        
    Cams = ('L', 'R', 'H')
    LID_str = Model + '-' + Cams[RawHDR_Dict['Cam']-1]
    
    #Filter
    if RawHDR_Dict['Cam'] == 3:
        LID_str += 'RC_'
    elif 0 < RawHDR_Dict['Cam'] < 3:
        LID_str += "{0:0=2d}".format(RawHDR_Dict['FW']) + "_"
    else:
        LID_Browse_Error("Warning invalid CAM number")
    
    #TaskID, Run Number, Image Number
    LID_str += "{0:0=3d}".format(RawHDR_Dict['Task_ID']) + "_"
    LID_str += "{0:0=3d}".format(RawHDR_Dict['Task_Run_No']) + "_"
    LID_str += "{0:0=3d}".format(RawHDR_Dict['Img_No']) + "_"
    
    #Temp and Integration time (Uncal for now)
    if 0 < RawHDR_Dict['Cam'] < 3:
        LID_str += "{0:0=4d}".format(RawHDR_Dict['W_End_Temp']) + "_"
        LID_str += "{0:0=7d}".format(RawHDR_Dict['W_Int_Time']) + "_"
    elif RawHDR_Dict['Cam'] == 3:
        LID_str += "{0:0=4d}".format(RawHDR_Dict['H_Temp']) + "_"
        LID_str += "{0:0=7d}".format(RawHDR_Dict['H_Int_Time']) + "_"
    else:
        LID_Browse_Error("Warning invalid CAM number")
    
    ### Need to add ability to include start time in reasonable format
    
    
    
    return LID_str