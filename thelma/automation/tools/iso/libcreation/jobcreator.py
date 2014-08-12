"""
Creator for library creation ISO jobs.
"""
from thelma.automation.semiconstants import \
    get_rack_specs_from_reservoir_specs
from thelma.automation.semiconstants import get_item_status_future
from thelma.automation.semiconstants import get_reservoir_specs_standard_384
from thelma.automation.semiconstants import get_reservoir_specs_standard_96
from thelma.automation.tools.iso.libcreation.base import LibraryLayout
from thelma.automation.tools.iso.libcreation.base import NUMBER_SECTORS
from thelma.automation.tools.iso.libcreation.base import \
    DEFAULT_ALIQUOT_PLATE_CONCENTRATION
from thelma.automation.tools.iso.libcreation.base import \
    DEFAULT_PREPARATION_PLATE_CONCENTRATION
from thelma.automation.tools.iso.libcreation.base import \
    LibraryBaseLayoutConverter
from thelma.automation.tools.iso.poolcreation.base import \
    StockSampleCreationPosition
from thelma.automation.tools.iso.poolcreation.jobcreator import \
    StockSampleCreationIsoJobCreator
from thelma.automation.tools.iso.poolcreation.jobcreator import \
    StockSampleCreationIsoPopulator
from thelma.automation.utils.racksector import QuadrantIterator
from thelma.automation.utils.racksector import \
    get_sector_layouts_for_384_layout


__docformat__ = 'reStructuredText en'
__all__ = ['LibraryCreationIsoJobCreator',
           'LibraryCreationIsoPopulator',
           ]


class LibraryCreationIsoPopulator(StockSampleCreationIsoPopulator):
    #: The label pattern for preparation plates.
    PREP_PLATE_LABEL_PATTERN = '%s-%i-%inM-Q%i'
    #: The label pattern for aliquot plates.
    ALIQUOT_PLATE_LABEL_PATTERN = '%s-%i-%inM-%i'

    def __init__(self, iso_request, number_isos, **kw):
        StockSampleCreationIsoPopulator.__init__(self, iso_request,
                                                 number_isos, **kw)
        #: The library base layout.
        self.__base_layout = None
        #: Maps sector indices -> positions.
        self.__sector_positions = None

    def reset(self):
        StockSampleCreationIsoPopulator.reset(self)
        self.__base_layout = None
        self.__sector_positions = None

    @property
    def _base_layout(self):
        if self.__base_layout is None:
            lib = self.iso_request.molecule_design_library
            converter = LibraryBaseLayoutConverter(lib.rack_layout,
                                                   parent=self)
            self.__base_layout = converter.get_result()
        return self.__base_layout

    @property
    def _sector_positions(self):
        if self.__sector_positions is None:
            self.__sector_positions = \
                QuadrantIterator.sort_into_sectors(self._base_layout,
                                                   NUMBER_SECTORS)
        return self.__sector_positions

    def _create_iso_layout(self):
        layout = LibraryLayout.from_base_layout(self._base_layout)
        for positions in self._sector_positions.values():
            if not self._have_candidates:
                break
            for base_pos in positions:
                if not self._have_candidates:
                    break
                lib_cand = self._pool_candidates.pop(0)
                lib_pos = \
                    StockSampleCreationPosition(base_pos.rack_position,
                                                lib_cand.pool,
                                                lib_cand.get_tube_barcodes())
                layout.add_position(lib_pos)
        return layout

    def _populate_iso(self, iso, layout):
        StockSampleCreationIsoPopulator._populate_iso(self, iso, layout)
        # Create sector preparation plates.
        library_name = self.iso_request.label
        ir_specs_96 = get_reservoir_specs_standard_96()
        plate_specs_96 = get_rack_specs_from_reservoir_specs(ir_specs_96)
        ir_specs_384 = get_reservoir_specs_standard_384()
        plate_specs_384 = get_rack_specs_from_reservoir_specs(ir_specs_384)
        future_status = get_item_status_future()
        sec_layout_map = get_sector_layouts_for_384_layout(layout)
        # Create preparation plates.
        for sec_idx in range(NUMBER_SECTORS):
            if not sec_idx in sec_layout_map:
                continue
            # TODO: Move label creation to LABELS class.
            prep_label = self.PREP_PLATE_LABEL_PATTERN \
                                % (library_name,
                                   iso.layout_number,
                                   DEFAULT_PREPARATION_PLATE_CONCENTRATION,
                                   sec_idx + 1)
            prep_plate = plate_specs_96.create_rack(prep_label, future_status)
            sec_layout = sec_layout_map[sec_idx]
            iso.add_sector_preparation_plate(prep_plate, sec_idx,
                                             sec_layout.create_rack_layout())
        # Create aliquot plates.
        for i in range(self.iso_request.number_aliquots):
            # TODO: Move label creation to LABELS class.
            aliquot_label = self.ALIQUOT_PLATE_LABEL_PATTERN \
                                % (library_name,
                                   iso.layout_number,
                                   DEFAULT_ALIQUOT_PLATE_CONCENTRATION,
                                   i + 1)
            aliquot_plate = plate_specs_384.create_rack(aliquot_label,
                                                        future_status)
            iso.add_aliquot_plate(aliquot_plate)


class LibraryCreationIsoJobCreator(StockSampleCreationIsoJobCreator):
    _ISO_POPULATOR_CLASS = LibraryCreationIsoPopulator


