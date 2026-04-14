# ⚙️ Funzione `trgfn_contratti_righe_guard_modalita_c`

```sql
CREATE FUNCTION trgfn_contratti_righe_guard_modalita_c()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_righe_guard_modalita_c()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_contratto_listino_id vendite.contratti.listino_id%TYPE;
    v_codice_interno       config.stati_doc_contratti.codice_interno%TYPE;
BEGIN
    -- Short-circuit 1: se la riga ha gia' prezzo_unitario,
    -- nessun guard serve (caso assolutamente piu' comune).
    -- Evita la query sul contratto per ogni INSERT/UPDATE conforme.
    IF NEW.prezzo_unitario IS NOT NULL THEN
        RETURN NEW;
    END IF;

    -- Short-circuit 2: righe inattive non contribuiscono al contratto.
    IF COALESCE(NEW.attivo, true) = false THEN
        RETURN NEW;
    END IF;

    SELECT c.listino_id, s.codice_interno
      INTO v_contratto_listino_id, v_codice_interno
      FROM vendite.contratti c
      JOIN config.stati_doc_contratti s
        ON s.id = c.stato_doc_contratto_id
     WHERE c.id = NEW.contratto_id;

    -- Guard attivo solo se contratto ATTIVO e modalita' C.
    IF v_codice_interno IS DISTINCT FROM 'ATTIVO'
       OR v_contratto_listino_id IS NOT NULL THEN
        RETURN NEW;
    END IF;

    -- A questo punto lo short-circuit iniziale garantisce
    -- NEW.prezzo_unitario IS NULL: contratto ATTIVO + modalita' C
    -- + riga attiva senza prezzo -> violazione.
    PERFORM script.fn_log_and_raise_error(
        'vendite',
        TG_NAME,
        'E_CONTRATTO_MODALITA_C_RIGA_SENZA_PREZZO',
        jsonb_build_object(
            'detail', 'riga contratto modalita'' C (listino_id NULL) senza prezzo_unitario',
            'contratto_id', NEW.contratto_id,
            'riga_id', NEW.id,
            'articolo_id', NEW.articolo_id
        ),
        NULL::uuid,
        'Riga contratto modalita'' C: prezzo_unitario obbligatorio'
    );

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_righe_guard_modalita_c()
IS 'Guard BEFORE INS/UPD su vendite.contratti_righe: se contratto ATTIVO e modalita'' C, prezzo_unitario obbligatorio sulla riga attiva. Pricing v5.';
```

---
{% include-markdown "signature-core.md" %}
