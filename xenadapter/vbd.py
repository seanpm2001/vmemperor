from xenadapter.xenobject import XenObject

from rethinkdb import RethinkDB
r = RethinkDB()

class VBD(XenObject):
    api_class = 'VBD'
    EVENT_CLASSES = ['vbd']
    db_table_name = 'vbds'


    def delete(self) -> bool:
        '''

        :return: False if unable to unplug device from running VM
        '''
        from .vm import VM
        vm = VM(self.xen, ref=self.get_VM())

        if vm.get_power_state() == 'Running' and self.get_unpluggable():
            self.unplug()
        else:
            return False

        self.destroy()
        return True
