"""
An adjusted planner for library screening ISO generation.
"""
from thelma.automation.tools.iso.lab.base import FinalLabIsoPosition
from thelma.automation.tools.iso.lab.planner import LabIsoBuilder
from thelma.automation.tools.iso.lab.planner import LabIsoPlanner
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.models.iso import ISO_STATUS

__docformat__ = 'reStructuredText en'

__all__ = ['LibraryIsoBuilder',
           'LibraryIsoPlanner']


class LibraryIsoBuilder(LabIsoBuilder):
    """
    A special lab ISO builder for library screenings. Unlike in normal lab
    ISOs there are no ISO preparation or aliquot plates but pre-existing library
    plates.
    """

    def __init__(self, iso_request, excluded_racks, requested_tubes):
        """
        Constructor

        :param iso_request: The ISO request the ISOs shall belong to.
        :type iso_request: :class:`thelma.models.iso.LabIsoRequest`

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for stock sample picking.
        :type excluded_racks: A list of rack barcodes

        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of tube barcodes.
        """
        LabIsoBuilder.__init__(self, iso_request=iso_request,
                               excluded_racks=excluded_racks,
                               requested_tubes=requested_tubes)

        #: The ISO request layout is required to transfer the library
        #: positions to the ISO plate layout -
        #: use :func:`set_iso_request_layout` to set.
        self.__iso_request_layout = None

        #: The picked library plates mapped onto layout numbers - use
        #: :func:`set_library_platesset_library_plates` to set.
        self.__library_plates = None

    def set_iso_request_layout(self, iso_request_layout):
        """
        The ISO request layout is required to transfer library positions
        to the ISO plate layouts.

        :param library_plates: The picked library plates mapped onto pools.
        :type library_plates: :class:`dict`

        :raise AttributeError: If the library plates have been set before.
        """
        self._set_immutable_value(iso_request_layout, '__iso_request_layout')

    def set_library_plates(self, library_plates):
        """
        The picked library plates must be mapped onto layout numbers.

        :param library_plates: The picked library plates mapped onto pools.
        :type library_plates: :class:`dict`

        :raise AttributeError: If the library plates have been set before.
        """
        self._set_immutable_value(library_plates, '__library_plates')

    def _fill_iso_plate_layout(self, iso_plate_layout, floating_map, pools):
        """
        We still need to add the library positions - their data is derived
        from the :attr:`__iso_request_layout` (the actual pool ID for the
        positions is not inserted).
        """
        for ir_pos in self.__iso_request_layout.get_working_positions():
            if not ir_pos.is_library: continue
            lib_pos = FinalLabIsoPosition.create_library_position(
                                rack_position=ir_pos.rack_position,
                                concentration=ir_pos.iso_concentration,
                                volume=ir_pos.iso_volume)
            iso_plate_layout.add_position(lib_pos)

    def _add_final_iso_plates(self, iso):
        """
        We need to pick a layout number and attach the plate to the ISO. The
        referring plates and layout numbers are removed from the available
        plates map (:attr:`__library_plates`).
        """
        layout_number = min(self.__library_plates.keys())
        library_plates = self.__library_plates[layout_number]
        iso.library_plates = library_plates
        del self.__library_plates[layout_number]


