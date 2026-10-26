{% include-markdown "it/dbzero/script/manual/fn_guard_passaggio.md" %}
# ⚙️ Funzione `fn_guard_passaggio`

```sql
CREATE FUNCTION fn_guard_passaggio(p_auth_user_id integer, p_testata regclass, p_stato_da_id bigint, p_stato_a_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_guard_passaggio(p_auth_user_id integer, p_testata regclass, p_stato_da_id bigint, p_stato_a_id bigint)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Uso, nella prima riga del verbo, dopo aver preso la testata FOR UPDATE:
--   PERFORM script.fn_guard_passaggio(v_utente, 'vendite.ddt',
--                                     v_ddt.stato_doc_ddt_id, v_stato_a_id);
DECLARE
    v_manuale boolean;
    v_azione  config.azioni_processo.permission_codename%TYPE;
BEGIN
    -- Gli stati: bigint di uno dei vocabolari della mappa.
    SELECT p.manuale, p.azione_processo_codename
      INTO v_manuale, v_azione
      FROM script.fn_doc_passaggio(p_testata, p_stato_da_id, p_stato_a_id) p;

    IF NOT FOUND THEN
        -- rev 2026-10-26 (20261026-01): allo stato che il documento ha
        -- gia'. Il guard di transizione non lo vede (lo stato non cambia,
        -- e un UPDATE che lo riscrive resta lecito): lo rifiuta il verbo,
        -- qui, prima di ogni suo lavoro.
        IF p_stato_da_id = p_stato_a_id THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'script.fn_guard_passaggio', 'E_DOC_GIA_NELLO_STATO',
                jsonb_build_object('testata',     p_testata::text,
                                   'stato_da_id', p_stato_da_id,
                                   'stato_a_id',  p_stato_a_id),
                NULL::uuid,
                COALESCE(script.fn_doc_stato_codice(p_testata, p_stato_a_id),
                         p_stato_a_id::text));
        END IF;

        -- Un cambio di stato fuori matrice: la matrice ha un giudice
        -- solo, il guard di transizione del documento, all'UPDATE.
        RETURN;
    END IF;

    IF NOT v_manuale THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_guard_passaggio', 'E_DOC_PASSAGGIO_DI_PROCESSO',
            jsonb_build_object('testata',     p_testata::text,
                               'stato_da_id', p_stato_da_id,
                               'stato_a_id',  p_stato_a_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    IF v_azione IS NOT NULL THEN
        PERFORM script.fn_guard_azione(p_auth_user_id, v_azione);
    END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_guard_passaggio(p_auth_user_id integer, p_testata regclass, p_stato_da_id bigint, p_stato_a_id bigint)
IS 'BB del modello del documento, prima meta'' del verbo di stato: il permesso del passaggio, nella prima riga del verbo, prima di scrivere qualunque cosa. Legge la riga da script.fn_doc_passaggio: riga di processo (manuale = false) -> E_DOC_PASSAGGIO_DI_PROCESSO (la scrive solo il verbo che ne e'' la causa); riga con l''azione -> script.fn_guard_azione (E_PERMESSO_NEGATO); riga senza azione -> passa (il permesso sul documento lo controlla il backend, M-3); nessuna riga e stato chiesto uguale a quello di oggi -> E_DOC_GIA_NELLO_STATO (rev 2026-10-26, 20261026-01: il guard di transizione non vede un passaggio che non cambia lo stato, e un UPDATE che lo riscrive resta lecito; la regola e'' del verbo); nessuna riga per un cambio di stato -> passa, e il passaggio lo rifiuta il guard di transizione del documento all''UPDATE (la matrice ha un giudice solo). La seconda meta'' e'' script.fn_doc_scrivi_stato. Brief: brief-modello-documento-vendita §7 (M-1, M-3, M-4, S-2, Tid 2026-10-24/25), §9.10 (Tid 2026-10-26).';
```

</div>

---
{% include-markdown "signature-core.md" %}
