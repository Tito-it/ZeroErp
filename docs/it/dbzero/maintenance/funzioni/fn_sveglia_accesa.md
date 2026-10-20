{% include-markdown "it/dbzero/maintenance/manual/fn_sveglia_accesa.md" %}
# ⚙️ Funzione `fn_sveglia_accesa`

```sql
CREATE FUNCTION fn_sveglia_accesa(p_processo_codice text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION maintenance.fn_sveglia_accesa(p_processo_codice text)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_canale       dbops.processi.canale%TYPE;
    v_obsoleto_dal dbops.processi.obsoleto_dal%TYPE;
    -- La risposta: nessuna colonna di cui sia il riflesso.
    v_acceso       boolean;
BEGIN
    -- =========================================================
    -- Scopo:
    --   La sveglia del processo deve far partire il lavoro?
    --   Per chi DECIDE: true o false, mai NULL.
    --
    -- Regole:
    --   - la regola e' in dbops.fn_processo_acceso_su_valori,
    --     la lettura in dbops.fn_processo_acceso_dichiarato:
    --     qui si trasformano i NULL in errori;
    --   - non la chiama la convergenza del rilascio (P-3).
    -- =========================================================
    SELECT p.canale, p.obsoleto_dal
      INTO v_canale, v_obsoleto_dal
      FROM dbops.processi p
     WHERE p.codice = p_processo_codice;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'maintenance', 'fn_sveglia_accesa', 'E_PROCESSO_NON_TROVATO',
            jsonb_build_object('processo_codice', p_processo_codice),
            NULL::uuid,
            COALESCE(p_processo_codice, '-'));
    END IF;

    IF v_canale = 'CODA' OR v_obsoleto_dal IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'maintenance', 'fn_sveglia_accesa', 'E_PROCESSO_SENZA_SVEGLIA',
            jsonb_build_object('processo_codice', p_processo_codice,
                               'canale',          v_canale,
                               'obsoleto_dal',    v_obsoleto_dal),
            NULL::uuid,
            p_processo_codice);
    END IF;

    v_acceso := dbops.fn_processo_acceso_dichiarato(p_processo_codice);

    IF v_acceso IS NULL THEN
        -- Non decidibile. Prima la causa piu' probabile:
        -- l'ambiente non dichiarato (solleva E_CONFIG_MANCANTE).
        PERFORM script.fn_ambiente_installazione();

        -- Ambiente dichiarato: allora manca il default nel
        -- catalogo (riga senza le colonne di accensione).
        PERFORM script.fn_log_and_raise_error(
            'maintenance', 'fn_sveglia_accesa', 'E_CONFIG_MANCANTE',
            jsonb_build_object('configurazione', 'dbops.processi.acceso_in_sviluppo/acceso_in_produzione',
                               'processo_codice', p_processo_codice),
            NULL::uuid,
            format('il default di accensione del processo %s', p_processo_codice));
    END IF;

    RETURN v_acceso;
END;
$function$

COMMENT ON FUNCTION maintenance.fn_sveglia_accesa(p_processo_codice text)
IS 'La sveglia del processo deve far partire il lavoro? true o false, mai NULL: per chi DECIDE. La chiedono il passo di ogni job pgAgent di un processo (85_pgagent/20261016-30: se false il passo non lancia la procedura e non scrive nel giornale) e le sveglie systemd dei COMMAND (giro BE). NON la chiede la convergenza del rilascio (90_end/ci_apply/20260926-10), che chiama le procedure strutturali sempre: spegnere ferma la sveglia, non l''aggiornamento (P-3). Errori: E_PROCESSO_NON_TROVATO, E_PROCESSO_SENZA_SVEGLIA (CODA o ritirato), E_CONFIG_MANCANTE (ambiente non dichiarato, oppure catalogo senza il default). La regola e'' in dbops.fn_processo_acceso_su_valori, la lettura in dbops.fn_processo_acceso_dichiarato. SECURITY DEFINER: pgAgent gira come zeroerp_job, che non legge dbops; porta stretta, un codice in e un booleano fuori. Brief: brief-db-processi-accensione-per-ambiente (§5.3).';
```

</div>

---
{% include-markdown "signature-core.md" %}
