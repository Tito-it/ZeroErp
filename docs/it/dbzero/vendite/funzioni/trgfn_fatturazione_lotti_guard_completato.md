# ⚙️ Funzione `trgfn_fatturazione_lotti_guard_completato`

```sql
CREATE FUNCTION trgfn_fatturazione_lotti_guard_completato()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatturazione_lotti_guard_completato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: COMPLETATO («la corsa e' finita bene») si scrive solo su
--        un lotto che se l'e' guadagnato: non fermo, non abortito.
-- Uso:   BEFORE UPDATE OF stato_lotto FOR EACH ROW.
DECLARE
    v_fermo        vendite.vw_lotti_segnalazioni_summary.fermo%TYPE;
    v_fermo_motivo vendite.vw_lotti_segnalazioni_summary.fermo_motivo%TYPE;
    v_is_abortito  config.stati_doc_fiscale.is_abortito%TYPE;
BEGIN
    -- Solo l'ARRIVO su COMPLETATO: restarci, o andare altrove, non
    -- e' affare di questo guard.
    IF NEW.stato_lotto IS DISTINCT FROM 'COMPLETATO'
       OR OLD.stato_lotto IS NOT DISTINCT FROM NEW.stato_lotto THEN
        RETURN NEW;
    END IF;

    -- ── 1) ABORTITO ─────────────────────────────────────
    -- Il flag, non un elenco di stati. NEW e non OLD: e' lo stato
    -- con cui la riga uscira' da questo UPDATE.
    -- ⚠️ Stato nullo o non risolvibile -> non abortito: il ramo
    --    tace, e decide il ramo 2.
    SELECT s.is_abortito
      INTO v_is_abortito
      FROM config.stati_doc_fiscale s
     WHERE s.id = NEW.stato_doc_fiscale_id;

    IF v_is_abortito IS TRUE THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'trgfn_fatturazione_lotti_guard_completato',
            'E_LOTTO_COMPLETATO_NON_GUADAGNATO',
            jsonb_build_object('lotto_id', NEW.id,
                               'da', OLD.stato_lotto,
                               'motivo', 'ABORTITO'),
            NULL::uuid,
            NEW.codice,
            'e'' annullato');
    END IF;

    -- ── 2) FERMO ────────────────────────────────────────
    -- ⭐ Si LEGGE la sede unica: nessun addendo ricalcolato qui. Un
    --   addendo nuovo del verdetto vale da solo anche per questo guard.
    -- ⚠️ La sede legge le righe FIGLIE (esiti, segnalazioni, ponte),
    --   non la colonna che questo UPDATE sta cambiando: in BEFORE ROW
    --   la tabella ha ancora OLD, e qui non importa.
    SELECT s.fermo, s.fermo_motivo
      INTO v_fermo, v_fermo_motivo
      FROM vendite.vw_lotti_segnalazioni_summary s
     WHERE s.lotto_id = NEW.id;

    IF v_fermo IS TRUE THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'trgfn_fatturazione_lotti_guard_completato',
            'E_LOTTO_COMPLETATO_NON_GUADAGNATO',
            jsonb_build_object('lotto_id', NEW.id,
                               'da', OLD.stato_lotto,
                               'motivo', 'FERMO',
                               'fermo_motivo', v_fermo_motivo),
            NULL::uuid,
            NEW.codice,
            CASE v_fermo_motivo
                WHEN 'CRITICHE'          THEN 'ha segnalazioni critiche aperte'
                WHEN 'FATTURE_IN_ERRORE' THEN 'ha fatture in errore'
                WHEN 'ESITI_IN_ERRORE'   THEN 'ha documenti in errore'
                ELSE 'risulta fermo'
            END);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fatturazione_lotti_guard_completato()
IS 'Guard BEFORE UPDATE OF stato_lotto su vendite.fatturazione_lotti: COMPLETATO si rifiuta (E_LOTTO_COMPLETATO_NON_GUADAGNATO, TECNICO) se lo stato fiscale del lotto e'' abortito (config.stati_doc_fiscale.is_abortito, letto da NEW) o se la sede unica vendite.vw_lotti_segnalazioni_summary lo dice fermo — letto, non ricalcolato. ⭐ Sulla COLONNA e non in una funzione: il runner scrive stato_lotto con un UPDATE diretto. (rev 2026-10-27, 20261027-28: la funzione di allora, fn_set_fatturazione_lotto_stato, e'' ritirata da 20261027-07; i passaggi ammessi del job stanno nella matrice config.transizioni_stati_lotto_job, e li giudica trgfn_fatturazione_lotti_guard_stato_job. Questo guard resta la sola regola del fermo: COMPLETATO solo se guadagnato.) Nasce da LTF-0010972 (2026-09-12): un rilancio ha scritto COMPLETATO con due documenti ancora in ERRORE. ⚠️ Non chiude la porta dell''esito (ERRORE scritto su un lotto gia'' COMPLETATO): quella la sorveglia vw_lotti_chiusi_con_gruppi_in_errore. Solo UPDATE: un lotto che nasce COMPLETATO non ha righe figlie. Brief: brief-db-annullamento-chiude-la-vita §9.3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
