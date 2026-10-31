# ⚙️ Funzione `fn_articolo_quota_fissa_a_canone`

```sql
CREATE FUNCTION fn_articolo_quota_fissa_a_canone(p_articolo_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_articolo_quota_fissa_a_canone(p_articolo_id uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT (EXISTS ( SELECT 1
            FROM (catalogo.articoli a
              JOIN config.listini_tipologie t ON (((t.id = a.listino_tipologia_id) AND (t.e_quota_fissa IS TRUE))))
           WHERE ((a.id = fn_articolo_quota_fissa_a_canone.p_articolo_id) AND (EXISTS ( SELECT 1
                    FROM vendite.fn_articolo_erogazioni(a.id) e(tipo_erogazione, fonte_quantita_attesa, e_default, origine, ordine)
                   WHERE ((e.e_default IS TRUE) AND ((e.tipo_erogazione)::text = 'CANONE'::text))))))) AS "exists";
END

COMMENT ON FUNCTION vendite.fn_articolo_quota_fissa_a_canone(p_articolo_id uuid)
IS 'L''articolo e'' una quota fissa a canone: tipologia di listino di quota fissa (config.listini_tipologie.e_quota_fissa) ed erogazione di default CANONE (vendite.fn_articolo_erogazioni). Si addebita da se'', ogni periodo, a ogni contratto del listino che non la ritocca: per questo la sua riga di listino deve avere la periodicita''. Sede unica (regola del 2): la leggono il motivo 3 di script.fn_check_versione_listino_attivabile e il guard vendite.trgfn_listini_righe_guard_periodicita_quota_fissa. SECURITY INVOKER. Nasce il 2026-10-31 (20261031-49), brief-db-contratto-righe-periodiche-in-commessa §7.10.';
```

</div>

---
{% include-markdown "signature-core.md" %}
