{% include-markdown "it/dbzero/script/manual/fn_check_rinuncia_reversibile.md" %}
# ⚙️ Funzione `fn_check_rinuncia_reversibile`

```sql
CREATE FUNCTION fn_check_rinuncia_reversibile(p_resi_riga_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_rinuncia_reversibile(p_resi_riga_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono di RIAPRIRE una rinuncia
--   (annullare la dichiarazione di definitivita' su una quota resa).
--   Funzione PURA (fn_check_*): nessun raise di dominio, nessuna
--   scrittura. Consumatore: vendite.fn_riapri_riconsegna_reso.
--   Brief: brief-db-chiusura-riconsegna-reso-definitivo §5.1.
-- Ritorna: [] se reversibile; altrimenti array ordinato di
--   {codice, reason, reason_key, dettaglio}.
--
-- STATO ATTUALE: ritorna SEMPRE []. E' deliberato, non incompleto.
--   Il gate corretto sarebbe "non piu' reversibile una volta emessa
--   la nota di credito sulla quota", ma il ramo NC non esiste ancora
--   nel progetto: oggi la coda accrediti (vw_resi_da_accreditare) la
--   alimenta e nessuno emette NC. Vietare qualcosa che non puo'
--   accadere sarebbe finto rigore.
--
-- ⚠️ QUANDO ARRIVERA' LA SLICE NC: il divieto va aggiunto QUI, e si
--   attiva da se' — fn_riapri_riconsegna_reso solleva gia' il primo
--   motivo che questa funzione produce. Non serve toccare la madre.
--   Motivo previsto: la quota rinunciata risulta coperta da una nota
--   di credito emessa -> riaprirla sfalserebbe un documento fiscale.
--   Codice da registrare allora (non oggi, per non lasciare a
--   catalogo un codice mai sollevato).
--
-- ⚠️ NON RIMUOVERE questa funzione "perche' ritorna sempre vuoto":
--   e' il punto di innesto del gate. Rimuoverla riporta il problema
--   a essere una nota in un commento che nessuno cerchera'.
DECLARE
    v_motivi jsonb := '[]'::jsonb;
    v_esiste boolean;
BEGIN
    IF p_resi_riga_id IS NULL OR p_resi_riga_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script','fn_check_rinuncia_reversibile','E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro','resi_riga_id','valore',p_resi_riga_id),
            NULL::uuid, 'resi_riga_id obbligatorio (>0)');
    END IF;

    -- La riga deve esistere: un id inventato non e' "reversibile",
    -- e' un errore del chiamante. Si segnala come motivo (non come
    -- raise) per restare puri: la madre decide se sollevare.
    SELECT EXISTS (SELECT 1 FROM vendite.resi_righe rr
                    WHERE rr.id = p_resi_riga_id)
      INTO v_esiste;

    IF NOT v_esiste THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_RESO_NOT_FOUND',
            'reason',     'RIGA_INESISTENTE',
            -- Riuso di E_RESO_NOT_FOUND: esiste a catalogo, nessun
            -- codice nuovo per un caso che e' un errore del chiamante.
            'reason_key', 'vendite.resi.rinuncia_reason.riga_inesistente',
            'dettaglio',  p_resi_riga_id);
        RETURN v_motivi;
    END IF;

    -- === PUNTO DI INNESTO SLICE NC ===
    -- Qui andra' il controllo sulla nota di credito emessa per la
    -- quota rinunciata. Finche' il ramo NC non esiste, nessun motivo.
    -- ==================================

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_rinuncia_reversibile(p_resi_riga_id bigint)
IS 'Funzione PURA (fn_check_*): motivi che impediscono di RIAPRIRE una rinuncia di ri-consegna (brief-db-chiusura-riconsegna-reso-definitivo S5.1). Ritorna [] se reversibile. GATE DORMIENTE: oggi l''unico motivo prodotto e'' la riga inesistente, perche'' il gate vero - "non piu'' reversibile a nota di credito emessa" - riguarda un ramo NC che nel progetto NON esiste ancora. E'' il PUNTO DI INNESTO: quando la slice NC arrivera'', il divieto si aggiunge QUI e si attiva da se'' (vendite.fn_riapri_riconsegna_reso solleva gia'' il primo motivo prodotto), senza toccare la madre. NON rimuovere perche'' "ritorna sempre vuoto": rimuoverla riporta la conseguenza a essere una nota in un commento. rev 2026-07-26.';
```

---
{% include-markdown "signature-core.md" %}
