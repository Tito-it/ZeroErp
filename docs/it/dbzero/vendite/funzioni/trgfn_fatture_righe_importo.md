{% include-markdown "it/dbzero/vendite/manual/trgfn_fatture_righe_importo.md" %}
# ⚙️ Funzione `trgfn_fatture_righe_importo`

```sql
CREATE FUNCTION trgfn_fatture_righe_importo()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatture_righe_importo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: l'importo di riga esiste sempre ed e' coerente con
--        quantita', prezzo e sconto della riga stessa.
-- Uso:   BEFORE INSERT OR UPDATE FOR EACH ROW (fase a20)
-- brief-fix-importi-riga-fattura-zero §4.1 (D1).
--
-- Il difetto che chiude: la colonna esisteva dal principio ma
-- NESSUNO la scriveva — ne' fn_generate_fatture_righe, ne' il
-- repository Python, ne' un trigger — e ogni fattura del sistema
-- valeva 0,00 EUR.
-- rev 2026-10-21 (20261021-15, brief-db-modelli-documento-standard §10.7 R-3):
--   senza regole dell'articolo non vale piu' il letterale 2 / HALF_UP, ma i
--   parametri effettivi dell'emittente per l'utility della fattura, dal BB
--   vendite.fn_parametri_importo_riga: la stessa catena del totale.
DECLARE
    v_decimali vendite.articolo_regole_fatturazione.arrotondamento_importi_dec%TYPE;
    v_metodo   vendite.articolo_regole_fatturazione.metodo_arrotondamento_importi%TYPE;
    v_emittente vendite.fatture.emittente_soggetto_ruolo_id%TYPE;
    v_utility   vendite.fatture.utility_id%TYPE;
BEGIN
    -- La regola dell'articolo se c'e', altrimenti i parametri
    -- effettivi dell'emittente per l'utility della fattura: il BB
    -- da' sempre una riga (rev 20261021-15).
    SELECT f.emittente_soggetto_ruolo_id, f.utility_id
      INTO v_emittente, v_utility
      FROM vendite.fatture f
     WHERE f.id = NEW.fattura_id;

    SELECT p.arrotondamento_importi_dec, p.metodo_arrotondamento_importi
      INTO v_decimali, v_metodo
      FROM vendite.fn_parametri_importo_riga(NEW.articolo_id, v_emittente, v_utility) p;

    -- Senza regole dell'articolo e senza utility non c'e' da dove
    -- prendere i parametri: come il ricalcolo dei totali, non si
    -- indovina. Nell'applicazione non succede (la testata non nasce
    -- senza utility: fn_get_or_create_fattura_header).
    IF v_decimali IS NULL OR v_metodo IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'trgfn_fatture_righe_importo', 'E_CONFIG_MANCANTE',
            jsonb_build_object('fattura_id', NEW.fattura_id, 'articolo_id', NEW.articolo_id,
                               'utility_id', v_utility),
            NULL::uuid,
            concat('parametri d''importo di riga: articolo senza regole e fattura ', NEW.fattura_id, ' senza utility'));
    END IF;

    -- La regola di arrotondamento vive in un punto solo.
    -- rev 2026-09-28 (brief-db-liste-righe-documento, D-8.8): l'imponibile
    --   pieno viene dalla sede unica, l'arrotondamento resta configurato.
    NEW.imponibile_riga := script.fn_arrotonda_importo(
        script.fn_imponibile_riga(NEW.qta, NEW.prezzo_unitario, NEW.sconto_percentuale),
        v_decimali,
        v_metodo
    );

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fatture_righe_importo()
IS 'Calcola vendite.fatture_righe.imponibile_riga a ogni INSERT/UPDATE: qta * prezzo_unitario * (1 - sconto/100), arrotondato con decimali e metodo configurati su vendite.articolo_regole_fatturazione per l''articolo della riga (senza regole: i parametri effettivi dell''emittente per l''utility della fattura, vendite.fn_parametri_importo_riga, rev 20261021-15; prima il letterale 2 / HALF_UP). L''arrotondamento e'' delegato a script.fn_arrotonda_importo, unico punto in cui vive la regola. ⚠️ Sostituisce la colonna generata del 20260728-01, che era il presidio piu'' forte ma non poteva leggere le regole per articolo — una GENERATED usa solo dati della propria riga. Un valore passato dall''esterno viene SOVRASCRITTO (con la colonna generata veniva rifiutato): il risultato e'' lo stesso, la segnalazione no, ed e'' compensata da un pgTAP dedicato. NON tocca qta: l''arrotondamento delle quantita'' e'' una regola della singola attivita'' a monte, mai dell''aggregato di riga. brief-fix-importi-riga-fattura-zero §4.1 (D1), rev 2026-07-28.';
```

</div>

---
{% include-markdown "signature-core.md" %}
