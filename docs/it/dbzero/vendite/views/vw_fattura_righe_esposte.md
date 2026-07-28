{% include-markdown "it/dbzero/vendite/manual/vw_fattura_righe_esposte.md" %}
# 🔍 View `vw_fattura_righe_esposte`

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_fattura_righe_esposte
WITH (security_invoker=on) AS
WITH kit AS (
         SELECT r.fattura_id,
            r.kit_key,
            r.iva_id,
            r.dest_billing_account_id,
            r.kit_articolo_padre_id AS articolo_padre_id,
            r.kit_descrizione_padre AS descrizione_padre,
            min(r.riga_nr) AS riga_nr_padre,
            max(r.uom_id) AS uom_id,
            avg(r.qta) AS qta_media,
            sum(r.imponibile_riga) AS imponibile_totale,
            max((r.iva_natura)::text) AS iva_natura
           FROM vendite.fatture_righe r
          WHERE (r.kit_key IS NOT NULL)
          GROUP BY r.fattura_id, r.kit_key, r.iva_id, r.dest_billing_account_id, r.kit_articolo_padre_id, r.kit_descrizione_padre
        )
 SELECT r.fattura_id,
    'NORMALE'::text AS tipo_riga,
    r.riga_nr,
    r.riga_nr AS ordinamento,
    (0)::smallint AS livello,
    r.id AS fatture_righe_id,
    r.articolo_id,
    r.descrizione,
    r.uom_id,
    r.qta,
    r.prezzo_unitario,
    r.sconto_percentuale,
    r.iva_id,
    r.iva_natura,
    r.imponibile_riga AS imponibile,
    r.dest_billing_account_id,
    NULL::text AS kit_key
   FROM vendite.fatture_righe r
  WHERE (r.kit_key IS NULL)
UNION ALL
 SELECT k.fattura_id,
    'KIT_PADRE'::text AS tipo_riga,
    k.riga_nr_padre AS riga_nr,
    k.riga_nr_padre AS ordinamento,
    (0)::smallint AS livello,
    NULL::bigint AS fatture_righe_id,
    k.articolo_padre_id AS articolo_id,
    k.descrizione_padre AS descrizione,
    k.uom_id,
    k.qta_media AS qta,
        CASE
            WHEN (COALESCE(k.qta_media, (0)::numeric) = (0)::numeric) THEN NULL::numeric
            ELSE (k.imponibile_totale / k.qta_media)
        END AS prezzo_unitario,
    NULL::numeric AS sconto_percentuale,
    k.iva_id,
    k.iva_natura,
    k.imponibile_totale AS imponibile,
    k.dest_billing_account_id,
    k.kit_key
   FROM kit k
UNION ALL
 SELECT r.fattura_id,
    'KIT_COMPONENTE'::text AS tipo_riga,
    r.riga_nr,
    k.riga_nr_padre AS ordinamento,
    (1)::smallint AS livello,
    r.id AS fatture_righe_id,
    r.articolo_id,
    r.descrizione,
    r.uom_id,
    r.qta,
    NULL::numeric AS prezzo_unitario,
    NULL::numeric AS sconto_percentuale,
    r.iva_id,
    r.iva_natura,
    NULL::numeric AS imponibile,
    r.dest_billing_account_id,
    r.kit_key
   FROM (vendite.fatture_righe r
     JOIN kit k ON (((k.fattura_id = r.fattura_id) AND (k.kit_key = r.kit_key) AND (NOT (k.iva_id IS DISTINCT FROM r.iva_id)) AND (NOT (k.dest_billing_account_id IS DISTINCT FROM r.dest_billing_account_id)))))
  WHERE ((r.kit_key IS NOT NULL) AND (r.kit_esposto_in_fattura IS TRUE));
```


---
{% include-markdown "signature-core.md" %}
