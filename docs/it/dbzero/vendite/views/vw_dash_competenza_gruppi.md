{% include-markdown "it/dbzero/vendite/manual/vw_dash_competenza_gruppi.md" %}
# 🔍 View `vw_dash_competenza_gruppi`

> 📝 **Descrizione**
>
> I documenti da emettere di una competenza, un gruppo per riga. Dal 2026-09-06 porta anche l'esito dell'ULTIMO tentativo di fatturazione (ultimo_esito, ultimo_errore_codice, ultimo_errore_messaggio, ultimo_errore_quando, ultimo_lotto_codice), letto da vendite.fatturazione_lotti_gruppi. Nasce da un caso vero: un lotto prendeva in carico tre documenti, ne fatturava due, e il terzo — caduto prima di diventare fattura — restava qui senza nessun segno, quindi sembrava fatturabile. Il segno NON spegne stadio ne' commessa_emittibile (decisione di Tid): dice che un tentativo e' fallito, non che il documento non si possa fatturare. Il legame e' (gruppo, mese di competenza): senza il mese, il documento di settembre erediterebbe l'errore di agosto. Le colonne restano NULL finche' il backend non scrive l'esito con vendite.fn_segna_esito_gruppo_lotto. Brief: brief-db-esito-gruppo-lotto R-3.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_competenza_gruppi
WITH (security_invoker=true) AS
WITH aggregato AS (
         SELECT a.competenza_mese,
            a.gruppo_key,
            a.sorgente_tipo_id,
            a.sorgente_uid,
            a.commessa_id,
            a.commessa_codice,
            a.emittente_soggetto_ruolo_id,
            a.cliente_display,
            a.stadio,
            a.commessa_emittibile,
            a.commessa_stato_codice_interno,
            a.commessa_stato_descrizione,
            a.billing_account_id,
            count(*) AS n_attivita,
            COALESCE(sum(a.valore), (0)::numeric) AS valore,
            min(a.data_attivita) AS data_attivita_min,
            max(a.data_attivita) AS data_attivita_max,
            bool_or(((a.tipo_movimento)::text = 'ONERE'::text)) AS ha_oneri,
            array_agg(DISTINCT a.registro_id) AS registri_ids,
            min((a.registro_codice)::text) AS registro_codice_unico,
            min(a.data_documento_prevista) AS data_prevista_unica
           FROM vendite.vw_dash_competenza_attivita a
          GROUP BY a.competenza_mese, a.gruppo_key, a.sorgente_tipo_id, a.sorgente_uid, a.commessa_id, a.commessa_codice, a.emittente_soggetto_ruolo_id, a.cliente_display, a.stadio, a.commessa_emittibile, a.commessa_stato_codice_interno, a.commessa_stato_descrizione, a.billing_account_id
        )
 SELECT g.competenza_mese,
    g.gruppo_key,
    COALESCE(s.codice_interno, 'ONERI_COMMESSA'::character varying) AS tipo_gruppo,
    s.area AS area_documento,
    COALESCE(doc.documento_numero, g.commessa_codice, g.gruppo_key) AS riferimento,
    g.commessa_id,
    g.commessa_codice,
    g.emittente_soggetto_ruolo_id,
    g.cliente_display,
    g.stadio,
    g.n_attivita,
    g.valore,
    g.data_attivita_min,
    g.data_attivita_max,
    g.ha_oneri,
    g.sorgente_tipo_id,
    g.sorgente_uid,
    g.commessa_emittibile,
    g.commessa_stato_codice_interno,
    g.commessa_stato_descrizione,
    doc.documento_id,
    COALESCE(ba_riga.parent_account_id, ba_riga.id) AS ba_fatturazione_id,
    ba_fatt.codice AS ba_codice_fatturazione,
    sog.ragione_sociale_completa AS cliente_fatturazione_display,
    sog.id_fiscale_univoco_cf_piva AS id_fiscale,
    s_ef.ragione_sociale_completa AS emittente_ragione_sociale,
    g.registri_ids,
    (cardinality(g.registri_ids))::smallint AS registri_n,
        CASE
            WHEN (cardinality(g.registri_ids) = 1) THEN g.registro_codice_unico
            ELSE NULL::text
        END AS registro_codice,
        CASE
            WHEN (cardinality(g.registri_ids) = 1) THEN g.data_prevista_unica
            ELSE NULL::date
        END AS data_documento_prevista,
    esito.stato_esecuzione AS ultimo_esito,
    esito.errore_codice AS ultimo_errore_codice,
    esito.errore_messaggio AS ultimo_errore_messaggio,
    esito.errore_quando AS ultimo_errore_quando,
    esito.lotto_codice AS ultimo_lotto_codice
   FROM (((((((((aggregato g
     LEFT JOIN config.sorgenti s ON ((s.id = g.sorgente_tipo_id)))
     LEFT JOIN LATERAL vendite.fn_get_sorgente_documento_ref(g.sorgente_tipo_id, g.sorgente_uid) doc(documento_id, documento_numero) ON ((s.area IS NOT NULL)))
     LEFT JOIN anagrafiche.billing_account ba_riga ON ((ba_riga.id = g.billing_account_id)))
     LEFT JOIN anagrafiche.billing_account ba_fatt ON ((ba_fatt.id = COALESCE(ba_riga.parent_account_id, ba_riga.id))))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_fatt ON ((sr_fatt.id = ba_fatt.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti sog ON ((sog.id = sr_fatt.soggetto_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON ((sr_ef.id = g.emittente_soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_ef ON ((s_ef.id = sr_ef.soggetto_id)))
     LEFT JOIN LATERAL ( SELECT lg.stato_esecuzione,
            lg.errore_codice,
            lg.errore_messaggio,
            lg.errore_quando,
            l.codice AS lotto_codice
           FROM (vendite.fatturazione_lotti_gruppi lg
             JOIN vendite.fatturazione_lotti l ON ((l.id = lg.lotto_id)))
          WHERE ((lg.gruppo_key = g.gruppo_key) AND (l.competenza_mese = g.competenza_mese) AND (lg.stato_esecuzione IS NOT NULL))
          ORDER BY COALESCE(lg.errore_quando, lg.data_update) DESC, lg.id DESC
         LIMIT 1) esito ON (true));
```


---
{% include-markdown "signature-core.md" %}
