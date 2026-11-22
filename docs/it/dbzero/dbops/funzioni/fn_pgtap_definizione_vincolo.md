{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_definizione_vincolo.md" %}
# ⚙️ Funzione `fn_pgtap_definizione_vincolo`

```sql
CREATE FUNCTION fn_pgtap_definizione_vincolo(p_tabella regclass, p_vincolo name)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_definizione_vincolo(p_tabella regclass, p_vincolo name)
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la definizione del vincolo p_vincolo di p_tabella, come la scrive
--   pg_get_constraintdef per un vincolo nato sul database. Un IN su varchar
--   riletto da un dump (cast su ogni elemento) torna alla forma col cast
--   sull'array. NULL se il vincolo non c'e'.
-- Uso:
--   SELECT is(dbops.fn_pgtap_definizione_vincolo('magazzino.inventari', 'chk_mag_inventari_stato'),
--             'CHECK (…)', '…');
DECLARE
    -- Un elemento della forma riletta: ('…'::character varying)::text, con
    -- l'apice raddoppiato dentro il letterale.
    c_elemento CONSTANT text := $re$\('(?:[^']|'')*'::character varying\)::text$re$;
    v_testo    text;
    v_trovato  text[];
BEGIN
    SELECT pg_catalog.pg_get_constraintdef(k.oid) INTO v_testo
      FROM pg_catalog.pg_constraint k
     WHERE k.conrelid = p_tabella
       AND k.conname  = p_vincolo;

    IF v_testo IS NULL THEN
        RETURN NULL;
    END IF;

    -- Un array per giro: termina perche' l'array riscritto comincia con
    -- «((ARRAY[» e non e' piu' della forma cercata.
    LOOP
        v_trovato := regexp_match(
            v_testo,
            '(ANY|ALL) \(ARRAY\[(' || c_elemento || '(?:, ' || c_elemento || ')*)\]\)');
        EXIT WHEN v_trovato IS NULL;

        v_testo := replace(
            v_testo,
            v_trovato[1] || ' (ARRAY[' || v_trovato[2] || '])',
            v_trovato[1] || ' ((ARRAY['
                || regexp_replace(v_trovato[2],
                                  $re$\(('(?:[^']|'')*'::character varying)\)::text$re$,
                                  '\1', 'g')
                || '])::text[])');
    END LOOP;

    RETURN v_testo;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_definizione_vincolo(p_tabella regclass, p_vincolo name)
IS 'Fixture pgTAP: la definizione del vincolo p_vincolo della tabella p_tabella (pg_get_constraintdef) nella forma che il vincolo ha quando nasce sul database, la stessa di un database costruito dal changelog. Su PostgreSQL 19 un IN su una colonna varchar riletto da un dump (pg_upgrade, restore) si scrive col cast su ogni elemento, ANY (ARRAY[(''A''::character varying)::text, ...]): la funzione lo riporta alla forma col cast sull''array, ANY ((ARRAY[''A''::character varying, ...])::text[]), array per array, ANY e ALL. Un array con elementi di altra forma resta com''e''. NULL se il vincolo non esiste.';
```

</div>

---
{% include-markdown "signature-core.md" %}
