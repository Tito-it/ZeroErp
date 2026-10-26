{% include-markdown "it/dbzero/anagrafiche/manual/vw_istanze_utilities_dettaglio.md" %}
# 🔍 View `vw_istanze_utilities_dettaglio`

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_istanze_utilities_dettaglio AS
SELECT iu.id AS istanza_id,
    iu.codice AS istanza_codice,
    iu.proprietario_inquilino,
    iu.fittizia,
    iu.soggetto_id,
    s.ragione_sociale_completa,
    s.id_fiscale_univoco_cf_piva,
    iu.pdp_id,
    p.pdp AS pdp_codice,
    p.stato_pdp_id,
    sp.codice AS stato_pdp_codice,
    sp.descrizione AS stato_pdp_descrizione,
    p.utility_id,
    u.codice AS utility_codice,
    u.descrizione AS utility_descrizione,
    iu.parent_istanza_id,
    iu.indirizzo_dettaglio_id,
    idv.indirizzo_normalizzato,
    idv.via_norm,
    idv.civico,
    idv.estensione_civico,
    idv.palazzina,
    idv.scala,
    idv.piano,
    idv.interno,
    idv.altro,
    idv.civic_geoloc,
    idv.street_geoloc,
    idv.comune_id AS indirizzo_comune_id,
    ic.comune AS comune_descrizione,
    ic.provincia AS provincia_sigla,
    ic.codice_postale AS cap,
    ic.indirizzo_generale,
    ic.tipo_toponimo,
    ic.nome_strada,
    iu.tx_id,
    iu.data_insert,
    iu.user_insert,
    iu.data_update,
    iu.user_update,
    sp.codice_interno AS stato_pdp_codice_interno,
    u.codice_interno AS utility_codice_interno
   FROM ((((((anagrafiche.istanze_utilities iu
     JOIN anagrafiche.soggetti s ON ((s.id = iu.soggetto_id)))
     LEFT JOIN anagrafiche.pdp p ON ((p.id = iu.pdp_id)))
     LEFT JOIN config.stati_pdp sp ON ((sp.id = p.stato_pdp_id)))
     LEFT JOIN config.utilities u ON ((u.id = p.utility_id)))
     LEFT JOIN anagrafiche.vw_indirizzi_dettaglio idv ON ((idv.indirizzo_dettaglio_id = iu.indirizzo_dettaglio_id)))
     LEFT JOIN script.vw_indirizzo_completo ic ON ((ic.id_stradario = idv.stradario_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
