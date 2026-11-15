{% include-markdown "it/dbzero/vendite/manual/fn_preventivo_proietta_stato_smistamento.md" %}
# ⚙️ Funzione `fn_preventivo_proietta_stato_smistamento`

```sql
CREATE FUNCTION fn_preventivo_proietta_stato_smistamento(p_preventivo_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_preventivo_proietta_stato_smistamento(p_preventivo_id bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- =========================================================
-- Scopo: portare il preventivo nello stato che il suo
--   smistamento dice.
--   stato di accettazione, nessun residuo (ordine e commessa) -> EVASO;
--   EVASO, residuo su almeno una strada -> stato di accettazione;
--   ogni altro caso                     -> niente.
--   La transizione passa dalla matrice
--   (trgfn_preventivi_guard_transizione).
-- Consumatori: vendite.fn_push_preventivo_a_ordine,
--   vendite.fn_documento_ritira_legami (annullo dell'ordine),
--   vendite.trgfn_commesse_attivita_proietta_stato_preventivo
--   (invio in commessa, ritiro, annullo della commessa).
-- Brief: brief-db-annullo-a-valle-riapre-a-monte (D-1, D-10).
-- rev 2026-10-25 (20261025-45, brief-modello-documento-vendita
--   §8): e' il verbo dei passaggi di PROCESSO del preventivo
--   (manuale = false): scrive con la sola seconda meta' del
--   verbo comune, attraverso la porta. DEFINER, perche' la porta
--   vuole il proprietario; lo stato e' la proiezione dei residui,
--   non una scelta di chi chiama.
-- rev 2026-11-14 (brief-db-stati-documento-dal-vocabolario, giro 6a,
--   D-PROI): la partenza e il ritorno sono lo stato di accettazione del
--   vocabolario, quello da cui lo smistamento si apre; EVASO resta la
--   destinazione nominata del processo.
-- rev 2026-11-14 (brief-db-stati-documento-dal-vocabolario, giro 6g,
--   D-SMIST): da dove la proiezione parte lo dice
--   vendite.fn_preventivo_in_smistamento, la sede unica che legge anche la
--   capability.
-- =========================================================
DECLARE
    v_stato        config.stati_doc_preventivi.codice_interno%TYPE;
    -- Lo stato di oggi e' l'accettazione? Dal vocabolario.
    v_accettazione config.stati_doc_preventivi.accettazione%TYPE;
    -- Il nome della destinazione che manca, per il messaggio: il codice EVASO o
    -- la colonna accettazione, nessuna colonna di cui sia il riflesso.
    v_target       text;
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

    -- Lo stato di oggi. Preventivo assente: niente.
    SELECT s.codice_interno, s.accettazione
      INTO v_stato, v_accettazione
      FROM vendite.preventivi p
      JOIN config.stati_doc_preventivi s ON s.id = p.stato_doc_preventivo_id
     WHERE p.id = p_preventivo_id;

    -- Si parte solo da un preventivo che si smista: la sede unica della
    -- risposta, la stessa della capability.
    IF v_stato IS NULL
       OR NOT vendite.fn_preventivo_in_smistamento(v_accettazione, v_stato) THEN
        RETURN;
    END IF;

    v_residuo := vendite.fn_preventivo_ha_residuo_ordine(p_preventivo_id)
              OR vendite.fn_preventivo_ha_residuo_commessa(p_preventivo_id);

    -- EVASO e' la destinazione del processo, e si nomina col codice come la
    -- nomina la riga della matrice; il ritorno e' lo stato di accettazione.
    IF v_accettazione AND NOT v_residuo THEN
        v_target    := 'EVASO';
        v_target_id := script.fn_doc_stato_id('vendite.preventivi'::regclass, 'EVASO');
    ELSIF v_stato = 'EVASO' AND v_residuo THEN
        v_target    := 'accettazione';
        v_target_id := script.fn_stato_accettazione_id('vendite.preventivi'::regclass);
    ELSE
        RETURN;
    END IF;

    IF v_target_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_preventivo_proietta_stato_smistamento',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'config.stati_doc_preventivi.' || v_target),
            NULL::uuid, 'stato ' || v_target || ' (config.stati_doc_preventivi)');
    END IF;

    -- Il target e' sempre diverso dallo stato di oggi (IF sopra).
    -- La matrice la giudica il guard di transizione, all'UPDATE.
    PERFORM script.fn_doc_scrivi_stato('vendite.preventivi'::regclass,
                                       p_preventivo_id, v_target_id);
END;
$function$

COMMENT ON FUNCTION vendite.fn_preventivo_proietta_stato_smistamento(p_preventivo_id bigint)
IS 'Porta il preventivo nello stato che il suo smistamento dice. Dallo stato di accettazione (la colonna accettazione di config.stati_doc_preventivi), senza residuo su nessuna strada (vendite.fn_preventivo_ha_residuo_ordine, vendite.fn_preventivo_ha_residuo_commessa) -> EVASO; da EVASO, con un residuo su almeno una -> lo stato di accettazione; ogni altro stato, o preventivo assente -> niente. Da dove si parte lo dice vendite.fn_preventivo_in_smistamento (lo stato di accettazione o EVASO), la stessa risposta che script.fn_available_actions_preventivo espone in in_smistamento. L''accettazione e'' un significato e si legge dalla colonna, la stessa da cui script.fn_available_actions_preventivo e vendite.fn_push_preventivo_a_ordine aprono lo smistamento; EVASO e'' la destinazione del processo e si nomina col codice (script.fn_doc_stato_id), come la nomina la riga della matrice. Destinazione assente dal vocabolario: E_CONFIG_MANCANTE. E'' il verbo dei passaggi di processo del preventivo (manuale = false nella matrice): scrive con script.fn_doc_scrivi_stato, attraverso la porta (script.trgfn_doc_stato_solo_dal_verbo), e il passaggio lo giudica vendite.trgfn_preventivi_guard_transizione. Specchio di vendite.fn_ordine_proietta_stato_evasione. Consumatori: vendite.fn_push_preventivo_a_ordine, vendite.fn_documento_ritira_legami (annullo dell''ordine), vendite.trgfn_commesse_attivita_proietta_stato_preventivo (invio in commessa, ritiro delle righe, annullo della commessa). SECURITY DEFINER con search_path bloccato, perche'' la porta vuole il proprietario: lo stato e'' la proiezione dei residui, non una scelta di chi chiama, e il perimetro di chi agisce lo controllano i consumatori. Parametro non valido: E_VENDITE_CHIAMATA_NON_VALIDA (TECNICO).';
```

</div>

---
{% include-markdown "signature-core.md" %}
