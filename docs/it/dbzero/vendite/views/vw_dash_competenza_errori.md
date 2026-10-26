{% include-markdown "it/dbzero/vendite/manual/vw_dash_competenza_errori.md" %}
# 🔍 View `vw_dash_competenza_errori`

> 📝 **Descrizione**
>
> Lente 1 Competenza, blocco errori: eventi "vivi" della pipeline di fatturazione per mese di competenza. TASK_ERRORE = run in ERRORE (attivo) non superato da un COMPLETATO successivo sulla stessa chiave (lotto/step/task), competenza dal lotto. FATTURA_CRITICA = fatture.critical (sync da fatture_log), messaggio = ultimo log non disabilitato; competenza: lotto collegato -&gt; mesi distinti delle AF (una riga per mese) -&gt; fallback mese data fattura (DB-7). SCOPE EMITTENTE via fn_get_emittenti_scope_sr_ids(GUC): fail-closed. security_invoker=on. ⭐ Rev 2026-08-18 (R-4, brief perimetro-emittente Fase E): aggiunta in coda `emittente_ragione_sociale`. La union dei due rami e' avvolta in una CTE e il nome si risolve una volta all'esterno — entrambi i rami portano gia' la chiave (dal LOTTO il primo, dalla FATTURA il secondo). ⚠️ Il filtro di scope NON e' stato accorpato fuori dalla union, e non e' una svista: i due rami filtrano su sorgenti diverse e unificarli significherebbe sceglierne una. Il filtro sta dove sta la ragione.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_competenza_errori
WITH (security_invoker=on) AS
WITH escope AS (
         SELECT script.fn_get_emittenti_scope_sr_ids((NULLIF(current_setting('app.current_user_id'::text, true), ''::text))::integer) AS sr_ids
        ), task_err AS (
         SELECT tr.lotto_id,
            tr.task_code,
            tr.tentativo,
            tr.error_code,
            tr.error_message,
            tr.started_at
           FROM vendite.fatturazione_lotti_task_runs tr
          WHERE (((tr.task_stato)::text = 'ERRORE'::text) AND (tr.attivo IS TRUE) AND (NOT (EXISTS ( SELECT 1
                   FROM vendite.fatturazione_lotti_task_runs tr2
                  WHERE ((tr2.lotto_id = tr.lotto_id) AND (NOT (tr2.stato_doc_fiscale_id IS DISTINCT FROM tr.stato_doc_fiscale_id)) AND ((tr2.task_code)::text = (tr.task_code)::text) AND (tr2.tentativo > tr.tentativo) AND ((tr2.task_stato)::text = 'COMPLETATO'::text) AND (tr2.attivo IS TRUE))))))
        ), fatture_critiche AS (
         SELECT f.id,
            f.anno,
            f.serie,
            f.numero,
            f.data,
            f.emittente_soggetto_ruolo_id,
            ll.messaggio,
            ll.data_ora
           FROM (vendite.fatture f
             LEFT JOIN LATERAL ( SELECT fl.messaggio,
                    fl.data_ora
                   FROM vendite.fatture_log fl
                  WHERE ((fl.fattura_id = f.id) AND (fl.disabilitato IS FALSE))
                  ORDER BY fl.data_ora DESC
                 LIMIT 1) ll ON (true))
          WHERE (f.critical IS TRUE)
        ), fatture_competenze AS (
         SELECT fc.id AS fattura_id,
            l.competenza_mese,
            lf.lotto_id
           FROM ((fatture_critiche fc
             JOIN vendite.fatturazione_lotti_fatture lf ON ((lf.fattura_id = fc.id)))
             JOIN vendite.fatturazione_lotti l ON ((l.id = lf.lotto_id)))
        UNION
         SELECT fc.id,
            af.competenza_mese,
            NULL::bigint AS lotto_id
           FROM ((fatture_critiche fc
             JOIN vendite.fatture_righe fr ON ((fr.fattura_id = fc.id)))
             JOIN vendite.attivita_fatturabili af ON ((af.fattura_riga_id = fr.id)))
          WHERE (NOT (EXISTS ( SELECT 1
                   FROM vendite.fatturazione_lotti_fatture lf2
                  WHERE (lf2.fattura_id = fc.id))))
        UNION
         SELECT fc.id,
            (date_trunc('month'::text, (fc.data)::timestamp with time zone))::date AS competenza_mese,
            NULL::bigint AS lotto_id
           FROM fatture_critiche fc
          WHERE ((NOT (EXISTS ( SELECT 1
                   FROM vendite.fatturazione_lotti_fatture lf3
                  WHERE (lf3.fattura_id = fc.id)))) AND (NOT (EXISTS ( SELECT 1
                   FROM (vendite.fatture_righe fr2
                     JOIN vendite.attivita_fatturabili af2 ON ((af2.fattura_riga_id = fr2.id)))
                  WHERE (fr2.fattura_id = fc.id)))))
        ), eventi AS (
         SELECT 'TASK_ERRORE'::character varying AS tipo_evento,
            l.competenza_mese,
            l.id AS lotto_id,
            l.codice AS lotto_codice,
            l.stato_lotto,
            NULL::bigint AS fattura_id,
            NULL::smallint AS fattura_anno,
            NULL::character varying AS fattura_serie,
            NULL::bigint AS fattura_numero,
            te.task_code,
            te.error_code,
            te.error_message AS messaggio,
            te.started_at AS data_evento,
            l.emittente_soggetto_ruolo_id
           FROM ((task_err te
             JOIN vendite.fatturazione_lotti l ON ((l.id = te.lotto_id)))
             CROSS JOIN escope)
          WHERE ((escope.sr_ids IS NULL) OR (l.emittente_soggetto_ruolo_id = ANY (escope.sr_ids)))
        UNION ALL
         SELECT 'FATTURA_CRITICA'::character varying AS tipo_evento,
            fk.competenza_mese,
            fk.lotto_id,
            l2.codice AS lotto_codice,
            l2.stato_lotto,
            fc.id AS fattura_id,
            fc.anno AS fattura_anno,
            fc.serie AS fattura_serie,
            fc.numero AS fattura_numero,
            NULL::character varying AS task_code,
            NULL::character varying AS error_code,
            fc.messaggio,
            fc.data_ora AS data_evento,
            fc.emittente_soggetto_ruolo_id
           FROM (((fatture_critiche fc
             JOIN fatture_competenze fk ON ((fk.fattura_id = fc.id)))
             LEFT JOIN vendite.fatturazione_lotti l2 ON ((l2.id = fk.lotto_id)))
             CROSS JOIN escope)
          WHERE ((escope.sr_ids IS NULL) OR (fc.emittente_soggetto_ruolo_id = ANY (escope.sr_ids)))
        )
 SELECT e.tipo_evento,
    e.competenza_mese,
    e.lotto_id,
    e.lotto_codice,
    e.stato_lotto,
    e.fattura_id,
    e.fattura_anno,
    e.fattura_serie,
    e.fattura_numero,
    e.task_code,
    e.error_code,
    e.messaggio,
    e.data_evento,
    e.emittente_soggetto_ruolo_id,
    s_ef.ragione_sociale_completa AS emittente_ragione_sociale,
    COALESCE(cf.commesse, '[]'::jsonb) AS commesse_fallite,
    COALESCE(cf.n, 0) AS n_commesse_fallite
   FROM (((eventi e
     LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON ((sr_ef.id = e.emittente_soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_ef ON ((s_ef.id = sr_ef.soggetto_id)))
     LEFT JOIN LATERAL ( SELECT jsonb_agg(jsonb_build_object('commessa_id', (((ll.meta -> 'context'::text) ->> 'commessa_id'::text))::bigint, 'commessa_codice', c.codice, 'error_code', (ll.meta ->> 'error_code'::text), 'messaggio', ll.messaggio, 'dettaglio', (ll.meta ->> 'detail'::text)) ORDER BY (((ll.meta -> 'context'::text) ->> 'commessa_id'::text))::bigint) AS commesse,
            (count(*))::integer AS n
           FROM (vendite.fatturazione_lotti_log ll
             LEFT JOIN vendite.commesse c ON ((c.id = (((ll.meta -> 'context'::text) ->> 'commessa_id'::text))::bigint)))
          WHERE (((e.tipo_evento)::text = 'TASK_ERRORE'::text) AND (ll.lotto_id = e.lotto_id) AND (ll.disabilitato IS FALSE) AND (ll.status = 'C'::bpchar) AND (((ll.meta -> 'context'::text) ->> 'commessa_id'::text) ~ '^[0-9]+$'::text) AND (((ll.meta -> 'context'::text) ->> 'task'::text) = (e.task_code)::text) AND (ll.data_ora >= e.data_evento))) cf ON (true));
```

</div>


---
{% include-markdown "signature-core.md" %}
