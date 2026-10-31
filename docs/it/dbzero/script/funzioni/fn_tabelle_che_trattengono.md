{% include-markdown "it/dbzero/script/manual/fn_tabelle_che_trattengono.md" %}
# ⚙️ Funzione `fn_tabelle_che_trattengono`

```sql
CREATE FUNCTION fn_tabelle_che_trattengono(p_tabella regclass, p_ids bigint[], p_escluse regclass[])
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_tabelle_che_trattengono(p_tabella regclass, p_ids bigint[], p_escluse regclass[] DEFAULT ARRAY[]::regclass[])
 RETURNS text[]
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    -- Nudi: una riga del catalogo (pg_constraint), non una
    -- tabella di dominio.
    v_fk      record;
    v_cascata text;
    v_esiste  boolean;
    -- Le tabelle che trattengono, `schema.tabella`.
    v_dove    text[] := ARRAY[]::text[];
BEGIN
    -- =========================================================
    -- Scopo: le tabelle che tengono almeno una delle righe
    --   p_ids di p_tabella con una FK RESTRICT o NO ACTION, in
    --   ordine di nome, una volta ciascuna. '{}' = nessuna.
    --   Vedi l'intestazione del changeSet 20261028-34.
    -- =========================================================
    IF p_tabella IS NULL OR COALESCE(cardinality(p_ids), 0) = 0 THEN
        RETURN v_dove;
    END IF;

    FOR v_fk IN
        SELECT c.conrelid,
               n.nspname AS schema_nome,
               t.relname AS tabella_nome,
               a.attname AS colonna_nome
          FROM pg_catalog.pg_constraint c
          JOIN pg_catalog.pg_class t     ON t.oid = c.conrelid
          JOIN pg_catalog.pg_namespace n ON n.oid = t.relnamespace
          JOIN pg_catalog.pg_attribute a ON a.attrelid = c.conrelid
                                        AND a.attnum   = c.conkey[1]
          JOIN pg_catalog.pg_index pk    ON pk.indrelid = c.confrelid
                                        AND pk.indisprimary
         WHERE c.contype     = 'f'
           AND c.confrelid   = p_tabella
           AND c.confdeltype IN ('r', 'a')
           AND cardinality(c.conkey) = 1
           -- Sulla chiave primaria (a una colonna): i valori sono p_ids.
           AND pk.indnatts   = 1
           AND c.confkey[1]  = pk.indkey[0]
           AND c.conrelid   <> ALL (COALESCE(array_remove(p_escluse, NULL), ARRAY[]::regclass[])::oid[])
         ORDER BY n.nspname, t.relname, a.attname
    LOOP
        -- Le righe della stessa tabella che seguono p_tabella in
        -- CASCADE se ne vanno con lei: non trattengono.
        SELECT string_agg(format('%I = ANY ($1)', a2.attname), ' OR ' ORDER BY a2.attname)
          INTO v_cascata
          FROM pg_catalog.pg_constraint c2
          JOIN pg_catalog.pg_attribute a2 ON a2.attrelid = c2.conrelid
                                         AND a2.attnum   = c2.conkey[1]
         WHERE c2.contype     = 'f'
           AND c2.conrelid    = v_fk.conrelid
           AND c2.confrelid   = p_tabella
           AND c2.confdeltype = 'c';

        EXECUTE format('SELECT EXISTS (SELECT 1 FROM %I.%I WHERE %I = ANY ($1)%s)',
                       v_fk.schema_nome, v_fk.tabella_nome, v_fk.colonna_nome,
                       CASE WHEN v_cascata IS NULL THEN ''
                            ELSE format(' AND NOT (%s)', v_cascata) END)
           INTO v_esiste
          USING p_ids;

        -- Una tabella con due colonne si nomina una volta.
        IF v_esiste
           AND NOT (format('%s.%s', v_fk.schema_nome, v_fk.tabella_nome) = ANY (v_dove)) THEN
            v_dove := array_append(v_dove, format('%s.%s', v_fk.schema_nome, v_fk.tabella_nome));
        END IF;
    END LOOP;

    RETURN v_dove;
END;
$function$

COMMENT ON FUNCTION script.fn_tabelle_che_trattengono(p_tabella regclass, p_ids bigint[], p_escluse regclass[])
IS 'Le tabelle (`schema.tabella`, in ordine di nome, una volta ciascuna) che TRATTENGONO almeno una delle righe p_ids di p_tabella: una FK a una colonna verso la sua chiave primaria con ON DELETE RESTRICT o NO ACTION, derivata da pg_constraint (la prossima FK entra da sola). Escluse le tabelle di p_escluse (chi chiama le cancella prima o le giudica a parte); le righe della stessa tabella che seguono p_tabella in CASCADE non contano. ''{}'' = nessuna (anche con p_tabella o p_ids NULL o vuoti). Un nipote (RESTRICT verso una tabella che segue in CASCADE) non si vede. BB comune di script.fn_check_credenziale_eliminabile (motivo CON_STORIA, prima scritto nel suo corpo) e script.fn_check_versione_listino_eliminabile (motivo CITATA). SECURITY DEFINER del proprietario, search_path bloccato: chi trattiene sta anche sotto RLS, e il motivo e'' uno stato, non una visibilita''; restituisce solo nomi di tabelle. STABLE. Brief: brief-modello-documento-vendita §16.11 (E-3, Tid 2026-10-28).';
```

</div>

---
{% include-markdown "signature-core.md" %}
