{% include-markdown "it/dbzero/script/manual/trgfn_doc_stato_iniziale.md" %}
# ⚙️ Funzione `trgfn_doc_stato_iniziale`

```sql
CREATE FUNCTION trgfn_doc_stato_iniziale()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_doc_stato_iniziale()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- Nomi dal montaggio e la riga come jsonb: il BB serve
    -- dieci testate, nessuna colonna a cui ancorarsi.
    v_col_stato     text;
    v_vocabolario   regclass;
    v_riga          jsonb;
    -- l'id di uno stato di uno degli otto vocabolari: bigint
    -- in tutti (vedi script.fn_stato_iniziale_id)
    v_iniziale      bigint;
    v_stato         bigint;
    v_documento     config.sorgenti.etichetta%TYPE;
    -- descrizioni dal vocabolario del montaggio: otto tabelle,
    -- nessuna colonna a cui ancorarle
    v_nome_stato    text;
    v_nome_iniziale text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Un documento nasce nel suo stato iniziale (BEFORE
    --   INSERT, fascia _a05_).
    --
    -- Montaggio: [0] colonna di stato della testata,
    --   [1] vocabolario degli stati (schema.tabella).
    --
    -- Regole:
    --   - stato NULL: lo stato iniziale del vocabolario;
    --   - stato iniziale: passa;
    --   - altro stato: E_DOC_STATO_INIZIALE_NON_VALIDO;
    --   - montaggio sbagliato o vocabolario senza stato
    --     iniziale: E_SCRIPT_CHIAMATA_NON_VALIDA.
    -- =========================================================
    v_col_stato := TG_ARGV[0];
    v_riga      := to_jsonb(NEW);

    IF TG_NARGS <> 2
       OR NOT (v_riga ? v_col_stato)
       OR to_regclass(TG_ARGV[1]) IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('trigger', TG_NAME,
                               'table',   TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'tg_argv', TG_ARGV),
            NULL::uuid,
            'script.trgfn_doc_stato_iniziale',
            'montaggio: [0] colonna di stato della testata, [1] vocabolario degli stati');
    END IF;

    v_vocabolario := to_regclass(TG_ARGV[1]);
    v_iniziale    := script.fn_stato_iniziale_id(v_vocabolario);

    IF v_iniziale IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('trigger',     TG_NAME,
                               'table',       TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'vocabolario', v_vocabolario::text),
            NULL::uuid,
            'script.trgfn_doc_stato_iniziale',
            format('il vocabolario %s non dichiara lo stato iniziale', v_vocabolario));
    END IF;

    v_stato := (v_riga ->> v_col_stato)::bigint;

    -- Lo stato non detto: lo mette il database (P-2).
    IF v_stato IS NULL THEN
        NEW := jsonb_populate_record(NEW, jsonb_build_object(v_col_stato, v_iniziale));
        RETURN NEW;
    END IF;

    IF v_stato = v_iniziale THEN
        RETURN NEW;
    END IF;

    -- Il rifiuto: i nomi che legge una persona, solo qui.
    SELECT s.etichetta INTO v_documento
      FROM config.sorgenti s
     WHERE s.target_table = TG_RELID;

    EXECUTE format(
        'SELECT max(s.descrizione) FILTER (WHERE s.id = $1),'
        '       max(s.descrizione) FILTER (WHERE s.id = $2)'
        '  FROM %s s WHERE s.id IN ($1, $2)', v_vocabolario)
       INTO v_nome_stato, v_nome_iniziale
      USING v_stato, v_iniziale;

    PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME::text, 'E_DOC_STATO_INIZIALE_NON_VALIDO',
        jsonb_build_object('table',             TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                           'colonna',           v_col_stato,
                           'stato_id',          v_stato,
                           'stato_iniziale_id', v_iniziale),
        NULL::uuid,
        COALESCE(v_documento, TG_TABLE_NAME::text),
        COALESCE(v_nome_stato, v_stato::text),
        v_nome_iniziale);

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_doc_stato_iniziale()
IS 'BB della nascita (BEFORE INSERT, fascia _a05_): un documento nasce nel suo stato iniziale. Stato assente: mette lo stato iniziale del vocabolario (script.fn_stato_iniziale_id); stato iniziale: passa; altro stato: E_DOC_STATO_INIZIALE_NON_VALIDO (TECNICO). Chi ha bisogno di un documento gia'' avanti lo crea e poi lo porta avanti coi passaggi della matrice, nella stessa transazione. Montaggio: [0] colonna di stato della testata, [1] vocabolario degli stati; montaggio sbagliato o vocabolario senza stato iniziale: E_SCRIPT_CHIAMATA_NON_VALIDA. Montato sulle testate di vendita e d''acquisto (trg_<tabella>_a05_stato_iniziale_ins). Brief: brief-modello-documento-vendita §4-bis/§4-ter (N-1 … N-3, P-2, Tid 2026-10-24).';
```

</div>

---
{% include-markdown "signature-core.md" %}
