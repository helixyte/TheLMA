"""
Trac tools dealing with ISO Trac tickets.

AAB, Mar 2012
"""
from StringIO import StringIO
from tractor import AttachmentWrapper
from tractor import create_wrapper_for_ticket_creation
from tractor import create_wrapper_for_ticket_update
from tractor.ticket import RESOLUTION_ATTRIBUTE_VALUES
from tractor.ticket import SEVERITY_ATTRIBUTE_VALUES
from tractor.ticket import STATUS_ATTRIBUTE_VALUES
from tractor.ticket import TYPE_ATTRIBUTE_VALUES

from thelma.automation.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.base import BaseTool
from thelma.automation.tools.stock.base import STOCKMANAGEMENT_USER
from thelma.automation.tracbase import BaseTracTool
from thelma.models.experiment import ExperimentMetadata
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import IsoRequest
from thelma.models.user import User


__docformat__ = 'reStructuredText en'

__all__ = ['IsoRequestTicketCreator',
           'IsoRequestTicketUpdateTool',
           'IsoRequestTicketDescriptionRemover',
           'IsoRequestTicketDescriptionUpdater',
           'IsoRequestTicketDescriptionBuilder',
           'IsoRequestTicketActivator',
           'IsoRequestTicketAccepter',
           'IsoRequestTicketReassigner']


class IsoRequestTicketCreator(BaseTracTool):
    """
    Creates an ISO request trac ticket for a new experiment metadata object.

    **Return Value:** ticket ID
    """
    NAME = 'ISO Request Ticket Creator'
    #: The value for the ticket summary (title).
    SUMMARY = 'Internal Sample Order Request'
    #: The description for the empty ticket.
    DESCRIPTION_TEMPLATE = 'Autogenerated ticket for experiment ' \
                           'metadata \'\'\'%s\'\'\' (type: %s).\n\n'
    #: The value for ticket type.
    TYPE = TYPE_ATTRIBUTE_VALUES.TASK
    #: The value for the ticket's severity.
    SEVERITY = SEVERITY_ATTRIBUTE_VALUES.NORMAL
    #: The value for the ticket's component.
    COMPONENT = 'Logistics'

    def __init__(self, requester, experiment_metadata, parent=None):
        """
        Constructor.

        :param experiment_metadata_label: The new experiment metadata.
        :type experiment_metadata_label:
            :class:`thelma.models.experiment.ExperimentMetadata`
        :param requester: The user who will be owner and reporter of the ticket.
        :type requester: :class:`thelma.models.user.User`
        """
        BaseTracTool.__init__(self, parent=parent)

        #: The user creating the experiment metadata is also reporter and
        #: and owner of the ticket.
        self.requester = requester
        #: The new experiment metadata.
        self.experiment_metadata = experiment_metadata
        #: The ticket wrapper storing the value applied to the ticket.
        self._ticket = None

    def reset(self):
        """
        Resets all value except for the instantiation arguments.
        """
        BaseTracTool.reset(self)
        self._ticket = None

    def get_ticket_id(self):
        """
        Sends a request and returns the ticket ID generated by the trac.
        """
        self.send_request()
        return self.return_value

    def send_request(self):
        """
        Prepares and sends the Trac ticket creation request.
        """
        self.reset()
        self.add_info('Create ISO request ticket ...')
        self.__check_input()
        if not self.has_errors():
            self.__create_ticket_wrapper()
        if not self.has_errors():
            self.__submit_request()

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input ...')

        self._check_input_class('requester', self.requester, User)
        self._check_input_class('experiment metadata',
                                self.experiment_metadata, ExperimentMetadata)

    def __create_ticket_wrapper(self):
        # Creates the ticket wrapper to be sent.
        self.add_debug('Create ticket wrapper ...')
        emt_name = \
            self.experiment_metadata.experiment_metadata_type.display_name
        description = self.DESCRIPTION_TEMPLATE \
                      % (self.experiment_metadata.label, emt_name)
        self._ticket = create_wrapper_for_ticket_creation(
                                summary=self.SUMMARY,
                                description=description,
                                reporter=self.requester.directory_user_id,
                                owner=self.requester.directory_user_id,
                                component=self.COMPONENT,
                                type=self.TYPE,
                                severity=self.SEVERITY)

    def __submit_request(self):
        # Submits the request to the trac.
        self.add_debug('Send request ...')
        kw = dict(notify=self.NOTIFY, ticket_wrapper=self._ticket)
        ticket_id = self._submit(self.tractor_api.create_ticket, kw)
        if not self.has_errors():
            self.return_value = ticket_id
            self.add_info('Ticket created (ID: %i).' % (ticket_id))
            self.was_successful = True


