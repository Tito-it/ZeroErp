{% include-markdown "it/dbzero/catalogo/manual/vw_articoli_componenti_dettaglio.md" %}
# 🔍 View `vw_articoli_componenti_dettaglio`

> 📝 **Descrizione**
>
> Righe della distinta base (componenti di un articolo) con codici e descrizioni di prodotto e componente, piu' la capability di riga (puo_chiudersi, data_min_chiusura, data_default_chiusura, motivo_non_chiudibile) per «Chiudi riga». Dal 2026-09-28 (brief-db-liste-righe-documento, D-8.5) e' la SORGENTE UNICA delle righe: per la lista configurabile catalogo.articolo_componenti e per il repository, che prima ne rifaceva la proiezione e la capability in Python. Nello stesso giro aggiunte determina_qta_padre ed esposto_in_fattura, che solo la copia Python aveva. Tutte le righe, anche le non attive e le chiuse: filtro e ordine li mette chi legge.

```sql
CREATE OR REPLACE VIEW catalogo.vw_articoli_componenti_dettaglio AS
SELECT ac.id,
    ac.prodotto_id,
    ac.componente_id,
    ac.coeff_qta,
    ac.partecipa_qta,
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
            WHEN (ac.valido_al IS NULL) THEN ac.valido_dal
            ELSE NULL::date
        END AS data_min_chiusura,
        CASE
            WHEN (ac.valido_al IS NULL) THEN GREATEST(ac.valido_dal, CURRENT_DATE)
            ELSE NULL::date
        END AS data_default_chiusura,
        CASE
            WHEN (ac.valido_al IS NULL) THEN NULL::text
            ELSE 'RIGA_GIA_CHIUSA'::text
        END AS motivo_non_chiudibile,
    ac.determina_qta_padre,
    ac.esposto_in_fattura
   FROM ((catalogo.articoli_componenti ac
     LEFT JOIN catalogo.articoli ap ON ((ap.id = ac.prodotto_id)))
     LEFT JOIN catalogo.articoli acmp ON ((acmp.id = ac.componente_id)));
```


---
{% include-markdown "signature-core.md" %}
