# ⚙️ Funzione `trgfn_fatture_guard_numero_fiscale`

```sql
CREATE FUNCTION trgfn_fatture_guard_numero_fiscale()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatture_guard_numero_fiscale()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: una fattura che ha un numero fiscale non si cancella, e
--   la sua identita' fiscale (registro, anno, serie, numero) non
--   cambia piu'. La numerazione consuma un progressivo che non
--   torna indietro: una numerata che sparisce, o che cambia
--   numero, lascia un buco nella sequenza.
-- Uso:   BEFORE UPDATE OR DELETE FOR EACH ROW
--        WHEN (OLD.numero IS NOT NULL), fascia _a05_.
-- Il discriminante e' OLD.numero, non lo stato: la fattura e'
--   numerata mentre e' ancora EMESSA, e una soglia per stato
--   lascerebbe una finestra (come i due fratelli: data numerata,
--   numerata non annullabile). Nessuna GUC di bypass.
DECLARE
    v_cambiate text[];
BEGIN
    IF TG_OP = 'DELETE' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            TG_NAME::text,
            'E_FATTURA_NUMERATA_NON_CANCELLABILE',
            jsonb_build_object(
                'fattura_id',  OLD.id,
                'registro_id', OLD.registro_id,
                'anno',        OLD.anno,
                'serie',       OLD.serie,
                'numero',      OLD.numero,
                -- ⭐ Il bersaglio: la fattura su cui l'errore e'
                --    successo. Chi cancella la vede: altrimenti
                --    la RLS avrebbe gia' tolto la riga dalla DELETE.
                'bersaglio', jsonb_build_array(
                    jsonb_build_object('tipo', 'FATTURA',
                                       'id',   OLD.id::text))),
            NULL::uuid,
            -- Nel messaggio il NUMERO, non l'id: e' quello che
            -- compare sul documento.
            OLD.numero::text);
        RETURN OLD;
    END IF;

    v_cambiate := array_remove(ARRAY[
        CASE WHEN NEW.registro_id IS DISTINCT FROM OLD.registro_id THEN 'registro_id' END,
        CASE WHEN NEW.anno        IS DISTINCT FROM OLD.anno        THEN 'anno'        END,
        CASE WHEN NEW.serie       IS DISTINCT FROM OLD.serie       THEN 'serie'       END,
        CASE WHEN NEW.numero      IS DISTINCT FROM OLD.numero      THEN 'numero'      END
    ], NULL);

    -- Un UPDATE che non tocca l'identita' fiscale passa: note,
    -- snapshot e stato hanno ciascuno i propri guard.
    IF cardinality(v_cambiate) = 0 THEN
        RETURN NEW;
    END IF;

    PERFORM script.fn_log_and_raise_error(
        'vendite',
        TG_NAME::text,
        'E_FATTURA_NUMERO_NON_MODIFICABILE',
        jsonb_build_object(
            'fattura_id',  OLD.id,
            'registro_id', OLD.registro_id,
            'anno',        OLD.anno,
            'serie',       OLD.serie,
            'numero',      OLD.numero,
            'colonne',     to_jsonb(v_cambiate),
            'bersaglio', jsonb_build_array(
                jsonb_build_object('tipo', 'FATTURA',
                                   'id',   OLD.id::text))),
        NEW.tx_id,
        OLD.numero::text);

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fatture_guard_numero_fiscale()
IS 'Guard: una fattura che ha un numero fiscale non si cancella (E_FATTURA_NUMERATA_NON_CANCELLABILE) e non cambia registro_id, anno, serie o numero (E_FATTURA_NUMERO_NON_MODIFICABILE), entrambi CONFLITTO_STATO. La numerazione consuma un progressivo del registro che non torna indietro: una numerata che sparisce, o che cambia numero, lascia un buco nella sequenza fiscale. Il discriminante e'' OLD.numero, non lo stato (la fattura e'' numerata mentre e'' ancora EMESSA), come in trgfn_fatture_guard_data_numerata e trgfn_fatture_numerata_non_annulabile. La numerazione (fn_assign_numero_fattura, da numero NULL) resta fuori per il WHEN del trigger; un UPDATE che non tocca l''identita'' fiscale passa. Nessuna GUC di bypass: e'' un invariante fiscale. E'' la rete sotto le tre check dei percorsi che cancellano (E_LOTTO_FATTURE_NUMERATE, E_FATTURA_GIA_NUMERATA): chiude la corsa fra il loro controllo, che gira prima del lock, e la DELETE di fn_cleanup_fatture_by_ids, e il retro per cui un UPDATE poteva togliere il numero prima della DELETE. Trigger trg_fatture_a05_guard_numero_fiscale_upd_dlt, BEFORE UPDATE OR DELETE, WHEN (OLD.numero IS NOT NULL). Contesto: fattura_id, registro_id, anno, serie, numero, colonne (solo UPDATE), bersaglio. Nasce il 2026-10-04, brief-db-esclusioni-implicite Q-4 (decisione di Tid).';
```

</div>

---
{% include-markdown "signature-core.md" %}
