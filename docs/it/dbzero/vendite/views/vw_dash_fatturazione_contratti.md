{% include-markdown "it/dbzero/vendite/manual/vw_dash_fatturazione_contratti.md" %}
# 🔍 View `vw_dash_fatturazione_contratti`

> 📝 **Descrizione**
>
> Resolver area CONTRATTO (famiglia dash fatturazione / situazione aperta): 1 riga per contratto vivo (esito &lt;&gt; NEGATIVO), DE-ESPLOSO (niente asse mese, DL-12). Giudizio di transito RIACCESO dal 20261031-04 (brief-db-contratto-righe-periodiche-in-commessa §6.13, F-12 … F-15) per i contratti nello stato di emissione o di cessazione (colonne emissione e cessazione del vocabolario, dal 20261031-14; oggi ATTIVO e CESSATO), dalla sede del push vendite.fn_contratti_addebiti_maturati: fermo se ha un addebito maturato non in commessa (motivo CANONE_NON_GENERATO, RECUPERABILE) o un canone che non puo' partire (CANONE_NON_GENERABILE, ANOMALIA, vince sul primo); altrimenti is_transitato = true e il contratto esce dalla situazione aperta. La bozza resta sospesa: is_transitato/unita_transitate/motivo_fermo NULL. unita_totali = 1. data_riferimento = valido_dal (in essere da); se fermo, l'addebito piu' vecchio che aspetta (fonte scartata: valido_dal), mai dopo oggi. Area a conteggi: valore_* NULL. Consumata da vw_dash_fatturazione_documenti (union), e attraverso questa da vw_dash_aperto_documenti e vw_dash_backlog_documenti. Rev 2026-10-20 (20261020-84): l'area CONTRATTI diventa CONTRATTO.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_fatturazione_contratti
WITH (security_invoker=on) AS
SELECT 'CONTRATTO'::character varying AS area,
    NULL::date AS competenza_mese,
    c.id AS documento_id,
    (c.uid)::text AS documento_uid,
    (c.numero)::text AS codice,
    c.emittente_fiscale_id,
    NULL::bigint AS emittente_soggetto_ruolo_id,
    NULL::numeric AS valore_totale,
    NULL::numeric AS valore_transitato,
    1 AS unita_totali,
        CASE
            WHEN g.giudicato THEN ((NOT g.fermo))::integer
            ELSE NULL::integer
        END AS unita_transitate,
        CASE
            WHEN g.giudicato THEN (NOT g.fermo)
            ELSE NULL::boolean
        END AS is_transitato,
    false AS is_abortito,
    (
        CASE
            WHEN g.non_generabile THEN 'CANONE_NON_GENERABILE'::text
            WHEN g.da_mandare THEN 'CANONE_NON_GENERATO'::text
            ELSE NULL::text
        END)::character varying AS motivo_fermo,
    sdc.codice_interno AS stato_codice_interno,
    sdc.codice AS stato_codice,
    sdc.fase,
    sog.ragione_sociale_completa AS cliente_display,
    COALESCE(g.dal, c.valido_dal) AS data_riferimento
   FROM (((((vendite.contratti c
     JOIN config.stati_doc_contratti sdc ON (((sdc.id = c.stato_doc_contratto_id) AND ((sdc.esito)::text IS DISTINCT FROM 'NEGATIVO'::text))))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = c.billing_account_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = ba.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti sog ON ((sog.id = sr.soggetto_id)))
     CROSS JOIN LATERAL ( SELECT x.giudicato,
            COALESCE(x.non_generabile, false) AS non_generabile,
            COALESCE(x.da_mandare, false) AS da_mandare,
            COALESCE((x.non_generabile OR x.da_mandare), false) AS fermo,
            x.dal
           FROM ( SELECT (sdc.emissione OR sdc.cessazione) AS giudicato,
                    bool_or((a.scarto IS NOT NULL)) AS non_generabile,
                    bool_or((a.scarto IS NULL)) AS da_mandare,
                        CASE
                            WHEN (count(*) > 0) THEN LEAST(min(COALESCE(a.competenza_dal, c.valido_dal)), script.fn_data_operativa())
                            ELSE NULL::date
                        END AS dal
                   FROM vendite.fn_contratti_addebiti_maturati(NULL::date, NULL::bigint, c.id) a(contratto_id, contratto_uid, riga_id, billing_account_id, utility_id, emittente_soggetto_ruolo_id, competenza_dal, competenza_al, fatturazione_immediata, segment_key, articolo_id, istanza_utility_id, data_attivita, uom_id, quantita, qta_operativa, uom_operativa_id, factor_to_base, competenza_mese, prezzo_snapshot, prezzo_bloccato, meta, ramo, scarto)
                  WHERE (sdc.emissione OR sdc.cessazione)) x) g);
```

</div>


---
{% include-markdown "signature-core.md" %}
