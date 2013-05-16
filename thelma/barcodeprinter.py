"""
barcode printing
"""
import logging
import os
from subprocess import (Popen,
                        PIPE)

__docformat__ = "reStructuredText en"

__all__ = ['BarcodePrinter',
           'SatoBarcode',
           'UniTwoLabelRackBarcode',
           'LocationBarcode',
           'EmptyBarcode',
           'print_two_label_unirack_barcode',
           'print_location_barcode']

__author__ = 'F Oliver Gathmann'
__date__ = '$Date: 2012-10-25 14:14:00 +0200 (Thu, 25 Oct 2012) $'
__revision__ = '$Rev: 12918 $'
__source__ = '$URL: #$'

class BarcodePrinter:
    """
    Print a barcode to a barcode printer

    """
    def __init__(self, barcode_printer_name):
        """
        @param barcode_printer_name: The name of a printer in the unix-lpd system
            If None or "", then the barcode is printed to the terminal.
        @type barcode_printer_name: L{str} or L{NoneType}
        """
        self.barcode_printer_name = barcode_printer_name

    def print_barcode(self, barcode):
        """
        @param barcode: Barcode-instance that renders a string for the printer
        @type barcode: L{SatoBarcode}
        """
        bc_string = barcode.render()
        if self.barcode_printer_name and \
               not self.barcode_printer_name.upper().endswith('DUMMY'):
            cmd = 'lpr -H192.168.1.33:631 -P%s -#%d' % (self.barcode_printer_name, 1)
            self._run_command(cmd, input_string=bc_string)
        logging.getLogger().info('Sent format string %r to barcode printer %s' %
                                 (bc_string, self.barcode_printer_name))

    def get_printer_name(self):
        return self.barcode_printer_name

    def _run_command(self, cmd, suppress_errors=False, input_string=None,
                   environment=None):
        """
        Runs the given command string in a command shell.

        Uses L{os.popen3}).

        @param cmd_string: command to execute
        @type cmd_string: string
        @param input_string: input to pass to C{sys.stdin} of the process
        @type input_string: string
        @param suppress_errors: if set, errors happening during the execution of
          the command are only printed to C{sys.stdout}
        @type suppress_errors: Boolean
        @param environment: mapping to use as the environment for the subprocess
        @type environment: dictionary
        @raise OSError: if an error happens during command execution and
          L{suppressError} is not set
        @return: output to C{sys.stdout} from the command
        """
        if environment is None:
            environment = os.environ
        child = Popen(cmd, shell=True, env=environment,
                       stdin=PIPE, stdout=PIPE, stderr=PIPE)
        if not input_string is None:
            child.stdin.write(input_string)
            child.stdin.close()
        if child.wait() != 0:
            str_error = child.stderr.read()
            if not suppress_errors:
                raise OSError(str_error)
            else:
                print 'error during command execution: %s' % str_error
        return child.stdout.read()


class SatoBarcode(object):

    """
    Barcode generator for the Sato CL 412 printer for
    Cenix "Dish", "Tube", "Box", and "User" barcodes.

    """

    # rotation codes for 0, 90, 180, and 270 degrees:
    _ROT = { 0: 0, 90: 1, 180: 2, 270: 3}

    def __init__(self):
        pass

    def render(self):
        """
        Renders the barcode into a string which serves as a printing command
        to the barcode printer.

        @return: printing command
        @rtype: L{str}

        """
        pass

    #--- internal methods ----

    def _esc(self, char):
        return '%s%s' % (chr(27), char)

    def _start(self):
        return self._esc('A')

    def _stop(self):
        return self._esc('Z')

    def _print_speed(self, value):
        return self._esc('CS%d' % value)

    def _horizontal_space(self, num_pixels):
        return self._esc('H%04d' % num_pixels)

    def _vertical_space(self, num_pixels):
        return self._esc('V%04d' % num_pixels)

    def _darkness(self, value):
        return self._esc('#E%d' % value)

    def _mid_text(self, text, offsetX, offsetY):
        return (self._horizontal_space(offsetX)
                + self._vertical_space(offsetY)
                + self._esc('XM%s' % text))

    def _small_text(self, text, offsetX, offsetY):
        return (self._horizontal_space(offsetX)
                + self._vertical_space(offsetY)
                + self._esc('XS%s' % text))

    def _interleave_5_barcode(self, barcode, offsetX, offsetY, hight=80):
        return self._horizontal_space(offsetX)+self._vertical_space(offsetY)+\
               self._esc('B2020%02d%s' % (hight, barcode))

    code39Ratio = {'1:3': 'B1', '2:5': 'BD1', '1:2': 'D1' }
    #
    def _code_39_barcode(self, barcode, offsetX, offsetY,
                        hight=80, ratio='1:3', width=8):
        """allowed ratios are 1:3, 2:5, and 1:2, width is 01-12"""
        strRatio = self.code39Ratio[ratio]
        return self._horizontal_space(offsetX)+self._vertical_space(offsetY)+\
               self._esc('%s%02d%03d*%s*' % (strRatio, width, hight, barcode))

    def _text_barcode_C128(self, barcode, offsetX, offsetY,
                          hight=80, narrow_dots=3):
        """ less condens text barcode """
        return (self._horizontal_space(offsetX)
                + self._vertical_space(offsetY)
                + self._esc('BG%02d%03d>H%s' % (narrow_dots, hight, barcode)))

    def _text_barcode_C93(self, barcode, offsetX, offsetY, hight=80):
        "text barcode with better density, especially with excl. uppercase chars"
        return self._horizontal_space(offsetX) + self._vertical_space(offsetY) \
               +self._esc('BC02%03d%02d%s' % (hight,len(barcode),barcode))

    def _graphics_pcx(self, data, numBytes, offsetX, offsetY):
        return self._horizontal_space(offsetX) + self._vertical_space(offsetY) + \
               self._esc('GP%d,' % (numBytes) + data)

    def _quantity(self, num):
        return self._esc('Q%d' % num)

    def _rotate(self, deg):
        return self._esc('%%%d' % deg)

    def _rotate_90_degrees(self):
        return self._esc('%1')

    def _rotate_180_degrees(self):
        return self._esc('%2')

    def _rotate_270_degrees(self):
        return self._esc('%3')


