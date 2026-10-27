{% include-markdown "it/dbzero/vendite/manual/fn_commessa_proietta_stato_emittibile.md" %}
# ⚙️ Funzione `fn_commessa_proietta_stato_emittibile`

```sql
CREATE FUNCTION fn_commessa_proietta_stato_emittibile(p_commessa_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_commessa_proietta_stato_emittibile(p_commessa_id bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- =========================================================
-- Scopo: dopo un invio riuscito, portare la commessa nello
--   stato emittibile (vocabolario, emittibile = true).
--   Gia' emittibile: niente. La matrice e le condizioni le
--   giudica il guard di transizione, all'UPDATE.
-- Consumatori: vendite.fn_rendi_commessa_emittibile (il ponte
--   della push).
-- Brief: brief-modello-documento-vendita §14 (C-2).
-- =========================================================
DECLARE
    v_emittibile vendite.stati_commessa.emittibile%TYPE;
    v_target_id  vendite.stati_commessa.id%TYPE;
    -- Un conteggio: nessuna colonna da ancorare.
    v_n_stati    integer;
BEGIN
    IF p_commessa_id IS NULL OR p_commessa_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_commessa_proietta_stato_emittibile',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_commessa_id', p_commessa_id),
            NULL::uuid, 'vendite.fn_commessa_proietta_stato_emittibile',
            'p_commessa_id (obbligatorio, maggiore di zero)');
    END IF;

    -- Lo stato di oggi. Commessa assente: niente.
    SELECT s.emittibile
      INTO v_emittibile
      FROM vendite.commesse c
      JOIN vendite.stati_commessa s ON s.id = c.stato_commessa_id
     WHERE c.id = p_commessa_id;

    IF NOT FOUND OR v_emittibile THEN
        RETURN;
    END IF;

    -- ⛔ Guard sull'ARITA': zero righe e due righe sono lo stesso
    --   difetto, il catalogo non dice quale.
    SELECT count(*), min(s.id)
      INTO v_n_stati, v_target_id
      FROM vendite.stati_commessa s
     WHERE s.emittibile IS TRUE
       AND s.attivo     IS TRUE;

    IF v_n_stati <> 1 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_commessa_proietta_stato_emittibile',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('tabella', 'vendite.stati_commessa',
                               'colonna', 'emittibile',
                               'attesi',  1,
                               'trovati', v_n_stati),
            NULL::uuid,
            'vendite.stati_commessa: atteso esattamente uno stato attivo '
            || 'con emittibile = true, trovati ' || v_n_stati::text);
    END IF;

    PERFORM script.fn_doc_scrivi_stato('vendite.commesse'::regclass,
                                       p_commessa_id, v_target_id);
END;
$function$

COMMENT ON FUNCTION vendite.fn_commessa_proietta_stato_emittibile(p_commessa_id bigint)
IS 'BB del passaggio della push allo stato emittibile della commessa, brief-modello-documento-vendita §14 (C-2, Tid 2026-10-26): dopo un invio riuscito, porta la commessa nello stato che il vocabolario dichiara emittibile (vendite.stati_commessa.emittibile, guard sull''arita'': E_CONFIG_MANCANTE); gia'' emittibile: niente. Scrive con script.fn_doc_scrivi_stato attraverso la porta, senza la prima riga del verbo: il passaggio e'' la conseguenza dell''invio, e il permesso e'' quello della push (run_commesse_push, push_commessa_preventivi), non l''azione cambia_stato_commessa che l''operatore chiede con «rendi pronta». Matrice e condizioni (E_COMMESSA_STATO_TRANSIZIONE_INVALIDA, almeno una riga approvata da emettere) le giudica il guard di transizione. La chiama vendite.fn_rendi_commessa_emittibile. SECURITY DEFINER senza perimetro, come vendite.fn_preventivo_proietta_stato_smistamento e vendite.fn_offerta_proietta_stato_revisione; EXECUTE all''applicazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
