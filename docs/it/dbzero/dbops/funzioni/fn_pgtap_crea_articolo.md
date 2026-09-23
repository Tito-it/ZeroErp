{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_articolo.md" %}
# ⚙️ Funzione `fn_pgtap_crea_articolo`

```sql
CREATE FUNCTION fn_pgtap_crea_articolo(p_codice character varying, p_gestito boolean, p_requires_lotto boolean, p_requires_serial boolean, p_uom_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_articolo(p_codice character varying, p_gestito boolean DEFAULT true, p_requires_lotto boolean DEFAULT false, p_requires_serial boolean DEFAULT false, p_uom_id bigint DEFAULT NULL::bigint)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un articolo COSTRUITO con i flag che il
--   test sceglie (gestito a magazzino, per lotti, per seriale): pescarne uno
--   dal catalogo darebbe un articolo non gestito, cioe' un rifiuto che
--   sembra un test rosso. UoM: la prima attiva del seed (una vale l'altra).
-- Uso: v_art := dbops.fn_pgtap_crea_articolo('PGT-A', true, true, false);
-- ⭐ Rev 20260923-01: `p_uom_id` per chi la UoM base la deve SCEGLIERE —
--   chi misura le conversioni, che il guard ammette solo fra unita' della
--   stessa tipologia. La colonna e' loccata: o si sceglie qui, o mai piu'.
DECLARE
    v_uom catalogo.unita_misura.id%TYPE;
    v_id  catalogo.articoli.id%TYPE;
BEGIN
    IF p_uom_id IS NULL THEN
        SELECT u.id INTO v_uom FROM catalogo.unita_misura u WHERE u.attivo ORDER BY u.id LIMIT 1;
        IF v_uom IS NULL THEN
            RAISE EXCEPTION 'fn_pgtap_crea_articolo: catalogo.unita_misura e'' vuoto — e'' un seed di 80_data';
        END IF;
    ELSE
        -- ⚠️ Guard sul RISULTATO: una UoM inesistente o spenta qui parla,
        --   invece di arrivare alla FK con un messaggio che non nomina
        --   ne' la fixture ne' il parametro.
        SELECT u.id INTO v_uom
          FROM catalogo.unita_misura u
         WHERE u.id = p_uom_id AND u.attivo;
        IF v_uom IS NULL THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_articolo: p_uom_id = % non e'' una unita'' di misura attiva a catalogo',
                p_uom_id;
        END IF;
    END IF;

    INSERT INTO catalogo.articoli (codice, descrizione, uom_id,
                                   gestito_a_magazzino, requires_lotto, requires_serial)
    VALUES (p_codice, 'Fixture pgTAP: ' || p_codice, v_uom,
            COALESCE(p_gestito, true), COALESCE(p_requires_lotto, false), COALESCE(p_requires_serial, false))
    RETURNING id INTO v_id;
    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_articolo(p_codice character varying, p_gestito boolean, p_requires_lotto boolean, p_requires_serial boolean, p_uom_id bigint)
IS 'Fixture pgTAP: un articolo COSTRUITO con i flag scelti dal test (gestito_a_magazzino, requires_lotto, requires_serial). Pescare un articolo dal catalogo darebbe uno non gestito e un E_MAG_ARTICOLO_NON_GESTITO che sembra un test rosso (brief magazzino Lotto 2, sezione 5). ⭐ Rev 20260923-01: quinto parametro p_uom_id, la UoM BASE — senza, resta la prima attiva del seed. Serve a chi misura le CONVERSIONI: catalogo.trgfn_uom_conversioni_guard_tipo le ammette solo fra unita'' della stessa tipologia, e articoli.uom_id e'' una colonna loccata, quindi la base si sceglie alla nascita o non si sceglie piu''. Solo per i pgTAP.';
```

---
{% include-markdown "signature-core.md" %}
