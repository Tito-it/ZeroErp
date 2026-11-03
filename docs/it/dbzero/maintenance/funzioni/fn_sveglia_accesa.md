{% include-markdown "it/dbzero/maintenance/manual/fn_sveglia_accesa.md" %}
# ⚙️ Funzione `fn_sveglia_accesa`

```sql
CREATE FUNCTION fn_sveglia_accesa(p_processo_codice text)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

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
IS 'La sveglia del processo deve far partire il lavoro? true o false, mai NULL: e'' la lettura per chi decide. La chiedono il passo di ogni job pgAgent di un processo (se la risposta e'' false il passo non lancia la procedura e il giornale non scrive niente), le sveglie systemd dei comandi del backend e «Esegui ora». Non la chiede la convergenza del rilascio, che chiama le procedure strutturali sempre: spegnere ferma la sveglia, non l''aggiornamento. La regola sta in dbops.fn_processo_acceso_su_valori, la lettura in dbops.fn_processo_acceso_dichiarato; qui un NULL diventa l''errore giusto. Errori: E_PROCESSO_NON_TROVATO (codice inesistente); E_PROCESSO_SENZA_SVEGLIA (canale CODA, o processo ritirato); E_CONFIG_MANCANTE in tre casi: ambiente non dichiarato senza una scelta a mano che decida da sola, scelta a mano di accensione non ammessa dal divieto di accensione in produzione con l''ambiente non dichiarato, catalogo senza il default di accensione per l''ambiente. SECURITY DEFINER: pgAgent si collega come zeroerp_job, che non legge dbops. La porta e'' stretta: un codice in, un booleano fuori.';
```

</div>

---
{% include-markdown "signature-core.md" %}
