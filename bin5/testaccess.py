#
#  Test procedura di accesso
#

import ftools
import getpass

ftools.update_userlist()
userid = input("Username: ")
pwd = getpass.getpass("Password: ")
ret = ftools.authenticate(userid, pwd, "ldap.ced.inaf.it", 389)

print(ret)
