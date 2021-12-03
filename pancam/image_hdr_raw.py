# -*- coding: utf-8 -*-
"""
Created on Thu Nov 14 17:03:24 2019

@author: ucasbwh
"""
from bitstruct import unpack_from as upf


class decodeRAW_IMGHDR_Error(Exception):
    """error for unexpected things"""
    pass


def decodeRAW_ImgHDR(header_bytes):
    """returns a dict of image metadata"""

    img_info = {}
    if len(header_bytes) != 48:
        raise decodeRAW_IMGHDR_Error('Img header bytes not 48')

    # Byte 0
    img_info['Block_Type'] = upf('u1', header_bytes, offset=0)[0]
    img_info['TM_Criticality'] = upf('u2', header_bytes, offset=1)[0]
    img_info['MMS_Dest'] = upf('u1', header_bytes, offset=3)[0]
    img_info['Instr_ID'] = upf('u4', header_bytes, offset=4)[0]
    # Byte 1
    img_info['UTM_Type_ID'] = upf('u6', header_bytes, offset=8)[0]
    img_info['Seq_Flag'] = upf('u2', header_bytes, offset=14)[0]
    # Byte 2-7
    img_info['Pkt_CUC'] = f"{upf('u48', header_bytes[2:8])[0]:#016_X}"
    # Byte 8-10
    img_info['Data_Len'] = upf('u24', header_bytes, offset=64)[0]
    # Byte 11
    img_info['Ancil_Len'] = upf('u8', header_bytes, offset=88)[0]
    # Byte 12 - Reserved
    if upf('u8', header_bytes, offset=96)[0] != 0:
        raise decodeRAW_IMGHDR_Error("Header Byte 12 not 0")
    # Byte 13-16
    img_info['SOL'] = upf('u12', header_bytes, offset=104)[0]      # PAN_TM_PIU_HKN_SIID_SOL
    img_info['Task_ID'] = upf('u7', header_bytes, offset=116)[0]   # PAN_TM_PIU_HKN_SIID_TID
    img_info['Task_RNO'] = upf('u7', header_bytes, offset=123)[0]  # PAN_TM_PIU_HKN_SIID_TRN
    img_info['Cam'] = upf('u2', header_bytes, offset=130)[0]       # PAN_TM_PIU_HKN_SIID_PC
    img_info['FW'] = upf('u4', header_bytes, offset=132)[0]        # PAN_TM_PIU_HKN_SIID_FW
    # Byte 17
    img_info['Img_No'] = upf('u8', header_bytes, offset=136)[0]    # PAN_TM_PIU_HKN_SIID_IN
    # Byte 18-23
    img_info['PIU_Time'] = f"{upf('u48', header_bytes[18:24])[0]:#016_X}"  # No label in ICD

    # Some checks for common header here!

    # Check if WAC Camera
    if (img_info['Cam'] == 1) or (img_info['Cam'] == 2):
        # Byte 24
        img_info['W_CID'] = upf('u2', header_bytes, offset=192)[0]   # PAN_TM_WAC_DT_CID
        img_info['W_MK_F'] = upf('u1', header_bytes, offset=194)[0]  # PAN_TM_WAC_DT_MK
        img_info['W_Bin'] = upf('u2', header_bytes, offset=195)[0]   # PAN_TM_WAC_DT_BIN
        img_info['W_ID'] = upf('u3', header_bytes, offset=197)[0]    # PAN_TM_WAC_DT_WID
        # Byte 25-30
        img_info['W_Start_Time'] = '0x' + header_bytes[25:30].hex()  # PAN_TM_WAC_DT_ITS
        # Byte 31-36
        img_info['W_Time'] = f"{upf('u48', header_bytes[31:37])[0]:#016_X}"   # PAN_TM_WAC_DT_WTS
        # Byte 37-40
        img_info['W_Int_Time'] = upf('u20', header_bytes, offset=296)[0]  # PAN_TM_WAC_DT_IT
        img_info['Img_Exposure_sec'] = f"{(img_info['W_Int_Time']+1) * 0.001}"

        img_info['W_End_Temp'] = upf('u12', header_bytes, offset=316)[0]  # PAN_TM_WAC_DT_STP
        # Byte 41
        img_info['W_Inh_F'] = upf('u1', header_bytes, offset=328)[0]     # PAN_TM_WAC_DT_INH
        img_info['W_AE_F'] = upf('u1', header_bytes, offset=329)[0]      # PAN_TM_WAC_DT_AE
        img_info['W_Pad_F'] = upf('u1', header_bytes, offset=330)[0]     # PAN_TM_WAC_DT_PAD
        img_info['W_Gain'] = upf('u2', header_bytes, offset=331)[0]      # PAN_TM_WAC_DT_GAS
        img_info['W_Dum_F'] = upf('u1', header_bytes, offset=333)[0]     # PAN_TM_WAC_DT_DD
        img_info['W_AE_Suc_F'] = upf('u1', header_bytes, offset=334)[0]  # PAN_TM_WAC_DT_AESF
        if upf('u1', header_bytes, offset=335)[0] != 0:                  # PAN_TM_WAC_DT_RES
            raise decodeRAW_IMGHDR_Error("Header Byte 41 Bit 0 not 0")
        # Byte 42-43
        img_info['W_IMG_CRC'] = upf('u16', header_bytes, offset=336)[0]  # PAN_TM_WAC_DT_CRC
        # Byte 44
        img_info['W_PKT_CRC'] = upf('u8', header_bytes, offset=352)[0]
        # Byte 45-47
        if upf('u24', header_bytes, offset=360)[0] != 0:
            raise decodeRAW_IMGHDR_Error("Header Bytes 44-47 not 0")

    # Check if HRC Camera
    elif img_info['Cam'] == 3:
        # Byte 24-25
        img_info['H_Sharp'] = upf('u16', header_bytes, offset=192)[0]     # PAN_TM_HRC_ HK_CS
        # Byte 26-28
        img_info['H_Temp'] = upf('u10', header_bytes, offset=208)[0]      # PAN_TM_HRC_HK_TP
        img_info['H_Enc_Pos'] = upf('u10', header_bytes, offset=218)[0]   # PAN_TM_HRC_HK_ENC
        img_info['H_Enc_F'] = upf('u1', header_bytes, offset=228)[0]      # PAN_TM_HRC_HK_EP
        img_info['H_AI_F'] = upf('u1', header_bytes, offset=229)[0]       # PAN_TM_HRC_HK_AI
        img_info['H_AF_F'] = upf('u1', header_bytes, offset=230)[0]       # PAN_TM_HRC_HK_AF
        img_info['H_MM_F'] = upf('u1', header_bytes, offset=231)[0]       # PAN_TM_HRC_HK_MM
        # Byte 29
        img_info['H_IMG_No'] = upf('u8', header_bytes, offset=232)[0]     # PAN_TM_HRC_HK_IFC
        # Byte 30
        img_info['H_Gain'] = upf('u2', header_bytes, offset=240)[0]       # PAN_TM_HRC_HK_GA
        img_info['H_ES_F'] = upf('u1', header_bytes, offset=242)[0]       # PAN_TM_HRC_HK_ES
        img_info['H_EI_F'] = upf('u1', header_bytes, offset=243)[0]       # PAN_TM_HRC_HK_EI
        if upf('u1', header_bytes, offset=244)[0] != 0:
            raise decodeRAW_IMGHDR_Error("Header Byte 30 Bit 3 not 0")
        img_info['H_Enc_ERR_F'] = upf('u1', header_bytes, offset=245)[0]   # PAN_TM_HRC_HK_ERENC
        img_info['H_AI_ERR_F'] = upf('u1', header_bytes, offset=246)[0]    # PAN_TM_HRC_HK_ERAI
        img_info['H_AF_ERR_F'] = upf('u1', header_bytes, offset=247)[0]    # PAN_TM_HRC_HK_ERAF
        # Byte 31-32
        img_info['H_Steps'] = upf('u16', header_bytes, offset=248)[0]      # PAN_TM_HRC_RB1_MS
        # Byte 33-34
        img_info['H_Max_Int'] = upf('u16', header_bytes, offset=264)[0]    # PAN_TM_HRC_RB1_MAI
        # Byte 35-36
        img_info['H_Min_Int'] = upf('u16', header_bytes, offset=280)[0]    # PAN_TM_HRC_RB1_MII
        # Byte 37-39
        if upf('u4', header_bytes, offset=296)[0] != 0:
            raise decodeRAW_IMGHDR_Error("Header Byte 37 Bit 7-4 not 0")
        img_info['H_Int_Time'] = upf('u20', header_bytes, offset=300)[0]   # PAN_TM_HRC_RB2_IT
        img_info['Img_Exposure_sec'] = f"{(img_info['H_Int_Time'] * 0.350) * 0.001:.3f}"
        # Byte 40-42
        img_info['H_Foc_X'] = upf('u10', header_bytes, offset=320)[0]      # PAN_TM_HRC_RB2_FXC
        img_info['H_Foc_Y'] = upf('u10', header_bytes, offset=330)[0]      # PAN_TM_HRC_RB2_FYC
        if upf('u1', header_bytes, offset=340)[0] != 0:
            raise decodeRAW_IMGHDR_Error("Header Byte 42 Bit 3 not 0")
        img_info['H_SF_F'] = upf('u1', header_bytes, offset=341)[0]        # PAN_TM_HRC_RB2_SFS
        img_info['H_Win_Size'] = upf('u2', header_bytes, offset=342)[0]    # PAN_TM_HRC_RB2_FWZ
        # Byte 43-44
        img_info['H_Des_Pix'] = upf('u16', header_bytes, offset=344)[0]    # PAN_TM_HRC_RB3_DPN
        # Byte 45
        img_info['H_AI_Tol'] = upf('u8', header_bytes, offset=360)[0]      # PAN_TM_HRC_RB3_TOL
        # Byte 46-47
        img_info['H_Steps_Cnt'] = upf('u16', header_bytes, offset=368)[0]  # PAN_TM_HRC_RB3_MSC

    # Raise error as no Cam reported
    else:
        decodeRAW_IMGHDR_Error("Invalid Cam Value")

    # Custom entries
    img_info['Image_ID'] = "{0:0=3d}{1:0=3d}{2:0=3d}".format(
        img_info['Task_ID'], img_info['Task_RNO'], img_info['Img_No']
    )

    return img_info
