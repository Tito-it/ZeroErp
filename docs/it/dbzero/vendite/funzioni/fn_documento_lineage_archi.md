{% include-markdown "it/dbzero/vendite/manual/fn_documento_lineage_archi.md" %}
# ⚙️ Funzione `fn_documento_lineage_archi`

```sql
CREATE FUNCTION fn_documento_lineage_archi(p_tipo_ids bigint[], p_uids text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_documento_lineage_archi(p_tipo_ids bigint[] DEFAULT NULL::bigint[], p_uids text[] DEFAULT NULL::text[])
 RETURNS TABLE(from_tipo_id bigint, from_uid text, to_tipo_id bigint, to_uid text, ruolo character varying, arco text, is_ramo_inverso boolean, rango_origine smallint)
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
            FROM (UNNEST(fn_documento_lineage_archi.p_tipo_ids, fn_documento_lineage_archi.p_uids) s(tipo_id, uid)
              JOIN config.sorgenti so ON ((so.id = s.tipo_id)))
           WHERE (s.uid IS NOT NULL)
         ), chiavi AS MATERIALIZED (
          SELECT k.prev_uids,
             ( SELECT array_agg(p.id) AS array_agg
                    FROM vendite.preventivi p
                   WHERE (p.uid = ANY (k.prev_uids))) AS prev_ids,
             k.off_uids,
             ( SELECT array_agg(oc.id) AS array_agg
                    FROM vendite.offerte_commerciali oc
                   WHERE (oc.uid = ANY (k.off_uids))) AS off_ids,
             k.ord_ids,
             ( SELECT array_agg(o.uid) AS array_agg
                    FROM vendite.ordini o
                   WHERE (o.id = ANY (k.ord_ids))) AS ord_uids,
             k.con_ids,
             k.ddt_ids,
             k.fat_ids,
             k.com_ids,
             k.res_ids,
             ( SELECT so.id
                    FROM config.sorgenti so
                   WHERE ((so.codice_interno)::text = 'PREVENTIVO'::text)) AS t_prev,
             ( SELECT so.id
                    FROM config.sorgenti so
                   WHERE ((so.codice_interno)::text = 'ORDINE_VENDITA'::text)) AS t_ord,
             ( SELECT so.id
                    FROM config.sorgenti so
                   WHERE ((so.codice_interno)::text = 'CONTRATTO'::text)) AS t_con,
             ( SELECT so.id
                    FROM config.sorgenti so
                   WHERE ((so.codice_interno)::text = 'DDT_VENDITA'::text)) AS t_ddt,
             ( SELECT so.id
                    FROM config.sorgenti so
                   WHERE ((so.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text)) AS t_off
            FROM seme k
         ), cs_semi AS MATERIALIZED (
          SELECT cs.id,
             cs.commessa_id,
             cs.sorgente_tipo_id,
             cs.ruolo_link,
             cs.sorgente_uid AS k_uuid,
             cs.sorgente_id AS k_bigint
            FROM (chiavi k
              JOIN vendite.commesse_sorgenti cs ON (((cs.commessa_id = ANY (k.com_ids)) AND ((((cs.sorgente_tipo_id = k.t_prev) OR (cs.sorgente_tipo_id = k.t_ord)) OR (cs.sorgente_tipo_id = k.t_con)) OR (cs.sorgente_tipo_id = k.t_ddt)))))
         ), prev_k AS MATERIALIZED (
          SELECT p.uid
            FROM vendite.preventivi p
           WHERE ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))
         ), ord_k AS MATERIALIZED (
          SELECT o.id
            FROM vendite.ordini o
           WHERE ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))
         ), archi(from_tipo_id, from_uid, to_tipo_id, to_uid, ruolo, arco) AS (
          SELECT s_from.id,
             (p.uid)::text AS uid,
             s_to.id,
             (o.id)::text AS id,
             NULL::character varying AS "varchar",
             'A'::text AS text
            FROM (((vendite.ordini o
              JOIN config.sorgenti s_from ON (((s_from.id = o.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'PREVENTIVO'::text) AND (s_from.attivo IS TRUE))))
              JOIN vendite.preventivi p ON (((p.id = o.sorgente_id) OR (p.uid = o.sorgente_uid))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'ORDINE_VENDITA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))
         UNION ALL
          SELECT s_from.id,
             (p.uid)::text AS uid,
             s_to.id,
             (cm.id)::text AS id,
             cs.ruolo_link,
             'B'::text
            FROM ((((vendite.commesse_sorgenti cs
              JOIN prev_k p ON ((p.uid = cs.sorgente_uid)))
              JOIN vendite.commesse cm ON ((cm.id = cs.commessa_id)))
              JOIN config.sorgenti s_from ON (((s_from.id = cs.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'PREVENTIVO'::text))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'COMMESSA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))
         UNION ALL
          SELECT s_from.id,
             (oc.uid)::text AS uid,
             s_to.id,
             (c.id)::text AS id,
             NULL::character varying AS "varchar",
             'C'::text
            FROM (((vendite.contratti c
              JOIN config.sorgenti s_from ON (((s_from.id = c.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s_from.attivo IS TRUE))))
              JOIN vendite.offerte_commerciali oc ON (((oc.id = c.sorgente_id) OR (oc.uid = c.sorgente_uid))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'CONTRATTO'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))
         UNION ALL
          SELECT s_from.id,
             (oc.uid)::text AS uid,
             s_to.id,
             (o.id)::text AS id,
             NULL::character varying AS "varchar",
             'D'::text
            FROM (((vendite.ordini o
              JOIN config.sorgenti s_from ON (((s_from.id = o.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s_from.attivo IS TRUE))))
              JOIN vendite.offerte_commerciali oc ON (((oc.id = o.sorgente_id) OR (oc.uid = o.sorgente_uid))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'ORDINE_VENDITA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))
         UNION ALL
          SELECT s_off.id,
             (padre.uid)::text AS uid,
             s_off.id,
             (figlia.uid)::text AS uid,
             NULL::character varying AS "varchar",
             'V'::text
            FROM ((vendite.offerte_commerciali figlia
              JOIN vendite.offerte_commerciali padre ON ((padre.id = figlia.revisione_padre_id)))
              JOIN config.sorgenti s_off ON ((((s_off.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s_off.attivo IS TRUE))))
           WHERE ((figlia.revisione_padre_id IS NOT NULL) AND (fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))
         UNION ALL
          SELECT s_from.id,
             (o.id)::text AS id,
             s_to.id,
             (cm.id)::text AS id,
             cs.ruolo_link,
             'E'::text
            FROM ((((vendite.commesse_sorgenti cs
              JOIN ord_k o ON ((o.id = cs.sorgente_id)))
              JOIN vendite.commesse cm ON ((cm.id = cs.commessa_id)))
              JOIN config.sorgenti s_from ON (((s_from.id = cs.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'ORDINE_VENDITA'::text))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'COMMESSA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))
         UNION ALL
          SELECT s_from.id,
             (c.id)::text AS id,
             s_to.id,
             (cm.id)::text AS id,
             cs.ruolo_link,
             'F'::text
            FROM ((((vendite.commesse_sorgenti cs
              JOIN vendite.contratti c ON ((c.id = cs.sorgente_id)))
              JOIN vendite.commesse cm ON ((cm.id = cs.commessa_id)))
              JOIN config.sorgenti s_from ON (((s_from.id = cs.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'CONTRATTO'::text))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'COMMESSA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))
         UNION ALL
          SELECT s_from.id,
             (d.id)::text AS id,
             s_to.id,
             (cm.id)::text AS id,
             cs.ruolo_link,
             'U'::text
            FROM ((((vendite.commesse_sorgenti cs
              JOIN vendite.ddt d ON ((d.id = cs.sorgente_id)))
              JOIN vendite.commesse cm ON ((cm.id = cs.commessa_id)))
              JOIN config.sorgenti s_from ON (((s_from.id = cs.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'DDT_VENDITA'::text))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'COMMESSA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))
         UNION ALL
          SELECT DISTINCT s_from.id,
             (cm.id)::text AS id,
             s_to.id,
             (f.id)::text AS id,
             NULL::character varying AS "varchar",
             'G'::text
            FROM (((((vendite.attivita_fatturabili af
              JOIN vendite.commesse cm ON ((cm.id = af.commessa_id)))
              JOIN vendite.fatture_righe fr ON ((fr.id = af.fattura_riga_id)))
              JOIN vendite.fatture f ON ((f.id = fr.fattura_id)))
              JOIN config.sorgenti s_from ON ((((s_from.codice_interno)::text = 'COMMESSA'::text) AND (s_from.attivo IS TRUE))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'FATTURA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((af.fattura_riga_id IS NOT NULL) AND (fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))
         UNION ALL
          SELECT s_from.id,
             (o.id)::text AS id,
             s_to.id,
             (d.id)::text AS id,
             NULL::character varying AS "varchar",
             'H'::text
            FROM (((vendite.ddt d
              JOIN config.sorgenti s_from ON (((s_from.id = d.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'ORDINE_VENDITA'::text))))
              JOIN vendite.ordini o ON (((o.id = d.sorgente_id) OR (o.uid = d.sorgente_uid))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'DDT_VENDITA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))
         UNION ALL
          SELECT s_from.id,
             (d.id)::text AS id,
             s_to.id,
             (r.id)::text AS id,
             NULL::character varying AS "varchar",
             'R'::text
            FROM (((vendite.resi r
              JOIN config.sorgenti s_from ON (((s_from.id = r.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'DDT_VENDITA'::text))))
              JOIN vendite.ddt d ON ((d.id = r.sorgente_id)))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'RESO_VENDITA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))
         UNION ALL
          SELECT DISTINCT s_fat.id,
             (rr.fattura_id)::text AS fattura_id,
             s_fat.id,
             (fr.fattura_id)::text AS fattura_id,
             NULL::character varying AS "varchar",
             'N'::text
            FROM ((vendite.fatture_righe fr
              JOIN vendite.fatture_righe rr ON ((rr.id = fr.riga_rettificata_id)))
              JOIN config.sorgenti s_fat ON ((((s_fat.codice_interno)::text = 'FATTURA'::text) AND (s_fat.attivo IS TRUE))))
           WHERE ((fr.riga_rettificata_id IS NOT NULL) AND (rr.fattura_id <> fr.fattura_id) AND (fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))
         UNION ALL
          SELECT DISTINCT s_from.id,
             (r.id)::text AS id,
             s_to.id,
             (fr.fattura_id)::text AS fattura_id,
             NULL::character varying AS "varchar",
             'S'::text
            FROM ((((((vendite.resi_righe_accrediti acc
              JOIN vendite.resi_righe rr ON ((rr.id = acc.resi_riga_id)))
              JOIN vendite.resi r ON ((r.id = rr.reso_id)))
              JOIN vendite.attivita_fatturabili af ON ((af.commessa_attivita_id = acc.commessa_attivita_id)))
              JOIN vendite.fatture_righe fr ON ((fr.id = af.fattura_riga_id)))
              JOIN config.sorgenti s_from ON ((((s_from.codice_interno)::text = 'RESO_VENDITA'::text) AND (s_from.attivo IS TRUE))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'FATTURA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((af.fattura_riga_id IS NOT NULL) AND (fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))
         UNION ALL
          SELECT DISTINCT s_from.id,
             (r.id)::text AS id,
             s_to.id,
             (d.id)::text AS id,
             NULL::character varying AS "varchar",
             'T'::text
            FROM ((((((vendite.resi_righe_riconsegne rrr
              JOIN vendite.resi_righe rr ON ((rr.id = rrr.resi_riga_id)))
              JOIN vendite.resi r ON ((r.id = rr.reso_id)))
              JOIN vendite.ddt_righe dr ON ((dr.id = rrr.ddt_riga_id)))
              JOIN vendite.ddt d ON ((d.id = dr.ddt_id)))
              JOIN config.sorgenti s_from ON ((((s_from.codice_interno)::text = 'RESO_VENDITA'::text) AND (s_from.attivo IS TRUE))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'DDT_VENDITA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))
         UNION ALL
          SELECT s_from.id,
             (p.uid)::text AS uid,
             s_to.id,
             (o.id)::text AS id,
             NULL::character varying AS "varchar",
             'A'::text
            FROM (((vendite.ordini o
              JOIN config.sorgenti s_from ON (((s_from.id = o.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'PREVENTIVO'::text) AND (s_from.attivo IS TRUE))))
              JOIN vendite.preventivi p ON (((p.id = o.sorgente_id) OR (p.uid = o.sorgente_uid))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'ORDINE_VENDITA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (o.sorgente_tipo_id = ( SELECT k.t_prev
                    FROM chiavi k)) AND ((o.sorgente_id = ANY (( SELECT k.prev_ids
                    FROM chiavi k)::bigint[])) OR (o.sorgente_uid = ANY (( SELECT k.prev_uids
                    FROM chiavi k)::uuid[]))))
         UNION ALL
          SELECT s_from.id,
             (p.uid)::text AS uid,
             s_to.id,
             (o.id)::text AS id,
             NULL::character varying AS "varchar",
             'A'::text
            FROM (((vendite.ordini o
              JOIN config.sorgenti s_from ON (((s_from.id = o.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'PREVENTIVO'::text) AND (s_from.attivo IS TRUE))))
              JOIN vendite.preventivi p ON (((p.id = o.sorgente_id) OR (p.uid = o.sorgente_uid))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'ORDINE_VENDITA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (o.id = ANY (( SELECT k.ord_ids
                    FROM chiavi k)::bigint[])) AND ((p.uid = ANY (( SELECT k.prev_uids
                    FROM chiavi k)::uuid[])) IS NOT TRUE))
         UNION ALL
          SELECT s_from.id,
             (p.uid)::text AS uid,
             s_to.id,
             (cm.id)::text AS id,
             cs.ruolo_link,
             'B'::text
            FROM ((((vendite.commesse_sorgenti cs
              JOIN config.sorgenti s_from ON (((s_from.id = cs.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'PREVENTIVO'::text))))
              JOIN vendite.preventivi p ON ((p.uid = cs.sorgente_uid)))
              JOIN vendite.commesse cm ON ((cm.id = cs.commessa_id)))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'COMMESSA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (cs.sorgente_tipo_id = ( SELECT k.t_prev
                    FROM chiavi k)) AND (cs.sorgente_uid = ANY (( SELECT k.prev_uids
                    FROM chiavi k)::uuid[])) AND (p.uid = ANY (( SELECT k.prev_uids
                    FROM chiavi k)::uuid[])))
         UNION ALL
          SELECT s_from.id,
             (p.uid)::text AS uid,
             s_to.id,
             (cm.id)::text AS id,
             cs.ruolo_link,
             'B'::text
            FROM ((((cs_semi cs
              JOIN config.sorgenti s_from ON (((s_from.id = cs.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'PREVENTIVO'::text))))
              JOIN vendite.preventivi p ON ((p.uid = cs.k_uuid)))
              JOIN vendite.commesse cm ON ((cm.id = cs.commessa_id)))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'COMMESSA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (cs.sorgente_tipo_id = ( SELECT k.t_prev
                    FROM chiavi k)) AND ((p.uid = ANY (( SELECT k.prev_uids
                    FROM chiavi k)::uuid[])) IS NOT TRUE))
         UNION ALL
          SELECT s_from.id,
             (oc.uid)::text AS uid,
             s_to.id,
             (c.id)::text AS id,
             NULL::character varying AS "varchar",
             'C'::text
            FROM (((vendite.contratti c
              JOIN config.sorgenti s_from ON (((s_from.id = c.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s_from.attivo IS TRUE))))
              JOIN vendite.offerte_commerciali oc ON (((oc.id = c.sorgente_id) OR (oc.uid = c.sorgente_uid))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'CONTRATTO'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (c.sorgente_tipo_id = ( SELECT k.t_off
                    FROM chiavi k)) AND ((c.sorgente_id = ANY (( SELECT k.off_ids
                    FROM chiavi k)::bigint[])) OR (c.sorgente_uid = ANY (( SELECT k.off_uids
                    FROM chiavi k)::uuid[]))))
         UNION ALL
          SELECT s_from.id,
             (oc.uid)::text AS uid,
             s_to.id,
             (c.id)::text AS id,
             NULL::character varying AS "varchar",
             'C'::text
            FROM (((vendite.contratti c
              JOIN config.sorgenti s_from ON (((s_from.id = c.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s_from.attivo IS TRUE))))
              JOIN vendite.offerte_commerciali oc ON (((oc.id = c.sorgente_id) OR (oc.uid = c.sorgente_uid))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'CONTRATTO'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (c.id = ANY (( SELECT k.con_ids
                    FROM chiavi k)::bigint[])) AND ((oc.uid = ANY (( SELECT k.off_uids
                    FROM chiavi k)::uuid[])) IS NOT TRUE))
         UNION ALL
          SELECT s_from.id,
             (oc.uid)::text AS uid,
             s_to.id,
             (o.id)::text AS id,
             NULL::character varying AS "varchar",
             'D'::text
            FROM (((vendite.ordini o
              JOIN config.sorgenti s_from ON (((s_from.id = o.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s_from.attivo IS TRUE))))
              JOIN vendite.offerte_commerciali oc ON (((oc.id = o.sorgente_id) OR (oc.uid = o.sorgente_uid))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'ORDINE_VENDITA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (o.sorgente_tipo_id = ( SELECT k.t_off
                    FROM chiavi k)) AND ((o.sorgente_id = ANY (( SELECT k.off_ids
                    FROM chiavi k)::bigint[])) OR (o.sorgente_uid = ANY (( SELECT k.off_uids
                    FROM chiavi k)::uuid[]))))
         UNION ALL
          SELECT s_from.id,
             (oc.uid)::text AS uid,
             s_to.id,
             (o.id)::text AS id,
             NULL::character varying AS "varchar",
             'D'::text
            FROM (((vendite.ordini o
              JOIN config.sorgenti s_from ON (((s_from.id = o.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s_from.attivo IS TRUE))))
              JOIN vendite.offerte_commerciali oc ON (((oc.id = o.sorgente_id) OR (oc.uid = o.sorgente_uid))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'ORDINE_VENDITA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (o.id = ANY (( SELECT k.ord_ids
                    FROM chiavi k)::bigint[])) AND ((oc.uid = ANY (( SELECT k.off_uids
                    FROM chiavi k)::uuid[])) IS NOT TRUE))
         UNION ALL
          SELECT s_off.id,
             (padre.uid)::text AS uid,
             s_off.id,
             (figlia.uid)::text AS uid,
             NULL::character varying AS "varchar",
             'V'::text
            FROM ((vendite.offerte_commerciali figlia
              JOIN vendite.offerte_commerciali padre ON ((padre.id = figlia.revisione_padre_id)))
              JOIN config.sorgenti s_off ON ((((s_off.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s_off.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (figlia.revisione_padre_id = ANY (( SELECT k.off_ids
                    FROM chiavi k)::bigint[])))
         UNION ALL
          SELECT s_off.id,
             (padre.uid)::text AS uid,
             s_off.id,
             (figlia.uid)::text AS uid,
             NULL::character varying AS "varchar",
             'V'::text
            FROM ((vendite.offerte_commerciali figlia
              JOIN vendite.offerte_commerciali padre ON ((padre.id = figlia.revisione_padre_id)))
              JOIN config.sorgenti s_off ON ((((s_off.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s_off.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (figlia.id = ANY (( SELECT k.off_ids
                    FROM chiavi k)::bigint[])) AND ((padre.uid = ANY (( SELECT k.off_uids
                    FROM chiavi k)::uuid[])) IS NOT TRUE))
         UNION ALL
          SELECT s_from.id,
             (o.id)::text AS id,
             s_to.id,
             (cm.id)::text AS id,
             cs.ruolo_link,
             'E'::text
            FROM ((((vendite.commesse_sorgenti cs
              JOIN config.sorgenti s_from ON (((s_from.id = cs.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'ORDINE_VENDITA'::text))))
              JOIN vendite.ordini o ON ((o.id = cs.sorgente_id)))
              JOIN vendite.commesse cm ON ((cm.id = cs.commessa_id)))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'COMMESSA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (cs.sorgente_tipo_id = ( SELECT k.t_ord
                    FROM chiavi k)) AND (cs.sorgente_id = ANY (( SELECT k.ord_ids
                    FROM chiavi k)::bigint[])) AND (o.id = ANY (( SELECT k.ord_ids
                    FROM chiavi k)::bigint[])))
         UNION ALL
          SELECT s_from.id,
             (o.id)::text AS id,
             s_to.id,
             (cm.id)::text AS id,
             cs.ruolo_link,
             'E'::text
            FROM ((((cs_semi cs
              JOIN config.sorgenti s_from ON (((s_from.id = cs.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'ORDINE_VENDITA'::text))))
              JOIN vendite.ordini o ON ((o.id = cs.k_bigint)))
              JOIN vendite.commesse cm ON ((cm.id = cs.commessa_id)))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'COMMESSA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (cs.sorgente_tipo_id = ( SELECT k.t_ord
                    FROM chiavi k)) AND ((o.id = ANY (( SELECT k.ord_ids
                    FROM chiavi k)::bigint[])) IS NOT TRUE))
         UNION ALL
          SELECT s_from.id,
             (c.id)::text AS id,
             s_to.id,
             (cm.id)::text AS id,
             cs.ruolo_link,
             'F'::text
            FROM ((((vendite.commesse_sorgenti cs
              JOIN config.sorgenti s_from ON (((s_from.id = cs.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'CONTRATTO'::text))))
              JOIN vendite.contratti c ON ((c.id = cs.sorgente_id)))
              JOIN vendite.commesse cm ON ((cm.id = cs.commessa_id)))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'COMMESSA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (cs.sorgente_tipo_id = ( SELECT k.t_con
                    FROM chiavi k)) AND (cs.sorgente_id = ANY (( SELECT k.con_ids
                    FROM chiavi k)::bigint[])) AND (c.id = ANY (( SELECT k.con_ids
                    FROM chiavi k)::bigint[])))
         UNION ALL
          SELECT s_from.id,
             (c.id)::text AS id,
             s_to.id,
             (cm.id)::text AS id,
             cs.ruolo_link,
             'F'::text
            FROM ((((cs_semi cs
              JOIN config.sorgenti s_from ON (((s_from.id = cs.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'CONTRATTO'::text))))
              JOIN vendite.contratti c ON ((c.id = cs.k_bigint)))
              JOIN vendite.commesse cm ON ((cm.id = cs.commessa_id)))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'COMMESSA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (cs.sorgente_tipo_id = ( SELECT k.t_con
                    FROM chiavi k)) AND ((c.id = ANY (( SELECT k.con_ids
                    FROM chiavi k)::bigint[])) IS NOT TRUE))
         UNION ALL
          SELECT s_from.id,
             (d.id)::text AS id,
             s_to.id,
             (cm.id)::text AS id,
             cs.ruolo_link,
             'U'::text
            FROM ((((vendite.commesse_sorgenti cs
              JOIN config.sorgenti s_from ON (((s_from.id = cs.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'DDT_VENDITA'::text))))
              JOIN vendite.ddt d ON ((d.id = cs.sorgente_id)))
              JOIN vendite.commesse cm ON ((cm.id = cs.commessa_id)))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'COMMESSA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (cs.sorgente_tipo_id = ( SELECT k.t_ddt
                    FROM chiavi k)) AND (cs.sorgente_id = ANY (( SELECT k.ddt_ids
                    FROM chiavi k)::bigint[])) AND (d.id = ANY (( SELECT k.ddt_ids
                    FROM chiavi k)::bigint[])))
         UNION ALL
          SELECT s_from.id,
             (d.id)::text AS id,
             s_to.id,
             (cm.id)::text AS id,
             cs.ruolo_link,
             'U'::text
            FROM ((((cs_semi cs
              JOIN config.sorgenti s_from ON (((s_from.id = cs.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'DDT_VENDITA'::text))))
              JOIN vendite.ddt d ON ((d.id = cs.k_bigint)))
              JOIN vendite.commesse cm ON ((cm.id = cs.commessa_id)))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'COMMESSA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (cs.sorgente_tipo_id = ( SELECT k.t_ddt
                    FROM chiavi k)) AND ((d.id = ANY (( SELECT k.ddt_ids
                    FROM chiavi k)::bigint[])) IS NOT TRUE))
         UNION ALL
          SELECT DISTINCT s_from.id,
             (cm.id)::text AS id,
             s_to.id,
             (f.id)::text AS id,
             NULL::character varying AS "varchar",
             'G'::text
            FROM (((((vendite.attivita_fatturabili af
              JOIN vendite.commesse cm ON ((cm.id = af.commessa_id)))
              JOIN vendite.fatture_righe fr ON ((fr.id = af.fattura_riga_id)))
              JOIN vendite.fatture f ON ((f.id = fr.fattura_id)))
              JOIN config.sorgenti s_from ON ((((s_from.codice_interno)::text = 'COMMESSA'::text) AND (s_from.attivo IS TRUE))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'FATTURA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (af.commessa_id = ANY (( SELECT k.com_ids
                    FROM chiavi k)::bigint[])))
         UNION ALL
          SELECT DISTINCT s_from.id,
             (cm.id)::text AS id,
             s_to.id,
             (f.id)::text AS id,
             NULL::character varying AS "varchar",
             'G'::text
            FROM (((((vendite.fatture_righe fr
              JOIN vendite.fatture f ON ((f.id = fr.fattura_id)))
              JOIN vendite.attivita_fatturabili af ON ((af.fattura_riga_id = fr.id)))
              JOIN vendite.commesse cm ON ((cm.id = af.commessa_id)))
              JOIN config.sorgenti s_from ON ((((s_from.codice_interno)::text = 'COMMESSA'::text) AND (s_from.attivo IS TRUE))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'FATTURA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (fr.fattura_id = ANY (( SELECT k.fat_ids
                    FROM chiavi k)::bigint[])) AND ((cm.id = ANY (( SELECT k.com_ids
                    FROM chiavi k)::bigint[])) IS NOT TRUE))
         UNION ALL
          SELECT s_from.id,
             (o.id)::text AS id,
             s_to.id,
             (d.id)::text AS id,
             NULL::character varying AS "varchar",
             'H'::text
            FROM (((vendite.ddt d
              JOIN config.sorgenti s_from ON (((s_from.id = d.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'ORDINE_VENDITA'::text))))
              JOIN vendite.ordini o ON (((o.id = d.sorgente_id) OR (o.uid = d.sorgente_uid))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'DDT_VENDITA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (d.sorgente_tipo_id = ( SELECT k.t_ord
                    FROM chiavi k)) AND ((d.sorgente_id = ANY (( SELECT k.ord_ids
                    FROM chiavi k)::bigint[])) OR (d.sorgente_uid = ANY (( SELECT k.ord_uids
                    FROM chiavi k)::uuid[]))))
         UNION ALL
          SELECT s_from.id,
             (o.id)::text AS id,
             s_to.id,
             (d.id)::text AS id,
             NULL::character varying AS "varchar",
             'H'::text
            FROM (((vendite.ddt d
              JOIN config.sorgenti s_from ON (((s_from.id = d.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'ORDINE_VENDITA'::text))))
              JOIN vendite.ordini o ON (((o.id = d.sorgente_id) OR (o.uid = d.sorgente_uid))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'DDT_VENDITA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (d.id = ANY (( SELECT k.ddt_ids
                    FROM chiavi k)::bigint[])) AND ((o.id = ANY (( SELECT k.ord_ids
                    FROM chiavi k)::bigint[])) IS NOT TRUE))
         UNION ALL
          SELECT s_from.id,
             (d.id)::text AS id,
             s_to.id,
             (r.id)::text AS id,
             NULL::character varying AS "varchar",
             'R'::text
            FROM (((vendite.resi r
              JOIN config.sorgenti s_from ON (((s_from.id = r.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'DDT_VENDITA'::text))))
              JOIN vendite.ddt d ON ((d.id = r.sorgente_id)))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'RESO_VENDITA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (r.sorgente_tipo_id = ( SELECT k.t_ddt
                    FROM chiavi k)) AND (r.sorgente_id = ANY (( SELECT k.ddt_ids
                    FROM chiavi k)::bigint[])))
         UNION ALL
          SELECT s_from.id,
             (d.id)::text AS id,
             s_to.id,
             (r.id)::text AS id,
             NULL::character varying AS "varchar",
             'R'::text
            FROM (((vendite.resi r
              JOIN config.sorgenti s_from ON (((s_from.id = r.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'DDT_VENDITA'::text))))
              JOIN vendite.ddt d ON ((d.id = r.sorgente_id)))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'RESO_VENDITA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (r.id = ANY (( SELECT k.res_ids
                    FROM chiavi k)::bigint[])) AND ((d.id = ANY (( SELECT k.ddt_ids
                    FROM chiavi k)::bigint[])) IS NOT TRUE))
         UNION ALL
          SELECT DISTINCT s_fat.id,
             (rr.fattura_id)::text AS fattura_id,
             s_fat.id,
             (fr.fattura_id)::text AS fattura_id,
             NULL::character varying AS "varchar",
             'N'::text
            FROM ((vendite.fatture_righe rr
              JOIN vendite.fatture_righe fr ON ((fr.riga_rettificata_id = rr.id)))
              JOIN config.sorgenti s_fat ON ((((s_fat.codice_interno)::text = 'FATTURA'::text) AND (s_fat.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (rr.fattura_id = ANY (( SELECT k.fat_ids
                    FROM chiavi k)::bigint[])) AND (rr.fattura_id <> fr.fattura_id))
         UNION ALL
          SELECT DISTINCT s_fat.id,
             (rr.fattura_id)::text AS fattura_id,
             s_fat.id,
             (fr.fattura_id)::text AS fattura_id,
             NULL::character varying AS "varchar",
             'N'::text
            FROM ((vendite.fatture_righe fr
              JOIN vendite.fatture_righe rr ON ((rr.id = fr.riga_rettificata_id)))
              JOIN config.sorgenti s_fat ON ((((s_fat.codice_interno)::text = 'FATTURA'::text) AND (s_fat.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (fr.fattura_id = ANY (( SELECT k.fat_ids
                    FROM chiavi k)::bigint[])) AND (rr.fattura_id <> fr.fattura_id) AND ((rr.fattura_id = ANY (( SELECT k.fat_ids
                    FROM chiavi k)::bigint[])) IS NOT TRUE))
         UNION ALL
          SELECT DISTINCT s_from.id,
             (r.id)::text AS id,
             s_to.id,
             (fr.fattura_id)::text AS fattura_id,
             NULL::character varying AS "varchar",
             'S'::text
            FROM ((((((vendite.resi_righe rr
              JOIN vendite.resi r ON ((r.id = rr.reso_id)))
              JOIN vendite.resi_righe_accrediti acc ON ((acc.resi_riga_id = rr.id)))
              JOIN vendite.attivita_fatturabili af ON ((af.commessa_attivita_id = acc.commessa_attivita_id)))
              JOIN vendite.fatture_righe fr ON ((fr.id = af.fattura_riga_id)))
              JOIN config.sorgenti s_from ON ((((s_from.codice_interno)::text = 'RESO_VENDITA'::text) AND (s_from.attivo IS TRUE))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'FATTURA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (rr.reso_id = ANY (( SELECT k.res_ids
                    FROM chiavi k)::bigint[])))
         UNION ALL
          SELECT DISTINCT s_from.id,
             (r.id)::text AS id,
             s_to.id,
             (fr.fattura_id)::text AS fattura_id,
             NULL::character varying AS "varchar",
             'S'::text
            FROM ((((((vendite.fatture_righe fr
              JOIN vendite.attivita_fatturabili af ON ((af.fattura_riga_id = fr.id)))
              JOIN vendite.resi_righe_accrediti acc ON ((acc.commessa_attivita_id = af.commessa_attivita_id)))
              JOIN vendite.resi_righe rr ON ((rr.id = acc.resi_riga_id)))
              JOIN vendite.resi r ON ((r.id = rr.reso_id)))
              JOIN config.sorgenti s_from ON ((((s_from.codice_interno)::text = 'RESO_VENDITA'::text) AND (s_from.attivo IS TRUE))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'FATTURA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (fr.fattura_id = ANY (( SELECT k.fat_ids
                    FROM chiavi k)::bigint[])) AND ((r.id = ANY (( SELECT k.res_ids
                    FROM chiavi k)::bigint[])) IS NOT TRUE))
         UNION ALL
          SELECT DISTINCT s_from.id,
             (r.id)::text AS id,
             s_to.id,
             (d.id)::text AS id,
             NULL::character varying AS "varchar",
             'T'::text
            FROM ((((((vendite.resi_righe rr
              JOIN vendite.resi r ON ((r.id = rr.reso_id)))
              JOIN vendite.resi_righe_riconsegne rrr ON ((rrr.resi_riga_id = rr.id)))
              JOIN vendite.ddt_righe dr ON ((dr.id = rrr.ddt_riga_id)))
              JOIN vendite.ddt d ON ((d.id = dr.ddt_id)))
              JOIN config.sorgenti s_from ON ((((s_from.codice_interno)::text = 'RESO_VENDITA'::text) AND (s_from.attivo IS TRUE))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'DDT_VENDITA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (rr.reso_id = ANY (( SELECT k.res_ids
                    FROM chiavi k)::bigint[])))
         UNION ALL
          SELECT DISTINCT s_from.id,
             (r.id)::text AS id,
             s_to.id,
             (d.id)::text AS id,
             NULL::character varying AS "varchar",
             'T'::text
            FROM ((((((vendite.ddt_righe dr
              JOIN vendite.ddt d ON ((d.id = dr.ddt_id)))
              JOIN vendite.resi_righe_riconsegne rrr ON ((rrr.ddt_riga_id = dr.id)))
              JOIN vendite.resi_righe rr ON ((rr.id = rrr.resi_riga_id)))
              JOIN vendite.resi r ON ((r.id = rr.reso_id)))
              JOIN config.sorgenti s_from ON ((((s_from.codice_interno)::text = 'RESO_VENDITA'::text) AND (s_from.attivo IS TRUE))))
              JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'DDT_VENDITA'::text) AND (s_to.attivo IS TRUE))))
           WHERE ((NOT ((fn_documento_lineage_archi.p_tipo_ids IS NULL) AND (fn_documento_lineage_archi.p_uids IS NULL))) AND (dr.ddt_id = ANY (( SELECT k.ddt_ids
                    FROM chiavi k)::bigint[])) AND ((r.id = ANY (( SELECT k.res_ids
                    FROM chiavi k)::bigint[])) IS NOT TRUE))
         )
  SELECT a.from_tipo_id,
     a.from_uid,
     a.to_tipo_id,
     a.to_uid,
     a.ruolo,
     a.arco,
     (a.arco = ANY (ARRAY['R'::text, 'N'::text])) AS is_ramo_inverso,
     (
         CASE a.arco
             WHEN 'A'::text THEN 10
             WHEN 'B'::text THEN 10
             WHEN 'C'::text THEN 10
             WHEN 'D'::text THEN 10
             WHEN 'E'::text THEN 20
             WHEN 'F'::text THEN 20
             WHEN 'H'::text THEN 20
             WHEN 'G'::text THEN 30
             WHEN 'U'::text THEN 40
             WHEN 'R'::text THEN 40
             WHEN 'S'::text THEN 50
             WHEN 'T'::text THEN 50
             WHEN 'N'::text THEN 50
             WHEN 'V'::text THEN 60
             ELSE NULL::integer
         END)::smallint AS rango_origine
    FROM archi a;
END

COMMENT ON FUNCTION vendite.fn_documento_lineage_archi(p_tipo_ids bigint[], p_uids text[])
IS 'Gli ARCHI della lineage dei documenti, grezzi (chiavi, ruolo, lettera A…V, is_ramo_inverso, rango_origine), per chiave del nodo. Il seme e'' quello di vendite.fn_documento_lineage_nodi: il tipo (config.sorgenti.id) e la chiave del documento in testo secondo il key_selector, l''uid per preventivo e offerta e l''id per ordine, contratto, DDT, fattura, commessa e reso, in due array paralleli; entrambi NULL = tutti gli archi (vendite.vw_documento_lineage_archi ne e'' la proiezione decorata); array vuoti, tipo ignoto o chiave inesistente non seminano niente; una chiave fuori forma per il suo tipo fa fallire il cast del seme. Col seme: gli archi uscenti da un nodo del seme e quelli entranti il cui from non sta nel seme, ciascuno una volta, con gli stessi DISTINCT del modo senza seme (G, N, S, T). Il seme scende come array (= ANY) sulla prima tabella di ogni ramo. Gli archi A (preventivo -> ordine), C (offerta -> contratto), D (offerta -> ordine) e H (ordine -> bolla) leggono la provenienza di testata del documento a valle (sorgente_*) con la regola d''incontro (doc.id = sorgente_id OR doc.uid = sorgente_uid), in tutti e due i modi, con gli indici ix_ordini_v_sorgente_uid / _id, ix_contratti_sorgente_uid / _id e ix_ddt_v_sorgente / ix_ddt_v_sorgente_id. L''arco R (bolla -> reso) la legge per sorgente_id, in tutti e due i modi, con l''indice ix_resi_sorgente_id: un reso nasce solo da una bolla, che ha chiave id. Nei rami B, E, F, U (le sorgenti delle commesse) la chiave del link sta nella colonna del suo tipo, vendite.commesse_sorgenti.sorgente_uid per il preventivo e sorgente_id per ordine, contratto e DDT (indici ix_commesse_sorgenti_sorgente_uid e uq_commesse_sorgenti_sorgente_commessa): il join verso il documento confronta colonne dello stesso tipo, senza cast, ed e'' leakproof anche sotto RLS. V e'' la revisione dell''offerta (madre -> figlia, revisione_padre_id), rango 60, non un''origine. Il vocabolario delle lettere e'' quello di vendite.vw_documento_lineage_archi: un arco nuovo si aggiunge qui, nei due modi. SET jit = off e plan_cache_mode = force_generic_plan: la funzione si pianifica una volta per sessione. BEGIN ATOMIC, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