class IsoRequestTicketUpdateTool(BaseTracTool):
    """
    A super class for all ISO request ticket updating processes.

    **Return Value:** The updated ticket.
    """

    #: A comment for the update.
    BASE_COMMENT = None

    def __init__(self, id_providing_entity, parent=None):
        """
        Constructor.

        :param id_providing_entity: The entity providing the ticket ID.
        :type id_providing_entity:
            :class:`thelma.models.experiment.ExperimentMetadata` or
            :class:`thelma.models.iso.IsoRequest`
        """
        BaseTracTool.__init__(self, parent=parent)
        #: The experiment metadata or ISO request object the ticket belongs to.
        self.id_providing_entity = id_providing_entity
        #: The ticket ID.
        self._ticket_id = None
        #: The wrapper for the ticket update.
        self._update_wrapper = None
        #: A comment for the update. If the comment is not set, it will
        #: replaced by the :attr:`BASE_COMMENT`.
        self._comment = None

    def reset(self):
        """
        Resets all value except for the instantiation arguments.
        """
        BaseTracTool.reset(self)
        self._ticket_id = None
        self._update_wrapper = None
        self._comment = None

    def send_request(self):
        """
        Sends the update request.
        """
        self.reset()
        self.add_info('Start preparation ...')
        self._check_input()
        if not self.has_errors():
            self._set_ticket_id()
        if not self.has_errors():
            self._prepare_update_wrapper()
        if not self.has_errors():
            self._submit_request()

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        pass

    def _set_ticket_id(self):
        """
        Sets the ticket ID.
        """
        self.add_debug('Set ticket ID.')

        if isinstance(self.id_providing_entity, ExperimentMetadata):
            self._ticket_id = self.id_providing_entity.ticket_number
        elif isinstance(self.id_providing_entity, IsoRequest):
            self._ticket_id = self.id_providing_entity.experiment_metadata.\
                              ticket_number
        else:
            msg = 'Unknown ID-providing entity. The entity must either ' \
                  'be an ExperimentMetadata or an IsoRequest object ' \
                  '(obtained: %s).' \
                  % (self.id_providing_entity.__class__.__name__)
            self.add_error(msg)

        if not self.has_errors():
            self._check_input_class('ticket ID', self._ticket_id, int)

    def _prepare_update_wrapper(self):
        """
        Creates the ticket wrapper containing the update information.
        You can also use this method to set the :attr:`_comment.`
        """
        self.add_error('Abstract method: _prepare_update_wrapper()')

    def _submit_request(self):
        """
        Submits the request.
        """
        self.add_debug('Send request ...')

        if self._comment is None: self._comment = self.BASE_COMMENT

        kw = dict(ticket_wrapper=self._update_wrapper, comment=self._comment,
                  notify=self.NOTIFY)
        updated_ticket = self._submit(self.tractor_api.update_ticket, kw)
        if not self.has_errors():
            self.return_value = updated_ticket
            self.add_info('Ticket %i has been updated.' % (self._ticket_id))
            self.was_successful = True


