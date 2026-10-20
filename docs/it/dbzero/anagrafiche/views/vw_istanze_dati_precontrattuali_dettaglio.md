{% include-markdown "it/dbzero/anagrafiche/manual/vw_istanze_dati_precontrattuali_dettaglio.md" %}
# 🔍 View `vw_istanze_dati_precontrattuali_dettaglio`

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_istanze_dati_precontrattuali_dettaglio
WITH (security_invoker=on) AS
SELECT idp.id AS istanza_dati_precontrattuali_id,
    idp.istanza_utility_id,
    idp.utility_id AS istanza_dati_utility_id,
    idp.classe_utenza_id,
    cu.descrizione AS classe_utenza_descrizione,
    cu.codice AS classe_utenza_codice,
    tu.id AS tipo_utenza_id,
    tu.descrizione AS tipo_utenza_descrizione,
    tu.codice AS tipo_utenza_codice,
    idp.param_1_num,
    idp.param_2_txt,
    idp.meta,
    idp.tx_id,
    idp.storicizza,
    idp.data_insert,
    idp.user_insert,
    idp.data_update,
    idp.user_update,
    iud.istanza_id,
    iud.istanza_codice,
    iud.proprietario_inquilino,
    iud.fittizia,
    iud.soggetto_id,
    iud.ragione_sociale_completa,
    iud.id_fiscale_univoco_cf_piva,
    iud.pdp_id,
    iud.pdp_codice,
    iud.stato_pdp_id,
    iud.stato_pdp_codice,
    iud.stato_pdp_descrizione,
    iud.utility_id,
    iud.utility_codice,
    iud.utility_descrizione,
    iud.parent_istanza_id,
    iud.indirizzo_dettaglio_id,
    iud.indirizzo_normalizzato,
    iud.via_norm,
    iud.civico,
    iud.estensione_civico,
    iud.palazzina,
    iud.scala,
    iud.piano,
    iud.interno,
    iud.altro,
    iud.civic_geoloc,
    iud.street_geoloc,
    iud.indirizzo_comune_id,
    iud.comune_descrizione,
    iud.provincia_sigla,
    iud.cap,
    iud.indirizzo_generale,
    iud.tipo_toponimo,
    iud.nome_strada,
    iud.tx_id AS istanza_tx_id,
    iud.data_insert AS istanza_data_insert,
    iud.user_insert AS istanza_user_insert,
    iud.data_update AS istanza_data_update,
    iud.user_update AS istanza_user_update,
    iud.stato_pdp_codice_interno,
    iud.utility_codice_interno
   FROM (((anagrafiche.istanze_dati_precontrattuali idp
     JOIN anagrafiche.vw_istanze_utilities_dettaglio iud ON ((iud.istanza_id = idp.istanza_utility_id)))
     LEFT JOIN config.classi_utenze cu ON ((cu.id = idp.classe_utenza_id)))
     LEFT JOIN config.tipi_utenze tu ON ((tu.id = cu.tipo_utenza_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
