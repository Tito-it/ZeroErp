{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_articolo.md" %}
# ⚙️ Funzione `fn_pgtap_crea_articolo`

```sql
CREATE FUNCTION fn_pgtap_crea_articolo(p_codice character varying, p_gestito boolean, p_requires_lotto boolean, p_requires_serial boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_articolo(p_codice character varying, p_gestito boolean DEFAULT true, p_requires_lotto boolean DEFAULT false, p_requires_serial boolean DEFAULT false)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un articolo COSTRUITO con i flag che il
--   test sceglie (gestito a magazzino, per lotti, per seriale): pescarne uno
--   dal catalogo darebbe un articolo non gestito, cioe' un rifiuto che
--   sembra un test rosso. UoM: la prima attiva del seed (una vale l'altra).
-- Uso: v_art := dbops.fn_pgtap_crea_articolo('PGT-A', true, true, false);
DECLARE
    v_uom catalogo.unita_misura.id%TYPE;
    v_id  catalogo.articoli.id%TYPE;
BEGIN
    SELECT u.id INTO v_uom FROM catalogo.unita_misura u WHERE u.attivo ORDER BY u.id LIMIT 1;
    IF v_uom IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_crea_articolo: catalogo.unita_misura e'' vuoto — e'' un seed di 80_data';
    END IF;
    INSERT INTO catalogo.articoli (codice, descrizione, uom_id,
                                   gestito_a_magazzino, requires_lotto, requires_serial)
    VALUES (p_codice, 'Fixture pgTAP: ' || p_codice, v_uom,
            COALESCE(p_gestito, true), COALESCE(p_requires_lotto, false), COALESCE(p_requires_serial, false))
    RETURNING id INTO v_id;
    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_articolo(p_codice character varying, p_gestito boolean, p_requires_lotto boolean, p_requires_serial boolean)
IS 'Fixture pgTAP: un articolo COSTRUITO con i flag scelti dal test (gestito_a_magazzino, requires_lotto, requires_serial), UoM la prima attiva del seed. Pescare un articolo dal catalogo darebbe uno non gestito e un E_MAG_ARTICOLO_NON_GESTITO che sembra un test rosso (brief magazzino Lotto 2, sezione 5). Solo per i pgTAP.';
```

---
{% include-markdown "signature-core.md" %}
