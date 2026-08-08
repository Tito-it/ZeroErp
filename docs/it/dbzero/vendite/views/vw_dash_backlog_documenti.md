{% include-markdown "it/dbzero/vendite/manual/vw_dash_backlog_documenti.md" %}
# 🔍 View `vw_dash_backlog_documenti`

> 📝 **Descrizione**
>
> Backlog fatturazione (lente 2). rev 2026-07-18 (step 9, DL-24): la vista E' una UNION — ramo documenti (da vw_dash_fatturazione_documenti, invariato) + DUE rami resi a grana (reso x motivo): RICONSEGNA_NON_ESEGUITA (RECUPERABILE) da vw_resi_da_riconsegnare e MERCE_RESA_GIA_FATTURATA (FISIOLOGICO oggi: nessuna azione esiste — niente NC, quantita' immutabile; diventa recuperabile promuovendo UNA cella di seed) da vw_resi_da_accreditare con etichetta DOVUTA (le facoltative sono opzione, non arretrato). I resi NON stanno nella union pre-commessa: REVERSE_FLOW. Misura a conteggi (DL-11): valore_fermo NULL, mai 0. Classe/azione risolte UNA volta a valle su config.motivi_fermo, filtro classe &lt;&gt; FISIOLOGICO per tutti i rami. Deroga dichiarata: unica area dove un documento (reso misto) puo' comparire due volte. security_invoker=on + RLS. rev 2026-07-06: forma originaria.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_backlog_documenti
WITH (security_invoker=on) AS
WITH base AS (
         SELECT d.area,
            d.competenza_mese,
            d.documento_id,
            d.documento_uid,
            d.codice,
            d.cliente_display,
            d.emittente_fiscale_id,
            d.emittente_soggetto_ruolo_id,
            (d.valore_totale - d.valore_transitato) AS valore_fermo,
            (d.unita_totali - d.unita_transitate) AS unita_ferme,
            d.motivo_fermo,
            d.data_riferimento,
            d.stato_codice_interno,
            d.stato_codice,
            d.fase
           FROM vendite.vw_dash_fatturazione_documenti d
          WHERE (d.motivo_fermo IS NOT NULL)
        UNION ALL
         SELECT 'RESI'::character varying AS "varchar",
            (date_trunc('month'::text, (q.data)::timestamp with time zone))::date AS date_trunc,
            q.reso_id,
            (q.reso_uid)::text AS reso_uid,
            (q.reso_numero)::text AS reso_numero,
            q.destinatario_denominazione,
            q.emittente_fiscale_id,
            NULL::bigint AS int8,
            NULL::numeric AS "numeric",
            (count(*))::integer AS count,
            'RICONSEGNA_NON_ESEGUITA'::character varying AS "varchar",
            q.data,
            sdr.codice_interno,
            sdr.codice,
            sdr.fase
           FROM ((vendite.vw_resi_da_riconsegnare q
             JOIN vendite.resi r2 ON ((r2.id = q.reso_id)))
             JOIN config.stati_doc_reso sdr ON ((sdr.id = r2.stato_doc_reso_id)))
          GROUP BY q.reso_id, q.reso_uid, q.reso_numero, q.data, q.destinatario_denominazione, q.emittente_fiscale_id, sdr.codice_interno, sdr.codice, sdr.fase
        UNION ALL
         SELECT 'RESI'::character varying AS "varchar",
            (date_trunc('month'::text, (a.data)::timestamp with time zone))::date AS date_trunc,
            a.reso_id,
            (a.reso_uid)::text AS reso_uid,
            (a.reso_numero)::text AS reso_numero,
            a.destinatario_denominazione,
            a.emittente_fiscale_id,
            NULL::bigint AS int8,
            NULL::numeric AS "numeric",
            (count(*))::integer AS count,
            'MERCE_RESA_GIA_FATTURATA'::character varying AS "varchar",
            a.data,
            sdr.codice_interno,
            sdr.codice,
            sdr.fase
           FROM ((vendite.vw_resi_da_accreditare a
             JOIN vendite.resi r3 ON ((r3.id = a.reso_id)))
             JOIN config.stati_doc_reso sdr ON ((sdr.id = r3.stato_doc_reso_id)))
          WHERE ((a.etichetta)::text = 'DOVUTA'::text)
          GROUP BY a.reso_id, a.reso_uid, a.reso_numero, a.data, a.destinatario_denominazione, a.emittente_fiscale_id, sdr.codice_interno, sdr.codice, sdr.fase
        )
 SELECT b.area,
    b.competenza_mese,
    b.documento_id,
    b.documento_uid,
    b.codice,
    b.cliente_display,
    b.emittente_fiscale_id,
    b.emittente_soggetto_ruolo_id,
    b.valore_fermo,
    b.unita_ferme,
    b.motivo_fermo,
    COALESCE(mf.classe, 'ANOMALIA'::character varying) AS classe,
    mf.azione,
    b.data_riferimento,
    (CURRENT_DATE - b.data_riferimento) AS anzianita_giorni,
    b.stato_codice_interno,
    b.stato_codice,
    b.fase
   FROM (base b
     LEFT JOIN config.motivi_fermo mf ON ((((mf.codice_interno)::text = (b.motivo_fermo)::text) AND (mf.attivo IS TRUE))))
  WHERE ((COALESCE(mf.classe, 'ANOMALIA'::character varying))::text <> 'FISIOLOGICO'::text);
```


---
{% include-markdown "signature-core.md" %}
