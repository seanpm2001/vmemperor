from exc import *


class GenericOS:
    '''
    A class that generates kernel boot arguments string for various Linux distributions
    '''

    def __init__(self):
        self.dhcp = True
        self.other_config = {}

    def pv_args(self) -> str:
        '''
        Obtain pv_args - kernel parameters for paravirtualized VM
        :return:
        '''

    def hvm_args(self) -> str:
        '''
        Obtain hvm_args - whatever that might be
        :return:
        '''

    def set_install_url(self, url):
        '''
        Set install URL to other_config field
        :param url:
        :return:
        '''

    def set_scenario(self, url):
        raise NotImplementedError

    def set_kickstart(self, url):
        return 'ks={0}'.format(url)

    def set_preseed(self, url):
        return 'preseed/url={0}'.format(url)

    def set_hostname(self, hostname):
        self.hostname = hostname

    def set_network_parameters(self, ip=None, gw=None, netmask=None, dns1=None, dns2=None):
        if not ip:
            self.dhcp = True
            self.ip = None
        else:
            if not gw:
                raise XenAdapterArgumentError(self, "Network configuration: IP has been specified, missing gateway")
            if not netmask:
                raise XenAdapterArgumentError(self, "Network configuration: IP has been specified, missing netmask")
            ip_string = " ip=%s::%s:%s" % (ip, gw, netmask)

            if dns1:
                ip_string = ip_string + ":::off:%s" % dns1
                if dns2:
                    ip_string = ip_string + ":%s" % dns2

            self.ip = ip_string
        self.dhcp = False

    def set_os_kind(self, os_kind):
        pass

class DebianOS(GenericOS):
    '''
    OS-specific parameters for Ubuntu
    '''

    def set_scenario(self, url):
        self.scenario = self.set_preseed(url)
        # self.scenario = self.set_kickstart(url)

    def pv_args(self):
        if self.dhcp:
            self.ip = "netcfg/disable_dhcp=false"
        return "auto=true console=hvc0 debian-installer/locale=en_US console-setup/layoutcode=us console-setup/ask_detect=false interface=eth0 %s netcfg/get_hostname=%s %s --" % (
            self.ip, self.hostname, self.scenario)

    def set_network_parameters(self, ip=None, gw=None, netmask=None, dns1=None, dns2=None):
        if not ip:
            self.dhcp = True
            self.ip = None
        else:
            if not gw:
                raise XenAdapterArgumentError(self, "Network configuration: IP has been specified, missing gateway")
            if not netmask:
                raise XenAdapterArgumentError(self, "Network configuration: IP has been specified, missing netmask")

            ip_string = " ipv6.disable=1 netcfg/disable_autoconfig=true netcfg/use_autoconfig=false  netcfg/confirm_static=true netcfg/get_ipaddress=%s netcfg/get_gateway=%s netcfg/get_netmask=%s netcfg/get_nameservers=%s netcfg/get_domain=vmemperor" % (
                ip, gw, netmask, dns1)

            self.ip = ip_string
            self.dhcp = False

    def get_release(self, num):
        releases = {
            '7': 'wheezy',
            '8': 'jessie',
            '9': 'stretch'
        }
        if str(num) in releases.keys():
            return releases[str(num)]
        if num in releases.values():
            return num
        return None

    def set_os_kind(self, os_kind: str):
        try:
            debian_release = self.get_release(os_kind.split()[1])
            self.other_config['debian-release'] = debian_release
        except IndexError:
            pass


    def set_install_url(self, url):
        if not url:
            url = 'http://ftp.ru.debian.org/debian/'

        self.other_config['install-repository'] = url
        self.other_config['default-mirror'] = url

class UbuntuOS(DebianOS):
    '''
    OS-specific parameters for Ubuntu
    '''
    def get_release(self, num):
        releases = {
            '12.04': 'precise',
            '14.04': 'trusty',
            '14.10': 'utopic',
            '15.04': 'vivid',
            '15.10': 'willy',
            '16.04': 'xenial',
            '16.10': 'yakkety',
            '17.04': 'zesty',
            '17.10': 'artful',
        }
        if num in releases.keys():
            return releases[num]
        if num in releases.values():
            return num
        return None


    def set_install_url(self, url):
        if not url:
            url = 'http://archive.ubuntu.com/ubuntu/'
        super().set_install_url(url)





class CentOS(GenericOS):
    """
    OS-specific parameters for CetOS
    """

    def set_scenario(self, url):
        self.scenario = self.set_kickstart(url)

    def pv_args(self):
        return "%s %s" % (self.ip, self.scenario)


class OSChooser:
    @classmethod
    def get_os(cls, os_kind):
        if os_kind.startswith('ubuntu'):
            os = UbuntuOS()
        elif os_kind.startswith('centos'):
            os = CentOS()
        elif os_kind.startswith('debian'):
            os = DebianOS()
        else:
            return None

        os.set_os_kind(os_kind)
        return os

