{% include-markdown "it/dbzero/catalogo/manual/vw_articoli_componenti_dettaglio.md" %}
# 🔍 View `vw_articoli_componenti_dettaglio`

> 📝 **Descrizione**
>
> Righe della distinta base (catalogo.articoli_componenti) con codice e descrizione di prodotto e componente, il modo di esposizione in fattura (esposizione_in_fattura, con codice ed etichetta_key da config.esposizioni_componente: la logica confronta esposizione_in_fattura, il codice e' solo a video) e la capability di riga per «Chiudi riga»: puo_chiudersi (il legame non ha ancora una fine), data_min_chiusura (la prima fine ammessa: la piu' tarda fra valido_dal e ieri, perche' la fine non cambia i giorni gia' passati, come vuole catalogo.trgfn_articoli_componenti_block_modifica_struttura), data_default_chiusura (la piu' tarda fra valido_dal e oggi), motivo_non_chiudibile (RIGA_GIA_CHIUSA). Sorgente unica delle righe della lista configurabile catalogo.articolo_componenti e del repository. Tutte le righe, anche le non attive e le chiuse: filtro e ordine li mette chi legge.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW catalogo.vw_articoli_componenti_dettaglio AS
SELECT ac.id,
    ac.prodotto_id,
    ac.componente_id,
    ac.coeff_qta,
    ac.obbligatorio,
    ac.valido_dal,
    ac.valido_al,
    ac.meta,
    ac.user_insert,
    ac.user_update,
    ac.data_insert,
    ac.data_update,
    ac.tx_id,
    ac.storicizza,
    ac.attivo,
    ac.note_target_tipo,
    ac.note_id,
    ap.codice AS prodotto_codice,
    ap.descrizione AS prodotto_descrizione,
    acmp.codice AS componente_codice,
    acmp.descrizione AS componente_descrizione,
    (ac.valido_al IS NULL) AS puo_chiudersi,
        CASE
            WHEN (ac.valido_al IS NULL) THEN GREATEST(ac.valido_dal, ( SELECT (script.fn_data_operativa() - 1)))
            ELSE NULL::date
        END AS data_min_chiusura,
        CASE
            WHEN (ac.valido_al IS NULL) THEN GREATEST(ac.valido_dal, ( SELECT script.fn_data_operativa() AS fn_data_operativa))
            ELSE NULL::date
        END AS data_default_chiusura,
        CASE
            WHEN (ac.valido_al IS NULL) THEN NULL::text
            ELSE 'RIGA_GIA_CHIUSA'::text
        END AS motivo_non_chiudibile,
    ac.esposizione_in_fattura,
    ec.codice AS esposizione_in_fattura_codice,
    ec.etichetta_key AS esposizione_in_fattura_etichetta_key
   FROM (((catalogo.articoli_componenti ac
     LEFT JOIN catalogo.articoli ap ON ((ap.id = ac.prodotto_id)))
     LEFT JOIN catalogo.articoli acmp ON ((acmp.id = ac.componente_id)))
     LEFT JOIN config.esposizioni_componente ec ON (((ec.codice_interno)::text = (ac.esposizione_in_fattura)::text)));
```

</div>


---
{% include-markdown "signature-core.md" %}