class SatoUniTwoLabelRackBarcode(SatoBarcode):

    """
    Barcode generator for the Sato CL 412 printer for
    printing a barcode split over *two* labels - one machine-readable
    label and one human-readable label with two rows featuring a
    total of four label entries.

    """

    _LABEL_PROFILES = {
        'RACK': { 'rotation':SatoBarcode._ROT[180],
                     'bc_x'           : 130,
                     'bc_y'           : 80,
                     'bc_hight'       : 120,
                     'bc_narrow_dots' : 2,
                     'num_bc_x'       : 50,
                     'num_bc_y'       : 20,
                     'offset_x'       : 945,
                     'offset_y'       : 30,
                     'text_x1'        : 255,
                     'text_x2'        : 255,
                     'field1_y'       : 40,
                     'field2_y'       : 10,
                   }
    }

    def __init__(self, barcode, label_row_1, label_row_2=''):
        super(SatoUniTwoLabelRackBarcode, self).__init__()
        self.barcode   = barcode
        self.label_row_1 = label_row_1 or ''
        self.label_row_2 = label_row_2 or ''

    def render(self):
        profile = self._LABEL_PROFILES['RACK']
        text_label = (self._start()
                     + self._print_speed(1)
                     + self._darkness(5)
                     + self._rotate(profile['rotation'])
                     + self._mid_text(self.label_row_1,
                                      profile['text_x1']+profile['offset_x'],
                                      profile['field1_y']+profile['offset_y'])
                     + self._mid_text(self.label_row_2,
                                      profile['text_x2']+profile['offset_x'],
                                      profile['field2_y']+profile['offset_y'])
                     + self._quantity(1)
                     + self._stop())
        if self.barcode != '':
            barcode_label = (self._start()
                             + self._print_speed(1)
                             + self._darkness(5)
                             + self._rotate(profile['rotation'])
                             + self._text_barcode_C128(self.barcode,
                                                     profile['bc_x']+profile['offset_x'],
                                                     profile['bc_y']+profile['offset_y'],
                                                     profile['bc_hight'],
                                                     profile['bc_narrow_dots'])
                             + self._quantity(1)
                             + self._stop())
            return text_label + barcode_label
        else:
            return text_label

UniTwoLabelRackBarcode = SatoUniTwoLabelRackBarcode


class SatoUniLocationBarcode(SatoBarcode):

    _LABEL_PROFILES = {
       'LOCATION': { 'rotation': SatoBarcode._ROT[180], 'bc_x':180, 'bc_y':125,
                     'bc_hight':60, 'num_bc_x':175, 'num_bc_y':65,
                     'offset_x':1000, 'offset_y':25, 'text_x':120,
                     'row1_y':200
                     }
       }

    def __init__(self, barcode, label_row_1):
        super(SatoUniLocationBarcode, self).__init__()
        self.barcode   = barcode
        self.label_row_1 = label_row_1 or ''

    def render(self):
        profile = self._LABEL_PROFILES['LOCATION']
        return ( self._start()
                 + self._print_speed(1)
                 + self._darkness(5)
                 + self._rotate(profile['rotation'])
                 + self._mid_text(self.label_row_1,
                                 profile['text_x']+profile['offset_x'],
                                 profile['row1_y']+profile['offset_y'])
                 + self._interleave_5_barcode(self.barcode,
                                            profile['bc_x']+profile['offset_x'],
                                            profile['bc_y']+profile['offset_y'],
                                            profile['bc_hight'])
                 + self._mid_text(self.barcode,
                                 profile['num_bc_x']+profile['offset_x'],
                                 profile['num_bc_y']+profile['offset_y'])
                 + self._quantity(1)
                 + self._stop()
                 )

LocationBarcode = SatoUniLocationBarcode

class SatoEmptyBarcode(SatoBarcode):
    """
    'Print' an empty barcode
    """
    MAX_QUANTITY = 20

    def __init__(self, quantity=1):
        super(SatoEmptyBarcode, self).__init__()
        if quantity > self.MAX_QUANTITY:
            raise ValueError('Quantity %s above max '\
                             'value %d' % (quantity,self.MAX_QUANTITY))
        self.quantity = quantity

    def render(self):
        return (  self._start()
                + self._print_speed(1)
                + self._darkness(5)
                + self._rotate(self._ROT[180])
                + self._mid_text(' ', 1000, 100)
                + self._quantity(self.quantity)
                + self._stop()
                )

EmptyBarcode = SatoEmptyBarcode


def print_two_label_unirack_barcode(barcode_number,
                                     label_row_1, label_row_2, printer_name=None):
    """print two-label unidb barcode"""
    barcode = UniTwoLabelRackBarcode(barcode=barcode_number,
                                        label_row_1=label_row_1,
                                        label_row_2=label_row_2)
    barcodePrinter = BarcodePrinter(printer_name)
    barcodePrinter.print_barcode(barcode)


def print_location_barcode(barcode_number, label_row_1, printer_name=None):
    barcode = LocationBarcode(barcode=barcode_number,
                              label_row_1=label_row_1)
    barcodePrinter = BarcodePrinter(printer_name)
    barcodePrinter.print_barcode(barcode)
