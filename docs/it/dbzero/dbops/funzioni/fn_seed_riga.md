{% include-markdown "it/dbzero/dbops/manual/fn_seed_riga.md" %}
# ⚙️ Funzione `fn_seed_riga`

```sql
CREATE FUNCTION fn_seed_riga(p_tabella regclass, p_riga_id text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_seed_riga(p_tabella regclass, p_riga_id text)
 RETURNS TABLE(seed_riga_id bigint, schema_name text, table_name text, personalizzata_il timestamp with time zone)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT s.id,
     s.schema_name,
     s.table_name,
     s.personalizzata_il
    FROM ((dbops.seed_righe s
      JOIN pg_class c ON ((c.oid = (fn_seed_riga.p_tabella)::oid)))
      JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
   WHERE ((s.schema_name = (n.nspname)::text) AND (s.table_name = (c.relname)::text) AND (s.riga_id = fn_seed_riga.p_riga_id));
END

COMMENT ON FUNCTION dbops.fn_seed_riga(p_tabella regclass, p_riga_id text)
IS 'La voce di dbops.seed_righe per la riga p_riga_id (la chiave primaria id, come testo) della tabella p_tabella: una riga se la riga e'' nata dal seed, nessuna se l''ha creata l''installazione o se la tabella non e'' iscritta al seed di primo impianto. seed_riga_id e'' l''id della voce, personalizzata_il dice se l''installazione l''ha gia'' modificata. Lo schema e il nome della tabella si leggono dal catalogo, non dal testo di regclass (che dipende dal search_path). La leggono il guard script.trgfn_seed_primo_impianto e le superfici config.vw_email_account_seed e config.vw_email_template_seed. SECURITY INVOKER, STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