class IsoRequestTicketDescriptionRemover(IsoRequestTicketUpdateTool):
    """
    Removes the description of an ISO request ticket after change of the
    number of replicates or the experiment metadata type.

    **Return Value:** The updated ticket.
    """
    NAME = 'ISO Request Ticket Description Remover'

    #: Comment template. The first place holder will contain the attribute
    #: name, the second the new value.
    BASE_COMMENT = 'The %s of the experiment metadata has been changed to ' \
                   '"%s".'
    #: The last line of the comment explaining that all type-dependend data
    #: has been removed from the ticket.
    REMOVE_COMMENT = ' All type-dependent data (incl. experiment design and ' \
                     'ISO request data) has been removed.'

    def __init__(self, experiment_metadata, changed_num_replicates,
                 changed_em_type, parent=None):
        """
        Constructor.

        :param bool changed_num_replicates: Flag indicating if the number of
            replicates has changed.
        :param bool changed_em_type: Flag indicating if the experiment
            metadata type has changed.
        """
        IsoRequestTicketUpdateTool.__init__(self, experiment_metadata,
                                            parent=parent)
        #: The new experiment metadata type (if the type has changed).
        self.changed_em_type = changed_em_type
        #: The new number of replicates (if the number has changed).
        self.changed_num_replicates = changed_num_replicates

    def _check_input(self):
        self._check_input_class('"changed experiment metadata type" flag',
                                self.changed_em_type, bool)
        self._check_input_class('"changed number replicates type" flag',
                                self.changed_num_replicates, bool)

    def _prepare_update_wrapper(self):
        """
        The description is reverted to the state directly after creation,
        whereas the comment lists the changed elements.
        """
        em_type = self.id_providing_entity.experiment_metadata_type
        description = IsoRequestTicketCreator.DESCRIPTION_TEMPLATE % (
                    self.id_providing_entity.label, em_type.display_name)
        self._comment = ''
        if self.changed_em_type:
            comment_em = self.BASE_COMMENT % ('experiment metadata type',
                                              em_type.display_name)
            self._comment += comment_em
        if self.changed_num_replicates:
            comment_nr = self.BASE_COMMENT % ('number_replicates',
                                    self.id_providing_entity.number_replicates)
            self._comment += comment_nr
        if len(self._comment) < 1:
            msg = 'Neither the number of replicates nor the experiment ' \
                  'metadata type have changed. The ticket description does ' \
                  'not need to be removed.'
            self.add_error(msg)
        else:
            self._comment += self.REMOVE_COMMENT
            self._update_wrapper = create_wrapper_for_ticket_update(
                                        ticket_id=self._ticket_id,
                                        description=description)


class IsoRequestTicketDescriptionUpdater(IsoRequestTicketUpdateTool):
    """
    Updates an ISO request ticket (in case of changes that have not been
    caused by a metadata file upload).

    **Return Value:** The updated ticket.
    """
    NAME = 'ISO Request Ticket Updater'
    #: A comment for the change.
    BASE_COMMENT = 'Experiment metadata update.'

    def __init__(self, experiment_metadata, experiment_metadata_link,
                 iso_request_link, parent=None):
        """
        Constructor.

        :param str experiment_metadata_link: Link to the experiment metadata
            in TheLMA.
        :param str iso_request_link: Link to the ISO request in TheLMA.
        """
        IsoRequestTicketUpdateTool.__init__(self, experiment_metadata,
                                            parent=parent)
        #: Link to the experiment metadata in TheLMA.
        self.experiment_metadata_link = experiment_metadata_link
        #: Link to the ISO request in TheLMA.
        self.iso_request_link = iso_request_link
        #: The value for the new ticket description.
        self.__ticket_description = None

    def reset(self):
        """
        Resets all value except for the instantiation arguments.
        """
        IsoRequestTicketUpdateTool.reset(self)
        self.__ticket_description = None

    def _check_input(self):
        """
        Checks the initialization values.
        """
        self._check_input_class('experiment metadata link',
                                self.experiment_metadata_link, basestring)
        self._check_input_class('ISO request link',
                                self.iso_request_link, basestring)

    def _prepare_update_wrapper(self):
        """
        Creates the ticket wrapper containing the update information.
        """
        if not self.has_errors(): self.__generate_ticket_description()
        if not self.has_errors():
            self._update_wrapper = create_wrapper_for_ticket_update(
                                        ticket_id=self._ticket_id,
                                        description=self.__ticket_description)

    def __generate_ticket_description(self):
        """
        Generates a new ticket description.
        """
        desc_builder = IsoRequestTicketDescriptionBuilder(
                                            self.id_providing_entity,
                                            self.experiment_metadata_link,
                                            self.iso_request_link,
                                            parent=self)
        self.__ticket_description = desc_builder.get_result()

        if self.__ticket_description is None:
            msg = 'Error when trying to generate ticket description.'
            self.add_error(msg)


