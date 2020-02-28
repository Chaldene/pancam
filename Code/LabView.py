# -*- coding: utf-8 -*-
"""
labview.py

Barry Whiteside
Mullard Space Science Laboratory - UCL

PanCam Data Processing Tools
Created 24 Feb 2020
"""

from pathlib import Path
import logging
import pandas as pd
import filecmp
from shutil import copyfile
import json
import shutil
import numpy as np

import PC_Fns
import hs

logger = logging.getLogger(__name__)

# Global parameters
labviewProcVer = {'LVProcVer': 1.0}


def hk_extract(lv_dir: Path, archive: bool = False):
    """Generates a Unproc_HKTM.pickle from the found HK txt files

    Arguments:
        lv_dir {Path} -- Dir containing .txt files with LabView generated files.

    Returns:
        Boolean -- Returns true if files found and function completed.

    Generates:
        Unproc_HKTM.pickle -- The pandas dataframe containing raw HK and time information within a folder for each instance.

    Archives:
        RMAP_HK  --  To Archive folder.
    """

    # Seartch through folder for HK file
    logger.info("Processing LabView HK")

    files_hk = PC_Fns.Find_Files(lv_dir, "RMAP_HK*.txt", Recursive=False)

    if not files_hk:
        return False

    # Proc dir
    proc_dir = lv_dir / "PROC"

    if archive:
        # Create directory for archive
        arc_dir = lv_dir / "ARCHIVE" / "RMAP_HK"
        if not arc_dir.is_dir():
            logger.info("Generating 'ARCHIVE' directory")
            arc_dir.mkdir(parents=True)

    # Read text file for HK
    hk_head = ['Time', 'RAW']
    hk_df = pd.DataFrame()

    for curfile in files_hk:
        logger.info("Reading %s", curfile.name)
        file_df = pd.read_csv(curfile, sep=r' \t ', header=None,
                              names=hk_head, engine='python')

        if not file_df.empty:
            file_df['RAW'] = file_df['RAW'].apply(
                lambda x: x.replace('\t', ' '))
            hk_df = hk_df.append(file_df, ignore_index=True)

        if archive:
            curfile.rename(arc_dir / curfile.name)

    hk_df['Source'] = 'LabView'
    hk_df.to_pickle(proc_dir / "Unproc_HKTM.pickle")
    logger.info("PanCam Unproc HK pickled.")
    logger.info("--HK Extract Completed.")

    return True


def hs_extract(lv_dir: Path, archive: bool = False):
    """Extracts the H&S from the .txt logs into a single pickel for furhter processing

    Arguments:
        lv_dir {Path} -- Dir containing .txt files with LabView generated files.

    Generates:
        hs_raw.pickle -- Pickle file in ['Time', 'RAW'] format for hs module.

    Archives:
        RMAP_H&S  --  To Archive folder.
    """

    # Search through folder for H&S file
    logger.info("Processing LabView H&S")

    files_hs = PC_Fns.Find_Files(lv_dir, "RMAP_H&S*.txt", Recursive=False)

    if not files_hs:
        return

    # Proc dir
    proc_dir = lv_dir / "PROC"

    if archive:
        # Create directory for archive
        arc_dir = lv_dir / "ARCHIVE" / "RMAP_H+S"
        if not arc_dir.is_dir():
            logger.info("Generating 'ARCHIVE' directory")
            arc_dir.mkdir(parents=True)

    # Read text file for H&S
    hs_head = ['Time', 'RAW']
    hs_df = pd.DataFrame()

    for curfile in files_hs:
        logger.info("Reading %s", curfile.name)
        file_df = pd.read_csv(curfile, sep=r' \t ',
                              header=None, names=hs_head, engine='python')
        if not file_df.empty:
            file_df['RAW'] = file_df['RAW'].apply(
                lambda x: x.replace('\t', ' '))
            hs_df = hs_df.append(file_df, ignore_index=True)

        if archive:
            curfile.rename(arc_dir / curfile.name)

    hs_df.to_pickle(proc_dir / "hs_raw.pickle")
    logger.info("PanCam H+S pickled.")
    logger.info("--HS Extract Completed")


