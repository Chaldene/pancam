# NavCam Images

For some instances of the Rover calibration data in Toulouse, NAVCAM images were
included within the '.ha' files and able to be extracted. Previously, the NAVCAM
images were given to us directly from Airbus engineers.

The default format for the NAVCAM images is the '.pgm' format, that contains a
17 byte header in ascii followed by the pixel data. The NAVCAM PGM is a 255-level
grayscale 1024x1024 image as standard. The function *rover.NavCamBrowse()* will
generate a .png preview of the NAVCAM image using the imageio libary directly
from the '.pgm' file.

## PGM Header

For a 1024x1024 image containing binary data the pgm header is:

    pgm_hdr = bytes('P5\n1024 1024 255\n', 'utf8')

Which in ASCII reads as:

    P5 <NL>
    1024 1024 255 <NL>

### 512x512 images

For smaller images it is a simple case of replacing the header with the correct
dimensions so for a 512x512 pgm the header is:

    pgm_hdr = bytes('P5\n512 512 255\n', 'utf8')

Which in ASCII reads as:

    P5 <NL>
    512 512 255 <NL>

## NAVCAM files within .ha logs

All LDT transfers found are now extracted by the *rover_ha.HaScan()* function.
Those that are identified as not being a PanCam TM are placed within the
"LDT_RAW" folder.

Once all the elements of the LDT have been rebuilt the *complete_file()*
class function is executed on the *LDTProperties* class, if the file size matches
that expected of a NAVCAM image, the image is converted to a pgm file and moved
to "NAVCAM" directory.

To convert a NAVCAM LDT file into a '.pgm' file thi first 68 bytes of the LDT
file are removed and replaced with the PGM header as described above. This is all
automatically performed by the *complete_file()* class function.

NAVCAM images that were downloaded using the RMAP_READ method during testing (ie.
the really slow method) have not been stored within the .ha files are are obtained
directly from Airbus.
