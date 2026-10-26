{% include-markdown "it/dbzero/vendite/manual/vw_dash_fatturazione_documenti.md" %}
# 🔍 View `vw_dash_fatturazione_documenti`

> 📝 **Descrizione**
>
> Union dei resolver per la dashboard fatturazione: preventivi, ordini, offerte, contratti, commesse e — dal 2026-07-18 (step 6, brief-db-fatturazione-ddt-resi §4a) — DDT. Le due lenti derivano da qui: il serbatoio filtra fase &lt;&gt; CHIUSO, il backlog filtra classe &lt;&gt; FISIOLOGICO. security_invoker=on (ri-specificato a ogni REPLACE: la reloption non e' visibile in pg_get_viewdef e verrebbe azzerata in silenzio -&gt; bypass RLS). ⭐ Rev 2026-08-18 (R-4, brief perimetro-emittente Fase E): aggiunta in coda `emittente_ragione_sociale`. ⚠️ Rev 2026-08-18 (-74, CORREZIONE): la prima stesura risolveva il nome da `emittente_soggetto_ruolo_id` dando per buono che «i sei resolver la portano tutti». NON e' vero: cinque su sei la scrivono NULL::bigint a mano (solo commesse ha il valore), quindi la colonna usciva vuota su 274 righe su 274 — e su vw_dash_aperto_documenti, che esclude l'area COMMESSE, sarebbe stata vuota per sempre. Ora la chiave si risolve con COALESCE(emittente_soggetto_ruolo_id, emittenti_fiscali.soggetto_ruolo_id): stessa cura gia' adottata in -63 per il ramo resi, e una sola catena di JOIN. ⚠️ La colonna `emittente_soggetto_ruolo_id` esposta resta NULL sui cinque rami: cambiarne la semantica e' una decisione a parte, non una correzione. Chi filtra su quella colonna ottiene zero righe su cinque aree su sei — per il perimetro emittente si usa `emittente_fiscale_id`.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_fatturazione_documenti
WITH (security_invoker=on) AS
SELECT d.area,
    d.competenza_mese,
    d.documento_id,
    d.documento_uid,
    d.codice,
    d.emittente_fiscale_id,
    d.emittente_soggetto_ruolo_id,
    d.valore_totale,
    d.valore_transitato,
    d.unita_totali,
    d.unita_transitate,
    d.is_transitato,
    d.is_abortito,
    d.motivo_fermo,
    d.stato_codice_interno,
    d.stato_codice,
    d.fase,
    d.cliente_display,
    d.data_riferimento,
    s_ef.ragione_sociale_completa AS emittente_ragione_sociale
   FROM (((( SELECT p.area,
            p.competenza_mese,
            p.documento_id,
            p.documento_uid,
            p.codice,
            p.emittente_fiscale_id,
            p.emittente_soggetto_ruolo_id,
            p.valore_totale,
            p.valore_transitato,
            p.unita_totali,
            p.unita_transitate,
            p.is_transitato,
            p.is_abortito,
            p.motivo_fermo,
            p.stato_codice_interno,
            p.stato_codice,
            p.fase,
            p.cliente_display,
            p.data_riferimento
           FROM vendite.vw_dash_fatturazione_preventivi p
        UNION ALL
         SELECT o.area,
            o.competenza_mese,
            o.documento_id,
            o.documento_uid,
            o.codice,
            o.emittente_fiscale_id,
            o.emittente_soggetto_ruolo_id,
            o.valore_totale,
            o.valore_transitato,
            o.unita_totali,
            o.unita_transitate,
            o.is_transitato,
            o.is_abortito,
            o.motivo_fermo,
            o.stato_codice_interno,
            o.stato_codice,
            o.fase,
            o.cliente_display,
            o.data_riferimento
           FROM vendite.vw_dash_fatturazione_ordini o
        UNION ALL
         SELECT f.area,
            f.competenza_mese,
            f.documento_id,
            f.documento_uid,
            f.codice,
            f.emittente_fiscale_id,
            f.emittente_soggetto_ruolo_id,
            f.valore_totale,
            f.valore_transitato,
            f.unita_totali,
            f.unita_transitate,
            f.is_transitato,
            f.is_abortito,
            f.motivo_fermo,
            f.stato_codice_interno,
            f.stato_codice,
            f.fase,
            f.cliente_display,
            f.data_riferimento
           FROM vendite.vw_dash_fatturazione_offerte f
        UNION ALL
         SELECT c.area,
            c.competenza_mese,
            c.documento_id,
            c.documento_uid,
            c.codice,
            c.emittente_fiscale_id,
            c.emittente_soggetto_ruolo_id,
            c.valore_totale,
            c.valore_transitato,
            c.unita_totali,
            c.unita_transitate,
            c.is_transitato,
            c.is_abortito,
            c.motivo_fermo,
            c.stato_codice_interno,
            c.stato_codice,
            c.fase,
            c.cliente_display,
            c.data_riferimento
           FROM vendite.vw_dash_fatturazione_contratti c
        UNION ALL
         SELECT m.area,
            m.competenza_mese,
            m.documento_id,
            m.documento_uid,
            m.codice,
            m.emittente_fiscale_id,
            m.emittente_soggetto_ruolo_id,
            m.valore_totale,
            m.valore_transitato,
            m.unita_totali,
            m.unita_transitate,
            m.is_transitato,
            m.is_abortito,
            m.motivo_fermo,
            m.stato_codice_interno,
            m.stato_codice,
            m.fase,
            m.cliente_display,
            m.data_riferimento
           FROM vendite.vw_dash_fatturazione_commesse m
        UNION ALL
         SELECT t.area,
            t.competenza_mese,
            t.documento_id,
            t.documento_uid,
            t.codice,
            t.emittente_fiscale_id,
            t.emittente_soggetto_ruolo_id,
            t.valore_totale,
            t.valore_transitato,
            t.unita_totali,
            t.unita_transitate,
            t.is_transitato,
            t.is_abortito,
            t.motivo_fermo,
            t.stato_codice_interno,
            t.stato_codice,
            t.fase,
            t.cliente_display,
            t.data_riferimento
           FROM vendite.vw_dash_fatturazione_ddt t) d
     LEFT JOIN anagrafiche.emittenti_fiscali ef ON ((ef.id = d.emittente_fiscale_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON ((sr_ef.id = COALESCE(d.emittente_soggetto_ruolo_id, ef.soggetto_ruolo_id))))
     LEFT JOIN anagrafiche.soggetti s_ef ON ((s_ef.id = sr_ef.soggetto_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
