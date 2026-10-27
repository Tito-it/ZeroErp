{% include-markdown "it/dbzero/script/manual/fn_available_actions_lotto.md" %}
# ⚙️ Funzione `fn_available_actions_lotto`

```sql
CREATE FUNCTION fn_available_actions_lotto(p_lotto_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_available_actions_lotto(p_lotto_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo:
--   Capability del lotto di fatturazione per il detail API.
--   Mirror data-driven di fn_available_actions_commessa: le
--   transizioni manuali (meta.manuale=true + action_key/label_key)
--   sono esposte come bottoni, le automatiche no. enabled/reasons
--   arrivano dalle funzioni pure script.fn_check_lotto_annullabile
--   e script.fn_check_lotto_riportabile_a_draft — le STESSE che le
--   due fn di mutazione usano per sollevare (sorgente unica: la UI
--   non puo' divergere dal DB).
--   🔴 NON espone avanza_step / rilancia_step: quel gate vive nel
--   runner Python (steps + criticita' + rilancio dello stesso
--   step, D-Q p.1) e ricostruirlo qui sarebbe la seconda copia
--   della regola che stiamo eliminando.
--   rev 2026-08-06: + target_state_descrizione, la forma leggibile
--   dello stato di destinazione. Serve alla frase di conferma
--   «portare il documento nello stato X»: il codice_interno non e'
--   quella forma e tradurlo nel FE sarebbe una seconda copia del
--   vocabolario degli stati. NULL sulla ristampa, che non cambia
--   stato.
--   rev 2026-10-27 (20261027-19, brief-modello-documento-vendita
--   §15, M-3): permesso => nascondi. Un passaggio con un'azione sulla
--   sua riga della matrice (numera_fatture_lotti su numera e riporta
--   in bozza) si nasconde a chi non ce l'ha; la riga si legge da
--   script.fn_doc_passaggio, la stessa che leggono il verbo e il
--   backend. Prima il permesso lo decideva il frontend con una sua
--   mappa (LOTTO_AZIONE_PERMESSO), che si ritira.
DECLARE
    -- Tipi nudi solo per valori CALCOLATI (azioni e motivi jsonb, flag,
    -- motivi e chiavi i18n composti): nessuna colonna di cui siano il riflesso.
    v_stato_id     vendite.fatturazione_lotti.stato_doc_fiscale_id%TYPE;
    v_stato_cod    config.stati_doc_fiscale.codice_interno%TYPE;
    v_tipo_lotto   vendite.fatturazione_lotti.tipo_lotto%TYPE;
    v_actions      jsonb;
    v_can_change   boolean := false;
    v_mot_annulla  jsonb;
    v_mot_riporta  jsonb;
    -- L'utente della sessione, per l'azione del passaggio (rev 2026-10-27).
    v_utente       config.user_override_azioni.auth_user_id%TYPE;
BEGIN
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    -- Stato corrente + tipo. LEFT JOIN: un lotto senza stato deve
    -- restare una riga (e non avere azioni), non sparire.
    SELECT fl.stato_doc_fiscale_id, sdf.codice_interno, fl.tipo_lotto
      INTO v_stato_id, v_stato_cod, v_tipo_lotto
      FROM vendite.fatturazione_lotti fl
      LEFT JOIN config.stati_doc_fiscale sdf
        ON sdf.id = fl.stato_doc_fiscale_id
     WHERE fl.id = p_lotto_id;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    -- Motivi ostativi dei due verbi distruttivi, calcolati UNA
    -- volta sola. Le fn sono pure: [] quando l'uscita e' lecita.
    v_mot_annulla := script.fn_check_lotto_annullabile(p_lotto_id);
    v_mot_riporta := script.fn_check_lotto_riportabile_a_draft(p_lotto_id);

    -- Transizioni manuali disponibili dallo stato corrente.
    -- ⚠️ Il predicato sulla matrice e' lo STESSO del guard vivo
    -- (vendite.trgfn_fatturazione_lotti_guard_stato): ammesso,
    -- solo_fattura = false, meta.tipo_lotto compatibile. Non si
    -- filtra su solo_lotto: il guard non lo fa, e le righe del
    -- lotto sono esattamente quelle non-solo_fattura.
    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'key',              t.meta->>'action_key',
                'target_state',     sa.codice_interno,
                -- Forma leggibile della destinazione: la colonna
                -- accanto, nello stesso JOIN. Il FE non puo'
                -- derivarla dal codice.
                'target_state_descrizione', sa.descrizione,
                'label_key',        t.meta->>'label_key',
                'requires_confirm', COALESCE((t.meta->>'requires_confirm')::boolean, false),
                'outlined',         COALESCE((t.meta->>'outlined')::boolean, false),
                'enabled',          CASE t.meta->>'action_key'
                                      WHEN 'annulla'         THEN jsonb_array_length(v_mot_annulla) = 0
                                      WHEN 'riporta_a_draft' THEN jsonb_array_length(v_mot_riporta) = 0
                                      ELSE true
                                    END,
                'reasons',          CASE t.meta->>'action_key'
                                      WHEN 'annulla'         THEN v_mot_annulla
                                      WHEN 'riporta_a_draft' THEN v_mot_riporta
                                      ELSE '[]'::jsonb
                                    END
            )
            ORDER BY sa.ordine
        ),
        '[]'::jsonb
    )
    INTO v_actions
    FROM config.stati_doc_fiscale_transizioni t
    JOIN config.stati_doc_fiscale sa ON sa.id = t.stato_to_id
    -- L'azione del passaggio dal lettore unico (rev 2026-10-27, M-3).
    CROSS JOIN LATERAL script.fn_doc_passaggio('vendite.fatturazione_lotti'::regclass,
                                               t.stato_from_id, t.stato_to_id) pz
    WHERE t.stato_from_id = v_stato_id
      -- Permesso => nascondi: chi non ha l'azione del passaggio non vede il bottone.
      AND (pz.azione_processo_codename IS NULL
           OR script.fn_check_azione_processo(v_utente, pz.azione_processo_codename))
      AND t.ammesso IS TRUE
      AND t.solo_fattura IS FALSE
      AND ((t.meta->>'tipo_lotto') IS NULL OR (t.meta->>'tipo_lotto') = v_tipo_lotto)
      AND COALESCE((t.meta->>'manuale')::boolean, false) IS TRUE
      AND (t.meta->>'action_key') IS NOT NULL
      AND (t.meta->>'label_key')  IS NOT NULL;

    -- can_change_state sulle sole azioni ABILITATE e sulle sole
    -- TRANSIZIONI: si calcola PRIMA di appendere la ristampa,
    -- che non cambia stato. Con le azioni disabilitate ora
    -- presenti in lista, un semplice array_length sarebbe
    -- sempre true.
    SELECT EXISTS (
        SELECT 1
          FROM jsonb_array_elements(v_actions) AS a
         WHERE COALESCE((a->>'enabled')::boolean, true) IS TRUE
    ) INTO v_can_change;

    -- Ristampa massiva (C-8): azione applicativa, non transizione
    -- — stampare e' leggere (I-4). Disponibile su lotto
    -- DEFINITIVA, cioe' quando le fatture sono numerate.
    IF v_stato_cod = 'DEFINITIVA' THEN
        v_actions := v_actions || jsonb_build_array(
            jsonb_build_object(
                'key',              'ristampa',
                'target_state',     NULL,
                -- Non e' un cambio di stato: nessuna destinazione
                -- da nominare.
                'target_state_descrizione', NULL,
                'label_key',        'vendite.lotti.azione_ristampa',
                'requires_confirm', true,
                'outlined',         true,
                'enabled',          true,
                'reasons',          '[]'::jsonb
            )
        );
    END IF;

    RETURN jsonb_build_object(
        'available_actions', v_actions,
        'can_change_state',  v_can_change,
        'stato_codice',      v_stato_cod,
        'tipo_lotto',        v_tipo_lotto
    );
END;
$function$

COMMENT ON FUNCTION script.fn_available_actions_lotto(p_lotto_id bigint)
IS 'Capability del lotto di fatturazione per il detail API: available_actions + can_change_state + stato_codice + tipo_lotto. Ottava della famiglia fn_available_actions_*, mirror di fn_available_actions_commessa. I verbi numera / riporta_a_draft / annulla nascono DATA-DRIVEN da config.stati_doc_fiscale_transizioni (meta seedato il 2026-08-04) con lo STESSO predicato del guard vivo vendite.trgfn_fatturazione_lotti_guard_stato (ammesso + solo_fattura=false + meta.tipo_lotto compatibile): matrice e pulsanti non possono divergere. La ristampa e'' cablata perche'' non e'' una transizione (stampare e'' leggere, I-4) ed e'' disponibile su lotto DEFINITIVA. ATTENZIONE CONTRATTO: la presenza di un''azione in available_actions NON significa eseguibile — i consumatori devono leggere enabled e mostrare reasons; enabled/reasons di annulla e riporta_a_draft arrivano dalle funzioni PURE script.fn_check_lotto_annullabile / _riportabile_a_draft, le STESSE usate dalle fn di mutazione per sollevare. can_change_state e'' calcolato sulle sole azioni ABILITATE e sulle sole transizioni (la ristampa non cambia stato). 🔴 NON espone avanza_step / rilancia_step: quel gate (step successivo + criticita'' + rilancio dello stesso step, D-Q p.1) vive in LottoPipelineRunner e ricostruirlo qui sarebbe una seconda copia della regola. Fallback NULL se il lotto non esiste. rev 2026-08-04. rev 2026-08-06: + target_state_descrizione accanto a target_state (config.stati_doc_fiscale.descrizione della destinazione). Serve alla frase di conferma «portare il documento nello stato X»: il codice_interno non e'' la forma leggibile e derivarla nel FE sarebbe una seconda copia del vocabolario degli stati; NULL sulla ristampa, che non cambia stato. rev 2026-09-27 (20260927-10): le azioni non portano piu'' la chiave icon. Il DB manda il SIGNIFICATO (key), il frontend sceglie il segno dal key con una mappa verbo -> icona in core/ (decisione D-1 di Tid, opzione A): un segno scritto qui era l''unico dell''app che non passava dalle costanti del frontend, e lo stesso verbo ne portava due. Brief: brief-db-icone-azioni-per-significato (D-1). rev 2026-09-28 (20260928-07): le azioni non portano piu'' la chiave severity. Come l''icona, il colore del pulsante lo decide il VERBO, uguale in tutti i domini, e il frontend lo ricava dal key (mappa verbo -> aspetto in core/, decisione di Tid): lo stesso verbo portava colori diversi fra i domini. label_key e outlined restano dati. Brief: brief-db-icone-azioni-per-significato (§9). ⭐ rev 2026-10-27 (20261027-19, brief-modello-documento-vendita §15, M-3, Q-F1): un passaggio con un''azione di processo sulla sua riga della matrice (letta da script.fn_doc_passaggio: numera_fatture_lotti su numera e riporta in bozza) si NASCONDE a chi non ha l''azione (script.fn_check_azione_processo, utente da app.current_user_id): permesso => nascondi, stato => disabilita col motivo. Prima il permesso lo decideva il frontend con una sua mappa, che si ritira.';
```

</div>

---
{% include-markdown "signature-core.md" %}
