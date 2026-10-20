{% include-markdown "it/dbzero/catalogo/manual/fn_articolo_usato.md" %}
# ⚙️ Funzione `fn_articolo_usato`

```sql
CREATE FUNCTION fn_articolo_usato(p_articolo_id uuid)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_articolo_usato(p_articolo_id uuid)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
    -- Anagrafica dell'articolo, non un suo uso (vedi il COMMENT).
    c_escluse CONSTANT regclass[] := ARRAY[
        'catalogo.articoli_componenti'::regclass,
        'catalogo.articoli_uom_operativa'::regclass,
        'catalogo.note_articoli'::regclass,
        'vendite.articoli_descrizioni_aggiuntive'::regclass,
        'vendite.articolo_regole_fatturazione'::regclass,
        'anagrafiche.soggetti_titoli_iva_ambiti'::regclass];
    v_fk    record;
    v_usato boolean;
BEGIN
    -- =========================================================
    -- Scopo:
    --   true se l'articolo compare in una tabella che lo punta con
    --   una FK (escluse le tabelle di anagrafica dell'articolo),
    --   in qualunque stato. NULL -> false.
    -- =========================================================
    IF p_articolo_id IS NULL THEN
        RETURN false;
    END IF;

    FOR v_fk IN
        SELECT c.conrelid::regclass AS tabella, a.attname AS colonna
          FROM pg_catalog.pg_constraint c
          JOIN pg_catalog.pg_attribute a
            ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
         WHERE c.contype = 'f'
           AND c.confrelid = 'catalogo.articoli'::regclass
           AND array_length(c.conkey, 1) = 1
           AND c.conrelid <> ALL (c_escluse)
         ORDER BY c.conrelid::regclass::text, a.attname
    LOOP
        EXECUTE format('SELECT EXISTS (SELECT 1 FROM %s WHERE %I = $1)',
                       v_fk.tabella, v_fk.colonna)
           INTO v_usato
          USING p_articolo_id;
        IF v_usato THEN
            RETURN true;
        END IF;
    END LOOP;

    RETURN false;
END;
$function$

COMMENT ON FUNCTION catalogo.fn_articolo_usato(p_articolo_id uuid)
IS 'Predicato (A-10 di brief-db-articoli-ammessi-per-documento, 2026-10-13): true se l''articolo e'' USATO, cioe'' compare in una tabella che lo punta con una FK, in qualunque stato (anche chiusa, annullata o attivo = false). Le tabelle si leggono da pg_constraint: una tabella nuova che punta all''articolo conta da sola (fail-closed). Escluse, perche'' anagrafica dell''articolo e non un suo uso: catalogo.articoli_componenti (la distinta ha i suoi guard), catalogo.articoli_uom_operativa, catalogo.note_articoli, vendite.articoli_descrizioni_aggiuntive, vendite.articolo_regole_fatturazione, anagrafiche.soggetti_titoli_iva_ambiti. SECURITY DEFINER: gli articoli sono unici per tutte le aziende, i documenti hanno la RLS per emittente; letto con la RLS di chi modifica l''articolo il predicato non vedrebbe i documenti delle altre aziende. Ritorna solo un boolean. Lo leggono catalogo.trgfn_articoli_guard_struttura_se_usato e dbops.lock_columns_conditional (il form). NULL -> false.';
```

</div>

---
{% include-markdown "signature-core.md" %}
