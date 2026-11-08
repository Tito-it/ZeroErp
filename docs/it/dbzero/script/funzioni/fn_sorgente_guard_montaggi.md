# ⚙️ Funzione `fn_sorgente_guard_montaggi`

```sql
CREATE FUNCTION fn_sorgente_guard_montaggi()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_sorgente_guard_montaggi()
 RETURNS TABLE(tabella regclass, schema_tabella name, nome_tabella name, livello_minimo text, azione_cancellazione text, argomenti_validi boolean, ha_sorgente_riga boolean, ha_sorgente_dettaglio boolean)
 LANGUAGE sql
 STABLE
 SET search_path TO 'pg_catalog', 'pg_temp'
BEGIN ATOMIC
 SELECT DISTINCT ON (tg.tgrelid) (tg.tgrelid)::regclass AS tgrelid,
     n.nspname,
     c.relname,
     a.livello_minimo,
     a.azione_cancellazione,
     a.valido,
     (EXISTS ( SELECT 1
            FROM pg_attribute r
           WHERE ((r.attrelid = tg.tgrelid) AND (r.attname = 'sorgente_riga'::name) AND (r.attnum > 0) AND (NOT r.attisdropped)))) AS "exists",
     (EXISTS ( SELECT 1
            FROM pg_attribute d
           WHERE ((d.attrelid = tg.tgrelid) AND (d.attname = 'sorgente_dettaglio'::name) AND (d.attnum > 0) AND (NOT d.attisdropped)))) AS "exists"
    FROM (((pg_trigger tg
      JOIN pg_class c ON ((c.oid = tg.tgrelid)))
      JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
      CROSS JOIN LATERAL script.fn_sorgente_guard_argomenti(dbops.fn_trigger_argomenti(tg.tgargs)) a(livello_minimo, azione_cancellazione, valido))
   WHERE ((tg.tgfoid = ('script.trgfn_guard_sorgente()'::regprocedure)::oid) AND (NOT tg.tgisinternal) AND ((c.relpersistence <> 't'::"char") OR ((n.oid = pg_my_temp_schema()) AND has_table_privilege(tg.tgrelid, 'SELECT'::text))))
   ORDER BY tg.tgrelid, tg.tgname;
END

COMMENT ON FUNCTION script.fn_sorgente_guard_montaggi()
IS 'Le tabelle che montano il guard unico della provenienza (script.trgfn_guard_sorgente), con quello che hanno dichiarato negli argomenti del trigger, letti con script.fn_sorgente_guard_argomenti: il livello minimo, l''azione quando l''origine si cancella (BLOCCA o CANCELLA), se gli argomenti sono validi; piu'' se la tabella ha le colonne sorgente_riga e sorgente_dettaglio. Una riga per tabella. Delle tabelle temporanee tiene solo quelle della sessione, leggibili da chi chiede. La leggono il lato «in uscita» (script.trgfn_sorgente_in_uscita) e il perimetro dei presidi (dbops.fn_sorgenti_orfane_perimetro). INVOKER, STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
