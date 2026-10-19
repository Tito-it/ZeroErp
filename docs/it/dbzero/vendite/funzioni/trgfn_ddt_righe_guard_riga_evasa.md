# ⚙️ Funzione `trgfn_ddt_righe_guard_riga_evasa`

```sql
CREATE FUNCTION trgfn_ddt_righe_guard_riga_evasa()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_righe_guard_riga_evasa()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$

-- =========================================================
-- Scopo: su una riga di DDT EVASA (vendite.fn_ddt_riga_evasa)
--   articolo, UoM, fattore e quantita' non cambiano (D-1 di
--   brief-db-ddt-righe-evase-dall-ordine). La quantita' passa solo
--   dal verbo vendite.fn_ddt_riga_correggi_qta_evasa: GUC
--   transazionale zeroerp.ddt_riga_correggi_qta = id della riga E
--   chi scrive e' il proprietario della tabella.
-- Uso: BEFORE UPDATE FOR EACH ROW, fascia _a10_.
-- =========================================================
DECLARE
    -- Le colonne ferme che questo UPDATE cambia: nomi, non valori.
    v_cambiate   text[];
    v_dal_verbo  boolean;
    -- La frase del rifiuto (script.fn_get_stato_testata_documento):
    -- composta, nessuna colonna di cui sia il riflesso.
    v_etichetta  text;
BEGIN
    v_cambiate := array_remove(ARRAY[
        CASE WHEN NEW.articolo_id      IS DISTINCT FROM OLD.articolo_id      THEN 'articolo_id'      END,
        CASE WHEN NEW.uom_operativa_id IS DISTINCT FROM OLD.uom_operativa_id THEN 'uom_operativa_id' END,
        CASE WHEN NEW.factor_to_base   IS DISTINCT FROM OLD.factor_to_base   THEN 'factor_to_base'   END,
        CASE WHEN NEW.qta_operativa    IS DISTINCT FROM OLD.qta_operativa    THEN 'qta_operativa'    END,
        CASE WHEN NEW.quantita         IS DISTINCT FROM OLD.quantita         THEN 'quantita'         END
    ], NULL);

    -- Nessuna colonna ferma cambia: niente da guardare.
    IF cardinality(v_cambiate) = 0 THEN
        RETURN NEW;
    END IF;

    -- Una riga a mano: resta libera.
    IF NOT vendite.fn_ddt_riga_evasa(OLD.id) THEN
        RETURN NEW;
    END IF;

    -- La porta del verbo: la sola quantita', per QUESTA riga, dal
    -- proprietario della tabella.
    v_dal_verbo := COALESCE(current_setting('zeroerp.ddt_riga_correggi_qta', true), '') = OLD.id::text
                   AND script.fn_is_proprietario_tabella(TG_RELID);
    IF v_dal_verbo
       AND v_cambiate <@ ARRAY['qta_operativa', 'quantita']::text[] THEN
        RETURN NEW;
    END IF;

    SELECT t.etichetta
      INTO v_etichetta
      FROM script.fn_get_stato_testata_documento('DDT_VENDITA', OLD.ddt_id) AS t;

    PERFORM script.fn_log_and_raise_error(
        'vendite', TG_NAME::text, 'E_DDT_RIGA_EVASA_FERMA',
        jsonb_build_object('ddt_riga_id', OLD.id,
                           'ddt_id',      OLD.ddt_id,
                           'colonne',     to_jsonb(v_cambiate),
                           'dal_verbo',   v_dal_verbo),
        NEW.tx_id,
        OLD.riga_nr::text,
        COALESCE(v_etichetta, 'DDT #' || OLD.ddt_id::text));
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_righe_guard_riga_evasa()
IS 'Guard (2026-10-11, brief-db-ddt-righe-evase-dall-ordine D-1): su una riga di DDT EVASA (vendite.fn_ddt_riga_evasa: ha un legame con una riga d''ordine o con una riga di reso da ri-consegnare, D-7) non cambiano articolo_id, uom_operativa_id, factor_to_base, qta_operativa, quantita: sono la fotografia di cio'' che si evade, e prima cambiavano senza che il legame lo vedesse (ordine evaso per 10, bolla a 6; reso da ri-consegnare 4, bolla a 2). Rifiuto E_DDT_RIGA_EVASA_FERMA (CONFLITTO_STATO; valori: numero di riga, etichetta del DDT; contesto: colonne cambiate). Il resto della riga resta libero in bozza; fuori bozza parla prima il lock delle righe (_a05_). La quantita'' passa solo dal verbo vendite.fn_ddt_riga_correggi_qta_evasa: GUC transazionale zeroerp.ddt_riga_correggi_qta = id della riga E proprietario della tabella (script.fn_is_proprietario_tabella), come la porta del registro di trgfn_ddt_guard_transizione; articolo, UoM e fattore non passano nemmeno dalla porta. BEFORE UPDATE senza OF (quantita la riscrive trgfn_qta_from_operativa): il confronto e'' nel corpo, ed esce subito se nessuna delle cinque colonne cambia. ⭐ rev 2026-10-19 (20261019-65, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente.';
```

---
{% include-markdown "signature-core.md" %}
