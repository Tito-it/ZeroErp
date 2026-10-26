{% include-markdown "it/dbzero/vendite/manual/vw_dash_commesse_respinte.md" %}
# 🔍 View `vw_dash_commesse_respinte`

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_commesse_respinte
WITH (security_invoker=on) AS
WITH escope AS (
         SELECT script.fn_get_emittenti_scope_sr_ids((NULLIF(current_setting('app.current_user_id'::text, true), ''::text))::integer) AS sr_ids
        )
 SELECT fl.competenza_mese,
    fl.id AS lotto_id,
    fl.codice AS lotto_codice,
    fl.stato_lotto,
    (((ll.meta -> 'context'::text) ->> 'commessa_id'::text))::bigint AS commessa_id,
    c.codice AS commessa_codice,
    ((ll.meta -> 'context'::text) ->> 'task'::text) AS task_code,
    (ll.meta ->> 'error_code'::text) AS error_code,
    ll.messaggio,
    (ll.meta ->> 'detail'::text) AS dettaglio,
    ll.data_ora AS respinta_il,
    fl.emittente_soggetto_ruolo_id,
    s_ef.ragione_sociale_completa AS emittente_ragione_sociale
   FROM (((((vendite.fatturazione_lotti_log ll
     JOIN vendite.fatturazione_lotti fl ON ((fl.id = ll.lotto_id)))
     LEFT JOIN vendite.commesse c ON (((c.id)::text = ((ll.meta -> 'context'::text) ->> 'commessa_id'::text))))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON ((sr_ef.id = fl.emittente_soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_ef ON ((s_ef.id = sr_ef.soggetto_id)))
     CROSS JOIN escope)
  WHERE ((ll.disabilitato IS FALSE) AND (ll.status = 'C'::bpchar) AND (((ll.meta -> 'context'::text) ->> 'commessa_id'::text) ~ '^[0-9]+$'::text) AND ((escope.sr_ids IS NULL) OR (fl.emittente_soggetto_ruolo_id = ANY (escope.sr_ids))));
```

</div>


---
{% include-markdown "signature-core.md" %}
