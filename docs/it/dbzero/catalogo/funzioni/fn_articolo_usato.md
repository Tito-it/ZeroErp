{% include-markdown "it/dbzero/catalogo/manual/fn_articolo_usato.md" %}
# ⚙️ Funzione `fn_articolo_usato`

```sql
CREATE FUNCTION fn_articolo_usato(p_articolo_id uuid)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

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
    --   in qualunque stato. NULL -> false. Ogni FK si confronta
    --   sulla chiave a cui punta.
    -- =========================================================
    IF p_articolo_id IS NULL THEN
        RETURN false;
    END IF;

    FOR v_fk IN
        SELECT c.conrelid::regclass AS tabella,
               -- Le coppie colonna figlia = colonna dell'articolo, senza
               -- la colonna PERIOD (l'ultima) di una FK temporale.
               array_agg(format('%I', fa.attname) ORDER BY k.ord) AS figlie,
               array_agg(format('%I', pa.attname) ORDER BY k.ord) AS padri,
               bool_and(pa.attname = 'id') AND count(*) = 1 AS su_id
          FROM pg_catalog.pg_constraint c
          CROSS JOIN LATERAL unnest(c.conkey, c.confkey)
                     WITH ORDINALITY AS k(figlia, padre, ord)
          JOIN pg_catalog.pg_attribute fa
            ON fa.attrelid = c.conrelid AND fa.attnum = k.figlia
          JOIN pg_catalog.pg_attribute pa
            ON pa.attrelid = c.confrelid AND pa.attnum = k.padre
         WHERE c.contype = 'f'
           AND c.confrelid = 'catalogo.articoli'::regclass
           AND c.conrelid <> ALL (c_escluse)
           AND NOT (c.conperiod AND k.ord = array_length(c.conkey, 1))
         GROUP BY c.oid, c.conrelid
         ORDER BY c.conrelid::regclass::text, c.oid
    LOOP
        IF v_fk.su_id THEN
            EXECUTE format('SELECT EXISTS (SELECT 1 FROM %s WHERE %s = $1)',
                           v_fk.tabella, v_fk.figlie[1])
               INTO v_usato
              USING p_articolo_id;
        ELSE
            EXECUTE format(
                'SELECT EXISTS (SELECT 1 FROM %s f JOIN catalogo.articoli a ON (%s) WHERE a.id = $1)',
                v_fk.tabella,
                (SELECT string_agg(format('f.%s = a.%s', v_fk.figlie[i], v_fk.padri[i]), ' AND ')
                   FROM generate_subscripts(v_fk.figlie, 1) i))
               INTO v_usato
              USING p_articolo_id;
        END IF;
        IF v_usato THEN
            RETURN true;
        END IF;
    END LOOP;

    RETURN false;
END;
$function$

COMMENT ON FUNCTION catalogo.fn_articolo_usato(p_articolo_id uuid)
IS 'Predicato: true se l''articolo e'' USATO, cioe'' compare in una tabella che lo punta con una FK, in qualunque stato (anche chiusa, annullata o attivo = false). Le tabelle si leggono da pg_constraint: una tabella nuova che punta all''articolo conta da sola (fail-closed). Ogni FK si confronta sulla chiave a cui punta: verso id a una colonna con l''id, verso un''altra chiave (per esempio il codice) o composita confrontando le sue colonne con quelle dell''articolo; la colonna PERIOD di una FK temporale non entra nel confronto. Escluse, perche'' anagrafica dell''articolo e non un suo uso: catalogo.articoli_componenti (la distinta ha i suoi guard), catalogo.articoli_uom_operativa, catalogo.note_articoli, vendite.articoli_descrizioni_aggiuntive, vendite.articolo_regole_fatturazione, anagrafiche.soggetti_titoli_iva_ambiti. SECURITY DEFINER: gli articoli sono unici per tutte le aziende, i documenti hanno la RLS per emittente; letto con la RLS di chi modifica l''articolo il predicato non vedrebbe i documenti delle altre aziende. Ritorna solo un boolean. Lo leggono catalogo.trgfn_articoli_guard_struttura_se_usato e dbops.lock_columns_conditional (il form). NULL -> false.';
```

</div>

---
{% include-markdown "signature-core.md" %}
