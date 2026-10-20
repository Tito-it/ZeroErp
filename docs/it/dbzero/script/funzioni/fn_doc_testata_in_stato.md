{% include-markdown "it/dbzero/script/manual/fn_doc_testata_in_stato.md" %}
# ⚙️ Funzione `fn_doc_testata_in_stato`

```sql
CREATE FUNCTION fn_doc_testata_in_stato(p_tabella regclass, p_stato text, p_sempre jsonb)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_doc_testata_in_stato(p_tabella regclass, p_stato text, p_sempre jsonb DEFAULT '[]'::jsonb)
 RETURNS jsonb
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: la testata in p_stato, dal montaggio del lock:
    --   {modificabile, non_modificabili}. non_modificabili =
    --   p_sempre seguite dalle colonne nominate che in p_stato
    --   non si cambiano (ordine del montaggio, senza doppioni);
    --   modificabile = almeno una colonna nominata si cambia.
    -- ⚠️ p_stato nudo: codice_interno di sei vocabolari (polimorfo).
    WITH nominate AS (
        SELECT e ->> 'colonna' AS colonna,
               script.fn_doc_lock_colonna_bloccata(m.regola, p_stato,
                                                   ARRAY[e ->> 'colonna']) IS NULL AS aperta,
               row_number() OVER (ORDER BY m.trigger_nome, x.k) AS ordine
          FROM script.fn_doc_lock_montaggi(p_tabella) AS m
          CROSS JOIN LATERAL jsonb_array_elements(m.regola -> 'colonne')
               WITH ORDINALITY AS x(e, k)
         WHERE m.regola ->> 'building_block' = 'TESTATA'
    )
    SELECT jsonb_build_object(
             'modificabile',     COALESCE(bool_or(n.aperta), false),
             'non_modificabili', COALESCE(p_sempre, '[]'::jsonb)
                                 || COALESCE(jsonb_agg(n.colonna ORDER BY n.ordine)
                                               FILTER (WHERE NOT n.aperta
                                                         AND NOT COALESCE(p_sempre, '[]'::jsonb)
                                                                 @> jsonb_build_array(n.colonna))
                                             , '[]'::jsonb))
      FROM nominate AS n;
$function$

COMMENT ON FUNCTION script.fn_doc_testata_in_stato(p_tabella regclass, p_stato text, p_sempre jsonb)
IS 'Building block (2026-10-10, brief-db-testata-dopo-emissione fase 2): la testata di un documento in p_stato (codice_interno), letta dal montaggio del lock di testata (script.fn_doc_lock_montaggi, decisione di script.fn_doc_lock_colonna_bloccata). jsonb {modificabile, non_modificabili}: non_modificabili = p_sempre (le colonne che la capability dichiara non modificabili in ogni stato) seguite dalle colonne nominate dal lock che in p_stato non si cambiano, nell''ordine del montaggio e senza doppioni; modificabile = almeno una colonna nominata si cambia in p_stato (in bozza tutte; senza lock di testata false). Sostituisce nelle capability di ordine, DDT, contratto, offerta, preventivo e reso le liste scritte a mano dei campi bloccati fuori bozza e gli stati scritti di can_edit_testata: la terza copia della regola, accanto a lock e backend.';
```

</div>

---
{% include-markdown "signature-core.md" %}
