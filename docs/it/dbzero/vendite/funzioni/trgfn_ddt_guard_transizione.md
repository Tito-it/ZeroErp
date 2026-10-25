{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_ddt_guard_transizione`

```sql
CREATE FUNCTION trgfn_ddt_guard_transizione()
```

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
DECLARE
    v_codice_da config.stati_doc_ddt.codice_interno%TYPE;
    v_codice_a  config.stati_doc_ddt.codice_interno%TYPE;
    v_ammessa   boolean := false;
BEGIN
    -- No-op se lo stato non cambia davvero (UPDATE su altre colonne).
    IF NEW.stato_doc_ddt_id IS NOT DISTINCT FROM OLD.stato_doc_ddt_id THEN
        RETURN NEW;
    END IF;

    SELECT
        max(CASE WHEN id = OLD.stato_doc_ddt_id THEN codice_interno END),
        max(CASE WHEN id = NEW.stato_doc_ddt_id THEN codice_interno END)
      INTO v_codice_da, v_codice_a
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
    IF v_codice_da = 'DRAFT' AND v_codice_a = 'EMESSO'
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
IS 'Trigger function: enforcement grafo transizioni stato DDT letto da config.transizioni_stati_ddt (E_STATO_DDT_TRANSIZIONE_NON_VALIDA). Regola 2: DRAFT->EMESSO richiede almeno una riga attiva (E_DDT_EMISSIONE_SENZA_RIGHE) — verdetto delegato a script.fn_check_ddt_emittibile (single source con fn_available_actions_ddt). Mirror di trgfn_ordini_guard_transizione. rev 2026-07-19 (brief-db-guard-righe-avanzamento-stato Rev 2). rev 2026-10-11 (20261011-83, brief-db-annullo-documento-con-legami D-4): la Regola 4 (annullo con legami) si ritira nel BB vendite.trgfn_doc_guard_annullo_con_legami. rev 2026-10-25 (20261025-14, brief-modello-documento-vendita §7): la Regola 3 (porta del registro, E_DDT_STATO_SOLO_DA_VERBO, GUC zeroerp.ddt_cambio_stato) si ritira: ogni cambio di stato della bolla passa dalla porta comune script.trgfn_doc_stato_solo_dal_verbo (trg_ddt_a05_stato_solo_dal_verbo_upd, E_DOC_STATO_SOLO_DAL_VERBO). rev 2026-10-25 (20261025-22): la frase del rifiuto di matrice riceve i due valori che ha (stato da, stato a); prima riceveva anche l''id del documento e a video usciva «da <id> a <stato da>».';
```

</div>

---
{% include-markdown "signature-core.md" %}
