"""
Authentication code.
"""

from threading import Lock

import ldap

from repoze.who.interfaces import IAuthenticator # pylint: disable=E0611,F0401
from repoze.who.interfaces import IChallengeDecider # pylint: disable=E0611,F0401
from zope.interface import directlyProvides # pylint: disable=E0611,F0401
from zope.interface import implements # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['LDAPAuthenticatorPlugin',
           'forbidden_challenge_decider',
           'remote_user_auth_policy_callback',
           ]


class LDAPAuthenticatorPlugin(object):
    """
    LDAP authentication plugin.

    Adds locking and transparent reconnect to the LDAP plugin featured on the
    pyramid site.
    """

    implements(IAuthenticator)

    NUMBER_RECONNECT_ATTEMPTS = 5

    def __init__(self, ldap_connection, base_dn):
        self.__ldap_connection = ldap_connection
        self.__base_dn = base_dn
        self.__lock = Lock()
        self.__conn = None

    def authenticate(self, environ, identity): # pylint: disable=W0613
        """
        Extract the validated username from the given identity map.

        :return: Validated username or *None*, if credentials are invalid.
        """
        result = None
        for dummy in range(self.NUMBER_RECONNECT_ATTEMPTS):
            try:
                result = self.__authenticate(identity)
            except ldap.SERVER_DOWN:
                # Reset connection and force a reconnect if the server was
                # restarted.
                self.__conn = None
            else:
                break
        return result

    def __authenticate(self, identity):
        if not ('login' in identity and 'password' in identity):
            # Invalid identity map. Do not raise an error.
            result = None
        else:
            self.__lock.acquire()
            if self.__conn is None:
                self.__conn = ldap.initialize(self.__ldap_connection)
            try:
                login = identity['login']
                pwd = identity['password']
                results = self.__conn.search_s(self.__base_dn,
                                               ldap.SCOPE_SUBTREE,
                                               '(uid=%s)' % login)
                if len(results) != 1 or len(pwd) == 0:
                    # LDAP NOT Authenticated - WRONG USERNAME or EMPTY PASSWORD
                    result = None
                else:
                    dn = results[0][0]
                    try:
                        self.__conn.simple_bind_s(dn, pwd)
                    except ldap.INVALID_CREDENTIALS:
                        # LDAP NOT Authenticated - WRONG PASSWORD
                        result = None
                    else:
                        # LDAP Authenticated
                        result = login
            finally:
                self.__lock.release()
        return result


def forbidden_challenge_decider(environ, status, headers): # pylint: disable=W0613
    """
    Newer pyramid versions return 403 instead of 401 when a forbidden view
    is accessed. This prevents the standard
    `repoze.who.classifiers:default_request_classifier` from doing the right
    thing and a challenge is never triggered.
    """
    return status.startswith('403 ')
directlyProvides(forbidden_challenge_decider, IChallengeDecider)


def remote_user_auth_policy_callback(userid, request): # pylint: disable=W0613
    groups = None
    if userid is not None:
        groups = []
    return groups

