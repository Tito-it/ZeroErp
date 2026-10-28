{% include-markdown "it/dbzero/vendite/manual/vw_dash_fatturazione_contratti.md" %}
# 🔍 View `vw_dash_fatturazione_contratti`

> 📝 **Descrizione**
>
> Resolver area CONTRATTI (famiglia dash fatturazione / situazione aperta): 1 riga per contratto vivo (esito &lt;&gt; NEGATIVO), DE-ESPLOSO (niente asse mese, DL-12). Giudizio di transito SOSPESO finche' non esiste il push ricorrente: is_transitato/unita_transitate/motivo_fermo = NULL (non "fermo": senza push ogni contratto sarebbe un falso-allarme perenne). data_riferimento = valido_dal ("in essere da"). Area a conteggi: valore_* NULL. Consumata da vw_dash_fatturazione_documenti (union) e da vw_dash_aperto_*; il Backlog non la vede (motivo_fermo NULL). Rev 2026-10-20 (20261020-84, brief-db-grammatica-unica-documenti 2d, G-6): l'area CONTRATTI diventa CONTRATTO, il codice della sorgente (il plurale e' ritirato).

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
    NULL::integer AS unita_transitate,
    NULL::boolean AS is_transitato,
    false AS is_abortito,
    NULL::character varying AS motivo_fermo,
    sdc.codice_interno AS stato_codice_interno,
    sdc.codice AS stato_codice,
    sdc.fase,
    sog.ragione_sociale_completa AS cliente_display,
    c.valido_dal AS data_riferimento
   FROM ((((vendite.contratti c
     JOIN config.stati_doc_contratti sdc ON (((sdc.id = c.stato_doc_contratto_id) AND ((sdc.esito)::text IS DISTINCT FROM 'NEGATIVO'::text))))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = c.billing_account_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = ba.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti sog ON ((sog.id = sr.soggetto_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
