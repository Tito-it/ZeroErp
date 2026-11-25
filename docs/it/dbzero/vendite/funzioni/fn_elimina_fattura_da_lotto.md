{% include-markdown "it/dbzero/vendite/manual/fn_elimina_fattura_da_lotto.md" %}
# ⚙️ Funzione `fn_elimina_fattura_da_lotto`

```sql
CREATE FUNCTION fn_elimina_fattura_da_lotto(p_lotto_id bigint, p_fattura_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_elimina_fattura_da_lotto(p_lotto_id bigint, p_fattura_id bigint)
 RETURNS TABLE(updated_attivita integer, deleted_fatture integer, deleted_righe integer, riemesse_attivita integer)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: toglie UNA fattura da un lotto PRE-FISCALE, cancellandola,
--        senza toccare il lotto ne' le altre fatture.
-- RD-7 (2026-08-04): togliere = CANCELLARE. Il modello «reperto»
--        (fattura staccata e portata ad ANNULLATA) e' caduto: era
--        incoerente che riportare in bozza un lotto INTERO
--        cancellasse le sue fatture EMESSA mentre la stessa
--        operazione su UNA riga lasciasse un documento vuoto.
-- Perimetro: lotto PRE-FISCALE (DRAFT o EMESSA) e fattura
--        PRE-FISCALE. Prima si pretendeva il lotto in DRAFT: era
--        il perimetro sbagliato, e il caso che conta e' proprio la
--        fattura critica dentro un lotto EMESSA.
-- Regole: C-22 — alla primitiva si passa `NULL` come
--         `p_lock_batch_id`. Passando quello del lotto si
--         libererebbero anche le attivita' delle ALTRE fatture.
DECLARE
    v_utente            config.user_override_azioni.auth_user_id%TYPE;
    v_motivi            jsonb;
    v_updated_attivita  INTEGER := 0;
    v_deleted_fatture   INTEGER := 0;
    v_deleted_righe     INTEGER := 0;
    v_riemesse_attivita INTEGER := 0;
BEGIN
    -- ⭐ rev 2026-11-25 (brief-db-porte-aperte-dalla-sola-guc, giro 1-7): SECURITY DEFINER.
    --   Il permesso in prima riga e' l'azione che l'endpoint controlla
    --   (reset_lotto_fattura_draft, risposta 3d §4.5); il perimetro lo
    --   rimette il verbo su lotto e fattura, prima dei motivi.
    v_utente := script.fn_utente_di_sessione('vendite.fn_elimina_fattura_da_lotto');
    PERFORM script.fn_guard_azione(v_utente, 'reset_lotto_fattura_draft');

    -- Le GUC che dentro un verbo DEFINER aprirebbero una porta si
    -- spengono all'ingresso: quella del reset del lotto (la riaccende
    -- solo la pulizia, e solo mentre lavora) e quella delle righe
    -- contabili del fondo.
    PERFORM set_config('zeroerp.maintenance_reset_lotto_draft', '', true);
    PERFORM set_config('zeroerp.allow_contabile_riga_delete_override', '', true);

    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_elimina_fattura_da_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id), NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_elimina_fattura_da_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id), NULL::uuid, 'p_fattura_id obbligatorio e > 0');
    END IF;

    -- Il perimetro, una volta, all'ingresso, sul lotto: la regola della
    -- policy di vendite.fatturazione_lotti, rimessa qui perche' il verbo
    -- legge da proprietario. Fuori perimetro il lotto «non c'e'», come un
    -- lotto che non esiste, e prima di dire qualunque cosa sul suo stato.
    IF NOT COALESCE(script.fn_scope_ef_whitelist_via_lotto(v_utente, p_lotto_id), false) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_elimina_fattura_da_lotto', 'E_LOTTO_NON_TROVATO',
            jsonb_build_object('detail', 'lotto inesistente o fuori perimetro', 'lotto_id', p_lotto_id),
            NULL::uuid, p_lotto_id::text);
    END IF;

    -- E la fattura: fuori perimetro «non c'e'», con la risposta del criterio
    -- per la fattura che non esiste.
    IF NOT COALESCE(script.fn_scope_ef_whitelist_via_fattura(v_utente, p_fattura_id), false) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_elimina_fattura_da_lotto', 'E_FATTURA_NON_TROVATA',
            jsonb_build_object('detail', 'fattura inesistente o fuori perimetro', 'fattura_id', p_fattura_id),
            NULL::uuid, p_fattura_id::text);
    END IF;

    -- PRECONDIZIONI — sede unica. Il check verifica anche
    -- l'esistenza di lotto e fattura e solleva il codice del
    -- PRIMO motivo; il context porta l'elenco completo, cosi'
    -- il BE puo' mostrarli tutti.
    v_motivi := script.fn_check_fattura_eliminabile_da_lotto(p_lotto_id, p_fattura_id);
    IF jsonb_array_length(v_motivi) > 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_elimina_fattura_da_lotto',
            v_motivi -> 0 ->> 'codice',
            jsonb_build_object('lotto_id', p_lotto_id, 'fattura_id', p_fattura_id, 'motivi', v_motivi),
            NULL::uuid,
            v_motivi -> 0 ->> 'dettaglio');
    END IF;

    -- C-22: NULL, non il lock_batch_id del lotto.
    SELECT c.deleted_fatture, c.deleted_righe, c.updated_attivita, c.riemesse_attivita
      INTO v_deleted_fatture, v_deleted_righe, v_updated_attivita, v_riemesse_attivita
      FROM vendite.fn_cleanup_fatture_by_ids(ARRAY[p_fattura_id], NULL::uuid) AS c;

    RETURN QUERY SELECT v_updated_attivita, v_deleted_fatture,
                        v_deleted_righe, v_riemesse_attivita;
END;
$function$

COMMENT ON FUNCTION vendite.fn_elimina_fattura_da_lotto(p_lotto_id bigint, p_fattura_id bigint)
IS 'Verbo SECURITY DEFINER di «togli la fattura dal lotto»: in prima riga script.fn_guard_azione con reset_lotto_fattura_draft (l''azione dell''endpoint), poi il perimetro su lotto e fattura (fuori: E_LOTTO_NON_TROVATO o E_FATTURA_NON_TROVATA, come se non esistessero); spegne all''ingresso le GUC delle porte. Toglie UNA fattura da un lotto PRE-FISCALE cancellandola, senza toccare il lotto ne'' le altre fatture. Rinominata da fn_elimina_fattura_da_lotto_draft il 2026-08-04 (RD-7): il «draft» era riferito al LOTTO, che ora non deve piu'' essere in bozza — basta che sia pre-fiscale, lo stesso confine delle due sorelle. ⚠️ L''allargamento chiude un disallineamento vivo: il drawer gatava la voce di riga sul solo stato della fattura, quindi su un lotto EMESSA la proponeva e la chiamata falliva (terza occorrenza dello stesso difetto). RD-7: togliere = CANCELLARE, il modello «reperto» e'' caduto perche'' era incoerente che il ritorno in bozza di un lotto INTERO cancellasse le sue fatture EMESSA mentre la stessa operazione su UNA riga lasciasse un documento vuoto. ⚠️ La cancellazione NON lascia traccia del contenuto: vendite.fatture.storicizza e'' false di default; resta storicizzata la sola riga di ponte. Le precondizioni non sono scritte qui — arrivano da script.fn_check_fattura_eliminabile_da_lotto, che solleva codici parlanti (831-834) al posto di quattro E_PARAMETRO_INVALIDO indistinguibili. Da C-22 passa NULL come lock_batch_id alla primitiva: il batch del lotto libererebbe anche le attivita'' delle altre fatture. Quarto contatore riemesse_attivita dal 2026-08-04, coerente con le sorelle (RD-4: le commesse_attivita tornano NON_EMESSA, ed e'' un fatto diverso dallo sblocco delle attivita_fatturabili).';
```

</div>

---
{% include-markdown "signature-core.md" %}
