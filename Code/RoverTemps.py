# -*- coding: utf-8 -*-
"""
Created on Sun Nov 17 20:38 2019

@author: ucasbwh
"""

### File for producing a quick plot of Rover temperatures

import matplotlib.pyplot as plt
from matplotlib import gridspec
import pandas as pd
import os

PROC_DIR =      r"C:\Users\ucasbwh\OneDrive - University College London\PanCam Documents\Rover Level Testing\Data\191107 - TVAC TP02 Testing\20191106_1734_ERJPMW_CRUISE_CHECKOUTS\PROC" 

RVTM = pd.read_pickle(os.path.join(PROC_DIR, "RoverTemps.pickle"))
print(RVTM['RAW_PIU_T'][0:20])

gs = gridspec.GridSpec(2, 1, height_ratios=[1, 1])
f = plt.figure()
        
a0 = f.add_subplot(gs[0])
a1 = f.add_subplot(gs[1], sharex=a0)

a0.plot(RVTM['DT'], RVTM['PIU_T'], '.', label='PIU')
a1.plot(RVTM['DT'], RVTM['DCDC_T'], '.', label='DCDC')

a0.grid(True)
a1.grid(True)

#remove y axis and spines
plt.setp(a0.get_xticklabels(), visible=False)

plt.show()
print("plot complete")

