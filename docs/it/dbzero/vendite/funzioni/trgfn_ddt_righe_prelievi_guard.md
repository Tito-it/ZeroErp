# ⚙️ Funzione `trgfn_ddt_righe_prelievi_guard`

```sql
CREATE FUNCTION trgfn_ddt_righe_prelievi_guard()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_righe_prelievi_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: i prelievi rispettano la regola del kit (D-L3-f). Vedi
--   l'intestazione del changeSet.
-- ⭐ rev 2026-10-08: la regola «solo con la bolla in bozza, salvo
--   l'ubicazione di arrivo in EMESSO/SPEDITO» non sta piu' qui. La dice
--   il building block vendite.trgfn_doc_righe_lock_fuori_bozza, montato
--   in fascia _a05_ con un nome minore di questo
--   (trg_ddt_righe_prelievi_a05_doc_bozza_ins_upd_dlt < ..._a05_guard_...):
--   parla prima, come parlava il ramo che c'era qui.
DECLARE
    v_ddt_id        vendite.ddt_righe.ddt_id%TYPE;
    v_riga_nr       vendite.ddt_righe.riga_nr%TYPE;
    v_riga_gestita  catalogo.articoli.gestito_a_magazzino%TYPE;
    v_comp_riga_id  vendite.ddt_righe_componenti.riga_ddt_id%TYPE;
    v_comp_gestito  catalogo.articoli.gestito_a_magazzino%TYPE;
    v_regola        text;
BEGIN
    -- Sul DELETE la regola del kit non ha niente da dire.
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;

    -- La riga, sotto RLS. Assente = cascata dalla riga o dalla testata,
    -- oppure fuori perimetro, che il WITH CHECK della policy rifiuta
    -- comunque.
    SELECT dr.ddt_id, dr.riga_nr, a.gestito_a_magazzino
      INTO v_ddt_id, v_riga_nr, v_riga_gestita
      FROM vendite.ddt_righe dr
      JOIN catalogo.articoli a ON a.id = dr.articolo_id
     WHERE dr.id = NEW.ddt_riga_id;
    IF NOT FOUND THEN
        RETURN NEW;
    END IF;

    -- La coerenza con la regola del kit (D-L3-f).
    IF TG_OP = 'UPDATE'
       AND (NEW.ddt_riga_id <> OLD.ddt_riga_id
            OR NEW.ddt_riga_componente_id IS DISTINCT FROM OLD.ddt_riga_componente_id) THEN
        v_regola := 'un prelievo non cambia riga ne'' componente: toglierlo e scriverne un altro';
    ELSIF NEW.ddt_riga_componente_id IS NULL THEN
        IF NOT v_riga_gestita THEN
            v_regola := 'l''articolo della riga non e'' gestito a magazzino, quindi non si preleva';
        END IF;
    ELSE
        SELECT drc.riga_ddt_id, c.gestito_a_magazzino
          INTO v_comp_riga_id, v_comp_gestito
          FROM vendite.ddt_righe_componenti drc
          JOIN catalogo.articoli c ON c.id = drc.componente_id
         WHERE drc.id = NEW.ddt_riga_componente_id;
        IF v_comp_riga_id IS DISTINCT FROM NEW.ddt_riga_id THEN
            v_regola := 'il componente indicato non appartiene a questa riga';
        ELSIF v_riga_gestita THEN
            v_regola := 'l''articolo della riga e'' gestito a magazzino: si preleva la riga, non i suoi componenti';
        ELSIF NOT v_comp_gestito THEN
            v_regola := 'il componente non e'' gestito a magazzino, quindi non si preleva';
        END IF;
    END IF;

    IF v_regola IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.trgfn_ddt_righe_prelievi_guard',
            'E_DDT_PRELIEVO_INCOERENTE',
            jsonb_build_object('ddt_id', v_ddt_id, 'riga_id', NEW.ddt_riga_id,
                               'componente_id', NEW.ddt_riga_componente_id),
            NEW.tx_id,
            v_riga_nr::text, v_regola);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_righe_prelievi_guard()
IS 'Guard BEFORE INSERT OR UPDATE OR DELETE su vendite.ddt_righe_prelievi: coerenza con la regola del kit (D-L3-f), E_DDT_PRELIEVO_INCOERENTE: senza componente l''articolo della riga e'' gestito; con componente, il componente e'' della riga ed e'' gestito, e la riga no; un prelievo non cambia riga ne'' componente. Lotto, seriale e ubicazione li giudica la check dell''emissione (script.fn_check_riga_magazzino). Brief: brief-db-magazzino-lotto-3-scarico-da-ddt. rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui §1, regola del 2): la regola «solo con la bolla in bozza, salvo un UPDATE della sola ubicazione_arrivo_id con la bolla EMESSO o SPEDITO» (D-L3-c) non e'' piu'' scritta qui: la dice il building block vendite.trgfn_doc_righe_lock_fuori_bozza, montato a livello RIGA con le colonne ammesse (trg_ddt_righe_prelievi_a05_doc_bozza_ins_upd_dlt, 20261008-93), che parla prima di questo guard. Sul DELETE questa funzione non ha piu'' niente da dire.';
```

</div>

---
{% include-markdown "signature-core.md" %}
