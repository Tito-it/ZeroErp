{% include-markdown "it/dbzero/anagrafiche/manual/vw_indirizzi_resolved_all.md" %}
# 🔍 View `vw_indirizzi_resolved_all`

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_indirizzi_resolved_all AS
SELECT scope,
    source,
    indirizzo_id,
    soggetto_id,
    soggetto_ruolo_id,
    istanza_utility_id,
    tipo_indirizzo_id,
    tipo_indirizzo_codice,
    tipo_indirizzo_descrizione,
    is_normalizzato,
    indirizzo_dettaglio_id,
    indirizzo_display,
    indirizzo_libero,
    administrative_area,
    locality,
    sublocality,
    postal_code,
    comune_id,
    comune_descrizione,
    cap,
    provincia,
    provincia_id,
    provincia_sigla,
    provincia_descrizione,
    regione_id,
    regione_descrizione,
    stato_id,
    stato_descrizione,
    stato_iso2,
    codice_postale_id,
    cap_codice,
    stradario_id,
    via_norm,
    civico,
    estensione_civico,
    palazzina,
    scala,
    piano,
    interno,
    altro,
    geoloc,
    storicizza,
    tx_id,
    data_insert,
    user_insert,
    data_update,
    user_update,
    tipo_indirizzo_codice_interno
   FROM anagrafiche.vw_indirizzi_resolved_base;
```

</div>


---
{% include-markdown "signature-core.md" %}
