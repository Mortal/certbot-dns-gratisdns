"""DNS Authenticator for GratisDNS."""
import logging
import re

import pyotp
import requests
import zope.interface

from certbot import interfaces
from certbot.plugins import dns_common

logger = logging.getLogger(__name__)

GRATISDNS_API = "https://admin.gratisdns.com"


@zope.interface.implementer(interfaces.IAuthenticator)
@zope.interface.provider(interfaces.IPluginFactory)
class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for GratisDNS

    This Authenticator uses the GratisDNS web interface to fulfill
    a dns-01 challenge.
    """

    description = (
        "Obtain certificates using a DNS TXT record "
        + "(if you are using GratisDNS for DNS)."
    )
    ttl = 60

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)
        self.credentials = None

    @classmethod
    def add_parser_arguments(cls, add):  # pylint: disable=arguments-differ
        super(Authenticator, cls).add_parser_arguments(
            add, default_propagation_seconds=660
        )
        add("credentials", help="GratisDNS credentials file.")

    def more_info(self):  # pylint: disable=missing-docstring,no-self-use
        return (
            "This plugin configures a DNS TXT record to respond to a dns-01 challenge using "
            + "the GratisDNS web interface."
        )

    def _setup_credentials(self):
        self.credentials = self._configure_credentials(
            "credentials",
            "GratisDNS credentials file",
            {
                "username": "GratisDNS username",
                "password": "GratisDNS password",
                "otp-secret": "TOTP secret in base32",
            },
        )

    def _perform(self, domain, validation_domain_name, validation):
        self._get_gratisdns_client().add_txt_record(
            domain, validation_domain_name, validation
        )

    def _cleanup(self, domain, validation_domain_name, validation):
        self._get_gratisdns_client().del_txt_record(
            domain, validation_domain_name, validation
        )

    def _get_gratisdns_client(self):
        return _GratisDnsClient(
            self.credentials.conf("username"),
            self.credentials.conf("password"),
            self.credentials.conf("otp-secret"),
            self.ttl,
        )


class _GratisDnsClient(object):
    """
    Encapsulates all communication with GratisDNS.
    """

    def __init__(self, username, password, otp_secret, ttl):
        super(_GratisDnsClient, self).__init__()

        self.username = username
        self.password = password
        self.totp = pyotp.TOTP(otp_secret)
        self.ttl = ttl
        self.session = requests.Session()

    def login(self):
        totp = self.totp.now()
        data = {
            "login": self.username,
            "password": self.password,
            "action": "logmein",
            "oauth": totp,
        }
        post_response = self.session.post(GRATISDNS_API, data=data)
        response = self.session.get(GRATISDNS_API, params={"action": "usersetup_user"})
        if self.username not in response.text:
            raise Exception("GratisDNS login failed for %s" % self.username)

    def check_domain(self, full_domain):
        params = {"action": "dns_primarydns"}
        response = self.session.get(GRATISDNS_API, params=params)
        if full_domain not in response.text:
            raise Exception(
                "Did not find the domain %s in the GratisDNS account for %s"
                % (full_domain, self.username)
            )

    def add_txt_record(self, full_domain, validation_domain_name, validation):
        self.login()
        self.check_domain(full_domain)
        assert validation_domain_name.endswith("." + full_domain)
        sub_domain = validation_domain_name.rpartition("." + full_domain)[0]
        params = {
            "action": "dns_primary_record_add_txt",
            "user_domain": full_domain,
        }
        data = {
            "action": "dns_primary_record_added_txt",
            "name": sub_domain,
            "ttl": self.ttl,
            "txtdata": validation,
            "user_domain": full_domain,
        }
        self.session.post(GRATISDNS_API, params=params, data=data)

    def get_txt_record_id(self, full_domain, validation):
        params = {
            "action": "dns_primary_changeDNSsetup",
            "user_domain": full_domain,
        }
        response = self.session.get(GRATISDNS_API, params=params)
        if validation not in response.text:
            # raise Exception("TXT value %r not found in DNS record" % validation)
            return None
        mo = re.search(r">%s.*?action=dns_primary_delete_txt(?:&|&amp;)id=([0-9]+)" % re.escape(validation), response.text, re.S)
        if mo is None:
            print(response.text)  # DEBUG
            raise Exception("Regex match failed")
        return int(mo.group(1))

    def del_txt_record(self, full_domain, validation_domain_name, validation):
        self.login()
        self.check_domain(full_domain)
        assert validation_domain_name.endswith("." + full_domain)
        record_id = self.get_txt_record_id(full_domain, validation)
        if record_id is None:
            return
        params = {
            "action": "dns_primary_delete_txt",
            "id": str(record_id),
            "user_domain": full_domain,
        }
        response = self.session.get(GRATISDNS_API, params=params)
        if "Record was deleted" not in response.text:
            raise Exception("TXT record was not deleted!")
