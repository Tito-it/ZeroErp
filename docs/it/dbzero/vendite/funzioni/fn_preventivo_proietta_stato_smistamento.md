{% include-markdown "it/dbzero/vendite/manual/fn_preventivo_proietta_stato_smistamento.md" %}
# ⚙️ Funzione `fn_preventivo_proietta_stato_smistamento`

```sql
CREATE FUNCTION fn_preventivo_proietta_stato_smistamento(p_preventivo_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_preventivo_proietta_stato_smistamento(p_preventivo_id bigint)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: portare il preventivo nello stato che il suo
--   smistamento dice.
--   ACCETTATO, nessun residuo (ordine e commessa) -> EVASO;
--   EVASO, residuo su almeno una strada          -> ACCETTATO;
--   ogni altro caso                              -> niente.
--   La transizione passa dalla matrice
--   (trgfn_preventivi_guard_transizione).
-- Consumatori: vendite.fn_push_preventivo_a_ordine,
--   vendite.fn_documento_ritira_legami (annullo dell'ordine),
--   vendite.trgfn_commesse_attivita_proietta_stato_preventivo
--   (invio in commessa, ritiro, annullo della commessa).
-- Brief: brief-db-annullo-a-valle-riapre-a-monte (D-1, D-10).
-- =========================================================
DECLARE
    v_stato        config.stati_doc_preventivi.codice_interno%TYPE;
    v_target       config.stati_doc_preventivi.codice_interno%TYPE;
    v_target_id    config.stati_doc_preventivi.id%TYPE;
    -- Esito di due predicati: nessuna colonna da ancorare.
    v_residuo      boolean;
BEGIN
    IF p_preventivo_id IS NULL OR p_preventivo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_preventivo_proietta_stato_smistamento',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_preventivo_id', p_preventivo_id),
            NULL::uuid, 'vendite.fn_preventivo_proietta_stato_smistamento',
            'p_preventivo_id (obbligatorio, maggiore di zero)');
    END IF;

    -- Lo stato di oggi. Preventivo assente o invisibile: niente.
    SELECT s.codice_interno
      INTO v_stato
      FROM vendite.preventivi p
      JOIN config.stati_doc_preventivi s ON s.id = p.stato_doc_preventivo_id
     WHERE p.id = p_preventivo_id;

    IF v_stato IS NULL OR v_stato NOT IN ('ACCETTATO', 'EVASO') THEN
        RETURN;
    END IF;

    v_residuo := vendite.fn_preventivo_ha_residuo_ordine(p_preventivo_id)
              OR vendite.fn_preventivo_ha_residuo_commessa(p_preventivo_id);

    v_target := CASE
                  WHEN v_stato = 'ACCETTATO' AND NOT v_residuo THEN 'EVASO'
                  WHEN v_stato = 'EVASO'     AND v_residuo     THEN 'ACCETTATO'
                END;

    IF v_target IS NULL THEN
        RETURN;
    END IF;

    SELECT s.id
      INTO v_target_id
      FROM config.stati_doc_preventivi s
     WHERE s.codice_interno = v_target
       AND s.attivo IS TRUE;

    IF v_target_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_preventivo_proietta_stato_smistamento',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'config.stati_doc_preventivi.' || v_target),
            NULL::uuid, 'stato ' || v_target || ' (config.stati_doc_preventivi)');
    END IF;

    UPDATE vendite.preventivi
       SET stato_doc_preventivo_id = v_target_id
     WHERE id = p_preventivo_id
       AND stato_doc_preventivo_id IS DISTINCT FROM v_target_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_preventivo_proietta_stato_smistamento(p_preventivo_id bigint)
IS 'Building block (2026-10-12, brief-db-annullo-a-valle-riapre-a-monte D-1/D-10 di Tid): porta il preventivo nello stato che il suo smistamento dice. ACCETTATO senza residuo su nessuna strada (vendite.fn_preventivo_ha_residuo_ordine, vendite.fn_preventivo_ha_residuo_commessa) -> EVASO; EVASO con un residuo su almeno una -> ACCETTATO; ogni altro stato, o preventivo assente o invisibile, -> niente. Specchio di vendite.fn_ordine_proietta_stato_evasione. La transizione passa dalla matrice (vendite.trgfn_preventivi_guard_transizione); si scrive solo se lo stato cambia; destinazione assente dal catalogo: E_CONFIG_MANCANTE. Sede unica della regola, che prima aveva tre copie su due livelli: il §8 di vendite.fn_push_preventivo_a_ordine, il §4b di vendite.fn_documento_ritira_legami e il gate EVASO del backend dopo l''invio in commessa. Consumatori: vendite.fn_push_preventivo_a_ordine, vendite.fn_documento_ritira_legami (annullo dell''ordine), vendite.trgfn_commesse_attivita_proietta_stato_preventivo (invio in commessa, ritiro delle righe, annullo della commessa). SECURITY INVOKER: scrive con la RLS di chi chiama. Parametro non valido: E_VENDITE_CHIAMATA_NON_VALIDA (TECNICO).';
```

</div>

---
{% include-markdown "signature-core.md" %}
