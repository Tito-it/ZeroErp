{% include-markdown "it/dbzero/script/manual/trgfn_doc_stato_solo_dal_verbo.md" %}
# ⚙️ Funzione `trgfn_doc_stato_solo_dal_verbo`

```sql
CREATE FUNCTION trgfn_doc_stato_solo_dal_verbo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_doc_stato_solo_dal_verbo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- Il BB serve piu' testate: la riga come jsonb, nessuna
    -- colonna a cui ancorarsi.
    v_col       text;
    v_prima     jsonb;
    v_dopo      jsonb;
    v_guc       text;
    v_atteso    text;
    v_verbo     boolean;
    v_documento config.sorgenti.etichetta%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: la porta (BEFORE UPDATE OF colonna di stato,
    --   fascia _a05_). Lo stato cambia solo dalla scrittura
    --   del verbo (script.fn_doc_scrivi_stato).
    -- =========================================================
    SELECT m.colonna_stato INTO v_col
      FROM script.fn_doc_stato_modello(TG_RELID::regclass) m;

    IF v_col IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('trigger', TG_NAME,
                               'table',   TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME),
            NULL::uuid,
            'script.trgfn_doc_stato_solo_dal_verbo',
            'montato su una testata della mappa del modello (script.fn_doc_stato_modello)');
    END IF;

    v_prima := to_jsonb(OLD);
    v_dopo  := to_jsonb(NEW);

    -- UPDATE OF scatta anche a valore uguale: lo stato non cambia, passa.
    IF (v_prima -> v_col) IS NOT DISTINCT FROM (v_dopo -> v_col) THEN
        RETURN NEW;
    END IF;

    v_guc    := current_setting('zeroerp.doc_cambio_stato', true);
    v_atteso := TG_RELID::text || ':' || (v_prima ->> 'id');
    v_verbo  := script.fn_is_proprietario_tabella(TG_RELID::regclass);

    IF v_guc IS DISTINCT FROM v_atteso OR NOT v_verbo THEN
        SELECT s.etichetta INTO v_documento
          FROM config.sorgenti s
         WHERE s.target_table = TG_RELID::regclass;

        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text, 'E_DOC_STATO_SOLO_DAL_VERBO',
            jsonb_build_object('table',        TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'id',           v_prima ->> 'id',
                               'colonna',      v_col,
                               'stato_da_id',  v_prima ->> v_col,
                               'stato_a_id',   v_dopo  ->> v_col,
                               'guc_valore',   v_guc,
                               'dentro_verbo', v_verbo,
                               'db_user',      current_user),
            NULL::uuid,
            COALESCE(v_documento, TG_TABLE_NAME::text),
            COALESCE(v_prima ->> 'numero', v_prima ->> 'id'));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_doc_stato_solo_dal_verbo()
IS 'BB della porta (BEFORE UPDATE OF <colonna di stato>, fascia _a05_): lo stato di un documento sul modello si cambia solo dalla scrittura del suo verbo, script.fn_doc_scrivi_stato. Due condizioni insieme: la GUC transazionale zeroerp.doc_cambio_stato porta questa testata e questo documento (''<oid>:<id>'') E chi esegue e'' il proprietario della tabella (script.fn_is_proprietario_tabella: un verbo DEFINER, non l''applicazione che accende la GUC da se''). Altrimenti E_DOC_STATO_SOLO_DAL_VERBO (TECNICO). Un UPDATE che riscrive lo stesso stato passa. Nessun argomento: la colonna di stato la dice script.fn_doc_stato_modello; testata fuori mappa: E_SCRIPT_CHIAMATA_NON_VALIDA. Sede unica delle porte di bolla e reso (prima Regola 3 di trgfn_ddt_guard_transizione e Regola 2 di trgfn_resi_guard_transizione, ritirate). Montato come trg_<tabella>_a05_stato_solo_dal_verbo_upd. Brief: brief-modello-documento-vendita §7 (S-1 b, Tid 2026-10-25).';
```

</div>

---
{% include-markdown "signature-core.md" %}
