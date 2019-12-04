# Plotter.py
#
# Barry Whiteside
# Mullard Space Science Laboratory - UCL
#
# PanCam Data Processing Tools


import matplotlib.pyplot as plt
from matplotlib import gridspec
import matplotlib.dates as mdates
import pandas as pd 
from pandas.plotting import register_matplotlib_converters
import numpy as np 
from pathlib import Path

register_matplotlib_converters()
myFmt = mdates.DateFormatter('%H:%M')

HK_Plot_Location = 'HK Plots'
# Voltage limits for calibrated plots
# Initialised as lists for dashed lines
Lim_VREF_Low  = [3.1]
Lim_VREF_High = [3.6]
Lim_6V0_Low   = [5.5]
Lim_6V0_High  = [6.3]
Lim_1V5_Low   = [1.4]
Lim_1V5_High  = [1.6]

class plotter_Error(Exception):
    """error for unexpected things"""
    pass

def MakeHKPlotsDir(PROC_DIR):
    """Checks to see if the 'HK Plots' directory has been generated, if not creates it"""
    HK_DIR = PROC_DIR / HK_Plot_Location
    if HK_DIR.is_dir():
        print("-'HK Plots' Directory already exists")
    else:
        print("Generating 'HK Plots' directory")
        HK_DIR.mkdir()
    return HK_DIR



def zero_to_nan(values):
    """Replace every 0 with 'nan' and return a copy."""
    #Taken from https://stackoverflow.com/questions/18697417/not-plotting-zero-in-matplotlib-or-change-zero-to-none-python
    List = [float('nan') if x==0 else x for x in values]
    List_Low = [float('nan') if x==0 else x-15 for x in values]
    List_High = [float('nan') if x==0 else x+15 for x in values]
    return List, List_Low, List_High



