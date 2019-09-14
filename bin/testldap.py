import ftools as ft
import ldaparcetri as ll

people = [p for p in ll.get_people_table(real=True) if (p.get('sn') and p.get('givenName'))]

page_data = ft.byinitial(people, key=lambda x: x.get('sn', 'z')[0].lower()+ \
                         x.get('givenName', 'z')[0].lower())

pass
