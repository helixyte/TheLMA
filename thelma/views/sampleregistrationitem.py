"""
"""
import json

from everest.mime import JsonMime
from everest.views.postcollection import PostCollectionView
from thelma.tools.stock.sampleregistration import SupplierSampleRegistrar
from pyramid.httpexceptions import HTTPCreated


__docformat__ = 'reStructuredText en'
__all__ = ['PostSupplierSampleRegistrationItemCollectionView',
           ]


class PostSupplierSampleRegistrationItemCollectionView(PostCollectionView):
    def _process_request_data(self, data):
        rpr = self._get_request_representer()
        reg_items = rpr.resource_from_data(data)
        kw = self.__extract_parameters(('rack_specs_name',
                                        'container_specs_name'))
        tool = SupplierSampleRegistrar([ri.get_entity() for ri in reg_items],
                                       **kw)
        tool.run()
        # Assemble return data.
        ss_data = []
        new_mdp_ids = set([mdp.id
                           for mdp
                           in tool.return_value['molecule_design_pools']])
        for ss in tool.return_value['stock_samples']:
            ss_data.append(
                    dict(tube_barcode=ss.container.barcode,
                         molecule_design_pool_id=ss.molecule_design_pool.id,
                         is_new_molecule_design_pool=
                                ss.molecule_design_pool.id in new_mdp_ids,
                         rack_barcode=ss.container.location.rack.barcode,
                         rack_position=ss.container.location.position.label,
                         volume=ss.volume,
                         concentration=ss.concentration,
                         supplier=ss.supplier.name
                         )
                           )
        # Prepare and return response.
        self.request.response.content_type = JsonMime.mime_type_string
        self.request.response.body = json.dumps(ss_data)
        self.request.response.status = self._status(HTTPCreated)
        return self.request.response

    def __extract_parameters(self, parameter_names):
        kw = {}
        prms = self.request.params
        for prm_name in parameter_names:
            prm_value = prms.get(prm_name, None)
            if not prm_value is None:
                kw[prm_name] = prm_value
        return kw
