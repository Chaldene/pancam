# -*- coding: utf-8 -*-
"""
Created on Fri Nov  1 11:07:37 2019

@author: ucasbwh
"""

### Overview Plot

import matplotlib.pyplot as plt
from matplotlib import gridspec
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from pandas.plotting import register_matplotlib_converters
import os

register_matplotlib_converters()

def Overview(PROC_DIR):
    
    print("---Producing OverView Plot")   
    
    TC = pd.read_pickle(os.path.join(PROC_DIR, "TC.pickle"))
    df = pd.read_pickle(os.path.join(PROC_DIR, "TM.pickle"))

    gs = gridspec.GridSpec(4, 1, height_ratios=[1, 0.5, 0.5, 0.5])
    gs.update(hspace=0.0)
    fig = plt.figure(figsize=(8.8, 8.5), constrained_layout=True)
    a0 = fig.add_subplot(gs[0])
    a1 = fig.add_subplot(gs[1], sharex=a0)
    a2 = fig.add_subplot(gs[2], sharex=a0)
    a3 = fig.add_subplot(gs[3], sharex=a0)

    # Action List
    size = TC.shape[0]
    TC['LEVEL'] = 1
    
    print(TC.ACTION.value_counts())
    
    markerline, stemline, baseline = a0.stem(TC['DT'], TC['LEVEL'], linefmt='C3-', basefmt="k-", use_line_collection=True)
    plt.setp(markerline, mec="k", mfc="w", zorder=3)
    markerline.set_ydata(np.zeros(size))
    a0.text(.99,.95,'Action List', horizontalalignment='right', transform=a0.transAxes)
    a0.grid(True)
    for i in range(0, size):
        a0.annotate(TC.ACTION.iloc[i], xy=(TC.DT.iloc[i], TC.LEVEL.iloc[i]), xytext=(0,-2),
                textcoords="offset points", va="top", ha="right", rotation=90)


    ## Cam Power and Enable Second dataset
    a1.plot(df['DT'], df[42], '.', label='Enable')
    a1.plot(df['DT'], df[43], '.', label='Power')
    a1.text(.99,.9,'Cam ENA and PWR', horizontalalignment='right', transform=a1.transAxes)
    a1.legend(loc='center right', bbox_to_anchor= (1.0, 0.5), ncol=1, borderaxespad=0, frameon=False)
    a1.grid(True)


    ## Errors
    a2.plot(df['DT'], df[32] != 0, '.', label='PIU')
    a2.plot(df['DT'], df[33] != 0, '.', label='FW')
    a2.plot(df['DT'], (df[34] != 0) & (df[34] != 0x4), '.', label='WACL')
    a2.plot(df['DT'], (df[35] != 0) & (df[35] != 0x4), '.', label='WACR')
    a2.plot(df['DT'], df[36] != 0, '.', label='HRC')                   

    a2.legend(loc='center right', bbox_to_anchor= (1.0, 0.5), ncol=1, borderaxespad=0, frameon=False)
    a2.text(.99,.9,'Errors excl. WAC CMD TO', horizontalalignment='right', transform=a2.transAxes)
    a2.set_ylim([-0.15,1.25])
    a2.set_yticks([0, 1], minor=False)
    plt.setp(a2.get_yticklabels(), visible=False)
    a2.grid(True)


    ## WAC CMD Timeout
    a3.plot(df['DT'], df[34] == 0x4, '.', label='WACL', color = 'C2')
    a3.plot(df['DT'], df[35] == 0x4, '.', label='WACR', color = 'C3')
    a3.text(.99,.9,'WAC CMD TO Error', horizontalalignment='right', transform=a3.transAxes)
    a3.legend(loc='center right', bbox_to_anchor= (1.0, 0.5), ncol=1, borderaxespad=0, frameon=False)
    a3.set_ylim([-0.15,1.25])
    a3.set_yticks([0, 1], minor=False)
    plt.setp(a3.get_yticklabels(), visible=False)
    a3.grid(True)
    
    
    #remove y axis and spines
    a0.get_yaxis().set_visible(False)
    
    plt.setp(a0.get_xticklabels(), visible=False)
    plt.setp(a1.get_xticklabels(), visible=False)
    plt.setp(a2.get_xticklabels(), visible=False)
          
    
    #Re-adjust x-axis so that 
    xlimits = a0.get_xlim()
    new_xlimits = (xlimits[0],(xlimits[1] - xlimits[0])*1.3+xlimits[0]);
    a0.set_xlim(new_xlimits)
    
    plt.show()
    
if __name__ == "__main__":
    #Dir =      r'C:\Users\ucasbwh\OneDrive - University College London\PanCam Documents\Rover Level Testing\Data\191107 - TVAC TP02 Testing\20191106_1734_ERJPMW_CRUISE_CHECKOUTS\PROC'
    Dir = r'C:\Users\ucasbwh\OneDrive - University College London\PanCam Documents\Rover Level Testing\Data\191107 - TVAC TP02 Testing\20191106_1734_ERJPMW_CRUISE_CHECKOUTS\PROC'
    
    Overview(Dir)