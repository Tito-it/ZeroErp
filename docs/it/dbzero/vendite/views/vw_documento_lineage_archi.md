{% include-markdown "it/dbzero/vendite/manual/vw_documento_lineage_archi.md" %}
# 🔍 View `vw_documento_lineage_archi`

> 📝 **Descrizione**
>
> Lineage documenti vendite (Step 2): grafo archi normalizzato A-H + R e N (rami di ritorno). Chiave nodo polimorfa (tipo_id, uid::text). Nodo target decorato via vw_documento_lineage_nodi. security_invoker=on. Base di vw_documento_lineage e fn_documento_lineage. ⭐ rev 2026-08-20 — ARCO N: fattura rettificata -&gt; nota di credito, ricostruito da vendite.fatture_righe.riga_rettificata_id (legame RIGA-RIGA) e NON da vendite.fatture_rettifiche: quel ponte lo popola un task della fase DEFINITIVA, dopo la numerazione, mentre riga_rettificata_id esiste dalla generazione delle righe — il grafo deve mostrare il legame quando c'e', non quando il documento e' chiuso. Stessa scelta dell'arco G (soft-link, non tabella ponte). E' il primo arco fra due nodi dello STESSO tipo (FATTURA-&gt;FATTURA): l'arco X-&gt;X e' escluso perche' sarebbe un ciclo e non una genealogia. ⭐ is_ramo_inverso E' CALCOLATO QUI, una volta sola: prima la lettera R era ripetuta in tre posti (due WHERE della summary e fn_documento_lineage) e il terzo dimenticato non avrebbe rotto niente di visibile — la nota di credito sarebbe solo comparsa come discendente forward, cambiando la frontiera di ogni lista. ⚠️ «Inverso» non e' «all'indietro nel tempo» (la NC nasce dopo): e' ramo di RITORNO — nel reso torna la merce, qui il valore. Espone anche from/to_natura_doc_codice, per distinguere i due nodi FATTURA.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_documento_lineage_archi
WITH (security_invoker=on) AS
WITH archi AS (
         SELECT s_from.id AS from_tipo_id,
            (p.uid)::text AS from_uid,
            s_to.id AS to_tipo_id,
            (o.id)::text AS to_uid,
            NULL::character varying AS ruolo,
            'A'::text AS arco
           FROM (((vendite.ordini o
             JOIN vendite.preventivi p ON ((p.id = o.documento_origine_id)))
             JOIN config.sorgenti s_from ON ((((s_from.codice_interno)::text = 'PREVENTIVO'::text) AND (s_from.attivo IS TRUE))))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'ORDINE_VENDITA'::text) AND (s_to.attivo IS TRUE))))
          WHERE ((o.documento_origine_tipo)::text = 'PREVENTIVO'::text)
        UNION ALL
         SELECT s_from.id,
            cs.sorgente_uid,
            s_to.id,
            (cs.commessa_id)::text AS commessa_id,
            cs.ruolo_link,
            'B'::text AS text
           FROM ((vendite.commesse_sorgenti cs
             JOIN config.sorgenti s_from ON (((s_from.id = cs.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'PREVENTIVO'::text))))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'COMMESSA'::text) AND (s_to.attivo IS TRUE))))
        UNION ALL
         SELECT s_from.id,
            (oc.uid)::text AS uid,
            s_to.id,
            (c.id)::text AS id,
            NULL::character varying AS "varchar",
            'C'::text AS text
           FROM (((vendite.contratti c
             JOIN vendite.offerte_commerciali oc ON ((oc.id = c.offerta_id)))
             JOIN config.sorgenti s_from ON ((((s_from.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s_from.attivo IS TRUE))))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'CONTRATTO'::text) AND (s_to.attivo IS TRUE))))
          WHERE (c.offerta_id IS NOT NULL)
        UNION ALL
         SELECT s_from.id,
            (oc.uid)::text AS uid,
            s_to.id,
            (o.id)::text AS id,
            NULL::character varying AS "varchar",
            'D'::text AS text
           FROM (((vendite.ordini o
             JOIN vendite.offerte_commerciali oc ON ((oc.id = o.documento_origine_id)))
             JOIN config.sorgenti s_from ON ((((s_from.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s_from.attivo IS TRUE))))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'ORDINE_VENDITA'::text) AND (s_to.attivo IS TRUE))))
          WHERE ((o.documento_origine_tipo)::text = 'OFFERTA'::text)
        UNION ALL
         SELECT s_from.id,
            cs.sorgente_uid,
            s_to.id,
            (cs.commessa_id)::text AS commessa_id,
            cs.ruolo_link,
            'E'::text AS text
           FROM ((vendite.commesse_sorgenti cs
             JOIN config.sorgenti s_from ON (((s_from.id = cs.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'ORDINE_VENDITA'::text))))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'COMMESSA'::text) AND (s_to.attivo IS TRUE))))
        UNION ALL
         SELECT s_from.id,
            cs.sorgente_uid,
            s_to.id,
            (cs.commessa_id)::text AS commessa_id,
            cs.ruolo_link,
            'F'::text AS text
           FROM ((vendite.commesse_sorgenti cs
             JOIN config.sorgenti s_from ON (((s_from.id = cs.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'CONTRATTO'::text))))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'COMMESSA'::text) AND (s_to.attivo IS TRUE))))
        UNION ALL
         SELECT DISTINCT s_from.id,
            (af.commessa_id)::text AS commessa_id,
            s_to.id,
            (f.id)::text AS id,
            NULL::character varying AS "varchar",
            'G'::text AS text
           FROM ((((vendite.attivita_fatturabili af
             JOIN vendite.fatture_righe fr ON ((fr.id = af.fattura_riga_id)))
             JOIN vendite.fatture f ON ((f.id = fr.fattura_id)))
             JOIN config.sorgenti s_from ON ((((s_from.codice_interno)::text = 'COMMESSA'::text) AND (s_from.attivo IS TRUE))))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'FATTURA'::text) AND (s_to.attivo IS TRUE))))
          WHERE (af.fattura_riga_id IS NOT NULL)
        UNION ALL
         SELECT s_from.id,
            (o.id)::text AS id,
            s_to.id,
            (d.id)::text AS id,
            NULL::character varying AS "varchar",
            'H'::text AS text
           FROM (((vendite.ddt d
             JOIN config.sorgenti s_from ON (((s_from.id = d.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'ORDINE_VENDITA'::text))))
             JOIN vendite.ordini o ON ((o.uid = d.sorgente_uid)))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'DDT_VENDITA'::text) AND (s_to.attivo IS TRUE))))
        UNION ALL
         SELECT s_from.id,
            (d.id)::text AS id,
            s_to.id,
            (r.id)::text AS id,
            NULL::character varying AS "varchar",
            'R'::text AS text
           FROM (((vendite.resi r
             JOIN config.sorgenti s_from ON (((s_from.id = r.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'DDT_VENDITA'::text))))
             JOIN vendite.ddt d ON ((d.uid = r.sorgente_uid)))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'RESO_VENDITA'::text) AND (s_to.attivo IS TRUE))))
        UNION ALL
         SELECT DISTINCT s_fat.id,
            (rr.fattura_id)::text AS fattura_id,
            s_fat.id,
            (fr.fattura_id)::text AS fattura_id,
            NULL::character varying AS "varchar",
            'N'::text AS text
           FROM ((vendite.fatture_righe fr
             JOIN vendite.fatture_righe rr ON ((rr.id = fr.riga_rettificata_id)))
             JOIN config.sorgenti s_fat ON ((((s_fat.codice_interno)::text = 'FATTURA'::text) AND (s_fat.attivo IS TRUE))))
          WHERE ((fr.riga_rettificata_id IS NOT NULL) AND (rr.fattura_id <> fr.fattura_id))
        )
 SELECT a.from_tipo_id,
    a.from_uid,
    nf.codice AS from_codice,
    a.to_tipo_id,
    a.to_uid,
    nt.codice AS to_codice,
    nt.stato_codice_interno AS to_stato_codice_interno,
    nt.fase AS to_fase,
    nt.is_abortito AS to_is_abortito,
    a.ruolo,
    a.arco,
    (a.arco = ANY (ARRAY['R'::text, 'N'::text])) AS is_ramo_inverso,
    nf.natura_doc_codice AS from_natura_doc_codice,
    nt.natura_doc_codice AS to_natura_doc_codice
   FROM ((archi a
     LEFT JOIN vendite.vw_documento_lineage_nodi nf ON (((nf.tipo_id = a.from_tipo_id) AND (nf.uid = a.from_uid))))
     LEFT JOIN vendite.vw_documento_lineage_nodi nt ON (((nt.tipo_id = a.to_tipo_id) AND (nt.uid = a.to_uid))));
```


---
{% include-markdown "signature-core.md" %}
