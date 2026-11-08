{% include-markdown "it/dbzero/dbops/manual/vw_processi_che_bypassano.md" %}
# 🔍 View `vw_processi_che_bypassano`

> 📝 **Descrizione**
>
> PRESIDIO — deve restare VUOTA. I ruoli APPLICATIVI (con login, non superuser) che hanno BYPASSRLS: un ruolo cosi' scavalca la separazione dei dati fra aziende emittenti. ⚠️ Non dice «nessuno bypassa la RLS»: pgAgent bypassa perche' e' superuser e il proprietario delle tabelle per proprieta', e devono, perche' fanno DDL. Fino al 2026-11-04 la vista ammetteva un debito dichiarato per nome (zeroerp_batch_fatturazione, ritirato il 2026-10-15) e il presidio contava solo le righe non dichiarate: un ruolo tornato con quel nome sarebbe passato muto. Un debito nuovo si dichiara con un changeSet sulla vista e sul presidio, non con una lista di nomi. A catalogo in dbops.presidi, soglia ZERO; lo prova db/pgtap/dbops/test-processi-registro.sql. security_invoker: legge solo pg_roles.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_processi_che_bypassano
WITH (security_invoker=true) AS
SELECT rolname AS ruolo
   FROM pg_roles r
  WHERE (rolbypassrls AND rolcanlogin AND (NOT rolsuper));
```

</div>


---
{% include-markdown "signature-core.md" %}
