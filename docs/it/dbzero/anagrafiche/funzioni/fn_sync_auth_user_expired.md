{% include-markdown "it/dbzero/anagrafiche/manual/fn_sync_auth_user_expired.md" %}
# ⚙️ Funzione `fn_sync_auth_user_expired`

```sql
CREATE FUNCTION fn_sync_auth_user_expired()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_sync_auth_user_expired()
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- Variabili locali tipizzate %TYPE (policy ZeroErp).
    v_auth_user_id anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_modified     boolean;        -- esito di fn_sync_auth_user_is_active: nessuna colonna dietro
    v_count        integer := 0;   -- un conteggio
BEGIN
    -- ------------------------------------------------------------
    -- Funzione: anagrafiche.fn_sync_auth_user_expired (v5, 07-10-2026)
    -- Scopo:
    --   Batch notturno: riallinea auth_user.is_active alla data di
    --   oggi, nei DUE versi. Una data che arriva non scrive niente e
    --   non fa scattare trigger, quindi:
    --     * SPEGNE la credenziale che non ha piu' nessuna veste
    --       utilizzabile (la veste o il rapporto sono scaduti);
    --     * ACCENDE la credenziale che ne ha una diventata valida oggi
    --       (valido_dal arrivato).
    --   ⭐ v5 (decisione di Tid, 2026-10-07): fino alla v4 il batch
    --   solo spegneva. Una credenziale con l'unica veste a valido_dal
    --   futuro nasceva spenta e restava spenta anche il giorno in cui
    --   la veste diventava valida, finche' qualcuno non scriveva sulla
    --   veste. Il nome resta (pgAgent, command Django e repository BE
    --   lo chiamano); il ritorno conta le credenziali riallineate.
    --   ⭐ v4 (brief-db-veste-utilizzabile): i candidati si scelgono
    --   con script.fn_veste_utilizzabile, la stessa regola che poi
    --   decide in fn_sync_auth_user_is_active. Prima il batch
    --   guardava solo identita_digitali.valido_al: con D-2 l'operatore
    --   umano scade anche col suo rapporto (risorse_umane.valido_al),
    --   e quel candidato il batch non lo avrebbe proposto mai.
    --   ⛔ Il «ramo legacy» (risorse_umane.valido_al via la vista
    --   risorse_umane_auth_user) e' caduto: la regola vive in
    --   identita_digitali.valido_al (decisione Tid 12-09-2026), e
    --   fn_sync_auth_user_is_active decide comunque SOLO sull'identita'
    --   — quel ramo poteva proporre candidati, mai cambiare l'esito.
    --
    --   Uso: pgAgent daily job + management command Django.
    --
    -- Ritorna: numero di credenziali effettivamente riallineate
    --          (spente o accese).
    -- ------------------------------------------------------------

    -- Short-circuit CI: se lo schema django non esiste, no-op.
    IF to_regclass('django.auth_user') IS NULL THEN
        RETURN 0;
    END IF;

    -- Loop sui candidati: credenziali che hanno delle vesti e il cui
    -- is_active non dice piu' «esiste una veste utilizzabile oggi»
    -- (la regola che decide in fn_sync_auth_user_is_active), nei due
    -- versi. Una credenziale senza vesti non e' affare di questo batch.
    FOR v_auth_user_id IN
        EXECUTE '
            SELECT au.id
              FROM django.auth_user au
             WHERE EXISTS (
                       SELECT 1
                         FROM anagrafiche.identita_digitali id
                        WHERE id.auth_user_id = au.id)
               AND au.is_active IS DISTINCT FROM EXISTS (
                       SELECT 1
                         FROM anagrafiche.identita_digitali id
                        WHERE id.auth_user_id = au.id
                          AND script.fn_veste_utilizzabile(id.id))
        '
    LOOP
        -- Invoca la nuova firma sync per ciascun candidato.
        -- La funzione sync applica la logica di fail-closed
        -- (fuori finestra -> false); qui contiamo solo quelli
        -- realmente modificati (v_modified = true).
        SELECT anagrafiche.fn_sync_auth_user_is_active(v_auth_user_id)
          INTO v_modified;

        IF v_modified THEN
            v_count := v_count + 1;
        END IF;
    END LOOP;

    RETURN v_count;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_sync_auth_user_expired()
IS 'Batch notturno: riallinea django.auth_user.is_active alla data di oggi nei due versi, perche'' una data che arriva non scrive niente e non fa scattare trigger. Spegne le credenziali che hanno vesti ma nessuna piu'' utilizzabile (veste o rapporto scaduti) e accende quelle che ne hanno una diventata valida oggi; la regola e'' script.fn_veste_utilizzabile, la stessa di fn_sync_auth_user_is_active, che fa l''aggiornamento. Una credenziale senza vesti resta fuori. Invocata da pgAgent daily e dal management command Django. Ritorna il numero di credenziali riallineate (spente o accese). Rev 2026-10-07 (brief-db-veste-utilizzabile): fino alla v4 solo spegneva, e una credenziale con l''unica veste a valido_dal futuro restava spenta anche il giorno in cui la veste diventava valida; il nome resta perche'' pgAgent, command e repository BE lo chiamano.';
```

</div>

---
{% include-markdown "signature-core.md" %}
