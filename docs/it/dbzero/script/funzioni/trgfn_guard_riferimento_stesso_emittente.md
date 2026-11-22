# ⚙️ Funzione `trgfn_guard_riferimento_stesso_emittente`

```sql
CREATE FUNCTION trgfn_guard_riferimento_stesso_emittente()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_guard_riferimento_stesso_emittente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- Gli argomenti di montaggio: due coppie (modo del registro
    -- dbops.emittente_modi, colonna della tabella).
    v_modo_riga dbops.emittente_modi.modo%TYPE := TG_ARGV[0];
    v_col_riga  text := TG_ARGV[1];   -- nome di colonna: nessuna colonna da ancorare
    v_modo_rif  dbops.emittente_modi.modo%TYPE := TG_ARGV[2];
    v_col_rif   text := TG_ARGV[3];   -- idem
    v_new       jsonb;
    v_old       jsonb;
    v_ef_riga   anagrafiche.emittenti_fiscali.id%TYPE;
    v_ef_rif    anagrafiche.emittenti_fiscali.id%TYPE;
BEGIN
    -- Scopo: il riferimento (lotto, seriale) e' dell'emittente
    --   della riga che lo nomina.
    -- Regole:
    --   0. montaggio: BEFORE ROW, INSERT o UPDATE, quattro
    --      argomenti, le due colonne nella tabella; altrimenti
    --      E_TRIGGER_ARGOMENTI_INVALIDI;
    --   1. riferimento nullo: passa;
    --   2. UPDATE che non cambia riga ne' riferimento: passa;
    --   3. emittente non risolto o diverso:
    --      E_RIFERIMENTO_DI_ALTRO_EMITTENTE (no-leak:
    --      inesistente e altrui rispondono uguale).
    v_new := to_jsonb(NEW);

    -- 0) Il montaggio.
    IF TG_WHEN <> 'BEFORE' OR TG_LEVEL <> 'ROW'
       OR TG_OP NOT IN ('INSERT', 'UPDATE')
       OR TG_NARGS <> 4
       OR NOT (v_new ? v_col_riga) OR NOT (v_new ? v_col_rif) THEN
        PERFORM script.fn_log_and_raise_error(
            TG_TABLE_SCHEMA::text,
            'script.trgfn_guard_riferimento_stesso_emittente',
            'E_TRIGGER_ARGOMENTI_INVALIDI',
            jsonb_build_object(
                'detail',    'atteso BEFORE ROW INSERT/UPDATE con (modo_riga, colonna_riga, modo_rif, colonna_rif), colonne della tabella',
                'tabella',   TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'trigger',   TG_NAME,
                'tg_op',     TG_OP,
                'argomenti', to_jsonb(TG_ARGV)),
            NULL::uuid,
            concat_ws(' ', TG_OP, coalesce(NULLIF(array_to_string(TG_ARGV, ', '), ''), '(nessun argomento)')));
    END IF;

    -- 1) Riferimento facoltativo, assente.
    IF v_new ->> v_col_rif IS NULL THEN
        RETURN NEW;
    END IF;

    -- 2) Niente di nuovo da giudicare.
    IF TG_OP = 'UPDATE' THEN
        v_old := to_jsonb(OLD);
        IF v_old -> v_col_rif  IS NOT DISTINCT FROM v_new -> v_col_rif
           AND v_old -> v_col_riga IS NOT DISTINCT FROM v_new -> v_col_riga THEN
            RETURN NEW;
        END IF;
    END IF;

    -- 3) I due emittenti, dal registro (risolutore DEFINER).
    v_ef_riga := script.fn_resolve_emittente_fiscale_id(v_modo_riga, (v_new ->> v_col_riga)::bigint);
    v_ef_rif  := script.fn_resolve_emittente_fiscale_id(v_modo_rif,  (v_new ->> v_col_rif)::bigint);

    IF v_ef_riga IS NULL OR v_ef_rif IS NULL OR v_ef_riga <> v_ef_rif THEN
        PERFORM script.fn_log_and_raise_error(
            TG_TABLE_SCHEMA::text,
            'script.trgfn_guard_riferimento_stesso_emittente',
            'E_RIFERIMENTO_DI_ALTRO_EMITTENTE',
            jsonb_build_object(
                'detail',      'il riferimento non e'' dell''emittente della riga, o non esiste',
                'campo',       v_col_rif,
                'tabella',     TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                v_col_riga,    v_new -> v_col_riga,
                v_col_rif,     v_new -> v_col_rif),
            NULLIF(v_new ->> 'tx_id', '')::uuid,
            VARIADIC ARRAY[]::text[]);   -- frase chiusa, senza segnaposto
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_guard_riferimento_stesso_emittente()
IS 'BB trigger: il riferimento di una riga (un lotto, un seriale) e'' dell''emittente della riga. Argomenti (modo_riga, colonna_riga, modo_rif, colonna_rif): due coppie del registro dbops.emittente_modi, risolte con script.fn_resolve_emittente_fiscale_id (SECURITY DEFINER: la lettura non dipende dalla RLS di chi scrive). Riferimento nullo: passa; UPDATE che non cambia ne'' riga ne'' riferimento: passa. Emittente non risolto o diverso: E_RIFERIMENTO_DI_ALTRO_EMITTENTE, campo = colonna del riferimento; inesistente e altrui rispondono uguale (no-leak). Montaggio sbagliato: E_TRIGGER_ARGOMENTI_INVALIDI. BEFORE INSERT OR UPDATE, fase a10, nome trg_<t>_a10_guard_rif_<oggetto>_emittente_ins_upd.';
```

</div>

---
{% include-markdown "signature-core.md" %}