def HK_Voltages(PROC_DIR, Interact):
    """"Produces a calibrated and uncalibrated voltage plots from pickle files"""

    print("---Producing Voltage Plots")

    HK_DIR = MakeHKPlotsDir(PROC_DIR)

    ## Search for PanCam RAW Processed Files
    FILT_DIR = "*RAW_HKTM.pickle"
    RawPikFile = sorted(PROC_DIR.rglob(FILT_DIR))

    if len(RawPikFile) == 0:
        print("**No RAW HKTM Files Found**")
        print("Plotting TM HK Voltages Aborted")
        return
    elif len(RawPikFile) > 1:
        plotter_Error("Warning more than one 'RAW_TM.pickle' found, only first used.") 

    RAW = pd.read_pickle(RawPikFile[0])

    gs = gridspec.GridSpec(3, 1, height_ratios=[1, 1, 1])
    fig = plt.figure(figsize=(14.0, 9.0))
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1], sharex=ax0)
    ax2 = fig.add_subplot(gs[2], sharex=ax0)

    ax0.plot(RAW.DT, RAW.Volt_Ref.astype('int64'), 'r-', label='VRef RAW')
    ax0.set_xlabel('')
    ax0.set_ylabel('VRef RAW [ENG]')
    ax0.grid(True)
    ax0.set_xticklabels([], visible=False)

    ax1.plot(RAW.DT, RAW.Volt_6V0.astype('int64'), 'b-', label='6V RAW')
    ax1.set_xlabel('')
    ax1.set_ylabel('6V RAW [ENG]')
    ax1.grid(True)
    ax1.set_xticklabels([], visible=False)

    ax2.plot(RAW.DT, RAW.Volt_1V5.astype('int64'), 'g-', label='1V5 RAW')
    ax2.set_ylabel('1V5 RAW [ENG]')
    ax2.set_xlabel('Data Time')
    ax2.grid(True)
    ax2.xaxis.set_major_formatter(myFmt)

    fig.tight_layout()
    fig.savefig(HK_DIR / 'VOLT_RAW.png')

    if Interact:
        plt.show(block=False)

    ## Search for PanCam CAL Processed Files
    FILT_DIR = "*Cal_HKTM.pickle"
    CalPikFile = sorted(PROC_DIR.rglob(FILT_DIR))

    if len(CalPikFile) == 0:
        print("**No Cal HKTM Files Found**")
        print("Plotting TM HK Voltages Aborted")
        return
    elif len(CalPikFile) > 1:
        plotter_Error("Warning more than one 'Cal_TM.pickle' found") 

    Cal = pd.read_pickle(CalPikFile[0])

    gs2 = gridspec.GridSpec(3, 1, height_ratios=[1, 1, 1])
    fig2 = plt.figure(figsize=(14.0, 9.0))
    ax3 = fig2.add_subplot(gs2[0])
    ax4 = fig2.add_subplot(gs2[1], sharex=ax3)
    ax5 = fig2.add_subplot(gs2[2], sharex=ax3)

    ax3.plot(Cal.DT, Cal.Volt_Ref, 'r-', label='VREF')
    ax3.plot([Cal['DT'].iloc[0], Cal['DT'].iloc[-1]], Lim_VREF_Low*2, 'darkred', linestyle='dashed')
    ax3.plot([Cal['DT'].iloc[0], Cal['DT'].iloc[-1]], Lim_VREF_High*2, 'darkred', linestyle='dashed')
    ax3.set_ylabel('VRef [V]')
    ax3.grid(True)
    ax3.set_xticklabels([], visible=False)

    ax4.plot(Cal.DT, Cal.Volt_6V0, 'b-', label='6V0')
    ax4.plot([Cal['DT'].iloc[0], Cal['DT'].iloc[-1]], Lim_6V0_Low*2, 'darkblue', linestyle='dashed')
    ax4.plot([Cal['DT'].iloc[0], Cal['DT'].iloc[-1]], Lim_6V0_High*2, 'darkblue', linestyle='dashed')
    ax4.set_ylabel('6V [V]')
    ax4.grid(True)
    ax4.set_xticklabels([], visible=False)

    ax5.plot(Cal.DT, Cal.Volt_1V5, 'g-', label='1V5')
    ax5.plot([Cal['DT'].iloc[0], Cal['DT'].iloc[-1]], Lim_1V5_Low*2, 'darkgreen', linestyle='dashed')
    ax5.plot([Cal['DT'].iloc[0], Cal['DT'].iloc[-1]], Lim_1V5_High*2, 'darkgreen', linestyle='dashed')
    ax5.set_ylabel('1V5 [V]')
    ax5.set_xlabel('Data Time')
    ax5.grid(True)
    ax5.xaxis.set_major_formatter(myFmt)

    fig2.tight_layout()
    fig2.savefig(HK_DIR / 'VOLT_CAL.png')

    if Interact:
        plt.show(block=True)



