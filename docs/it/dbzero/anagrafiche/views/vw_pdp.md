{% include-markdown "it/dbzero/anagrafiche/manual/vw_pdp.md" %}
# 🔍 View `vw_pdp`

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_pdp
WITH (security_invoker=on) AS
SELECT p.id AS pdp_id,
    p.pdp AS pdp_codice,
    p.utility_id,
    u.codice_interno AS utility_codice_interno,
    u.codice AS utility_codice,
    u.descrizione AS utility_descrizione,
    p.stato_pdp_id,
    sp.codice_interno AS stato_pdp_codice_interno,
    sp.codice AS stato_pdp_codice,
    sp.descrizione AS stato_pdp_descrizione,
    p.cliente_id,
    v.indirizzo_dettaglio_id,
    v.stradario_id,
    v.comune_id,
    v.descrizione_comune,
    v.cap,
    v.provincia,
    v.indirizzo_normalizzato,
    v.via_norm,
    v.civico,
    v.estensione_civico,
    v.palazzina,
    v.scala,
    v.piano,
    v.interno,
    v.altro,
    v.civic_geoloc,
    v.street_geoloc,
    v.attivo AS indirizzo_attivo,
    v.storicizza AS indirizzo_storicizza,
    v.tx_id AS indirizzo_tx_id,
    v.data_insert AS indirizzo_data_insert,
    v.user_insert AS indirizzo_user_insert,
    v.data_update AS indirizzo_data_update,
    v.user_update AS indirizzo_user_update
   FROM ((((anagrafiche.pdp p
     JOIN anagrafiche.vw_indirizzi_dettaglio v ON ((v.indirizzo_dettaglio_id = p.indirizzo_dettaglio_id)))
     JOIN config.utilities u ON ((u.id = p.utility_id)))
     JOIN config.stati_pdp sp ON ((sp.id = p.stato_pdp_id)))
     LEFT JOIN anagrafiche.clienti c ON ((c.id = p.cliente_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
