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

    -- Nessuna riga: la matrice ha un giudice solo, il guard di
    -- transizione del documento, all'UPDATE.
    IF NOT FOUND THEN
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
IS 'BB del modello del documento, prima meta'' del verbo di stato: il permesso del passaggio, nella prima riga del verbo, prima di scrivere qualunque cosa. Legge la riga da script.fn_doc_passaggio: riga di processo (manuale = false) -> E_DOC_PASSAGGIO_DI_PROCESSO (la scrive solo il verbo che ne e'' la causa); riga con l''azione -> script.fn_guard_azione (E_PERMESSO_NEGATO); riga senza azione -> passa (il permesso sul documento lo controlla il backend, M-3); nessuna riga -> passa, e il passaggio lo rifiuta il guard di transizione del documento all''UPDATE (la matrice ha un giudice solo). La seconda meta'' e'' script.fn_doc_scrivi_stato. Brief: brief-modello-documento-vendita §7 (M-1, M-3, M-4, S-2, Tid 2026-10-24/25).';
```

</div>

---
{% include-markdown "signature-core.md" %}
