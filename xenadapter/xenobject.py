import XenAPI
from exc import *
from authentication import BasicAuthenticator
import traceback

class XenObjectMeta(type):
    def __getattr__(cls, item):
        if item[0] == '_':
            item = item[1:]
        def method(xen, *args, **kwargs):

            if not hasattr(cls, 'api_class'):
                raise XenAdapterArgumentError(xen.log, "api_class not specified for XenObject")

            api_class = getattr(cls, 'api_class')
            api = getattr(xen.api, api_class)
            attr = getattr(api, item)
            try:
                return attr(*args, **kwargs)
            except XenAPI.Failure as f:
                raise XenAdapterAPIError(xen.log, "Failed to execute static method %s::%s: Error details: %s"
                                         % (api_class, item, f.details ))
        return method




class XenObject(metaclass=XenObjectMeta):

    def __init__(self, auth : BasicAuthenticator,  uuid=None, ref=None):
        '''Set  self.auth.xen_api_class to xen.api.something before calling this'''
        self.auth = auth
        # if not isinstance(xen, XenAdapter):
        #          raise AttributeError("No XenAdapter specified")
        self.log = self.auth.xen.log
        self.xen = self.auth.xen

        if uuid:
            self.uuid = uuid
            try:
                getattr(self, 'ref') #uuid check
            except XenAPI.Failure as f:
                raise  XenAdapterAPIError(auth.xen.log, "Failed to initialize object of type %s with UUID %s: %s" %
                                          (self.__class__.__name__, self.uuid, f.details))

        elif ref:
            self.ref = ref
        else:
            raise AttributeError("Not uuid nor ref not specified")



        self.access_prefix = 'vm-data/vmemperor/access'



    def check_access(self,  action):
        return True

    def manage_actions(self, action,  revoke=False, user=None, group=None, force=False):
        pass

    @classmethod
    def process_event(cls, xen, event, db):
        '''
        Make changes to a RethinkDB-based cache, processing a XenServer event
        :param xen: XenAdapter which generated event
        :param event: event dict
        :param db: rethinkdb DB
        :return: nothing
        '''
        pass

    @classmethod
    def process_record(cls, xen, record):
        '''
        Used by init_db. Should return dict with info that is supposed to be stored in DB
        :param xen:
        :param record:
        :return: dict suitable for document-oriented DB
        : default: return record as-is
        '''
        return record

    @classmethod
    def filter_record(cls, record):
        '''
        Used by get_all_records (my implementation)
        :param record: record from get_all_records (pure XenAPI method)
        :return: true if record is suitable for this class
        '''
        return True

    @classmethod
    def get_all_records(cls, xen):
        method = getattr(cls, '_get_all_records')
        return {k: v for k, v in method(xen).items()
                if cls.filter_record(v)}

    @classmethod
    def init_db(cls, xen):
        return [cls.process_record(xen, record) for record in cls.get_all_records(xen).values()]



    def __getattr__(self, name):
        api = getattr(self.xen.api, self.api_class)
        if name == 'uuid': #ленивое вычисление uuid по ref
            self.uuid = api.get_uuid(self.ref)
            return self.uuid
        elif name == 'ref': #ленивое вычисление ref по uuid
            self.ref = api.get_by_uuid(self.uuid)
            return self.ref



        attr = getattr(api, name)
        return lambda *args, **kwargs : attr(self.ref, *args, **kwargs)


class ACLXenObject(XenObject):
    def get_access_path(self, username=None, is_group=False):
        return '{3}/{0}/{1}/{2}'.format(self.auth.__class__.__name__,
                                                               'groups' if is_group else 'users',
                                                        username, self.access_prefix)

    ALLOW_EMPTY_XENSTORE = False # Empty xenstore for some objects might treat them as
    def check_access(self,  action):
        '''
        Check if it's possible to do 'action' with specified VM
        :param action: action to perform
        for 'VM'  these are

        - launch: can start/stop vm
        - destroy: can destroy vm
        - attach: can attach/detach disk/network interfaces
        :return: True if access granted, False if access denied, None if no info
        '''
        #if self.auth == 'root':
#            return True
        self.log.info("Checking %s %s rights for user %s: action %s" % (self.__class__.__name__, self.uuid, self.auth.get_id(), action))

        username = self.get_access_path(self.auth.get_id(), False)
        xenstore_data = self.get_xenstore_data()
        if not xenstore_data:
            if self.ALLOW_EMPTY_XENSTORE:
                return True
            raise XenAdapterUnauthorizedActionException(self.log,
                                                    "Unauthorized attempt (no info on access rights): needs privilege '%s', call stack: %s"
                                                    % (action, traceback.format_stack()))



        actionlist = xenstore_data[username].split(';') if username in xenstore_data else None
        if actionlist and (action in actionlist or 'all' in actionlist):
            self.log.info('User %s is allowed to perform action %s on %s %s' % (self.auth.get_id(), action, self.__class__.__name__, self.uuid))
            return True
        else:
            for group in self.auth.get_user_groups():
                groupname = self.get_access_path(group, True)
                actionlist = xenstore_data[groupname].split(';') if groupname in xenstore_data else None
                if actionlist and any(('all' in actionlist, action in actionlist)):
                    self.log.info('User %s via group %s is allowed to perform action %s on %s %s' % (self.auth.get_id(), group, action, self.__class__.__name__,  self.__uuid__))
                    return True

            raise XenAdapterUnauthorizedActionException(self.log,
                                                        "Unauthorized attempt: needs privilege '%s', call stack: %s"
                                                        % (action, traceback.format_stack()))

    def manage_actions(self, action,  revoke=False, user=None, group=None, force=False):
        '''
        Changes action list for a Xen object
        :param action:
        :param revoke:
        :param user: User ID as returned from authenticator.get_id()
        :param group:
        :param force: Change actionlist even if user do not have sufficient permissions. Used by CreateVM
        :return:
        '''

        if all((user,group)) or not any((user, group)):
            raise XenAdapterArgumentError(self.log, 'Specify user or group for XenObject::manage_actions')



        if user:
            real_name = self.get_access_path(user, False)
        elif group:
            real_name = self.get_access_path(group, True)

        if force or self.check_rights(action):
            xenstore_data = self.get_xenstore_data()
            if real_name in xenstore_data:
                actionlist = xenstore_data[real_name].split(';')
            else:
                actionlist = []

            if revoke:
                if action in actionlist:
                    actionlist.remove(action)
            else:
                if action not in actionlist:
                    actionlist.append(action)

            actions = ';'.join(actionlist)

            xenstore_data[real_name] = actions

            self.set_xenstore_data(xenstore_data)
