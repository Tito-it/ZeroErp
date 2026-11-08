{% include-markdown "it/dbzero/vendite/manual/fn_documento_lineage_nodi.md" %}
# ⚙️ Funzione `fn_documento_lineage_nodi`

```sql
CREATE FUNCTION fn_documento_lineage_nodi(p_tipo_ids bigint[], p_uids text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_documento_lineage_nodi(p_tipo_ids bigint[] DEFAULT NULL::bigint[], p_uids text[] DEFAULT NULL::text[])
 RETURNS TABLE(tipo_id bigint, uid text, codice character varying, stato_codice_interno character varying, stato_codice character varying, stato_descrizione character varying, fase character varying, is_abortito boolean, pipeline_rank smallint, natura_doc_codice_interno character varying, natura_doc_descrizione character varying, tipo_codice_interno character varying)
 LANGUAGE sql
 STABLE
 SET jit TO 'off'
 SET plan_cache_mode TO 'force_generic_plan'
BEGIN ATOMIC
 WITH seme AS MATERIALIZED (
          SELECT array_agg((s.uid)::uuid) FILTER (WHERE ((so.codice_interno)::text = 'PREVENTIVO'::text)) AS prev_uids,
             array_agg((s.uid)::uuid) FILTER (WHERE ((so.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text)) AS off_uids,
             array_agg((s.uid)::bigint) FILTER (WHERE ((so.codice_interno)::text = 'ORDINE_VENDITA'::text)) AS ord_ids,
             array_agg((s.uid)::bigint) FILTER (WHERE ((so.codice_interno)::text = 'CONTRATTO'::text)) AS con_ids,
             array_agg((s.uid)::bigint) FILTER (WHERE ((so.codice_interno)::text = 'DDT_VENDITA'::text)) AS ddt_ids,
             array_agg((s.uid)::bigint) FILTER (WHERE ((so.codice_interno)::text = 'FATTURA'::text)) AS fat_ids,
             array_agg((s.uid)::bigint) FILTER (WHERE ((so.codice_interno)::text = 'COMMESSA'::text)) AS com_ids,
             array_agg((s.uid)::bigint) FILTER (WHERE ((so.codice_interno)::text = 'RESO_VENDITA'::text)) AS res_ids
            FROM (UNNEST(fn_documento_lineage_nodi.p_tipo_ids, fn_documento_lineage_nodi.p_uids) s(tipo_id, uid)
              JOIN config.sorgenti so ON ((so.id = s.tipo_id)))
           WHERE (s.uid IS NOT NULL)
         )
  SELECT s.id,
     (p.uid)::text AS uid,
     p.numero,
     st.codice_interno,
     st.codice,
     st.descrizione,
     st.fase,
     st.is_abortito,
     (1)::smallint AS int2,
     NULL::character varying AS "varchar",
     NULL::character varying AS "varchar",
     s.codice_interno
    FROM ((vendite.preventivi p
      JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'PREVENTIVO'::text) AND (s.attivo IS TRUE))))
      LEFT JOIN config.stati_doc_preventivi st ON ((st.id = p.stato_doc_preventivo_id)))
   WHERE ((fn_documento_lineage_nodi.p_tipo_ids IS NULL) AND (fn_documento_lineage_nodi.p_uids IS NULL))
 UNION ALL
  SELECT s.id,
     (oc.uid)::text AS uid,
     oc.codice,
     st.codice_interno,
     st.codice,
     st.descrizione,
     st.fase,
     st.is_abortito,
     (1)::smallint AS int2,
     NULL::character varying AS "varchar",
     NULL::character varying AS "varchar",
     s.codice_interno
    FROM ((vendite.offerte_commerciali oc
      JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s.attivo IS TRUE))))
      LEFT JOIN config.stati_doc_offerte st ON ((st.id = oc.stato_doc_offerta_id)))
   WHERE ((fn_documento_lineage_nodi.p_tipo_ids IS NULL) AND (fn_documento_lineage_nodi.p_uids IS NULL))
 UNION ALL
  SELECT s.id,
     (o.id)::text AS id,
     o.numero,
     st.codice_interno,
     st.codice,
     st.descrizione,
     st.fase,
     st.is_abortito,
     (2)::smallint AS int2,
     NULL::character varying AS "varchar",
     NULL::character varying AS "varchar",
     s.codice_interno
    FROM ((vendite.ordini o
      JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'ORDINE_VENDITA'::text) AND (s.attivo IS TRUE))))
      LEFT JOIN config.stati_doc_ordini st ON ((st.id = o.stato_doc_ordine_id)))
   WHERE ((fn_documento_lineage_nodi.p_tipo_ids IS NULL) AND (fn_documento_lineage_nodi.p_uids IS NULL))
 UNION ALL
  SELECT s.id,
     (c.id)::text AS id,
     c.numero,
     st.codice_interno,
     st.codice,
     st.descrizione,
     st.fase,
     st.is_abortito,
     (2)::smallint AS int2,
     NULL::character varying AS "varchar",
     NULL::character varying AS "varchar",
     s.codice_interno
    FROM ((vendite.contratti c
      JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'CONTRATTO'::text) AND (s.attivo IS TRUE))))
      LEFT JOIN config.stati_doc_contratti st ON ((st.id = c.stato_doc_contratto_id)))
   WHERE ((fn_documento_lineage_nodi.p_tipo_ids IS NULL) AND (fn_documento_lineage_nodi.p_uids IS NULL))
 UNION ALL
  SELECT s.id,
     (d.id)::text AS id,
     d.numero,
     st.codice_interno,
     st.codice,
     st.descrizione,
     st.fase,
     st.is_abortito,
     (3)::smallint AS int2,
     NULL::character varying AS "varchar",
     NULL::character varying AS "varchar",
     s.codice_interno
    FROM ((vendite.ddt d
      JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'DDT_VENDITA'::text) AND (s.attivo IS TRUE))))
      LEFT JOIN config.stati_doc_ddt st ON ((st.id = d.stato_doc_ddt_id)))
   WHERE ((fn_documento_lineage_nodi.p_tipo_ids IS NULL) AND (fn_documento_lineage_nodi.p_uids IS NULL))
 UNION ALL
  SELECT s.id,
     (f.id)::text AS id,
     (vendite.fn_numero_documento_fattura(f.numero, f.serie))::text AS fn_numero_documento_fattura,
     st.codice_interno,
     st.codice,
     st.descrizione,
     st.fase,
     st.is_abortito,
     (5)::smallint AS int2,
     nd.codice_interno,
     nd.descrizione,
     s.codice_interno
    FROM (((vendite.fatture f
      JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'FATTURA'::text) AND (s.attivo IS TRUE))))
      LEFT JOIN config.stati_doc_fiscale st ON ((st.id = f.stato_doc_fiscale_id)))
      LEFT JOIN config.nature_doc_fiscale nd ON ((nd.id = f.natura_doc_id)))
   WHERE ((fn_documento_lineage_nodi.p_tipo_ids IS NULL) AND (fn_documento_lineage_nodi.p_uids IS NULL))
 UNION ALL
  SELECT s.id,
     (cm.id)::text AS id,
     cm.codice,
     st.codice_interno,
     st.codice,
     st.descrizione,
     st.fase,
     st.is_abortito,
     (4)::smallint AS int2,
     NULL::character varying AS "varchar",
     NULL::character varying AS "varchar",
     s.codice_interno
    FROM ((vendite.commesse cm
      JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'COMMESSA'::text) AND (s.attivo IS TRUE))))
      LEFT JOIN vendite.stati_commessa st ON ((st.id = cm.stato_commessa_id)))
   WHERE ((fn_documento_lineage_nodi.p_tipo_ids IS NULL) AND (fn_documento_lineage_nodi.p_uids IS NULL))
 UNION ALL
  SELECT s.id,
     (r.id)::text AS id,
     r.numero,
     st.codice_interno,
     st.codice,
     st.descrizione,
     st.fase,
     st.is_abortito,
     (0)::smallint AS int2,
     NULL::character varying AS "varchar",
     NULL::character varying AS "varchar",
     s.codice_interno
    FROM ((vendite.resi r
      JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'RESO_VENDITA'::text) AND (s.attivo IS TRUE))))
      LEFT JOIN config.stati_doc_reso st ON ((st.id = r.stato_doc_reso_id)))
   WHERE ((fn_documento_lineage_nodi.p_tipo_ids IS NULL) AND (fn_documento_lineage_nodi.p_uids IS NULL))
 UNION ALL
  SELECT s.id,
     (p.uid)::text AS uid,
     p.numero,
     st.codice_interno,
     st.codice,
     st.descrizione,
     st.fase,
     st.is_abortito,
     (1)::smallint AS int2,
     NULL::character varying AS "varchar",
     NULL::character varying AS "varchar",
     s.codice_interno
    FROM ((vendite.preventivi p
      JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'PREVENTIVO'::text) AND (s.attivo IS TRUE))))
      LEFT JOIN config.stati_doc_preventivi st ON ((st.id = p.stato_doc_preventivo_id)))
   WHERE ((NOT ((fn_documento_lineage_nodi.p_tipo_ids IS NULL) AND (fn_documento_lineage_nodi.p_uids IS NULL))) AND (p.uid = ANY (( SELECT k.prev_uids
            FROM seme k)::uuid[])))
 UNION ALL
  SELECT s.id,
     (oc.uid)::text AS uid,
     oc.codice,
     st.codice_interno,
     st.codice,
     st.descrizione,
     st.fase,
     st.is_abortito,
     (1)::smallint AS int2,
     NULL::character varying AS "varchar",
     NULL::character varying AS "varchar",
     s.codice_interno
    FROM ((vendite.offerte_commerciali oc
      JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s.attivo IS TRUE))))
      LEFT JOIN config.stati_doc_offerte st ON ((st.id = oc.stato_doc_offerta_id)))
   WHERE ((NOT ((fn_documento_lineage_nodi.p_tipo_ids IS NULL) AND (fn_documento_lineage_nodi.p_uids IS NULL))) AND (oc.uid = ANY (( SELECT k.off_uids
            FROM seme k)::uuid[])))
 UNION ALL
  SELECT s.id,
     (o.id)::text AS id,
     o.numero,
     st.codice_interno,
     st.codice,
     st.descrizione,
     st.fase,
     st.is_abortito,
     (2)::smallint AS int2,
     NULL::character varying AS "varchar",
     NULL::character varying AS "varchar",
     s.codice_interno
    FROM ((vendite.ordini o
      JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'ORDINE_VENDITA'::text) AND (s.attivo IS TRUE))))
      LEFT JOIN config.stati_doc_ordini st ON ((st.id = o.stato_doc_ordine_id)))
   WHERE ((NOT ((fn_documento_lineage_nodi.p_tipo_ids IS NULL) AND (fn_documento_lineage_nodi.p_uids IS NULL))) AND (o.id = ANY (( SELECT k.ord_ids
            FROM seme k)::bigint[])))
 UNION ALL
  SELECT s.id,
     (c.id)::text AS id,
     c.numero,
     st.codice_interno,
     st.codice,
     st.descrizione,
     st.fase,
     st.is_abortito,
     (2)::smallint AS int2,
     NULL::character varying AS "varchar",
     NULL::character varying AS "varchar",
     s.codice_interno
    FROM ((vendite.contratti c
      JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'CONTRATTO'::text) AND (s.attivo IS TRUE))))
      LEFT JOIN config.stati_doc_contratti st ON ((st.id = c.stato_doc_contratto_id)))
   WHERE ((NOT ((fn_documento_lineage_nodi.p_tipo_ids IS NULL) AND (fn_documento_lineage_nodi.p_uids IS NULL))) AND (c.id = ANY (( SELECT k.con_ids
            FROM seme k)::bigint[])))
 UNION ALL
  SELECT s.id,
     (d.id)::text AS id,
     d.numero,
     st.codice_interno,
     st.codice,
     st.descrizione,
     st.fase,
     st.is_abortito,
     (3)::smallint AS int2,
     NULL::character varying AS "varchar",
     NULL::character varying AS "varchar",
     s.codice_interno
    FROM ((vendite.ddt d
      JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'DDT_VENDITA'::text) AND (s.attivo IS TRUE))))
      LEFT JOIN config.stati_doc_ddt st ON ((st.id = d.stato_doc_ddt_id)))
   WHERE ((NOT ((fn_documento_lineage_nodi.p_tipo_ids IS NULL) AND (fn_documento_lineage_nodi.p_uids IS NULL))) AND (d.id = ANY (( SELECT k.ddt_ids
            FROM seme k)::bigint[])))
 UNION ALL
  SELECT s.id,
     (f.id)::text AS id,
     (vendite.fn_numero_documento_fattura(f.numero, f.serie))::text AS fn_numero_documento_fattura,
     st.codice_interno,
     st.codice,
     st.descrizione,
     st.fase,
     st.is_abortito,
     (5)::smallint AS int2,
     nd.codice_interno,
     nd.descrizione,
     s.codice_interno
    FROM (((vendite.fatture f
      JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'FATTURA'::text) AND (s.attivo IS TRUE))))
      LEFT JOIN config.stati_doc_fiscale st ON ((st.id = f.stato_doc_fiscale_id)))
      LEFT JOIN config.nature_doc_fiscale nd ON ((nd.id = f.natura_doc_id)))
   WHERE ((NOT ((fn_documento_lineage_nodi.p_tipo_ids IS NULL) AND (fn_documento_lineage_nodi.p_uids IS NULL))) AND (f.id = ANY (( SELECT k.fat_ids
            FROM seme k)::bigint[])))
 UNION ALL
  SELECT s.id,
     (cm.id)::text AS id,
     cm.codice,
     st.codice_interno,
     st.codice,
     st.descrizione,
     st.fase,
     st.is_abortito,
     (4)::smallint AS int2,
     NULL::character varying AS "varchar",
     NULL::character varying AS "varchar",
     s.codice_interno
    FROM ((vendite.commesse cm
      JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'COMMESSA'::text) AND (s.attivo IS TRUE))))
      LEFT JOIN vendite.stati_commessa st ON ((st.id = cm.stato_commessa_id)))
   WHERE ((NOT ((fn_documento_lineage_nodi.p_tipo_ids IS NULL) AND (fn_documento_lineage_nodi.p_uids IS NULL))) AND (cm.id = ANY (( SELECT k.com_ids
            FROM seme k)::bigint[])))
 UNION ALL
  SELECT s.id,
     (r.id)::text AS id,
     r.numero,
     st.codice_interno,
     st.codice,
     st.descrizione,
     st.fase,
     st.is_abortito,
     (0)::smallint AS int2,
     NULL::character varying AS "varchar",
     NULL::character varying AS "varchar",
     s.codice_interno
    FROM ((vendite.resi r
      JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'RESO_VENDITA'::text) AND (s.attivo IS TRUE))))
      LEFT JOIN config.stati_doc_reso st ON ((st.id = r.stato_doc_reso_id)))
   WHERE ((NOT ((fn_documento_lineage_nodi.p_tipo_ids IS NULL) AND (fn_documento_lineage_nodi.p_uids IS NULL))) AND (r.id = ANY (( SELECT k.res_ids
            FROM seme k)::bigint[])));
END

COMMENT ON FUNCTION vendite.fn_documento_lineage_nodi(p_tipo_ids bigint[], p_uids text[])
IS 'I NODI della lineage dei documenti, per chiave del nodo: una riga per documento delle otto testate-nodo (preventivo, offerta, ordine, contratto, DDT, fattura, commessa, reso), con codice, stato nativo, fase, is_abortito, pipeline_rank, natura fiscale (solo sulla fattura) e codice del tipo; un tipo spento in config.sorgenti non da'' nodi. Il seme e'' la chiave del nodo, in due array paralleli: p_tipo_ids[i] e'' un config.sorgenti.id, p_uids[i] la chiave del documento in testo secondo il key_selector (l''uid per preventivo e offerta, l''id per ordine, contratto, DDT, fattura, commessa e reso). Entrambi NULL = tutti i nodi (vendite.vw_documento_lineage_nodi ne e'' la proiezione); array vuoti = zero righe; una coppia con un tipo ignoto o una chiave inesistente non seleziona niente; una chiave fuori forma per il suo tipo fa fallire il cast del seme. Il seme si smista una volta in array tipizzati e ogni ramo cerca per indice (= ANY). I due modi, tutti e col seme, sono rami in UNION ALL, mai `p IS NULL OR`. SET jit = off e plan_cache_mode = force_generic_plan: con un seme non costante il piano tiene i rami dei due modi, e il JIT ne compilerebbe le espressioni a ogni chiamata; con le due clausole la funzione non si incorpora e si pianifica una volta per sessione, e chi la chiama non deve dichiarare niente. BEGIN ATOMIC (le dipendenze stanno in pg_depend), SECURITY INVOKER: la RLS resta di chi legge.';
```

</div>

---
{% include-markdown "signature-core.md" %}
