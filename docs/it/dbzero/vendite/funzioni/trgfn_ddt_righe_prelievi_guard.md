# ⚙️ Funzione `trgfn_ddt_righe_prelievi_guard`

```sql
CREATE FUNCTION trgfn_ddt_righe_prelievi_guard()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_righe_prelievi_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: i prelievi si scrivono solo con la bolla in bozza (salvo
--   l'ubicazione di arrivo fino al CONSEGNATO) e rispettano la regola
--   del kit (D-L3-f). Vedi l'intestazione del changeSet.
DECLARE
    v_riga_id       vendite.ddt_righe.id%TYPE;
    v_ddt_id        vendite.ddt_righe.ddt_id%TYPE;
    v_riga_nr       vendite.ddt_righe.riga_nr%TYPE;
    v_riga_gestita  catalogo.articoli.gestito_a_magazzino%TYPE;
    v_comp_riga_id  vendite.ddt_righe_componenti.riga_ddt_id%TYPE;
    v_comp_gestito  catalogo.articoli.gestito_a_magazzino%TYPE;
    v_stato         text;     -- dal lettore DEFINER, che torna text
    v_etichetta     text;
    v_solo_arrivo   boolean := false;
    v_regola        text;
BEGIN
    v_riga_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.ddt_riga_id ELSE NEW.ddt_riga_id END;

    -- La riga, sotto RLS. Assente = cascata dalla riga o dalla testata
    -- (la regola di stato l'hanno gia' applicata loro), oppure fuori
    -- perimetro, che il WITH CHECK della policy rifiuta comunque.
    SELECT dr.ddt_id, dr.riga_nr, a.gestito_a_magazzino
      INTO v_ddt_id, v_riga_nr, v_riga_gestita
      FROM vendite.ddt_righe dr
      JOIN catalogo.articoli a ON a.id = dr.articolo_id
     WHERE dr.id = v_riga_id;
    IF NOT FOUND THEN
        RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
    END IF;

    -- 1. Lo stato della bolla, dal lettore DEFINER dei documenti.
    SELECT t.stato, t.etichetta INTO v_stato, v_etichetta
      FROM script.fn_get_stato_testata_documento('DDT', v_ddt_id) t;

    IF v_stato IS NOT NULL AND v_stato <> 'DRAFT' THEN
        -- L'unica eccezione: l'ubicazione di arrivo, sola, fra l'emissione
        -- e la consegna (D-L3-c).
        IF TG_OP = 'UPDATE' AND v_stato IN ('EMESSO', 'SPEDITO') THEN
            v_solo_arrivo :=
                    NEW.ubicazione_arrivo_id IS DISTINCT FROM OLD.ubicazione_arrivo_id
                AND NEW.ddt_riga_id             = OLD.ddt_riga_id
                AND NEW.ddt_riga_componente_id IS NOT DISTINCT FROM OLD.ddt_riga_componente_id
                AND NEW.qta                     = OLD.qta
                AND NEW.lotto_id               IS NOT DISTINCT FROM OLD.lotto_id
                AND NEW.asset_id               IS NOT DISTINCT FROM OLD.asset_id
                AND NEW.ubicazione_id          IS NOT DISTINCT FROM OLD.ubicazione_id;
        END IF;
        IF NOT v_solo_arrivo THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'vendite.trgfn_ddt_righe_prelievi_guard',
                'E_RIGA_DOC_NON_BOZZA',
                jsonb_build_object('table', 'vendite.ddt_righe_prelievi',
                                   'documento', 'DDT', 'testata_id', v_ddt_id,
                                   'riga_id', v_riga_id, 'stato', v_stato),
                NULL::uuid,
                COALESCE(v_etichetta, v_ddt_id::text),
                v_stato,
                CASE TG_OP WHEN 'INSERT' THEN 'aggiungere'
                           WHEN 'UPDATE' THEN 'modificare'
                           ELSE 'togliere' END);
        END IF;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;

    -- 2. La coerenza con la regola del kit (D-L3-f).
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
IS 'Guard BEFORE INSERT OR UPDATE OR DELETE su vendite.ddt_righe_prelievi. (1) Solo in bozza: fuori da DRAFT E_RIGA_DOC_NON_BOZZA (stesso codice e stessa frase delle righe, stato dal lettore DEFINER script.fn_get_stato_testata_documento), salvo un UPDATE della sola ubicazione_arrivo_id con la bolla EMESSO o SPEDITO (D-L3-c: l''arrivo si compila fino al CONSEGNATO). (2) Coerenza con la regola del kit (D-L3-f), E_DDT_PRELIEVO_INCOERENTE: senza componente l''articolo della riga e'' gestito; con componente, il componente e'' della riga ed e'' gestito, e la riga no; un prelievo non cambia riga ne'' componente. Lotto, seriale e ubicazione li giudica la check dell''emissione (script.fn_check_riga_magazzino). Brief: brief-db-magazzino-lotto-3-scarico-da-ddt.';
```

---
{% include-markdown "signature-core.md" %}
