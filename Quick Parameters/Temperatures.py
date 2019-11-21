# -*- coding: utf-8 -*-
"""
Created on Tue Nov  5 10:23:39 2019

@author: ucasbwh
"""

import matplotlib.pyplot as plt
from matplotlib import gridspec
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from pandas.plotting import register_matplotlib_converters
import os

def Temperatures(PROC_DIR):
    
    print("---Producing Temperature Plots")   
    
    TC = pd.read_pickle(os.path.join(PROC_DIR, "TC.pickle"))
    df = pd.read_pickle(os.path.join(PROC_DIR, "TM.pickle"))
    
    Cal_A = [306.90, 308.57, 313.57, 307.91, 307.17, 310.42, 304.15]
    Cal_B = [-268.21, -268.14, -274.94, -267.41, -266.71, -270.04, -264.52]
    
    rREF = df[12]*256+df[13]
    
    #Start True Calibration
    p1 = df['DT']
    
    gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1])
    f = plt.figure()
        
    a0 = f.add_subplot(gs[0])
    a1 = f.add_subplot(gs[1], sharex=a0)
    
    LFW_T  =  (df[18]*256+df[19])*Cal_A[0]/rREF + Cal_B[0]
    RFW_T  =  (df[20]*256+df[21])*Cal_A[1]/rREF + Cal_B[1]
    HRC_T  =  (df[22]*256+df[23])*Cal_A[2]/rREF + Cal_B[2]
    LWAC_T = (df[24]*256+df[25])*Cal_A[3]/rREF + Cal_B[3]
    RWAC_T = (df[26]*256+df[27])*Cal_A[4]/rREF + Cal_B[4]
    LDO_T  =  (df[28]*256+df[29])*Cal_A[5]/rREF + Cal_B[5]
    ACT_T  =  (df[30]*256+df[31])*Cal_A[6]/rREF + Cal_B[6]
    
    a0.plot(p1, LFW_T, label='LFW')
    a0.plot(p1, RFW_T, label='RFW')
    a0.plot(p1, HRC_T, label='HRC')
    a0.plot(p1, LWAC_T,label='LWAC')
    a0.plot(p1, RWAC_T,label='RWAC')
    a0.plot(p1, ACT_T, label='ACT')
    a1.plot(p1, LDO_T, '-k',label='LDO')
    a0.grid(True)
    a1.grid(True)
    a0.set_ylabel('Temp [$^\circ$C]')
    a0.legend(loc='lower center', bbox_to_anchor= (0.5, 1.0), ncol=5, borderaxespad=0, frameon=False)
    a1.set_ylabel('LDO Temp [$^\circ$C]')
    
    myFmt = mdates.DateFormatter('%H:%M:%S')
    a1.xaxis.set_major_formatter(myFmt)
    plt.setp(a0.get_xticklabels(), visible=False)
    
    #Display Plot
    f.set_figheight(8)
    f.set_figwidth(15)
    f.tight_layout()
    
    f.set_figheight(5)
    f.set_figwidth(9)
    f.tight_layout()
    f.show()
    
    
    
    ## Database calibration plot
    Cal_A = 0.174221209411
    Cal_B = -277.94
    
    #Start plot
    p1 = df['DT']
    
    gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1])
    f = plt.figure()
        
    a0 = f.add_subplot(gs[0])
    a1 = f.add_subplot(gs[1], sharex=a0)
    
    LFW  =  (df[18]*256+df[19])*Cal_A + Cal_B
    RFW  =  (df[20]*256+df[21])*Cal_A + Cal_B
    HRC  =  (df[22]*256+df[23])*Cal_A + Cal_B
    LWAC =  (df[24]*256+df[25])*Cal_A + Cal_B
    RWAC =  (df[26]*256+df[27])*Cal_A + Cal_B
    LDO  =  (df[28]*256+df[29])*Cal_A + Cal_B
    ACT  =  (df[30]*256+df[31])*Cal_A + Cal_B
    
    a0.plot(p1, LFW, label='LFW')
    a0.plot(p1, RFW, label='RFW')
    a0.plot(p1, HRC, label='HRC')
    a0.plot(p1, LWAC,label='LWAC')
    a0.plot(p1, RWAC,label='RWAC')
    a0.plot(p1, ACT, label='ACT')
    a1.plot(p1, LDO, '-k',label='LDO')
    a0.grid(True)
    a1.grid(True)
    a0.set_ylabel('Temp [$^\circ$C]')
    a0.legend(loc='lower center', bbox_to_anchor= (0.5, 1.0), ncol=5, borderaxespad=0, frameon=False)
    a1.set_ylabel('LDO Temp [$^\circ$C]')
    
    myFmt = mdates.DateFormatter('%H:%M:%S')
    a1.xaxis.set_major_formatter(myFmt)
    plt.setp(a0.get_xticklabels(), visible=False)
    
    #Display Plot
    f.set_figheight(8)
    f.set_figwidth(15)
    f.tight_layout()
    
    f.set_figheight(5)
    f.set_figwidth(9)
    f.tight_layout()
    f.show()
      
    ## Raw Temperatures and heaters
    #Start plot
    p1 = df['DT']
    
    gs = gridspec.GridSpec(5, 1, height_ratios=[2, 1, 0.5, 0.5, 1.5])
    gs.update(hspace=0.0)
    size = TC.shape[0]
    
    f = plt.figure()
        
    a0 = f.add_subplot(gs[0])
    a1 = f.add_subplot(gs[1], sharex=a0)
    a2 = f.add_subplot(gs[2], sharex=a0)
    a3 = f.add_subplot(gs[3], sharex=a0)
    a4 = f.add_subplot(gs[4], sharex=a0)
    
    LFW  =  df[18]*256+df[19]
    RFW  =  df[20]*256+df[21]
    HRC  =  df[22]*256+df[23]
    LWAC =  df[24]*256+df[25]
    RWAC =  df[26]*256+df[27]
    LDO  =  df[28]*256+df[29]
    ACT  =  df[30]*256+df[31]
        
    a0.plot(p1, LFW, label='LFW')
    a0.plot(p1, RFW, label='RFW')
    a0.plot(p1, HRC, label='HRC')
    a0.plot(p1, LWAC,label='LWAC')
    a0.plot(p1, RWAC,label='RWAC')
    a0.plot(p1, ACT, label='ACT')
    a0.plot(p1, ((df[38]&0x0F).values << 8) + df[39], '--', label='HTR Set Point')
    a0.grid(True)
    a0.legend(loc='lower center', bbox_to_anchor= (0.5, 1.0), ncol=4, borderaxespad=0, frameon=False)
    a0.text(.99,.95,'Internal Temp', horizontalalignment='right', transform=a0.transAxes)
    
    a1.plot(p1, LDO, '-k',label='LDO')
    a1.grid(True)
    a1.text(.99,.9,'LDO Temp', horizontalalignment='right', transform=a1.transAxes)
    a1.yaxis.tick_right()
    a1.yaxis.set_label_position('right')
    
    a2.plot(p1, (df[38]&0x80).values >> 7, label = 'HTR ON')
    a2.plot(p1, (df[38]&0x40).values >> 6, label = 'AUTO')
    a2.legend(loc='center right', bbox_to_anchor= (1.0, 0.5), ncol=1, borderaxespad=0, frameon=False)
    a2.set_ylim([-0.1,1.1])
    a2.get_yaxis().set_visible(False)
    a2.grid(True)
    a2.text(.99,.8,'HTR Mode', horizontalalignment='right', transform=a2.transAxes)
    
    a3.plot(p1, (df[38]&0x30).values >> 4, label = 'HTR')
    a3.set_ylim([-0.1,3.5])
    a3.grid(True)
    a3.text(.99,.8,'HTR', horizontalalignment='right', transform=a3.transAxes)
    a3.yaxis.tick_right()
    a3.yaxis.set_label_position('right')
    
    myFmt = mdates.DateFormatter('%H:%M:%S')
    a3.xaxis.set_major_formatter(myFmt)
    plt.setp(a0.get_xticklabels(), visible=False)
    plt.setp(a1.get_xticklabels(), visible=False)
    plt.setp(a2.get_xticklabels(), visible=False)
    
    markerline, stemline, baseline = a4.stem(TC['DT'], TC['LEVEL'], linefmt='C3-', basefmt="k-", use_line_collection=True)
    plt.setp(markerline, mec="k", mfc="w", zorder=3)
    markerline.set_ydata(np.zeros(size))
    a4.text(.99,.9,'Action List', horizontalalignment='right', transform=a4.transAxes)
    a4.get_yaxis().set_visible(False)
    for i in range(0, size):
        a4.annotate(TC.ACTION.iloc[i], xy=(TC.DT.iloc[i], TC.LEVEL.iloc[i]), xytext=(0,-2),
                textcoords="offset points", va="top", ha="right", rotation=90)
    
    #Rescale x-axis to avoid clash with labels
    xlimits = a0.get_xlim()
    new_xlimits = (xlimits[0],(xlimits[1] - xlimits[0])*1.2+xlimits[0]);
    a0.set_xlim(new_xlimits)
    
    plt.setp(a0.get_xticklabels(), visible=False)
    plt.setp(a1.get_xticklabels(), visible=False)
    plt.setp(a2.get_xticklabels(), visible=False)
    plt.setp(a3.get_xticklabels(), visible=False)
    
    #Display Plot
    f.set_figheight(13)
    f.set_figwidth(15)
    f.tight_layout()
    
    f.set_figheight(7)
    f.set_figwidth(9)
    f.tight_layout()
    f.show()
    
if __name__ == "__main__":
    Dir =      r'C:\Users\ucasbwh\OneDrive - University College London\PanCam Documents\Rover Level Testing\Data\191107 - TVAC TP02 Testing\20191106_1734_ERJPMW_CRUISE_CHECKOUTS\PROC'
    Temperatures(Dir)