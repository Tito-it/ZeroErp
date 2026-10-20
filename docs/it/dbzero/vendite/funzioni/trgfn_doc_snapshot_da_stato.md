{% include-markdown "it/dbzero/vendite/manual/trgfn_doc_snapshot_da_stato.md" %}
# ⚙️ Funzione `trgfn_doc_snapshot_da_stato`

```sql
CREATE FUNCTION trgfn_doc_snapshot_da_stato()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_doc_snapshot_da_stato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: copiare sulla riga le bandiere booleane del
--   vocabolario degli stati, a ogni INSERT e UPDATE.
-- Montaggio: [0] colonna di stato, [1] vocabolario
--   (schema.tabella), poi coppie (colonna snapshot, colonna
--   del vocabolario). Vedi l'intestazione del changeSet.
-- =========================================================
DECLARE
    -- Nomi dal montaggio e la riga come jsonb: il BB serve
    -- tabelle diverse, nessuna colonna da ancorare.
    v_col_stato   text;
    v_vocabolario text;
    v_riga        jsonb;
    v_stato_id    bigint;
    v_bandiere    text[] := ARRAY[]::text[];
    v_valori      jsonb;
    v_patch       jsonb := '{}'::jsonb;
    i             integer;
BEGIN
    v_col_stato   := TG_ARGV[0];
    v_vocabolario := TG_ARGV[1];
    v_riga        := to_jsonb(NEW);

    -- Montaggio: stato, vocabolario e almeno una coppia; ogni
    -- colonna snapshot esiste sulla riga.
    IF TG_NARGS < 4 OR TG_NARGS % 2 <> 0
       OR NOT (v_riga ? v_col_stato)
       OR EXISTS (SELECT 1
                    FROM generate_series(2, TG_NARGS - 1, 2) AS g(k)
                   WHERE NOT (v_riga ? TG_ARGV[g.k])) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME::text, 'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('trigger', TG_NAME,
                               'table',   TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'tg_argv', TG_ARGV),
            NULL::uuid, 'vendite.trgfn_doc_snapshot_da_stato',
            'montaggio: [0] colonna di stato, [1] vocabolario, poi coppie (colonna snapshot, colonna del vocabolario)');
    END IF;

    FOR i IN 2 .. TG_NARGS - 1 BY 2 LOOP
        v_bandiere := v_bandiere || TG_ARGV[i + 1];
    END LOOP;

    v_stato_id := (v_riga ->> v_col_stato)::bigint;

    -- Le bandiere dello stato, in un colpo: {"is_abortito": true, ...}.
    IF v_stato_id IS NOT NULL THEN
        EXECUTE format('SELECT to_jsonb(s) FROM %s s WHERE s.id = $1',
                       v_vocabolario::regclass)
           INTO v_valori
          USING v_stato_id;
    END IF;

    FOR i IN 2 .. TG_NARGS - 1 BY 2 LOOP
        v_patch := v_patch || jsonb_build_object(
            TG_ARGV[i],
            COALESCE((v_valori ->> TG_ARGV[i + 1])::boolean, false));
    END LOOP;

    NEW := jsonb_populate_record(NEW, v_patch);
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_doc_snapshot_da_stato()
IS 'BB (2026-10-11, brief-db-annullo-documento-con-legami D-6): copia sulla riga le bandiere booleane del vocabolario degli stati, a ogni INSERT e UPDATE (BEFORE, fascia _z90_, senza OF: lo snapshot e'' derivato e una scrittura a mano non lo falsifica). Montaggio: [0] colonna di stato, [1] vocabolario (schema.tabella), poi coppie (colonna snapshot, colonna del vocabolario). Serve a indici e colonne generate, che non leggono un''altra tabella: vendite.contratti (is_abortito_snapshot, is_draft_snapshot -> partecipa_overlap_snapshot e uq_contratti_offerta_id) e vendite.ordini (is_abortito_snapshot -> uq_ordini_v_documento_origine_offerta). Stato NULL o assente: false. Montaggio sbagliato: E_VENDITE_CHIAMATA_NON_VALIDA. Regola del 2: prende il posto di vendite.trgfn_contratti_sync_is_abortito_snapshot.';
```

</div>

---
{% include-markdown "signature-core.md" %}
