{% include-markdown "it/dbzero/script/manual/fn_doc_lock_montaggi.md" %}
# ⚙️ Funzione `fn_doc_lock_montaggi`

```sql
CREATE FUNCTION fn_doc_lock_montaggi(p_tabella regclass)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_doc_lock_montaggi(p_tabella regclass)
 RETURNS TABLE(trigger_nome name, regola jsonb)
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: i trigger «si tocca solo in bozza» montati su
    --   p_tabella, con la regola che i loro argomenti dicono
    --   (script.fn_doc_lock_regola). Il lettore del montaggio:
    --   la capability legge lo stesso dato del lock.
    -- ⚠️ Solo i trigger che scattano: O (origin) e A (always).
    --   Uno disabilitato non ferma niente, e non deve spegnere
    --   niente.
    SELECT t.tgname,
           script.fn_doc_lock_regola(
             CASE t.tgfoid
               WHEN 'vendite.trgfn_doc_righe_lock_fuori_bozza'::regproc   THEN 'RIGHE'
               WHEN 'vendite.trgfn_doc_testata_lock_fuori_bozza'::regproc THEN 'TESTATA'
             END,
             dbops.fn_trigger_argomenti(t.tgargs))
      FROM pg_catalog.pg_trigger t
     WHERE t.tgrelid = p_tabella
       AND NOT t.tgisinternal
       AND t.tgenabled IN ('O', 'A')
       AND t.tgfoid IN ('vendite.trgfn_doc_righe_lock_fuori_bozza'::regproc,
                        'vendite.trgfn_doc_testata_lock_fuori_bozza'::regproc)
     ORDER BY t.tgname;
$function$

COMMENT ON FUNCTION script.fn_doc_lock_montaggi(p_tabella regclass)
IS 'Building block (2026-10-10, brief-db-testata-dopo-emissione fase 1, R-1; D-F2 di Tid: si legge il montaggio, nessuna tabella nuova): il LETTORE DEL MONTAGGIO. I trigger montati su p_tabella che eseguono vendite.trgfn_doc_righe_lock_fuori_bozza o vendite.trgfn_doc_testata_lock_fuori_bozza e che scattano (tgenabled O o A), una riga per trigger in ordine di nome, con la regola che i loro argomenti dicono (pg_trigger.tgargs -> dbops.fn_trigger_argomenti -> script.fn_doc_lock_regola, la stessa grammatica del trigger). Lock e capability leggono cosi'' lo stesso dato e lo capiscono allo stesso modo. Lo usa script.fn_doc_colonna_modificabile.';
```

</div>

---
{% include-markdown "signature-core.md" %}
