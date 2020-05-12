# -*- coding: utf-8 -*-
"""
main.py

Barry Whiteside
Mullard Space Science Laboratory - UCL

PanCam Data Processing Tools
Created 31 Oct 2019
"""

from pathlib import Path
import logging
import shutil

import plotter
import hk_cal
import hk_raw
import image_browse
import rover_ha
import rover
import swis
import hs
import labview
import tc_cal
import pancam_fns

logger, status = pancam_fns.setup_logging()

if __name__ == '__main__':

    status.info("Running main.py")

    # Select Folder to Process
    top_dir = Path(
        input("Type the path to the folder where the RAW log or archive files are stored: "))
    if (not top_dir.is_dir()) or top_dir == Path("."):
        logging.error("Non-Valid path provided - exiting")
        quit()

    # Determine if working with archived folder
    arch = input("Is the folder in a tar.bz2 archive? [Y/N (Default)]: ")
    if arch == 'Y' or arch == 'y':
        file_arch = input("Input the archive full filename: ")
        file_path = top_dir / file_arch

        if file_path.suffixes != ['.tar', '.bz2']:
            logger.error("Not a valid archive format - exiting")
            quit()

        logger.info("Unpacking archive to: %s", top_dir)
        shutil.unpack_archive(file_path, top_dir, 'bztar')

        # New top dir
        top_dir = top_dir / file_path.stem[:-4]

        arch_logs = False

    else:
        arch_user = input(
            "Do you want to archive the files after processing? [Y/N (Default)]: ")
        if arch_user == 'Y' or arch_user == 'y':
            arch_logs = True
        else:
            arch_logs = False

    # Test if processed directory folder exists, if not create it.
    proc_dir = top_dir / 'PROC'
    if not proc_dir.is_dir():
        MakeDir = True
        proc_dir.mkdir()

    # create file handler logger
    pancam_fns.setup_proc_logging(logger, proc_dir)
    logger.info('\n\n\n\n')
    logger.info("main.py")

    # First check if SWIS as multiple folders
    instances = swis.create_instances(top_dir)
    if instances:
        status.info("SWIS Instances Found")
        for inst in instances:
            proc_dir = inst / "PROC"
            status.info("Analysing %s", inst.name)
            swis.hk_extract(inst)
            swis.hs_extract(inst)
            hs.decode(proc_dir, True)
            hs.verify(inst)
            hk_raw.decode(proc_dir)
            hk_cal.cal_HK(proc_dir)
            tc_cal.decode_all(proc_dir)
            plotter.all_plots(proc_dir)
            swis.sci_extract(inst)
            swis.sci_compare(inst)
            image_browse.Img_RAW_Browse(proc_dir)

    else:
        # LabView Files
        if labview.hk_extract(top_dir, archive=arch_logs):
            status.info("LabView Type Found")
            labview.hs_extract(top_dir, archive=arch_logs)
            hs.decode(proc_dir)
            hs.verify(proc_dir)
            labview.tc_extract(top_dir)
            labview.sci_extract(top_dir, archive=arch_logs)
            labview.bin_move(top_dir, archive=arch_logs)
            labview.psu_extract(top_dir, archive=arch_logs)
            # labview.create_spw_images(proc_dir)
            if arch_logs:
                labview.create_archive(top_dir)

        # Rover files
        elif rover.TM_extract(top_dir):
            status.info("Rover Type Found")
            rover.TC_extract(top_dir)
            rover.NavCamBrowse(top_dir)
            rover_ha.HaScan(top_dir)
            rover_ha.RestructureHK(proc_dir)
            rover_ha.compareHaCSV(proc_dir)

        elif swis.nsvf_parse(top_dir):
            status.info("Single SWIS Type Found")
            swis.hk_extract(proc_dir)
            hs.decode(proc_dir, spw_header=True)
            hs.verify(proc_dir)
            swis.sci_extract(proc_dir, True)
            swis.sci_compare(proc_dir)

        # Process secondary files
        hk_raw.decode(proc_dir)
        image_browse.Img_RAW_Browse(proc_dir)
        hk_cal.cal_HK(proc_dir)
        tc_cal.decode_all(proc_dir)

        # Produce Plots
        plotter.all_plots(proc_dir)

    logger.info("main.py completed")