def sci_extract(lv_dir: Path, archive: bool = False):
    """Creates pci_spw files from the RMAP Sci packets. HS must be decoded and verified first.

    Arguments:
        lv_dir {Path} -- Dir containing .txt files with LabView generated files.

    Keyword Arguments:
        archive {bool} -- If True moves moves RMAP_Sci*.txt to archive folder (default: {False})

    Generates:
        *.pci_spw -- Binary files of the reconstructed images.

    Archives:
        RMAP_Sci  -- To Archive folder.
    """

    logger.info("Extracting science images from SpW Logs for comparing")

    files_sci = PC_Fns.Find_Files(lv_dir, "RMAP_Sci*.txt", Recursive=False)

    if not files_sci:
        return

    # Check for first file being empty due to labview bug
    if files_sci[0].stat().st_size == 0:
        logger.info("First RMAP_Sci packet empty - deleting.")
        files_sci[0].unlink()
        del files_sci[0]

    # Check matches expectation from H&S
    num_pkts = sum(1 for item in files_sci)
    num_expt = hs.sci_cnt(lv_dir / "PROC") * 7
    if num_pkts != num_expt:
        logger.error("Missing Sci Parts Detected!")
        logger.error("Expected: %d", num_expt)
        logger.error("Got: %d packets", num_pkts)
        logger.info("Looking for sequential short chunks")
        # Search for all files with a size 762030
        small_chunks = [files_sci.index(
            chunk) for chunk in files_sci if chunk.stat().st_size == 762030]
        # Search for any sequential small chunks
        repeat_chunks = [small_chunks[i+1]
                         for i, x in enumerate(np.diff(small_chunks) == 1) if x]
        if repeat_chunks:
            logger.error("Repeat chunks found. Renaming and excluding them")
            wrong_files = [files_sci[i] for i in repeat_chunks]
            for wrong_item in wrong_files:
                logger.info("Renaming to .ignore %s", wrong_item.name)
                wrong_item.rename(wrong_item.with_suffix('.txt.ignore'))
                files_sci.remove(wrong_item)

            num_pkts = sum(1 for item in files_sci)
            if num_pkts != num_expt:
                logger.critical(
                    "Still unexpected number of packets. Now %d", num_pkts)
            else:
                logger.error("Number of packets now as expected, %d", num_pkts)

    # Create directory for binary image files
    img_spw_dir = lv_dir / "PROC" / "IMG_SPW"
    if not img_spw_dir.is_dir():
        logger.info("Generating 'IMG_SPW' directory")
        img_spw_dir.mkdir()

    if archive:
        # Create directory for archive
        arc_dir = lv_dir / "ARCHIVE" / "RMAP_Sci"
        if not arc_dir.is_dir():
            logger.info("Generating 'ARCHIVE' directory")
            arc_dir.mkdir(parents=True)

    # Write each file as a binary (assuming 7 LDT per image)
    write_file = img_spw_dir / "001.pci_spw"
    logger.info("Creating spw binary file %s", write_file.name)
    wf = open(write_file, 'w+b')

    sci_head = ['Time', 'RAW']
    for curfile in files_sci:

        dl = pd.read_csv(curfile, sep=r' \t ', header=None,
                         names=sci_head, engine='python')
        if dl.shape[0] == 0:
            # Move .txt file to archive
            if archive:
                curfile.rename(arc_dir / curfile.name)
            logger.info("File empty %s", curfile.name)
            continue
        elif dl.shape[0] > 1:
            logger.error("More than one line found in file, using first line")

        dl['RAW'] = dl['RAW'].apply(lambda x: x.replace('\t', ' '))
        raw = dl['RAW'].apply(lambda x: bytearray.fromhex(x))

        # Assume images are all 2097200 bytes and so break on that.
        if write_file.stat().st_size >= 2097200:
            wf.close()
            cur_ldt = curfile.stem.split('_')[-1]
            write_file = img_spw_dir / (cur_ldt + ".pci_spw")
            logger.info("Creating spw binary file %s", write_file.name)
            wf = open(write_file, 'w+b')

        wf.write(raw[0])

        if archive:
            # Move .txt file to archive
            curfile.rename(arc_dir / curfile.name)

    wf.close()
    logger.info("--Extracting Science Images from SpW logs completed.")


