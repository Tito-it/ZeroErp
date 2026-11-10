{% include-markdown "it/dbzero/dbops/manual/fn_imposta_accensione_processo.md" %}
# ⚙️ Funzione `fn_imposta_accensione_processo`

```sql
CREATE FUNCTION fn_imposta_accensione_processo(p_processo_codice text, p_acceso boolean, p_motivo text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

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
    --   sveglia di un processo: acceso true/false, oppure
    --   NULL (torna il default per ambiente). Tutti e tre
    --   scrivono la riga col motivo: la riga e' l'ultimo
    --   gesto, la storia sta in storico.processi_accensione.
    --   Restituisce lo stato effettivo dopo il gesto (NULL se
    --   l'ambiente non e' dichiarato e la scelta e' il default).
    --
    -- Regole:
    --   - i limiti (senza sveglia, non spegnibile, motivo) li
    --     dice il guard della tabella: qui non si ripetono;
    --   - chi e quando li scrive l'audit generato (app.jwt_user),
    --     non il verbo;
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

    INSERT INTO dbops.processi_accensione (processo_id, acceso, motivo)
    VALUES (v_processo_id, p_acceso, p_motivo)
    ON CONFLICT (processo_id) DO UPDATE
       SET acceso = EXCLUDED.acceso,
           motivo = EXCLUDED.motivo;

    RETURN dbops.fn_processo_acceso_dichiarato(p_processo_codice);
END;
$function$

COMMENT ON FUNCTION dbops.fn_imposta_accensione_processo(p_processo_codice text, p_acceso boolean, p_motivo text)
IS 'Il verbo della scelta a mano: accende (true), spegne (false) o rimette al default per ambiente (NULL) la sveglia di un processo su questa installazione, col motivo, obbligatorio anche per il default. Tutti e tre i gesti scrivono la riga di dbops.processi_accensione (acceso NULL = segue il default): la riga e'' l''ultimo gesto, la storia sta in storico.processi_accensione. Chi e quando li scrive l''audit generato dalle automazioni (script.trgfn_audit_data_user_generic, app.jwt_user), non il verbo. Restituisce lo stato effettivo dopo il gesto (dbops.fn_processo_acceso_dichiarato). I limiti li dice il guard della tabella (E_PROCESSO_SENZA_SVEGLIA, E_PROCESSO_NON_SPEGNIBILE, E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO, E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE); codice inesistente: E_PROCESSO_NON_TROVATO. INVOKER: il permesso e'' del backend, come per Esegui ora.';
```

</div>

---
{% include-markdown "signature-core.md" %}
