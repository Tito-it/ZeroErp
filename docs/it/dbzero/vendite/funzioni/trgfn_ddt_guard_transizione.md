{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_ddt_guard_transizione`

```sql
CREATE FUNCTION trgfn_ddt_guard_transizione()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: enforcement DB-first del grafo transizioni stato DDT.
--   La transizione (OLD.stato -> NEW.stato) e' ammessa solo se
--   presente e attiva in config.transizioni_stati_ddt.
--   Letto dalla matrice (no grafo hardcodato). Mirror del guard
--   ordini (trgfn_ordini_guard_transizione).
--   rev 2026-07-19: la Regola 2 (righe) delega a
--   script.fn_check_ddt_emittibile — single source con la capability.
--   rev 2026-10-25 (20261025-22: i segnaposto della frase; 20261025-14, brief-modello-documento-vendita §7):
--   la Regola 3 (porta del registro) si ritira; ogni cambio di stato
--   della bolla passa dalla porta comune
--   script.trgfn_doc_stato_solo_dal_verbo (trg_ddt_a05_stato_solo_dal_verbo_upd).
-- rev 2026-11-14 (brief-db-stati-documento-dal-vocabolario, giro 6d): la Regola 2 dallo stato
--   iniziale allo stato di emissione, dal vocabolario. Dove sopra si legge
--   DRAFT o EMESSO, vale lo stato che il vocabolario marca.
DECLARE
    v_codice_da config.stati_doc_ddt.codice_interno%TYPE;
    v_codice_a  config.stati_doc_ddt.codice_interno%TYPE;
    -- Il significato della partenza e della destinazione, dal vocabolario.
    v_iniziale_da config.stati_doc_ddt.iniziale%TYPE;
    v_emissione_a config.stati_doc_ddt.emissione%TYPE;
    v_ammessa   boolean := false;
BEGIN
    -- No-op se lo stato non cambia davvero (UPDATE su altre colonne).
    IF NEW.stato_doc_ddt_id IS NOT DISTINCT FROM OLD.stato_doc_ddt_id THEN
        RETURN NEW;
    END IF;

    SELECT
        max(CASE WHEN id = OLD.stato_doc_ddt_id THEN codice_interno END),
        max(CASE WHEN id = NEW.stato_doc_ddt_id THEN codice_interno END),
        bool_or(iniziale)  FILTER (WHERE id = OLD.stato_doc_ddt_id),
        bool_or(emissione) FILTER (WHERE id = NEW.stato_doc_ddt_id)
      INTO v_codice_da, v_codice_a, v_iniziale_da, v_emissione_a
      FROM config.stati_doc_ddt
     WHERE id IN (OLD.stato_doc_ddt_id, NEW.stato_doc_ddt_id);

    -- Regola 1: la transizione deve esistere ed essere attiva in matrice.
    SELECT EXISTS (
        SELECT 1
          FROM config.transizioni_stati_ddt t
         WHERE t.stato_da_id = OLD.stato_doc_ddt_id
           AND t.stato_a_id  = NEW.stato_doc_ddt_id
           AND t.attivo IS TRUE
    ) INTO v_ammessa;

    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_STATO_DDT_TRANSIZIONE_NON_VALIDA',
            jsonb_build_object(
                'ddt_id',   NEW.id,
                'numero',   NEW.numero,
                'stato_da', v_codice_da,
                'stato_a',  v_codice_a
            ),
            NEW.tx_id,
            -- La frase ha due segnaposto (da, a): fino al 2026-10-25 qui c'era
            -- anche NEW.id, e a video usciva «da <id> a <stato da>». L'id resta
            -- nel contesto.
            coalesce(v_codice_da, 'NULL'),
            coalesce(v_codice_a,  'NULL')
        );
    END IF;

    -- Regola 2: DRAFT->EMESSO richiede almeno una riga attiva.
    -- Zero righe = niente da trasportare. Il "DDT solo trasporto"
    -- resta possibile: e' righe senza prezzo, non zero righe.
    -- Verdetto dalla single source (fn_check_ddt_emittibile).
    IF v_iniziale_da AND v_emissione_a
       AND script.fn_check_ddt_emittibile(NEW)
           @> '[{"codice": "E_DDT_EMISSIONE_SENZA_RIGHE"}]'::jsonb THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_DDT_EMISSIONE_SENZA_RIGHE',
            jsonb_build_object(
                'ddt_id', NEW.id,
                'numero', NEW.numero
            ),
            NEW.tx_id,
            NEW.id::text,
            coalesce(NEW.numero, 'NULL')
        );
    END IF;

    -- Regola 3 — RITIRATA (rev 2026-10-25, 20261025-14). La porta del
    --   registro (solo i passaggi di magazzino delle bolle che muovono
    --   merce) e' contenuta nella porta comune
    --   script.trgfn_doc_stato_solo_dal_verbo, che chiude ogni cambio di
    --   stato della bolla al suo verbo (E_DOC_STATO_SOLO_DAL_VERBO).

    -- Regola 4 — RITIRATA (rev 2026-10-11, D-4 di
    --   brief-db-annullo-documento-con-legami). L'avviso dell'annullo con
    --   legami vale per bolla, ordine, preventivo e contratto, e sta nel BB
    --   vendite.trgfn_doc_guard_annullo_con_legami (trg_ddt_m10_guard_annullo_
    --   con_legami_upd), che conta i legami da vendite.fn_documento_legami
    --   (anche le righe di commessa NON_EMESSA) e solleva
    --   E_DOC_ANNULLO_CON_LEGAMI. Una regola, una sede.

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_guard_transizione()
IS 'Trigger function (BEFORE UPDATE dello stato di vendite.ddt): giudica il passaggio. Regola 1: il passaggio esiste attivo in config.transizioni_stati_ddt (E_STATO_DDT_TRANSIZIONE_NON_VALIDA; nella frase lo stato da e lo stato a). Regola 2: dallo stato iniziale allo stato di emissione (le colonne iniziale ed emissione di config.stati_doc_ddt) la bolla ha almeno una riga attiva (E_DDT_EMISSIONE_SENZA_RIGHE), col verdetto di script.fn_check_ddt_emittibile, la stessa check della capability. Gli altri motivi dell''emissione li sollevano i guard del valore delle righe, degli indirizzi e dei prezzi; l''annullo con legami lo giudica il BB vendite.trgfn_doc_guard_annullo_con_legami, e chi puo'' scrivere lo stato la porta comune script.trgfn_doc_stato_solo_dal_verbo. I codici degli stati vanno nel contesto degli errori. Gemello di vendite.trgfn_ordini_guard_transizione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
