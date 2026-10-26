{% include-markdown "it/dbzero/vendite/manual/trgfn_commesse_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_commesse_guard_transizione`

```sql
CREATE FUNCTION trgfn_commesse_guard_transizione()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_commesse_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: enforcement DB-first del grafo transizioni stato commessa.
--   La transizione (OLD.stato -> NEW.stato) e' ammessa solo se
--   presente e attiva in vendite.transizioni_stati_commessa.
--   In piu', le destinazioni che hanno una regola di dominio la
--   leggono dalla propria funzione pura:
--     -> PRONTA_FATTURAZIONE  fn_check_commessa_pronta_fatturazione
--     -> CHIUSA               fn_check_commessa_chiudibile
--     -> ANNULLATA            fn_check_commessa_annullabile
--   Le stesse che script.fn_available_actions_commessa usa per
--   accendere o spegnere i bottoni: sorgente UNICA, la UI non
--   puo' divergere dal guard.
--   rev 2026-08-04: la regola di ingresso, prima scritta a mano
--   qui dentro, e' passata alla funzione pura (brief §3.3).
DECLARE
    v_codice_da vendite.stati_commessa.codice_interno%TYPE;
    v_codice_a  vendite.stati_commessa.codice_interno%TYPE;
    v_ammessa   boolean := false;
    v_motivi    jsonb;
BEGIN
    -- No-op se lo stato non cambia davvero (UPDATE su altre colonne).
    IF NEW.stato_commessa_id IS NOT DISTINCT FROM OLD.stato_commessa_id THEN
        RETURN NEW;
    END IF;

    SELECT
        max(CASE WHEN id = OLD.stato_commessa_id THEN codice_interno END),
        max(CASE WHEN id = NEW.stato_commessa_id THEN codice_interno END)
      INTO v_codice_da, v_codice_a
      FROM vendite.stati_commessa
     WHERE id IN (OLD.stato_commessa_id, NEW.stato_commessa_id);

    -- Regola 1: la transizione deve esistere ed essere attiva in matrice.
    SELECT EXISTS (
        SELECT 1
          FROM vendite.transizioni_stati_commessa t
         WHERE t.stato_da_id = OLD.stato_commessa_id
           AND t.stato_a_id  = NEW.stato_commessa_id
           AND t.attivo IS TRUE
    ) INTO v_ammessa;

    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_COMMESSA_STATO_TRANSIZIONE_INVALIDA',
            jsonb_build_object(
                'commessa_id', NEW.id,
                'codice',      NEW.codice,
                'stato_da',    v_codice_da,
                'stato_a',     v_codice_a
            ),
            NEW.tx_id,
            NEW.id::text,
            coalesce(v_codice_da, 'NULL'),
            coalesce(v_codice_a,  'NULL')
        );
    END IF;

    -- Regola 2 (rev 2026-08-04): destinazioni con regola di
    -- dominio. Ingresso e uscite trattati allo stesso modo: la
    -- regola vera vive nelle fn_check_*, qui si solleva soltanto,
    -- col codice del PRIMO motivo. Arita' fissa dei valori
    -- (codice commessa, dettaglio): vale per tutta la famiglia.
    IF v_codice_a IN ('PRONTA_FATTURAZIONE', 'CHIUSA', 'ANNULLATA') THEN
        v_motivi := CASE v_codice_a
                      WHEN 'PRONTA_FATTURAZIONE' THEN script.fn_check_commessa_pronta_fatturazione(NEW.id)
                      WHEN 'CHIUSA'              THEN script.fn_check_commessa_chiudibile(NEW.id)
                      ELSE                            script.fn_check_commessa_annullabile(NEW.id)
                    END;

        -- ⭐ La coda del primo motivo sta in un posto solo: l'helper legge il
        --   codice da `v_motivi -> 0`, ne prende i `valori` per la frase, fonde il
        --   `dettaglio` nel contesto e ci mette sempre l'elenco COMPLETO dei motivi
        --   (il backend puo' mostrarli tutti anche se la frase ne nomina uno).
        -- ⚠️ L'IF e' sparito e NON e' fail-open: l'helper tace su un array vuoto,
        --   che e' esattamente la risposta «passa». Su un non-array resta rumoroso.
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'database', TG_NAME::text,
            v_motivi,
            NULL,
            NEW.tx_id,
            jsonb_build_object(
                'commessa_id', NEW.id,
                'codice',      NEW.codice,
                'stato_da',    v_codice_da,
                'stato_a',     v_codice_a));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_commesse_guard_transizione()
IS 'Trigger function: enforcement del grafo transizioni stato commessa (matrice vendite.transizioni_stati_commessa) + regole di dominio delegate alle fn_check_* pure, condivise con script.fn_available_actions_commessa. rev 2026-08-04: anche l''ingresso in PRONTA_FATTURAZIONE passa dalla funzione pura (prima era scritto a mano nel trigger), perche'' la transizione diventa manuale e bottone e guard devono leggere lo stesso verdetto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
