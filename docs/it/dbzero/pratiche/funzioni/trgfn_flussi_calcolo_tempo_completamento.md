{% include-markdown "it/dbzero/pratiche/manual/trgfn_flussi_calcolo_tempo_completamento.md" %}
# ⚙️ Funzione `trgfn_flussi_calcolo_tempo_completamento`

```sql
CREATE FUNCTION trgfn_flussi_calcolo_tempo_completamento()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_flussi_calcolo_tempo_completamento()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: quando un flusso va COMPLETATO, gestisce il ciclo calcoli_tempo da/a.
-- Il flusso completato puo' essere flusso_da (avvio conteggio) e/o
-- flusso_a (chiusura conteggio) in formule diverse.
--
-- Caso ordine invertito: se flusso_da completa dopo flusso_a,
-- crea la riga e la chiude immediatamente.
DECLARE
    v_pratica_id     pratiche.flussi.pratica_id%TYPE;
    v_tipo_prest_id  pratiche.pratiche.tipo_prestazione_id%TYPE;
    v_template_id    pratiche.flussi.template_flusso_id%TYPE;
    v_stato_completato_id config.stati_flussi_pratiche.id%TYPE;
    v_formula        RECORD;
    v_flusso_partner RECORD;
    v_calcolo_id     pratiche.calcoli_tempo.id%TYPE;
    v_giorni_lordi   INTEGER;
    v_giorni_sosp    INTEGER;
    v_giorni_netti   INTEGER;
BEGIN
    -- Recupera contesto
    v_pratica_id   := NEW.pratica_id;
    v_template_id  := NEW.template_flusso_id;

    -- Se il flusso non ha template, nessun calcolo
    IF v_template_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT id INTO v_stato_completato_id
    FROM config.stati_flussi_pratiche WHERE codice_interno = 'COMPLETATO';

    -- Solo quando il flusso va in COMPLETATO
    IF NEW.stato_id <> v_stato_completato_id THEN
        RETURN NEW;
    END IF;

    SELECT tipo_prestazione_id INTO v_tipo_prest_id
    FROM pratiche.pratiche WHERE id = v_pratica_id;

    -- =========================================================
    -- FASE 1: il flusso completato e' un flusso_da (avvio conteggio)
    -- =========================================================
    FOR v_formula IN
        SELECT ft.id AS formula_id,
               ft.template_flusso_a_id,
               ft.giorni_esecuzione
        FROM pratiche.formule_tempo ft
        WHERE ft.tipo_prestazione_id = v_tipo_prest_id
          AND ft.template_flusso_da_id = v_template_id
          AND ft.attivo = true
    LOOP
        -- Cerca il flusso partner (flusso_a) nella stessa pratica
        SELECT f.id, f.stato_id, f.data_fine
        INTO v_flusso_partner
        FROM pratiche.flussi f
        WHERE f.pratica_id = v_pratica_id
          AND f.template_flusso_id = v_formula.template_flusso_a_id
        LIMIT 1;

        -- Se il flusso_a non esiste nella pratica, niente da fare
        IF v_flusso_partner.id IS NULL THEN
            CONTINUE;
        END IF;

        -- Verifica che non esista gia' un calcolo per questa combinazione
        IF EXISTS (
            SELECT 1 FROM pratiche.calcoli_tempo
            WHERE pratica_id = v_pratica_id
              AND flusso_da_id = NEW.id
              AND flusso_a_id = v_flusso_partner.id
              AND formula_tempo_id = v_formula.formula_id
        ) THEN
            CONTINUE;
        END IF;

        -- INSERT calcolo tempo (avvio)
        INSERT INTO pratiche.calcoli_tempo (
            pratica_id, flusso_da_id, flusso_a_id,
            formula_tempo_id, data_inizio_calcolo, giorni_formula
        )
        VALUES (
            v_pratica_id, NEW.id, v_flusso_partner.id,
            v_formula.formula_id, NEW.data_fine, v_formula.giorni_esecuzione
        )
        RETURNING id INTO v_calcolo_id;

        -- Caso ordine invertito: se flusso_a e' gia' COMPLETATO, chiudi subito
        IF v_flusso_partner.stato_id = v_stato_completato_id
           AND v_flusso_partner.data_fine IS NOT NULL THEN
            v_giorni_netti := pratiche.fn_calcola_tempo_netto_da_a(
                v_pratica_id, NEW.id, v_flusso_partner.id);

            v_giorni_lordi := GREATEST(0,
                EXTRACT(DAY FROM v_flusso_partner.data_fine - NEW.data_fine)::INTEGER);

            v_giorni_sosp := v_giorni_lordi - COALESCE(v_giorni_netti, v_giorni_lordi);

            UPDATE pratiche.calcoli_tempo
            SET data_fine_calcolo = v_flusso_partner.data_fine,
                giorni_lordi = v_giorni_lordi,
                giorni_sospensione = v_giorni_sosp,
                giorni_netti = v_giorni_netti,
                sforato = (v_giorni_netti > v_formula.giorni_esecuzione)
            WHERE id = v_calcolo_id;
        END IF;
    END LOOP;

    -- =========================================================
    -- FASE 2: il flusso completato e' un flusso_a (chiusura conteggio)
    -- =========================================================
    FOR v_formula IN
        SELECT ct.id AS calcolo_id,
               ct.flusso_da_id,
               ct.data_inizio_calcolo,
               ct.giorni_formula
        FROM pratiche.calcoli_tempo ct
        WHERE ct.pratica_id = v_pratica_id
          AND ct.flusso_a_id = NEW.id
          AND ct.data_fine_calcolo IS NULL
    LOOP
        v_giorni_netti := pratiche.fn_calcola_tempo_netto_da_a(
            v_pratica_id, v_formula.flusso_da_id, NEW.id);

        v_giorni_lordi := GREATEST(0,
            EXTRACT(DAY FROM NEW.data_fine - v_formula.data_inizio_calcolo)::INTEGER);

        v_giorni_sosp := v_giorni_lordi - COALESCE(v_giorni_netti, v_giorni_lordi);

        UPDATE pratiche.calcoli_tempo
        SET data_fine_calcolo = NEW.data_fine,
            giorni_lordi = v_giorni_lordi,
            giorni_sospensione = v_giorni_sosp,
            giorni_netti = v_giorni_netti,
            sforato = (v_giorni_netti > v_formula.giorni_formula)
        WHERE id = v_formula.calcolo_id;
    END LOOP;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_flussi_calcolo_tempo_completamento()
IS 'AFTER UPDATE stato_id -> COMPLETATO: crea e/o chiude calcoli_tempo modello da/a.';
```

</div>

---
{% include-markdown "signature-core.md" %}