class IsoRequestTicketDescriptionBuilder(BaseTool):
    """
    Creates or updates descriptions for ISO request tickets.
    """
    NAME = 'ISO Ticket Description Builder'
    #: The description for the empty ticket.
    HEAD_LINE = "Autogenerated Ticket for experiment metadata '''%s'''.\n\n"
    #: The title for the delivery date row.
    DELIVERY_DATE_TITLE = 'Delivery Date'
    #: The titles for the comment row.
    COMMENT_TITLE = 'Comment'
    #: The title for the project leader row.
    PROJECT_LEADER_TITLE = 'Project Leader'
    #: The title for the project row.
    PROJECT_TITLE = 'Project'
    #: The title for subproject row.
    SUBPROJECT_TITLE = 'Subproject'
    #: The title for the plate set label row.
    PLATE_SET_LABEL_TITLE = 'Plate Set Label'
    #: The title for the requester row.
    REQUESTER_TITLE = 'Requester'
    #: The title for the number of plates row.
    NUMBER_PLATES_TITLE = 'Number of Plates'
    #: The title for the number of aliquots.
    NUMBER_ALIQUOTS_TITLE = 'Number of Aliquots'
    #: The title for the aliquot plate rack shape.
    ISO_RACK_SHAPE_TITLE = 'ISO Plate Format'
    #: The title for the ISO plate specs row.
    ISO_RACK_SPECS_TITLE = 'ISO Plate Specs'
    #: The title for the experiment cell plate rack shape.
    EXP_RACK_SHAPE_TITLE = 'Cell Plate Format'
    #: The title for the experiment type.
    EXPERIMENT_TYPE_TITLE = 'Experiment Type'
    #: The title for the robot support flag.
    ROBOT_SUPPORT_TITLE = 'Robot support (mastermix)'
    #: Placeholder for unknown values.
    UNKNOWN_MARKER = 'not specified'
    #: These tables fields always occur (regardless of the experiment type).
    COMMON_TITLES = [EXPERIMENT_TYPE_TITLE, PROJECT_TITLE, PROJECT_LEADER_TITLE,
                     SUBPROJECT_TITLE]
    #: These table fields occur, if there is an ISO request at the experiment
    #: metadata.
    ISO_REQUEST_TITLES = [REQUESTER_TITLE, PLATE_SET_LABEL_TITLE,
                          NUMBER_PLATES_TITLE, NUMBER_ALIQUOTS_TITLE,
                          ISO_RACK_SHAPE_TITLE, ISO_RACK_SPECS_TITLE,
                          DELIVERY_DATE_TITLE, COMMENT_TITLE]
    #: These table fields occur if there is an experiment design at the
    #: experiment metadata.
    EXPERIMENT_DESIGN_TITLES = [EXP_RACK_SHAPE_TITLE, ROBOT_SUPPORT_TITLE]
    #: The template for each table row.
    BASE_TABLE_ROW = "|| '''%s: '''||%s||\n"
    #: The character used to generated the table field borders.
    BORDER_CHAR = '||'
    #: The link section of the description.
    LINK_SECTION = 'Link to experiment metadata:\n %s\n\n' \
                   'Link to ISO Request: \n %s \n\n'

    def __init__(self, experiment_metadata, experiment_metadata_link,
                 iso_request_link, parent=None):
        """
        Constructor.

        :param experiment_metadata: The update experiment metadata.
        :type experiment_metadata:
            :class:`thelma.models.experiment.ExperimentMetadata`
        :param str experiment_metadata_link: Link to the experiment metadata
            in TheLMA.
        :param str iso_request_link: Link to the ISO request in TheLMA.
        """
        BaseTool.__init__(self, parent=parent)
        #: The experiment metadata object the ticket belongs to.
        self.experiment_metadata = experiment_metadata
        #: Link to the experiment metadata in TheLMA.
        self.experiment_metadata_link = experiment_metadata_link
        #: Link to the ISO request in TheLMA.
        self.iso_request_link = iso_request_link
        #: The completed table part of the description.
        self.__wiki_table = None

    def reset(self):
        """
        Resets all attributes except for the initialization values.
        """
        BaseTool.reset(self)
        self.__wiki_table = None

    def run(self):
        self.reset()
        self.add_info('Build description ...')
        self.__check_input()
        if not self.has_errors():
            self.__build_wiki_table()
        if not self.has_errors():
            self.__assemble_description()

    def __check_input(self):
        # Checks the initialization values.
        self.add_debug('Check input ...')
        self._check_input_class('experiment metadata', self.experiment_metadata,
                                ExperimentMetadata)
        self._check_input_class('experiment metadata link',
                                self.experiment_metadata_link, basestring)
        self._check_input_class('ISO request link',
                                self.iso_request_link, basestring)

    def __build_wiki_table(self):
        # Builds the table for the wiki.
        self.__wiki_table = ''
        table_values = self.__collect_table_values()
        titles = self.COMMON_TITLES + self.EXPERIMENT_DESIGN_TITLES \
                 + self.ISO_REQUEST_TITLES
        for title in titles:
            if not table_values.has_key(title):
                continue
            value = table_values[title]
            table_line = self.BASE_TABLE_ROW % (title, value)
            self.__wiki_table += table_line
        self.__wiki_table += '\n\n'

    def __collect_table_values(self):
        # Generates a dictionary for the table values. Not all possible table
        # fields must occur.
        table_values = dict()
        # common values
        table_values[self.EXPERIMENT_TYPE_TITLE] = self.experiment_metadata.\
                                        experiment_metadata_type.display_name
        subproject = self.experiment_metadata.subproject
        table_values[self.SUBPROJECT_TITLE] = subproject.label
        project = subproject.project
        table_values[self.PROJECT_TITLE] = project.label
        project_leader = project.leader
        table_values[self.PROJECT_LEADER_TITLE] = project_leader.username
        # experiment design values
        experiment_design = self.experiment_metadata.experiment_design
        if not experiment_design is None:
            shape_name = self.experiment_metadata.experiment_design.\
                         rack_shape.name
            table_values[self.EXP_RACK_SHAPE_TITLE] = shape_name
            self.__set_robot_support_value(table_values)
        #: ISO request values
        iso_request = self.experiment_metadata.lab_iso_request
        if not iso_request is None:
            requester = iso_request.requester
            table_values[self.REQUESTER_TITLE] = requester.username
            table_values[self.NUMBER_PLATES_TITLE] = \
                                    '%i' % (iso_request.expected_number_isos)
            table_values[self.NUMBER_ALIQUOTS_TITLE] = \
                                    '%i' % (iso_request.number_aliquots)
            table_values[self.PLATE_SET_LABEL_TITLE] = \
                                    str(iso_request.label)
            del_date = iso_request.delivery_date
            if del_date:
                del_date_value = del_date.strftime("%a %b %d %Y")
            else:
                del_date_value = self.UNKNOWN_MARKER
            table_values[self.DELIVERY_DATE_TITLE] = del_date_value

            shape_name = iso_request.rack_layout.shape.name
            table_values[self.ISO_RACK_SHAPE_TITLE] = shape_name
            iso_plate_specs = iso_request.iso_plate_reservoir_specs
            table_values[self.ISO_RACK_SPECS_TITLE] = iso_plate_specs.name
            comment_value = self.experiment_metadata.lab_iso_request.comment
            if comment_value is None:
                comment_value = ' '
            table_values[self.COMMENT_TITLE] = comment_value
        return table_values

    def __set_robot_support_value(self, table_values):
        # The robot-support is a little harder o set. Some experiment types
        # do not offer robot-support at all, some enforce it and in some it
        # is optional (for these, the availablity can be retrieved from the
        # length of the experiment design worklist series).
        em_type = self.experiment_metadata.experiment_metadata_type
        design_series = self.experiment_metadata.experiment_design.\
                        worklist_series
        if design_series is None:
            mastermix_support = 'no'
        elif em_type.id == EXPERIMENT_SCENARIOS.OPTIMISATION:
            if len(design_series) == 2:
                mastermix_support = 'yes'
            else:
                mastermix_support = 'no'
        elif em_type.id == EXPERIMENT_SCENARIOS.SCREENING:
            if len(design_series) == 4:
                mastermix_support = 'yes'
            else:
                mastermix_support = 'no'
        elif em_type.id == EXPERIMENT_SCENARIOS.LIBRARY:
            mastermix_support = 'yes'
        table_values[self.ROBOT_SUPPORT_TITLE] = mastermix_support

    def __assemble_description(self):
        # Assembles the description.
        desc = ''
        head_line = self.HEAD_LINE % (self.experiment_metadata.label)
        desc += head_line
        desc += self.__wiki_table
        link_section = self.LINK_SECTION % (self.experiment_metadata_link,
                                            self.iso_request_link)
        desc += link_section
        self.return_value = desc


