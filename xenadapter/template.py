import json

from authentication import BasicAuthenticator
from handlers.graphql.types.template import GTemplate, TemplateActions
from .abstractvm import AbstractVM
from exc import *
import XenAPI
from .vm import VM
from xenadapter.helpers import use_logger


class Template(AbstractVM):
    EVENT_CLASSES = ['vm']
    ALLOW_EMPTY_OTHERCONFIG = True
    VMEMPEROR_TEMPLATE_PREFIX = 'vm/data/vmemperor/template'
    db_table_name = 'tmpls'
    GraphQLType = GTemplate
    Actions = TemplateActions

    @classmethod
    def filter_record(cls, xen, record, ref):
        return record['is_a_template'] and not record['is_a_snapshot']

    @classmethod
    def process_record(cls, xen, ref, record):
        '''
        Contary to parent method, this method can return many records as one XenServer template may convert to many
        VMEmperor templates
        :param ref:
        :param record:
        :return:
        '''
        new_rec = super().process_record(xen, ref, record)

        if record['HVM_boot_policy'] == '':
            new_rec['hvm'] = False
        else:
            new_rec['hvm'] = True

        new_rec['enabled'] = cls.is_enabled(record)
        new_rec['is_default_template'] = 'default_template' in record['other_config'] and\
                                         record['other_config']['default_template']
        if new_rec['is_default_template']:
            new_rec['_blocked_operations_'].append("destroy")

        #read xenstore data
        xenstore_data = record['xenstore_data']
        if not cls.VMEMPEROR_TEMPLATE_PREFIX in xenstore_data:
            if new_rec['hvm'] is False:
                if 'os_kind' in record['other_config']:
                    new_rec['os_kind'] = record['other_config']['os_kind']
                else:
                    if 'reference_label' in record:
                        for OS in 'ubuntu','centos', 'debian':
                            if record['reference_label'].startswith(OS):
                                new_rec['os_kind'] = OS
                                break

            return new_rec

        template_settings = json.load(xenstore_data[cls.VMEMPEROR_TEMPLATE_PREFIX])
        new_rec['os_kind'] = template_settings['os_kind']
        return new_rec


    @classmethod
    def get_access_data(cls, record,  new_rec, ref):
        if cls.is_enabled(record):
            return super().get_access_data(record, new_rec, ref)
        else:
            return {}

    @classmethod
    def is_enabled(cls, record):
        return 'vmemperor' in record['tags']


    @use_logger
    def clone(self, name_label):
        try:
            new_vm_ref = self.__getattr__('clone')(name_label)
            vm = VM(self.xen, new_vm_ref)
            self.log.info(f"New VM is created: ref:{vm.ref}, name_label: {name_label}")
            return vm
        except XenAPI.Failure as f:
            raise XenAdapterAPIError(self.log, f"Failed to clone template: {f.details}")

    @use_logger
    def set_enabled(self, enabled):
        '''
        Adds/removes tag 'vmemperor'
        :param enabled:
        :return:
        '''
        try:
            if enabled:
                self.add_tags('vmemperor')
                self.log.info(f"enabled")
            else:
                self.remove_tags('vmemperor')
                self.log.info(f"disabled")
        except XenAPI.Failure as f:
            raise XenAdapterAPIError(self.log, f"Failed to {'enable' if enabled else 'disable'} template: {f.details}")


