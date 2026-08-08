{% include-markdown "it/dbzero/vendite/manual/vw_contatore_merce.md" %}
# 🔍 View `vw_contatore_merce`

> 📝 **Descrizione**
>
> Il contatore (brief-db-fatturazione-ddt-resi §3a, step 1): per riga d'ordine (partita di merce ORDER-BACKED, non composita) espone tenuti (Σ ordini_righe_fulfillment.qta_evasa − Σ vw_resi_righe_effettive.quantita, tutti i tipi) e fatturati (Σ attivita_fatturabili.quantita NORMALE sui segmenti ORD:*:R:&lt;ordine_riga&gt; + DDT:*:R:&lt;ddt_riga&gt; attribuiti via fulfillment; l'esistenza della AF E' la frontiera EMESSA). differenza = tenuti − fatturati: &gt;0 fattura, &lt;0 accredita, =0 niente. Fonte unica per lister DDT / coda accrediti / resolver. STANDALONE e COMPOSITI esclusi (follow-up). security_invoker=on + RLS. rev 2026-07-17.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_contatore_merce
WITH (security_invoker=on) AS
WITH ful AS (
         SELECT f.ordine_riga_id,
            sum(f.qta_evasa) AS evaso
           FROM vendite.ordini_righe_fulfillment f
          GROUP BY f.ordine_riga_id
        ), res AS (
         SELECT e.ordine_riga_id,
            sum(e.quantita) AS reso
           FROM vendite.vw_resi_righe_effettive e
          WHERE (e.ordine_riga_id IS NOT NULL)
          GROUP BY e.ordine_riga_id
        ), af_seg AS (
         SELECT af.quantita,
            split_part((ca.segment_key)::text, ':'::text, 1) AS seg_tipo,
            ("substring"((ca.segment_key)::text, ':R:([0-9]+)'::text))::bigint AS seg_riga_id
           FROM (vendite.attivita_fatturabili af
             JOIN vendite.commesse_attivita ca ON ((ca.id = af.commessa_attivita_id)))
          WHERE (((af.tipo_movimento)::text = 'NORMALE'::text) AND (split_part((ca.segment_key)::text, ':'::text, 1) = ANY (ARRAY['ORD'::text, 'DDT'::text])) AND ((ca.segment_key)::text ~ ':R:[0-9]+'::text))
        ), fatt AS (
         SELECT x.ordine_riga_id,
            sum(x.quantita) AS fatturati
           FROM ( SELECT s.seg_riga_id AS ordine_riga_id,
                    s.quantita
                   FROM af_seg s
                  WHERE (s.seg_tipo = 'ORD'::text)
                UNION ALL
                 SELECT f.ordine_riga_id,
                    s.quantita
                   FROM (af_seg s
                     JOIN vendite.ordini_righe_fulfillment f ON ((f.ddt_riga_id = s.seg_riga_id)))
                  WHERE (s.seg_tipo = 'DDT'::text)) x
          GROUP BY x.ordine_riga_id
        ), partite AS (
         SELECT ful_1.ordine_riga_id
           FROM ful ful_1
        UNION
         SELECT res_1.ordine_riga_id
           FROM res res_1
        )
 SELECT orr.id AS ordine_riga_id,
    orr.ordine_id,
    orr.articolo_id,
    (COALESCE(ful.evaso, (0)::numeric) - COALESCE(res.reso, (0)::numeric)) AS tenuti,
    COALESCE(fatt.fatturati, (0)::numeric) AS fatturati,
    ((COALESCE(ful.evaso, (0)::numeric) - COALESCE(res.reso, (0)::numeric)) - COALESCE(fatt.fatturati, (0)::numeric)) AS differenza
   FROM (((((partite p
     JOIN vendite.ordini_righe orr ON ((orr.id = p.ordine_riga_id)))
     JOIN catalogo.articoli art ON ((art.id = orr.articolo_id)))
     LEFT JOIN ful ON ((ful.ordine_riga_id = orr.id)))
     LEFT JOIN res ON ((res.ordine_riga_id = orr.id)))
     LEFT JOIN fatt ON ((fatt.ordine_riga_id = orr.id)))
  WHERE (NOT COALESCE(art.is_composito, false));
```


---
{% include-markdown "signature-core.md" %}
