# TestFunctions.py
#
# Barry Whiteside
# Mullard Space Science Laboratory - UCL
#
# PanCam Data Processing Tools

import bitstruct
from collections import namedtuple


def LDTHeader(PKT_Bin):
    """Decodes and write to a file the LDT first packet parts."""
    bits_unpacked = bitstruct.unpack('u16u16u8u16u32u8u8', PKT_Bin[16:30])
    LDT_HDR = namedtuple('LDT_HDR', ['Unit_ID', 'SEQ_No', 'PART_ID', 'FILE_ID', 'FILE_SIZE', 'FILE_TYPE', 'SPARE'])
    SCI_LDT_HDR = LDT_HDR(*bits_unpacked)
    print(SCI_LDT_HDR)

    return