def HK_Temperatures(PROC_DIR, Interact):
    """"Produces a calibrated and uncalibrated temperature plots from pickle files"""

    print("---Producing Temperature Plots")

    HK_DIR = MakeHKPlotsDir(PROC_DIR)

    ## Search for PanCam RAW Processed Files
    FILT_DIR = "*RAW_HKTM.pickle"
    RawPikFile = sorted(PROC_DIR.rglob(FILT_DIR))

    if len(RawPikFile) == 0:
        print("**No RAW HKTM Files Found**")
        print("Plotting TM HK Temperatures Aborted")
        return
    elif len(RawPikFile) > 1:
        plotter_Error("Warning more than one 'RAW_TM.pickle' found only first used.") 

    RAW = pd.read_pickle(RawPikFile[0])

    # RAW Plot and Heater
    gs = gridspec.GridSpec(4, 1, height_ratios=[2, 1, 0.5, 0.5])
    gs.update(hspace=0.0)
    fig = plt.figure(figsize=(14.0, 9.0))
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1], sharex=ax0)
    ax2 = fig.add_subplot(gs[2], sharex=ax0)
    ax3 = fig.add_subplot(gs[3], sharex=ax0)

    ax0.plot(RAW.DT, RAW.Temp_LFW.astype('int64'),  label='LFW')
    ax0.plot(RAW.DT, RAW.Temp_RFW.astype('int64'),  label='RFW')
    ax0.plot(RAW.DT, RAW.Temp_HRC.astype('int64'),  label='HRC')
    ax0.plot(RAW.DT, RAW.Temp_LWAC.astype('int64'), label='LWAC')
    ax0.plot(RAW.DT, RAW.Temp_RWAC.astype('int64'), label='RWAC')
    ax0.plot(RAW.DT, RAW.Temp_HRCA.astype('int64'), label='ACT')
    # Heater set-point and 15 values shaded either side
    HSP, HSP_L, HSP_H = zero_to_nan(RAW.Stat_Temp_Se.astype('int64'))
    ax0_HSP = ax0.plot(RAW.DT, HSP, '--', color='k', label='HTR Set Point')
    ax0.fill_between(RAW.DT, HSP_L, HSP_H, color=ax0_HSP[0].get_color(), alpha=0.2)

    ax0.legend(loc='lower center', bbox_to_anchor=(0.5, 1.0), ncol=4, borderaxespad=0, frameon=False)
    ax0.text(.99, .95, 'Internal Temps', color='0.25', fontweight='bold', horizontalalignment='right', transform=ax0.transAxes)
    ax0.set_ylabel('RAW [ENG]')
    ax0.grid(True)
    ax0.set_xticklabels([],visible=False)

    ax1.plot(RAW.DT, RAW.Temp_LDO.astype('int64'), '-k', label='LDO')
    ax1.text(.99, .9, 'LDO Temp', color='0.25', fontweight='bold', horizontalalignment='right', transform=ax1.transAxes)
    ax1.yaxis.tick_right()
    ax1.yaxis.set_label_position('right')
    ax1.set_xlabel('')
    ax1.set_ylabel('LDO RAW [ENG]')
    ax1.grid(True)
    ax1.set_xticklabels([],visible=False)

    ax2.plot(RAW.DT, RAW.Stat_Temp_He.astype('int64'), label='HTR')
    ax2.set_ylim([-0.5, 3.5])
    ax2.grid(True)
    ax2.text(.99, .8, 'HTR', color='0.25', fontweight='bold', horizontalalignment='right', transform=ax2.transAxes)
    ax2.set_yticks([0, 1, 2, 3])
    ax2.set_yticklabels(['None', 'WACL', 'WACR', 'HRC'])
    ax2.set_xticklabels([],visible=False)

    ax3.plot(RAW.DT, RAW.Stat_Temp_On.astype('int64'), label='HTR On')
    ax3.plot(RAW.DT, RAW.Stat_Temp_Mo.astype('int64'), label='AUTO')
    ax3.legend(loc='center right', bbox_to_anchor=(1.0, 0.5), ncol=1, borderaxespad=0, frameon=False)
    ax3.set_ylim([-0.1, 1.1])
    ax3.get_yaxis().set_visible(False)
    ax3.set_xlabel('Data Time')
    ax3.grid(True)
    ax3.xaxis.set_major_formatter(myFmt)

    fig.tight_layout()
    fig.savefig(HK_DIR / 'INT_TEMP_RAW.png')

    if Interact:
        plt.show(block=False)

    ## Search for PanCam CAL Processed Files
    FILT_DIR = "*Cal_HKTM.pickle"
    CalPikFile = sorted(PROC_DIR.rglob(FILT_DIR))

    if len(CalPikFile) == 0:
        print("**No Cal HKTM Files Found**")
        print("Plotting TM HK Voltages Aborted")
        return
    elif len(CalPikFile) > 1:
        plotter_Error("Warning more than one 'Cal_TM.pickle' found") 

    Cal = pd.read_pickle(CalPikFile[0])

    gs2 = gridspec.GridSpec(2, 1, height_ratios=[3, 1])
    fig2 = plt.figure(figsize=(14.0, 9.0))
    ax3 = fig2.add_subplot(gs2[0])
    ax4 = fig2.add_subplot(gs2[1], sharex=ax3)

    ax3.plot(Cal.DT, Cal.Temp_LFW,  label='LFW')
    ax3.plot(Cal.DT, Cal.Temp_RFW,  label='RFW')
    ax3.plot(Cal.DT, Cal.Temp_HRC,  label='HRC')
    ax3.plot(Cal.DT, Cal.Temp_LWAC, label='LWAC')
    ax3.plot(Cal.DT, Cal.Temp_RWAC, label='RWAC')
    ax3.plot(Cal.DT, Cal.Temp_HRCA, label='ACT')
    ax3.grid(True)
    ax3.set_ylabel('Temp [$^\circ$C]')
    ax3.legend(loc='lower center', bbox_to_anchor=(0.5, 1.0), ncol=5, borderaxespad=0, frameon=False)
    ax3.set_xticklabels([], visible=False)

    ax4.plot(Cal.DT, Cal.Temp_LDO, '-k', label='LDO')
    ax4.grid(True)
    ax4.set_ylabel('LDO Temp [$^\circ$C]')
    ax4.xaxis.set_major_formatter(myFmt)

    fig2.tight_layout()
    fig2.savefig(HK_DIR / 'INT_TEMP_CAL.png')

    if Interact:
        plt.show(block=True)
    