def bin_move(lv_dir: Path, archive: bool = False):

    logger.info("Moving saved science images that match SpW logs")

    bin_files = PC_Fns.Find_Files(lv_dir, "*.bin")
    spw_files = PC_Fns.Find_Files(lv_dir, "*.pci_spw")

    if not bin_files:
        return

    # Create directory for binary image files
    img_dir = lv_dir / "PROC" / "IMG_RAW"
    if not img_dir.is_dir():
        logger.info("Generating 'IMG_RAW' directory")
        img_dir.mkdir()

    # Create directory for archive
    if archive:
        arc_dir = lv_dir / "ARCHIVE" / "Sci"
        if not arc_dir.is_dir():
            logger.info("Generating 'ARCHIVE' directory")
            arc_dir.mkdir(parents=True)

    for curfile in bin_files:
        curfile_matched = False
        curfile_partial = False
        curfile_bloated = False
        curfile_len = curfile.stat().st_size

        logger.info("Reading file: %s", curfile.name)

        # If a partial file create a temporary file for comparing
        tmp_file = lv_dir / "PROC" / "tmp_cmp.bin"
        if curfile_len < 2097200:
            logger.info("Incomplete image binary detected")
            curfile_partial = True

        if curfile_len > 2097200:
            logger.info("Binary image with too much data detected")
            curfile_bloated = True
            # Write curfile expected image size to tmp file
            with open(curfile, 'rb') as bin_f:
                logger.info("Creating tmp file of bin with actual image size")
                tmp = open(tmp_file, 'wb')
                tmp.write(bin_f.read(2097200))

        # Search through SpW files and check there is a match
        for ref in spw_files:

            if curfile_partial:
                # Write same equivalent bytes tmp file
                with open(ref, 'rb') as spw_f:
                    logger.info("Partial comparing with %s", ref.name)
                    tmp = open(tmp_file, 'wb')
                    tmp.write(spw_f.read(curfile_len))

                if filecmp.cmp(curfile, tmp_file, shallow=False):
                    curfile_matched = True
                    logger.info("Beginning of file matches %s", ref.name)

                    # Use spw generated binary as image
                    logger.info("Using generated image from SpW.txt files")
                    spw_files.remove(ref)
                    pci_raw_file = img_dir / \
                        (curfile.stem + "_repaired" + ref.stem + ".pci_raw")

                    # Copy to pci_raw folder and create json
                    copyfile(ref, pci_raw_file)
                    create_repairedjson(pci_raw_file)
                    ref.unlink()

            elif curfile_bloated:
                if filecmp.cmp(tmp_file, ref, shallow=False):
                    curfile_matched = True
                    logger.info(
                        "Trimmed bin image matches that of SpW.txt files")
                    spw_files.remove(ref)
                    pci_raw_file = img_dir / \
                        (curfile.stem + "_repaired" + ref.stem + ".pci_raw")

                    # Copy to pci_raw folder and create json
                    copyfile(ref, pci_raw_file)
                    create_repairedjson(pci_raw_file)
                    ref.unlink

            # If file is complete then a standard compare
            elif filecmp.cmp(curfile, ref, shallow=False):
                curfile_matched = True
                logger.info("File matches, deleting file: %s", ref.name)

                # Delete spw generated binary
                spw_files.remove(ref)
                ref.unlink()

                # Copy image to pci_raw folder and create json
                pci_raw_file = img_dir / (curfile.stem + ".pci_raw")
                copyfile(curfile, pci_raw_file)
                create_json(pci_raw_file)

            if curfile_matched:
                if archive:
                    # Move file to archive folder
                    curfile.rename(arc_dir / curfile.name)
                    # If not a partial file can delete png preview
                    pngfile = curfile.with_suffix(".png")
                    if (not curfile_partial) and pngfile.exists():
                        logger.info(
                            "Deleting png from LabView: %s", pngfile.name)
                        pngfile.unlink()
                break

        if not curfile_matched:
            logger.error("File has no corresponding match!!!")

    # if tmp_file.exists():
        # tmp_file.unlink()

    logger.info("--Moving saved science images completed.")


def create_json(img_file: Path):
    """Creates a json file to accompany .pci_raw image.

    Arguments:
        img_file {Path} - - Path to .pci_raw image

    Generates:
        img_name.json - - json file containing processor information.
    """

    json_file = img_file.with_suffix(".json")
    top_lev_dic = {"Processing Info": labviewProcVer}

    if json_file.exists():
        logger.info("Deleting file: %s", json_file.name)
    with open(json_file, 'w') as f:
        json.dump(top_lev_dic, f, indent=4)


def create_repairedjson(img_file: Path):
    """Creates a json file to accompany repaired.pci_raw image.

    Arguments:
        img_file {Path} - - Path to .pci_raw image

    Generates:
        img_name.json - - json file containing processor information.
    """

    json_file = img_file.with_suffix(".json")
    file_source = img_file.stem.split("_repaired")[-1]
    file_dic = {"Repair RMAM_Sci.txt Source Start": file_source}

    proc_info = labviewProcVer
    proc_info.update(file_dic)

    top_lev_dic = {"Processing Info": proc_info}

    if json_file.exists():
        logger.info("Deleting file: %s", json_file.name)
    with open(json_file, 'w') as f:
        json.dump(top_lev_dic, f, indent=4)


def create_archive(lv_dir: Path):
    """Creates a compressed tar archive of the archive folder

    Arguments:
        lv_dir {Path} -- Path to LabView directory

    Generates:
        ARCHIVE.tar.bz2 -- Compressed archive of original files
    """

    archive_name = lv_dir / "ARCHIVE"
    # Folde that will be archived
    target = lv_dir / "ARCHIVE"

    # bz2 is a good compromise between speed and efficiency
    shutil.make_archive(archive_name, 'bztar', target, logger=logger)

    # Once complete delete original folder
    shutil.rmtree(target)


if __name__ == "__main__":
    dir = Path(
        input("Type the path to the folder where the LabWiew files are stored: "))

    proc_dir = dir / "PROC"
    if proc_dir.is_dir():
        logger.info("Processing' Directory already exists")
    else:
        logger.info("Generating 'Processing' directory")
        proc_dir.mkdir()

    logging.basicConfig(filename=(proc_dir / 'processing.log'),
                        level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(module)s.%(funcName)s - %(message)s')
    logger.info('\n\n\n\n')
    logger.info("Running labview.py as main")
    logger.info("Reading directory: %s", dir)

    #hs_extract(dir, archive=True)
    #hk_extract(dir, archive=True)
    # hs.decode(proc_dir)
    # hs.verify(proc_dir)
    #sci_extract(dir, archive=True)
    bin_move(dir, archive=True)
    # create_archive(dir)
