{% include-markdown "it/dbzero/vendite/manual/trgfn_listini_versioni_guard_transizione_stato.md" %}
# ⚙️ Funzione `trgfn_listini_versioni_guard_transizione_stato`

```sql
CREATE FUNCTION trgfn_listini_versioni_guard_transizione_stato()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_listini_versioni_guard_transizione_stato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: i passaggi di stato di una versione di listino, dalla
--   matrice config.transizioni_stati_listino_versioni (nessun grafo
--   scritto qui: rev 2026-10-28, 20261028-08). Poi le condizioni:
--   -> CHIUSA: valido_al valorizzata e passata (< data operativa);
--   -> ATTIVA: il primo motivo di
--      script.fn_check_versione_listino_attivabile (spenta, senza
--      prezzi), lo stesso che spegne «Attiva» nella lista.
-- Lo scrivono solo i verbi (porta): vendite.fn_attiva_versione_listino
--   e vendite.fn_chiudi_versioni_listino_scadute.
DECLARE
    v_codice_da config.stati_doc_listino_versioni.codice_interno%TYPE;
    v_codice_a  config.stati_doc_listino_versioni.codice_interno%TYPE;
    v_ammessa   boolean := false;
BEGIN
    SELECT
        max(CASE WHEN s.id = OLD.stato_doc_listino_versione_id THEN s.codice_interno END),
        max(CASE WHEN s.id = NEW.stato_doc_listino_versione_id THEN s.codice_interno END)
      INTO v_codice_da, v_codice_a
      FROM config.stati_doc_listino_versioni s
     WHERE s.id IN (OLD.stato_doc_listino_versione_id, NEW.stato_doc_listino_versione_id);

    -- Regola 1: il passaggio esiste ed e' attivo in matrice.
    SELECT EXISTS (
        SELECT 1
          FROM config.transizioni_stati_listino_versioni t
         WHERE t.stato_da_id = OLD.stato_doc_listino_versione_id
           AND t.stato_a_id  = NEW.stato_doc_listino_versione_id
           AND t.attivo IS TRUE
    ) INTO v_ammessa;

    -- La chiusura: la data di fine c'e' ed e' passata. Prima e' una
    -- chiusura programmata (solo la data): lo stato lo scrive il
    -- job, quando la finestra scade.
    IF v_ammessa AND v_codice_a = 'CHIUSA' THEN
        v_ammessa := NEW.valido_al IS NOT NULL
                     AND NEW.valido_al < (SELECT script.fn_data_operativa());
    END IF;

    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME::text, 'E_VERSIONE_STATO_TRANSIZIONE_INVALIDA',
            jsonb_build_object(
                'versione_id', NEW.id,
                'listino_id',  NEW.listino_id,
                'stato_da',    v_codice_da,
                'stato_a',     v_codice_a,
                'valido_al',   NEW.valido_al),
            NEW.tx_id,
            NEW.id::text,
            COALESCE(v_codice_da, 'NULL'),
            COALESCE(v_codice_a,  'NULL'),
            COALESCE(NEW.valido_al::text, 'NULL'));
    END IF;

    -- L'attivazione: cio' che la vieta oltre la matrice (spenta,
    -- senza prezzi). ⭐ Il predicato e'
    -- script.fn_check_versione_listino_attivabile, lo stesso della
    -- superficie della lista e del verbo: qui si solleva soltanto.
    IF v_codice_a = 'ATTIVA' THEN
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'database', TG_NAME::text,
            script.fn_check_versione_listino_attivabile(NEW.id),
            NULL,
            NEW.tx_id,
            jsonb_build_object(
                'versione_id', NEW.id,
                'listino_id',  NEW.listino_id,
                'stato_da',    v_codice_da,
                'stato_a',     v_codice_a));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_listini_versioni_guard_transizione_stato()
IS 'Guard dei passaggi di stato di una versione di listino (BEFORE UPDATE OF stato_doc_listino_versione_id, quando lo stato cambia): il passaggio dev''essere attivo in config.transizioni_stati_listino_versioni (E_VERSIONE_STATO_TRANSIZIONE_INVALIDA); -> CHIUSA vuole valido_al passata; -> ATTIVA solleva il primo motivo di script.fn_check_versione_listino_attivabile (spenta, senza prezzi). Lo stato lo scrivono solo i verbi, dietro la porta: vendite.fn_attiva_versione_listino e vendite.fn_chiudi_versioni_listino_scadute. Rev 2026-10-28 (20261028-08): i passaggi dalla matrice, non piu'' dagli IF; la regola dell''attivazione dal backend. Brief: brief-modello-documento-vendita §16 (L-1, L-4).';
```

</div>

---
{% include-markdown "signature-core.md" %}
