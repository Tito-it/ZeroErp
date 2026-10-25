{% include-markdown "it/dbzero/vendite/manual/trgfn_resi_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_resi_guard_transizione`

```sql
CREATE FUNCTION trgfn_resi_guard_transizione()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_resi_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: enforcement DB-first del grafo transizioni stato reso.
--   La transizione (OLD.stato -> NEW.stato) e' ammessa solo se
--   presente e attiva in config.transizioni_stati_reso (no grafo
--   hardcodato). Mirror di trgfn_ddt_guard_transizione.
--   rev 2026-10-25 (20261025-22: i segnaposto della frase; 20261025-15, brief-modello-documento-vendita §7):
--   la Regola 2 (porta del registro) si ritira; ogni cambio di stato
--   del reso passa dalla porta comune
--   script.trgfn_doc_stato_solo_dal_verbo (trg_resi_a05_stato_solo_dal_verbo_upd).
DECLARE
    v_codice_da config.stati_doc_reso.codice_interno%TYPE;
    v_codice_a  config.stati_doc_reso.codice_interno%TYPE;
    v_ammessa   boolean := false;
BEGIN
    -- No-op se lo stato non cambia davvero (UPDATE su altre colonne).
    IF NEW.stato_doc_reso_id IS NOT DISTINCT FROM OLD.stato_doc_reso_id THEN
        RETURN NEW;
    END IF;

    SELECT
        max(CASE WHEN id = OLD.stato_doc_reso_id THEN codice_interno END),
        max(CASE WHEN id = NEW.stato_doc_reso_id THEN codice_interno END)
      INTO v_codice_da, v_codice_a
      FROM config.stati_doc_reso
     WHERE id IN (OLD.stato_doc_reso_id, NEW.stato_doc_reso_id);

    -- La transizione deve esistere ed essere attiva in matrice.
    SELECT EXISTS (
        SELECT 1
          FROM config.transizioni_stati_reso t
         WHERE t.stato_da_id = OLD.stato_doc_reso_id
           AND t.stato_a_id  = NEW.stato_doc_reso_id
           AND t.attivo IS TRUE
    ) INTO v_ammessa;

    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_STATO_RESO_TRANSIZIONE_NON_VALIDA',
            jsonb_build_object(
                'reso_id',  NEW.id,
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

    -- Regola 2 — RITIRATA (rev 2026-10-25, 20261025-15). La porta del
    --   registro (solo conferma e annullo del confermato dei resi che
    --   fanno rientrare merce) e' contenuta nella porta comune
    --   script.trgfn_doc_stato_solo_dal_verbo, che chiude ogni cambio di
    --   stato del reso ai suoi verbi (E_DOC_STATO_SOLO_DAL_VERBO).

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_resi_guard_transizione()
IS 'Trigger function: enforcement grafo transizioni stato reso letto da config.transizioni_stati_reso (E_STATO_RESO_TRANSIZIONE_NON_VALIDA). Mirror di trgfn_ddt_guard_transizione. rev 2026-07-13. rev 2026-10-25 (20261025-15, brief-modello-documento-vendita §7): la Regola 2 (porta del registro, E_RESO_STATO_SOLO_DA_VERBO, GUC zeroerp.reso_cambio_stato) si ritira: ogni cambio di stato del reso passa dalla porta comune script.trgfn_doc_stato_solo_dal_verbo (trg_resi_a05_stato_solo_dal_verbo_upd, E_DOC_STATO_SOLO_DAL_VERBO). rev 2026-10-25 (20261025-22): la frase del rifiuto di matrice riceve i due valori che ha (stato da, stato a); prima riceveva anche l''id del documento e a video usciva «da <id> a <stato da>».';
```

</div>

---
{% include-markdown "signature-core.md" %}
