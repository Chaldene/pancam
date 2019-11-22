# -*- coding: utf-8 -*-
"""
Created on Thu Nov 21 10:14:24 2019

@author: ucasbwh
"""
from bitstruct import unpack_from as upf
import pandas as pd

def PandUPF(Column, Len, OffBy, OffBi):
    """Extracts a single RAW value from a binary pandas data column"""
    if int(Len[1:]) > 63:
        raise ValueError("PandUPF used for variable larger than 63 bits. Returned value is cast to an Int64")
    Extract = Column.apply(lambda x: upf(Len, x, offset=8*OffBy+OffBi)[0]).astype('Int64')
    return Extract