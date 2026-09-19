{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_magazzino.md" %}
# ⚙️ Funzione `fn_pgtap_crea_magazzino`

```sql
CREATE FUNCTION fn_pgtap_crea_magazzino(p_codice character varying, p_usa_ubicazioni boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_magazzino(p_codice character varying, p_usa_ubicazioni boolean DEFAULT false)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un magazzino dell'EMITTENTE DELL'OPERATORE
--   in sessione (script.fn_pgtap_emittente_operatore: il guard di scope lo
--   pretende), con un indirizzo fabbricato e usa_ubicazioni scelto dal test
--   (D-L2-m). Da chiamare DOPO fn_pgtap_set_contesto_operatore.
-- Uso: v_mag := dbops.fn_pgtap_crea_magazzino('PGT-MAG-A', true);
DECLARE
    v_ef  magazzino.magazzini.emittente_fiscale_id%TYPE;
    v_ind magazzino.magazzini.indirizzo_dettaglio_id%TYPE;
    v_id  magazzino.magazzini.id%TYPE;
BEGIN
    v_ef := script.fn_pgtap_emittente_operatore();
    IF v_ef IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_crea_magazzino: nessun emittente per l''operatore in sessione — chiamare prima fn_pgtap_set_contesto_operatore';
    END IF;
    v_ind := dbops.fn_pgtap_crea_indirizzo_dettaglio(p_codice);
    INSERT INTO magazzino.magazzini (codice, descrizione, indirizzo_dettaglio_id, emittente_fiscale_id, usa_ubicazioni)
    VALUES (p_codice, 'Fixture pgTAP: ' || p_codice, v_ind, v_ef, COALESCE(p_usa_ubicazioni, false))
    RETURNING id INTO v_id;
    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_magazzino(p_codice character varying, p_usa_ubicazioni boolean)
IS 'Fixture pgTAP: un magazzino dell''emittente dell''operatore in sessione (script.fn_pgtap_emittente_operatore), indirizzo fabbricato, usa_ubicazioni scelto dal test (D-L2-m). Da chiamare dopo fn_pgtap_set_contesto_operatore. Solo per i pgTAP (brief magazzino Lotto 2, sezione 5).';
```

---
{% include-markdown "signature-core.md" %}
