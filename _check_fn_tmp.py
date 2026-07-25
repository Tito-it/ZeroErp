import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','zeroerp_backend.settings')
django.setup()
from django.db import connection
with connection.cursor() as c:
    c.execute("""
      SELECT pg_get_function_result(p.oid)
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
       WHERE n.nspname='vendite' AND p.proname='fn_list_commessa_attivita'
    """)
    for r in c.fetchall():
        res = r[0]
        print("RETURNS:", res)
        print("HA fatturata:", "fatturata" in res)
