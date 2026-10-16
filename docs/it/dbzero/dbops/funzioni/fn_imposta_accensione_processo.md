{% include-markdown "it/dbzero/dbops/manual/fn_imposta_accensione_processo.md" %}
# ⚙️ Funzione `fn_imposta_accensione_processo`

```sql
CREATE FUNCTION fn_imposta_accensione_processo(p_processo_codice text, p_acceso boolean, p_motivo text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_imposta_accensione_processo(p_processo_codice text, p_acceso boolean, p_motivo text)
 RETURNS boolean
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_processo_id dbops.processi.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   La scelta a mano di questa installazione sulla
    --   sveglia di un processo. acceso true/false la scrive,
    --   acceso NULL la toglie (torna il default per ambiente).
    --   Restituisce lo stato effettivo dopo il gesto (NULL se
    --   l'ambiente non e' dichiarato e la riga e' stata tolta).
    --
    -- Regole:
    --   - i limiti (senza sveglia, non spegnibile, motivo) li
    --     dice il guard della tabella: qui non si ripetono;
    --   - il permesso e' del backend.
    -- =========================================================
    SELECT p.id
      INTO v_processo_id
      FROM dbops.processi p
     WHERE p.codice = p_processo_codice;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'fn_imposta_accensione_processo', 'E_PROCESSO_NON_TROVATO',
            jsonb_build_object('processo_codice', p_processo_codice),
            NULL::uuid,
            COALESCE(p_processo_codice, '-'));
    END IF;

    IF p_acceso IS NULL THEN
        DELETE FROM dbops.processi_accensione a
         WHERE a.processo_id = v_processo_id;
    ELSE
        INSERT INTO dbops.processi_accensione (processo_id, acceso, motivo)
        VALUES (v_processo_id, p_acceso, p_motivo)
        ON CONFLICT (processo_id) DO UPDATE
           SET acceso      = EXCLUDED.acceso,
               motivo      = EXCLUDED.motivo,
               -- Le automazioni non coprono dbops: l'audit
               -- dell'aggiornamento si scrive qui.
               data_update = now(),
               user_update = CURRENT_USER;
    END IF;

    RETURN dbops.fn_processo_acceso_dichiarato(p_processo_codice);
END;
$function$

COMMENT ON FUNCTION dbops.fn_imposta_accensione_processo(p_processo_codice text, p_acceso boolean, p_motivo text)
IS 'Il verbo della scelta a mano: accende (true) o spegne (false) la sveglia di un processo su questa installazione, col motivo; acceso NULL toglie la scelta e torna il default per ambiente del catalogo (nessuna traccia nella tabella: la tiene il registro delle operazioni del backend). data_update e user_update li scrive il verbo: le automazioni non coprono dbops. Restituisce lo stato effettivo dopo il gesto (dbops.fn_processo_acceso_dichiarato). I limiti li dice il guard della tabella (E_PROCESSO_SENZA_SVEGLIA, E_PROCESSO_NON_SPEGNIBILE, E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO); codice inesistente: E_PROCESSO_NON_TROVATO. INVOKER: il permesso e'' del backend, come per Esegui ora. Brief: brief-db-processi-accensione-per-ambiente (A-2).';
```

---
{% include-markdown "signature-core.md" %}