class IsoRequestTicketActivator(IsoRequestTicketUpdateTool):
    """
    Assigns a ticket to the stock management.

    **Return Value:** The updated ticket.
    """
    NAME = 'ISO Request Ticket Activator'
    #: A comment for the change.
    BASE_COMMENT = 'The ticket has been assigned to the stock management.'

    def _prepare_update_wrapper(self):
        """
        Creates the ticket wrapper containing the update information.
        """
        self._update_wrapper = create_wrapper_for_ticket_update(
                                            ticket_id=self._ticket_id,
                                            owner=STOCKMANAGEMENT_USER)


class IsoRequestTicketAccepter(IsoRequestTicketUpdateTool):
    """
    Assigns an ISO request ticket to a particular member of the stock
    management.

    **Return Value:** The updated ticket.
    """
    NAME = 'ISO Request Ticket Accepter'
    #: A comment for the change.
    BASE_COMMENT = 'The ticket was accepted by %s.'

    def __init__(self, iso_request, username, parent=None):
        """
        Constructor.

        :param str username: Name of the user accepting the ticket.
        """
        IsoRequestTicketUpdateTool.__init__(self, iso_request, parent=parent)
        #: The user name of the user who has accepted the ticket.
        self.username = username

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        self._check_input_class('user name', self.username, basestring)

    def _prepare_update_wrapper(self):
        """
        Creates the ticket wrapper containing the update information.
        """
        self._update_wrapper = create_wrapper_for_ticket_update(
                                ticket_id=self._ticket_id,
                                owner=self.username,
                                cc=STOCKMANAGEMENT_USER)
        self._comment = self.BASE_COMMENT % (self.username)


