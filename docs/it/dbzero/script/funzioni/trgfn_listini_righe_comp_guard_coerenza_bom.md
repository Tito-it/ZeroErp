{% include-markdown "it/dbzero/script/manual/trgfn_listini_righe_comp_guard_coerenza_bom.md" %}
# ⚙️ Funzione `trgfn_listini_righe_comp_guard_coerenza_bom`

```sql
CREATE FUNCTION trgfn_listini_righe_comp_guard_coerenza_bom()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.trgfn_listini_righe_comp_guard_coerenza_bom()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: BEFORE INS/UPD su listini_righe_componenti — 7 guard coerenza BoM.
--   Verifica che la riga listino componente sia allineata con
--   catalogo.articoli_componenti e vendite.listini_versioni.
DECLARE
    v_ac_prodotto_id  catalogo.articoli_componenti.prodotto_id%TYPE;
    v_ac_componente_id catalogo.articoli_componenti.componente_id%TYPE;
    v_ac_attivo       catalogo.articoli_componenti.attivo%TYPE;
    v_ac_validita     catalogo.articoli_componenti.validita%TYPE;
    v_padre_is_comp   catalogo.articoli.is_composito%TYPE;
    v_padre_iva_id    catalogo.articoli.iva_id%TYPE;
    v_figlio_iva_id   catalogo.articoli.iva_id%TYPE;
    v_lv_validita     vendite.listini_versioni.validita%TYPE;
BEGIN
    -- Lettura BoM in unica query
    SELECT ac.prodotto_id, ac.componente_id, ac.attivo, ac.validita,
           a_padre.is_composito, a_padre.iva_id,
           a_figlio.iva_id
      INTO v_ac_prodotto_id, v_ac_componente_id, v_ac_attivo, v_ac_validita,
           v_padre_is_comp, v_padre_iva_id,
           v_figlio_iva_id
      FROM catalogo.articoli_componenti ac
      JOIN catalogo.articoli a_padre ON a_padre.id = ac.prodotto_id
      JOIN catalogo.articoli a_figlio ON a_figlio.id = ac.componente_id
     WHERE ac.id = NEW.articolo_componente_id;

    -- Guard 1: articolo_componente_id deve esistere e essere attivo
    IF NOT FOUND OR NOT COALESCE(v_ac_attivo, TRUE) THEN
        PERFORM script.fn_log_and_raise_error(
            'script', TG_NAME, 'E_LISTINO_COMPONENTE_COERENZA_BOM',
            jsonb_build_object(
                'causa', 'articolo_componente_id non trovato o non attivo',
                'articolo_componente_id', NEW.articolo_componente_id
            ),
            NULL::uuid,
            format('articolo_componente_id=%s non trovato o non attivo',
                   NEW.articolo_componente_id)
        );
    END IF;

    -- Guard 2: articolo_padre_id deve coincidere con ac.prodotto_id
    IF NEW.articolo_padre_id IS DISTINCT FROM v_ac_prodotto_id THEN
        PERFORM script.fn_log_and_raise_error(
            'script', TG_NAME, 'E_LISTINO_COMPONENTE_COERENZA_BOM',
            jsonb_build_object(
                'causa', 'articolo_padre_id non coincide con BoM.prodotto_id',
                'articolo_padre_id_ricevuto', NEW.articolo_padre_id,
                'prodotto_id_atteso',          v_ac_prodotto_id
            ),
            NULL::uuid,
            format('articolo_padre_id=%s atteso=%s',
                   NEW.articolo_padre_id, v_ac_prodotto_id)
        );
    END IF;

    -- Guard 3: articolo_figlio_id deve coincidere con ac.componente_id
    IF NEW.articolo_figlio_id IS DISTINCT FROM v_ac_componente_id THEN
        PERFORM script.fn_log_and_raise_error(
            'script', TG_NAME, 'E_LISTINO_COMPONENTE_COERENZA_BOM',
            jsonb_build_object(
                'causa', 'articolo_figlio_id non coincide con BoM.componente_id',
                'articolo_figlio_id_ricevuto', NEW.articolo_figlio_id,
                'componente_id_atteso',         v_ac_componente_id
            ),
            NULL::uuid,
            format('articolo_figlio_id=%s atteso=%s',
                   NEW.articolo_figlio_id, v_ac_componente_id)
        );
    END IF;

    -- Guard 4: padre deve essere composito
    IF NOT COALESCE(v_padre_is_comp, FALSE) THEN
        PERFORM script.fn_log_and_raise_error(
            'script', TG_NAME, 'E_LISTINO_COMPONENTE_COERENZA_BOM',
            jsonb_build_object(
                'causa', 'articolo padre non e'' composito',
                'articolo_padre_id', NEW.articolo_padre_id
            ),
            NULL::uuid,
            format('articolo_padre_id=%s non e'' composito',
                   NEW.articolo_padre_id)
        );
    END IF;

    -- Guard 5: IVA figlio = IVA padre
    IF v_padre_iva_id IS DISTINCT FROM v_figlio_iva_id THEN
        PERFORM script.fn_log_and_raise_error(
            'script', TG_NAME, 'E_LISTINO_COMPONENTE_COERENZA_BOM',
            jsonb_build_object(
                'causa', 'IVA padre != IVA figlio',
                'iva_padre', v_padre_iva_id,
                'iva_figlio', v_figlio_iva_id
            ),
            NULL::uuid,
            format('IVA padre=%s != figlio=%s',
                   v_padre_iva_id, v_figlio_iva_id)
        );
    END IF;

    -- Guard 6: validita riga listino comp ⊆ validita BoM
    -- (v_ac_validita e' NOT NULL per constraint, ma check difensivo coerente con guard 7)
    IF v_ac_validita IS NULL OR NOT (v_ac_validita @> NEW.validita) THEN
        PERFORM script.fn_log_and_raise_error(
            'script', TG_NAME, 'E_LISTINO_COMPONENTE_COERENZA_BOM',
            jsonb_build_object(
                'causa', 'validita riga listino comp non contenuta in validita BoM',
                'validita_listino_comp', NEW.validita::text,
                'validita_bom',          v_ac_validita::text
            ),
            NULL::uuid,
            format('validita=%s non contenuta in BoM=%s',
                   NEW.validita, v_ac_validita)
        );
    END IF;

    -- Guard 7: validita riga listino comp ⊆ validita versione listino
    SELECT lv.validita INTO v_lv_validita
      FROM vendite.listini_versioni lv
     WHERE lv.id = NEW.listino_versione_id;

    IF v_lv_validita IS NULL OR NOT (v_lv_validita @> NEW.validita) THEN
        PERFORM script.fn_log_and_raise_error(
            'script', TG_NAME, 'E_LISTINO_COMPONENTE_COERENZA_BOM',
            jsonb_build_object(
                'causa', 'validita riga listino comp non contenuta in validita versione listino',
                'validita_listino_comp', NEW.validita::text,
                'validita_versione',     v_lv_validita::text
            ),
            NULL::uuid,
            format('validita=%s non contenuta in versione=%s',
                   NEW.validita, v_lv_validita)
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_listini_righe_comp_guard_coerenza_bom()
IS 'Trigger BEFORE INS/UPD su listini_righe_componenti: 7 guard coerenza BoM. (1) ac esiste+attivo, (2) padre_id coerente, (3) figlio_id coerente, (4) padre composito, (5) IVA padre=figlio, (6) validita ⊆ BoM, (7) validita ⊆ versione listino. Raise E_LISTINO_COMPONENTE_COERENZA_BOM (447). rev 2026-05-13.';
```

---
{% include-markdown "signature-core.md" %}