def Rover_Temperatures(PROC_DIR, Interact):
    """"Produces a Rover temperature plot from pickle files"""

    print("---Producing Rover Temperature Plot")

    HK_DIR = MakeHKPlotsDir(PROC_DIR)

    ## Search for PanCam Rover Status Processed Files
    FILT_DIR = "*RoverStatus.pickle"
    RawPikFile = sorted(PROC_DIR.rglob(FILT_DIR))

    if len(RawPikFile) == 0:
        print("**No Rover Status Files Found**")
        print("Plotting Rover Temperatures Aborted")
        return
    elif len(RawPikFile) > 1:
        plotter_Error("Warning more than one 'RoverStatus.pickle' found only first used.")

    ROV = pd.read_pickle(RawPikFile[0])

    ## Search for PanCam Rover Temperature Processed Files
    FILT_DIR = "*RoverTemps.pickle"
    RawPikFile = sorted(PROC_DIR.rglob(FILT_DIR))

    if len(RawPikFile) == 0:
        print("**No Rover Temps Files Found**")
        print("Plotting Rover Temperatures Aborted")
        return
    elif len(RawPikFile) > 1:
        plotter_Error("Warning more than one 'RoverTemps.pickle' found only first used.") 

    TMP = pd.read_pickle(RawPikFile[0])

    # Rover Temperatures
    gs  = gridspec.GridSpec(2, 1, height_ratios=[3, 1])
    fig = plt.figure(figsize=(14.0, 9.0))
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1], sharex=ax0)

    ax0.plot(TMP.DT, TMP.PIU_T.astype('int64'), label='PIU')
    ax0.plot(TMP.DT, TMP.DCDC_T.astype('int64'), label='DCDC')
    ax0.legend(loc='upper right', frameon=False)
    ax0.set_ylabel('Rover Monitored \n Temperature [$^\circ$C]')
    ax0.grid(True)
    ax0.set_xticklabels([],visible=False)

    ax1.plot(ROV.DT, ROV.HTR_ST.astype('int64'), label='Heater Status')
    ax1.text(.99, .9, 'Rover Heater Status', color='0.25', fontweight='bold', horizontalalignment='right', transform=ax1.transAxes)
    ax1.yaxis.tick_right()
    ax1.yaxis.set_label_position('right')
    ax1.set_xlabel('')
    ax1.set_ylabel('LDO RAW [ENG]')
    ax1.grid(True)
    ax1.set_ylim([-0.1, 1.1])
    ax1.get_yaxis().set_visible(False)
    ax1.set_xlabel('Date Time')
    ax1.xaxis.set_major_formatter(myFmt)

    fig.tight_layout()
    fig.savefig(HK_DIR / 'ROV_TEMPS.png')

    if Interact:
        plt.show()