class IsoRequestTicketReassigner(IsoRequestTicketUpdateTool):
    """
    Assigns an ISO request ticket back to requester and optionally closes
    the ticket.

    **Return Value:** The updated ticket, the comment and the generated file
        stream.
    """
    NAME = 'ISO Request Ticket Reassigner'
    BASE_COMMENT = 'The ticket has been assigned back to the requester (%s).'
    #: The completed remark.
    COMPLETED_TEXT = 'The ISO request has been completed.'
    #: In case of completion there might molecule design IDs which have
    #: not been added to an ISO.
    MISSING_POOLS_ADDITION = '\n\nAttention! There are some sample molecule ' \
        'design pools left which have not been used in any ISO: %s.'
    #: The name for the file with the missing molecule designs.
    MISSING_POOLS_FILE_NAME = 'missing_molecule_design_pools.csv'
    #: The file description for the missing molecule design file.
    MISSING_POOLS_DESCRIPTION = 'Floating molecule design pools which have ' \
                            'not been added to at least 1 completed ISO.'

    def __init__(self, iso_request, completed=True, parent=None):
        """
        Constructor.

        :param iso_request: The ISO request to be accepted.
        :type iso_request: :class:`thelma.models.iso.IsoRequest`
        :param bool completed: Flag indicating if the ISO was completed.
        """
        IsoRequestTicketUpdateTool.__init__(self, iso_request, parent=parent)
        #: Indicates whether the ISO was completed.
        self.completed = completed
        #: If there are molecule design pools left (in case of completion) an
        #: additional file is uploaded.
        self.__missing_pools_stream = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        IsoRequestTicketUpdateTool.reset(self)
        self.__missing_pools_stream = None

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        self._check_input_class('completed flag', self.completed, bool)

    def _prepare_update_wrapper(self):
        """
        Creates the ticket wrapper containing the update information.
        In addition, it assembles the comment.
        """
        reporter = self.id_providing_entity.requester.directory_user_id
        project_leader = self.id_providing_entity.experiment_metadata.\
                         subproject.project.leader.directory_user_id
        self._update_wrapper = create_wrapper_for_ticket_update(owner=reporter,
                            cc=project_leader, ticket_id=self._ticket_id)
        comment = self.BASE_COMMENT % (reporter)
        if self.completed:
            self._comment = '%s %s' % (comment, self.COMPLETED_TEXT)
            self._update_wrapper.status = STATUS_ATTRIBUTE_VALUES.CLOSED
            self._update_wrapper.resolution = RESOLUTION_ATTRIBUTE_VALUES.FIXED
            self.__add_missing_molecule_design_pools()
        else:
            self._comment = comment

    def __add_missing_molecule_design_pools(self):
        # Finds missing molecule design pools, add them to the comment and
        # creates a file if necessary.
        missing_pools = self.__find_missing_molecule_design_pools()
        if len(missing_pools) > 0:
            missing_pool_str = ', '.join(missing_pools)
            comment_addition = self.MISSING_POOLS_ADDITION % (missing_pool_str)
            self._comment += comment_addition
            self.__missing_pools_stream = StringIO()
            for pool_id in missing_pools:
                self.__missing_pools_stream.write('%s\n' % (pool_id))
            self.__missing_pools_stream.seek(0)

    def __find_missing_molecule_design_pools(self):
        # Finds missing molecule design pools.
        self.add_debug('Find missing molecule design pools ...')
        pool_set = self.id_providing_entity \
                       .experiment_metadata.molecule_design_pool_set
        if pool_set is None:
            result = []
        elif len(pool_set) < 1:
            result = []
        else:
            used_pool_ids = set()
            for iso in self.id_providing_entity.isos:
                if not iso.status == ISO_STATUS.DONE:
                    continue
                for md_pool in iso.molecule_design_pool_set:
                    used_pool_ids.add(md_pool.id)
            missing_pools = []
            for md_pool in pool_set:
                if not md_pool.id in used_pool_ids:
                    missing_pools.append(md_pool.id)
            missing_pools.sort()
            str_pools = [] # string concatenation requires strings
            for pool_id in missing_pools:
                str_pools.append('%i' % (pool_id))
            result = str_pools
        return result

    def _submit_request(self):
        """
        Submits the request.
        """
        self.add_debug('Send request ...')
        if self._comment is None:
            self._comment = self.BASE_COMMENT
        kw1 = dict(ticket_wrapper=self._update_wrapper, comment=self._comment,
                   notify=self.NOTIFY)
        updated_ticket = self._submit(self.tractor_api.update_ticket, kw1)
        if not self.__missing_pools_stream is None and not self.has_errors():
            attachment_wrapper = AttachmentWrapper(
                                content=self.__missing_pools_stream,
                                file_name=self.MISSING_POOLS_FILE_NAME,
                                description=self.MISSING_POOLS_DESCRIPTION)
            kw2 = dict(ticket_id=self._ticket_id, attachment=attachment_wrapper,
                       replace_existing=False)
            try:
                self._submit(self.tractor_api.add_attachment, kw2)
            finally:
                self.__missing_pools_stream.seek(0)
        if not self.has_errors():
            self.return_value = updated_ticket, self._comment, \
                                self.__missing_pools_stream
            self.add_info('Ticket %i has been updated.' % (self._ticket_id))
            self.was_successful = True


class IsoRequestTicketReopener(IsoRequestTicketUpdateTool):
    """
    Reopens an ISO request ticket and assigns it to the person who has
    requested the reopening.

    **Return Value:** The updated ticket.
    """
    NAME = 'ISO Request Ticket Reopener'
    BASE_COMMENT = 'The ticket has been reopened by %s.'

    def __init__(self, iso_request, username, parent=None):
        """
        Constructor.

        :param str username: The name of the user reopening the ticket.
        """
        IsoRequestTicketUpdateTool.__init__(self, iso_request, parent=parent)

        #: The name of the user the ticket shall be assigned to.
        self.username = username

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        self._check_input_class('user name', self.username, basestring)

    def _prepare_update_wrapper(self):
        """
        Creates the ticket wrapper containing the update information.
        In addition, it assembles the comment.
        """
        self._comment = self.BASE_COMMENT % (self.username)
        self._update_wrapper = create_wrapper_for_ticket_update(
                            ticket_id=self._ticket_id,
                            cc=STOCKMANAGEMENT_USER,
                            owner=self.username,
                            status=STATUS_ATTRIBUTE_VALUES.REOPENED)
