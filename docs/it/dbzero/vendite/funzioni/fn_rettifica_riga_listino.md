{% include-markdown "it/dbzero/vendite/manual/fn_rettifica_riga_listino.md" %}
# ⚙️ Funzione `fn_rettifica_riga_listino`

```sql
CREATE FUNCTION fn_rettifica_riga_listino(p_listino_riga_id bigint, p_prezzo numeric, p_motivo text)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_rettifica_riga_listino(p_listino_riga_id bigint, p_prezzo numeric, p_motivo text)
 RETURNS TABLE(listino_riga_id bigint, prezzo_precedente numeric, prezzo_nuovo numeric, motivo text)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente      config.user_override_azioni.auth_user_id%TYPE;
    v_versione_id vendite.listini_righe.listino_versione_id%TYPE;
    v_prima       vendite.listini_righe.prezzo%TYPE;
v_dopo        vendite.listini_righe.prezzo%TYPE;
    v_tx_id       vendite.listini_righe.tx_id%TYPE;
    -- Tipo esplicito: il motivo ripulito, come p_motivo.
    v_motivo      text := btrim(p_motivo);
    -- Il tetto del motivo: una costante sola, letta dal controllo e
    --   dal messaggio.
    c_motivo_max  CONSTANT integer := 500;
BEGIN
    -- ==========================================================
    -- Scopo: rettificare il prezzo di una riga del listino in uso,
    --   col motivo, e lasciarne la traccia nella riga
    --   (meta.rettifiche_controllate[]). E' l'unica scrittura di una
    --   riga fuori dalla bozza. Vedi l'intestazione del changeSet
    --   20261115-67.
    -- ==========================================================
    v_utente := script.fn_utente_di_sessione('vendite.fn_rettifica_riga_listino');

    -- 1. Parametri e riga, nel perimetro.
    IF p_listino_riga_id IS NULL OR p_listino_riga_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_rettifica_riga_listino',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_listino_riga_id', p_listino_riga_id),
            NULL::uuid, 'vendite.fn_rettifica_riga_listino',
            'p_listino_riga_id (obbligatorio, maggiore di zero)');
    END IF;
    IF p_prezzo IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_rettifica_riga_listino',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_listino_riga_id', p_listino_riga_id, 'campo', 'prezzo'),
            NULL::uuid, 'vendite.fn_rettifica_riga_listino',
            'p_prezzo (obbligatorio)');
    END IF;

    SELECT lr.listino_versione_id, lr.prezzo, lr.tx_id
      INTO v_versione_id, v_prima, v_tx_id
      FROM vendite.listini_righe lr
     WHERE lr.id = p_listino_riga_id
       AND script.fn_scope_ef_whitelist_via_listino_versione(v_utente, lr.listino_versione_id)
       FOR UPDATE OF lr;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_rettifica_riga_listino',
            'E_VENDITE_LISTINO_RIGA_NOT_FOUND',
            -- Frase chiusa: nessun segnaposto, il variadico vuoto e' esplicito.
            jsonb_build_object('id', p_listino_riga_id), NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- 2. Prima cio' che vieta: il primo motivo della check, sul prezzo.
    --    La riga e' sotto FOR UPDATE: un documento non la cita fra la
    --    check e la scrittura (la FK prende il KEY SHARE).
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', 'vendite.fn_rettifica_riga_listino',
        script.fn_check_listino_riga_rettificabile(p_listino_riga_id),
        'prezzo',
        v_tx_id,
        jsonb_build_object('listino_riga_id', p_listino_riga_id,
                           'listino_versione_id', v_versione_id,
                           'prezzo_prima', v_prima, 'prezzo', p_prezzo));

    -- 3. Il motivo: obbligatorio, al piu' c_motivo_max caratteri.
    IF v_motivo IS NULL OR v_motivo = '' OR length(v_motivo) > c_motivo_max THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_rettifica_riga_listino',
            'E_RIGA_LISTINO_RETTIFICA_MOTIVO_OBBLIGATORIO',
            jsonb_build_object('campo', 'motivo', 'listino_riga_id', p_listino_riga_id,
                               'lunghezza', length(v_motivo)),
            v_tx_id,
            c_motivo_max::text);
    END IF;

    -- 4. Il prezzo e la traccia, con la porta aperta per QUESTA riga: il
    --    guard delle righe la onora col proprietario della tabella, e
    --    dentro la porta lascia cambiare solo il prezzo e meta. Prezzo
    --    negativo: il CHECK della tabella. La porta si richiude anche
    --    in errore.
    BEGIN
        PERFORM set_config('zeroerp.listino_riga_rettifica', p_listino_riga_id::text, true);
        -- Il prezzo, poi la traccia col valore SALVATO (alla scala
        -- della colonna, come prezzo_precedente).
        UPDATE vendite.listini_righe lr
           SET prezzo = p_prezzo
         WHERE lr.id = p_listino_riga_id
        RETURNING lr.prezzo INTO v_dopo;
        UPDATE vendite.listini_righe lr
           SET meta = jsonb_set(
                          lr.meta, '{rettifiche_controllate}',
                          COALESCE(lr.meta -> 'rettifiche_controllate', '[]'::jsonb)
                          || jsonb_build_array(jsonb_build_object(
                                 'data',              now(),
                                 'operatore',         v_utente,
                                 'prezzo_precedente', v_prima::text,
                                 'prezzo_nuovo',      v_dopo::text,
                                 'motivo',            v_motivo)))
         WHERE lr.id = p_listino_riga_id;
        PERFORM set_config('zeroerp.listino_riga_rettifica', '', true);
    EXCEPTION WHEN OTHERS THEN
        PERFORM set_config('zeroerp.listino_riga_rettifica', '', true);
        RAISE;
    END;

    RETURN QUERY SELECT p_listino_riga_id, v_prima, v_dopo, v_motivo;
END;
$function$

COMMENT ON FUNCTION vendite.fn_rettifica_riga_listino(p_listino_riga_id bigint, p_prezzo numeric, p_motivo text)
IS 'VERBO «Rettifica» di una riga di listino: corregge, col motivo, il prezzo di una riga del listino in uso, ed e'' l''unica scrittura di una riga fuori dalla bozza (in bozza la riga si modifica direttamente). La riga FOR UPDATE nel perimetro (script.fn_scope_ef_whitelist_via_listino_versione: DEFINER, la RLS non c''e''; non trovata o fuori perimetro E_VENDITE_LISTINO_RIGA_NOT_FOUND; p_listino_riga_id o p_prezzo mancanti E_VENDITE_CHIAMATA_NON_VALIDA); prima cio'' che vieta, sul campo prezzo (il primo motivo di script.fn_check_listino_riga_rettificabile: in bozza E_RIGA_LISTINO_RETTIFICA_IN_BOZZA, CHIUSA E_RIGA_LISTINO_VERSIONE_CHIUSA, non in vigore alla data operativa E_RIGA_LISTINO_RETTIFICA_NON_IN_VIGORE, citata da un documento E_RIGA_LISTINO_PROPAGATA); poi il motivo, obbligatorio e al piu'' 500 caratteri (E_RIGA_LISTINO_RETTIFICA_MOTIVO_OBBLIGATORIO, campo motivo). Scrive il prezzo e appende a meta.rettifiche_controllate[] la traccia (data, operatore = app.current_user_id, prezzo_precedente, prezzo_nuovo, motivo), con la porta aperta per questa riga (GUC transazionale zeroerp.listino_riga_rettifica = id della riga: la onora vendite.trgfn_listini_righe_guard_stato col proprietario della tabella, script.fn_is_proprietario_tabella, e dentro lascia cambiare il solo prezzo e meta); la porta si richiude anche in errore. Prezzo negativo: il CHECK chk_listini_righe_prezzo. Ritorna la riga, il prezzo di prima, quello nuovo e il motivo. Prende il posto della rettifica controllata del backend (sviluppo-listini-v3 N6). Il permesso d''area resta al backend. SECURITY DEFINER con search_path bloccato; EXECUTE solo all''applicazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
