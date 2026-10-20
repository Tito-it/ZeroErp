{% include-markdown "it/dbzero/dbops/manual/vw_processi_che_bypassano.md" %}
# 🔍 View `vw_processi_che_bypassano`

> 📝 **Descrizione**
>
> Ruoli APPLICATIVI (login, non superuser) con BYPASSRLS. ⚠️ NON dice «nessuno bypassa la RLS»: pgAgent bypassa per superuser e il proprietario delle tabelle per proprieta', e devono, perche' fanno DDL. Regola presidiata: ZERO righe con stato = NON_DICHIARATO. Le righe DEBITO_DICHIARATO sono la porta registrata come porta, con la fase in cui si chiude (6-bis): a regime la vista deve restare del tutto vuota. Brief: brief-db-processi-automatici-identita-e-perimetro §8.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_processi_che_bypassano AS
SELECT rolname AS ruolo,
        CASE
            WHEN (rolname = ANY (ARRAY['zeroerp_batch_fatturazione'::text])) THEN 'DEBITO_DICHIARATO'::text
            ELSE 'NON_DICHIARATO'::text
        END AS stato,
    'Ritiro previsto alla fase 6-bis del brief processi automatici'::text AS nota
   FROM pg_roles r
  WHERE (rolbypassrls AND rolcanlogin AND (NOT rolsuper));
```

</div>


---
{% include-markdown "signature-core.md" %}
