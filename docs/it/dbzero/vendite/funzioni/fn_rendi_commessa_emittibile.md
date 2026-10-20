{% include-markdown "it/dbzero/vendite/manual/fn_rendi_commessa_emittibile.md" %}
# ⚙️ Funzione `fn_rendi_commessa_emittibile`

```sql
CREATE FUNCTION fn_rendi_commessa_emittibile(p_commessa_id bigint, p_righe_ids bigint[], p_user text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_rendi_commessa_emittibile(p_commessa_id bigint, p_righe_ids bigint[] DEFAULT NULL::bigint[], p_user text DEFAULT NULL::text)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: dopo un invio in commessa, approvare le righe
--   dell'invio e portare la commessa a PRONTA_FATTURAZIONE.
--   p_righe_ids: array di id (%TYPE[] non esiste). Vedi
--   l'intestazione del changeSet.
-- Ritorna: le righe approvate (un CONTEGGIO).
-- =========================================================
DECLARE
    -- CONTEGGIO delle righe approvate.
    v_approvate integer := 0;
    v_stato     vendite.stati_commessa.codice_interno%TYPE;
BEGIN
    IF p_commessa_id IS NULL OR p_commessa_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_rendi_commessa_emittibile',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_commessa_id', p_commessa_id),
            NULL::uuid, 'vendite.fn_rendi_commessa_emittibile',
            'p_commessa_id (obbligatorio, maggiore di zero)');
    END IF;

    -- 1. Le righe dell'invio. Array vuoto: nessuna riga di questo
    --    invio e' atterrata, niente da approvare.
    IF p_righe_ids IS NULL OR cardinality(p_righe_ids) > 0 THEN
        v_approvate := vendite.fn_approva_commessa_attivita(
                           p_commessa_id, p_righe_ids, p_user);
    END IF;

    -- 2. La testata. Gia' PRONTA_FATTURAZIONE: la matrice non ammette
    --    da = a, non si tenta. CHIUSA o ANNULLATA: si tenta, e la
    --    matrice rifiuta forte.
    SELECT sc.codice_interno
      INTO v_stato
      FROM vendite.commesse c
      JOIN vendite.stati_commessa sc ON sc.id = c.stato_commessa_id
     WHERE c.id = p_commessa_id;

    IF v_stato IS DISTINCT FROM 'PRONTA_FATTURAZIONE' THEN
        PERFORM vendite.fn_cambia_stato_commessa(
            p_commessa_id, 'PRONTA_FATTURAZIONE', p_user);
    END IF;

    RETURN COALESCE(v_approvate, 0);
END;
$function$

COMMENT ON FUNCTION vendite.fn_rendi_commessa_emittibile(p_commessa_id bigint, p_righe_ids bigint[], p_user text)
IS 'Madre (2026-10-12, brief-db-annullo-a-valle-riapre-a-monte D-10 di Tid): dopo un invio in commessa approva le righe dell''invio (vendite.fn_approva_commessa_attivita) e porta la commessa a PRONTA_FATTURAZIONE (vendite.fn_cambia_stato_commessa). Prima lo faceva il backend (commesse_service._rendi_commessa_emittibile), che ora la chiama. p_righe_ids: NULL = nessun filtro; vuoto = nessuna riga di questo invio atterrata, niente approvazione ma la testata va comunque a PRONTA_FATTURAZIONE; pieno = le sole righe dell''invio (non si approvano le righe BOZZA di terzi). Gia'' PRONTA_FATTURAZIONE: il cambio non si tenta (la matrice non ammette da = a); CHIUSA o ANNULLATA: si tenta e la matrice rifiuta (non si invia in una commessa chiusa). Una madre e non un trigger: «le righe di questo invio» le conosce solo chi orchestra l''invio. SECURITY INVOKER. Ritorna le righe approvate.';
```

</div>

---
{% include-markdown "signature-core.md" %}
