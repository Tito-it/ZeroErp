{% include-markdown "it/dbzero/anagrafiche/manual/vw_soggetti_ruoli_dettaglio.md" %}
# 🔍 View `vw_soggetti_ruoli_dettaglio`

> 📝 **Descrizione**
>
> Vista generale ruolo+soggetto: espone riferimenti fiscali/anagrafici del soggetto a partire da soggetto_ruolo_id, con decodifica tipo ruolo e titolo cortesia.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_soggetti_ruoli_dettaglio AS
SELECT sr.id AS soggetto_ruolo_id,
    sr.soggetto_id AS soggetto_ruolo_soggetto_id,
    sr.tipo_ruolo_id AS soggetto_ruolo_tipo_ruolo_id,
    tr.codice AS tipo_ruolo_codice,
    tr.codice_interno AS tipo_ruolo_codice_interno,
    tr.descrizione AS tipo_ruolo_descrizione,
    s.id AS soggetto_id,
    s.codice AS soggetto_codice,
    s.ragione_sociale,
    s.ragione_sociale_completa,
    s.cognome,
    s.nome,
    s.id_fiscale_univoco_cf_piva,
    s.partita_iva,
    s.codice_fiscale,
    s.data_nascita,
    s.sesso,
    s.stato_id,
    s.comune_id,
    s.titolo_cortesia_id,
    s.default_contatto_id,
    s.tipo_soggetto_dettaglio_id,
    s.attivo AS soggetto_attivo,
    s.storicizza AS soggetto_storicizza,
    s.tx_id AS soggetto_tx_id,
    s.data_insert AS soggetto_data_insert,
    s.user_insert AS soggetto_user_insert,
    s.data_update AS soggetto_data_update,
    s.user_update AS soggetto_user_update,
    tc.descrizione AS titolo_cortesia_descrizione,
    tc.descrizione_breve AS titolo_cortesia_descrizione_breve,
    sr.meta AS soggetto_ruolo_meta,
    sr.tx_id AS soggetto_ruolo_tx_id,
    sr.data_insert AS soggetto_ruolo_data_insert,
    sr.user_insert AS soggetto_ruolo_user_insert,
    sr.data_update AS soggetto_ruolo_data_update,
    sr.user_update AS soggetto_ruolo_user_update
   FROM (((anagrafiche.soggetti_ruoli sr
     JOIN anagrafiche.soggetti s ON ((s.id = sr.soggetto_id)))
     JOIN config.tipi_ruoli tr ON ((tr.id = sr.tipo_ruolo_id)))
     LEFT JOIN config.titoli_cortesia tc ON ((tc.id = s.titolo_cortesia_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