def Rover_Power(PROC_DIR, Interact):
    """"Produces a Rover power consumption plot from pickle files"""

    print("---Producing Rover Power Plot")

    HK_DIR = MakeHKPlotsDir(PROC_DIR)

    ## Search for PanCam Rover Status Processed Files
    FILT_DIR = "*RoverStatus.pickle"
    RawPikFile = sorted(PROC_DIR.rglob(FILT_DIR))

    if len(RawPikFile) == 0:
        print("**No Rover Status Files Found**")
        print("Plotting Rover Power Aborted")
        return
    elif len(RawPikFile) > 1:
        plotter_Error("Warning more than one 'RoverStatus.pickle' found only first used.")

    ROV = pd.read_pickle(RawPikFile[0])

    # Rover Current and Status Plot
    gs  = gridspec.GridSpec(2, 1, height_ratios=[3, 1])
    fig = plt.figure(figsize=(14.0, 9.0))
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1], sharex=ax0)

    ax0.plot(ROV.DT, ROV.Inst_Curr, label='Instr.')
    ax0.plot(ROV.DT, ROV.HTR_Curr, label='HTR')
    ax0.legend(loc='upper right')
    ax0.set_ylabel('Current [A]')
    ax0.grid(True)
    ax0.set_xticklabels([],visible=False)

    ax1.plot(ROV.DT, ROV.PWR_ST, label='Instr.')
    ax1.plot(ROV.DT, ROV.HTR_ST, label='HTR')
    ax1.text(.99, .9, 'Status', color='0.25', fontweight='bold', horizontalalignment='right', transform=ax1.transAxes)
    ax1.yaxis.tick_right()
    ax1.yaxis.set_label_position('right')
    ax1.set_xlabel('')
    ax1.set_ylabel('Status')
    ax1.grid(True)
    ax1.set_ylim([-0.1, 1.1])
    ax1.get_yaxis().set_visible(False)
    ax1.set_xlabel('Date Time')
    ax1.xaxis.set_major_formatter(myFmt)

    fig.tight_layout()
    fig.savefig(HK_DIR / 'ROV_PWR.png')

    if Interact:
        plt.show(block=False)

    # Rover Status and Power Extract
    ACT = ROV[(ROV.PWR_ST > 0) | (ROV.HTR_ST > 0)]
    gs2  = gridspec.GridSpec(2, 1, height_ratios=[3, 1])
    fig2 = plt.figure(figsize=(14.0, 9.0))
    ax2 = fig2.add_subplot(gs2[0])
    ax3 = fig2.add_subplot(gs2[1], sharex=ax2)

    ax2.plot(ACT.DT, ACT.Inst_Curr, label='Instr.')
    ax2.plot(ACT.DT, ACT.HTR_Curr, label='HTR')
    ax2.legend(loc='upper right')
    ax2.set_ylabel('Current [A]')
    ax2.grid(True)
    ax2.set_xticklabels([],visible=False)

    ax3.plot(ACT.DT, ACT.PWR_ST, '.', label='Instr.')
    ax3.plot(ACT.DT, ACT.HTR_ST, '.', label='HTR')
    ax3.text(.99, .9, 'Status', color='0.25', fontweight='bold', horizontalalignment='right', transform=ax3.transAxes)
    ax3.yaxis.tick_right()
    ax3.yaxis.set_label_position('right')
    ax3.set_xlabel('')
    ax3.set_ylabel('Status')
    ax3.grid(True)
    ax3.set_ylim([-0.1, 1.1])
    ax3.get_yaxis().set_visible(False)
    ax3.set_xlabel('Date Time')
    ax3.xaxis.set_major_formatter(myFmt)

    fig2.tight_layout()
    fig2.savefig(HK_DIR / 'ROV_PWR_EXT.png')

    if Interact:
        plt.show()



if __name__ == "__main__":
    #DIR = Path(input("Type the path to the PROC folder where the processed files are stored: "))
    DIR = Path(r"C:\Users\ucasbwh\OneDrive - University College London\PanCam Documents\Rover Level Testing\Data\191107 - TVAC TP02 Testing\20191106_1734_ERJPMW_CRUISE_CHECKOUTS\PROC")
    #HK_Temperatures(DIR, True)
    #Rover_Temperatures(DIR, True)
    Rover_Power(DIR, True)
