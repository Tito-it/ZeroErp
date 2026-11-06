# ⚙️ Funzione `fn_ddt_trigger_ordine_testata`

```sql
CREATE FUNCTION fn_ddt_trigger_ordine_testata(p_sorgente_tipo_id bigint, p_sorgente_uid uuid, p_sorgente_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ddt_trigger_ordine_testata(p_sorgente_tipo_id bigint, p_sorgente_uid uuid, p_sorgente_id bigint DEFAULT NULL::bigint)
 RETURNS character varying
 LANGUAGE sql
 STABLE PARALLEL SAFE
BEGIN ATOMIC
 SELECT o.fatturazione_trigger
    FROM (config.sorgenti so
      JOIN vendite.ordini o ON (((o.id = fn_ddt_trigger_ordine_testata.p_sorgente_id) OR (o.uid = fn_ddt_trigger_ordine_testata.p_sorgente_uid))))
   WHERE ((so.id = fn_ddt_trigger_ordine_testata.p_sorgente_tipo_id) AND ((so.codice_interno)::text = 'ORDINE_VENDITA'::text))
 UNION ALL
  SELECT o.fatturazione_trigger
    FROM (((config.sorgenti so
      JOIN vendite.resi r ON (((r.id = fn_ddt_trigger_ordine_testata.p_sorgente_id) OR (r.uid = fn_ddt_trigger_ordine_testata.p_sorgente_uid))))
      JOIN LATERAL ( SELECT orr.ordine_id
            FROM (vendite.resi_righe rr
              JOIN vendite.ordini_righe orr ON ((orr.id = rr.ordine_riga_id)))
           WHERE (rr.reso_id = r.id)
           ORDER BY rr.id
          LIMIT 1) x ON (true))
      JOIN vendite.ordini o ON ((o.id = x.ordine_id)))
   WHERE ((so.id = fn_ddt_trigger_ordine_testata.p_sorgente_tipo_id) AND ((so.codice_interno)::text = 'RESO_VENDITA'::text));
END

COMMENT ON FUNCTION vendite.fn_ddt_trigger_ordine_testata(p_sorgente_tipo_id bigint, p_sorgente_uid uuid, p_sorgente_id bigint)
IS 'Il fatturazione_trigger dell''ordine dietro la testata di una bolla. Se la testata dichiara un ordine (ORDINE_VENDITA), e'' quell''ordine, cercato con la regola (o.id = p_sorgente_id OR o.uid = p_sorgente_uid). Se dichiara un reso (RESO_VENDITA, la bolla di riconsegna), e'' l''ordine dietro le righe del reso (resi_righe.ordine_riga_id, la prima per id): la riconsegna segue la corsia dell''ordine da cui la merce era partita. NULL se la bolla non viene da un ordine ne'' da un reso nato da un ordine, se la sorgente manca o se il documento non e'' visibile (SECURITY INVOKER: la RLS di chi chiede). Serve alla riga-onere senza legame di fulfillment, scritta a mano sulla bolla, il cui trigger non si legge dal legame. La leggono vendite.fn_ddt_push_diagnosi e script.fn_check_ddt_emittibile. p_sorgente_id e'' in coda, DEFAULT NULL. BEGIN ATOMIC.';
```

</div>

---
{% include-markdown "signature-core.md" %}