class LibraryIsoPlanner(LabIsoPlanner):
    """
    Ordering a library plate is a special case, because we do not have any
    ISO-specific processing but only job-related preparation routes.
    In addition, we do not generated new aliquot plates for library ISOs but
    assign pre-existing library plates as final ISO plates.

    **Return Value:** :class:`LibraryIsoBuilder`
    """
    NAME = 'Library ISO Planner'

    _BUILDER_CLS = LibraryIsoBuilder

    def __init__(self, log, iso_request, number_isos,
                       excluded_racks=None, requested_tubes=None):
        """
        Constructor:

        :param log: The log to record events.
        :type log: :class:`thelma.ThelmaLog`

        :param iso_request: The ISO request containing the ISO layout for the
            ISO (and experiment metadata with the molecule design pools).
        :type iso_request: :class:`thelma.models.iso.IsoRequest`

        :param number_isos: The number of ISOs ordered.
        :type number_isos: :class:`int`

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for stock sample picking.
        :type excluded_racks: A list of rack barcodes

        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of tube barcodes.
        """
        LabIsoPlanner.__init__(self, log=log, iso_request=self.iso_request,
                               number_isos=number_isos,
                               excluded_racks=excluded_racks,
                               requested_tubes=requested_tubes)

        #: The molecule design library used for the screen.
        self.__library = None

        #: The library plates (future aliquot plates) mapped onto layout
        #: numbers.
        self.__library_plates = None

    def reset(self):
        LabIsoPlanner.reset(self)
        self.__library = None
        self.__library_plates = None

    def _analyse_iso_request(self):
        """
        We need to find the library in addition.
        """
        LabIsoPlanner._analyse_iso_request(self)

        self.__library = self.iso_request.molecule_design_library
        if self._has_floatings:
            msg = 'There are both library and floating positions in the ' \
                  'ISO request layout!'
            self.add_error(msg)
        elif self.__library is None:
            msg = 'There is no library for this ISO request!'
            self.add_error(msg)
        else:
            self.__find_library_plates()
            if not self.has_errors():
                self._real_number_isos = len(self.__library_plates)
                # pylint: disable=E1103
                self._builder.set_iso_request_layout(self._iso_request_layout)
                self._builder.set_library_plates(self.__library_plates)
                # pylint: enable=E1103

    def __find_library_plates(self):
        """
        Determines which layout number have not been covered by the ISO
        request yet, picks unused ones (in order of layout numbers) and fetches
        aliquot plates for them.
        """
        number_aliquots = self.iso_request.number_aliquots

        used_layout_numbers = set()
        for iso in self.iso_request.isos:
            if iso.status == ISO_STATUS.CANCELLED: continue
            for lp in iso.library_plates:
                used_layout_numbers.add(lp.layout_number)

        queued_layout_numbers = set()
        for i in range(self.__library.number_layouts):
            ln = i + 1
            if ln in used_layout_numbers: continue
            queued_layout_numbers.add(ln)
        if len(queued_layout_numbers) < 1:
            msg = 'There are no unused library layouts left for this ISO ' \
                  'request!'
            self.add_error(msg)
            return None

        available_plates = dict()
        for lp in self.__library.library_plates:
            if not lp in queued_layout_numbers: continue
            if lp.has_been_used: continue
            add_list_map_element(available_plates, lp.layout_number, lp)
        self.__check_plate_availability(queued_layout_numbers, available_plates,
                                        number_aliquots)
        if self.has_errors(): return None

        for layout_number in sorted(list(queued_layout_numbers)):
            plates = available_plates[layout_number]
            self.__library_plates[layout_number] = []
            for i in range(number_aliquots):
                lp = plates.pop(0)
                self.__library_plates[layout_number].append(lp)
            if len(self.__library_plates) == self.number_isos: break

        if len(queued_layout_numbers) < self.number_isos:
            msg = 'You have requested %i ISOs. The system will only generate ' \
                  '%s ISO though, because there are no more library layouts ' \
                  'left for this ISO request.' \
                  % (self.number_isos, len(self.__library_plates))
            self.add_warning(msg)

    def __check_plate_availability(self, queued_layout_numbers,
                                   available_plates, number_aliquots):
        """
        Checks whether there are enough plates left for the queued layout
        numbers. Records warnings in case of missing plates.
        """
        not_enough_plates = []
        no_plates_left = []
        del_numbers = []
        for layout_number in queued_layout_numbers:
            if not available_plates.has_key(layout_number):
                no_plates_left.append(layout_number)
                del_numbers.append(layout_number)
                continue
            elif len(available_plates[layout_number]) < number_aliquots:
                info = '%i (%i plates)' % (layout_number,
                                           len(available_plates[layout_number]))
                not_enough_plates.append(info)
                del_numbers.append(layout_number)

        if len(no_plates_left) > 0:
            msg = 'There are no unused library plates left for some layout ' \
                  'numbers that are still in the queue: %s.' \
                  % (', '.join(sorted(no_plates_left)))
            self.add_warning(msg)
        if len(not_enough_plates) > 0:
            msg = 'There are not enough unused library plates left for some ' \
                  'layout numbers that are still in the queue: %s.' \
                  % (', '.join(sorted(not_enough_plates)))
            self.add_warning(msg)

        if len(queued_layout_numbers) == len(del_numbers):
            msg = 'Cannot generate ISOs because there is no sufficient ' \
                  'number of library plates left for any layout still in the ' \
                  'queue (%s).' % (', '.join(sorted(del_numbers)))
            self.add_error(msg)
        for layout_number in del_numbers:
            queued_layout_numbers.remove(layout_number)

    def _assign_sectors(self):
        """
        Sectors are not supported for this type of ISO requests.
        """
        pass

    def _assign_iso_specific_rack_positions(self):
        """
        All fixed positions are shared by all ISOs of the job.
        """
        pass

