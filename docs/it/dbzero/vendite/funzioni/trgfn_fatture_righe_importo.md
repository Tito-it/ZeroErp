# ⚙️ Funzione `trgfn_fatture_righe_importo`

```sql
CREATE FUNCTION trgfn_fatture_righe_importo()
```

**Definizione completa:**

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
DECLARE
    v_decimali vendite.articolo_regole_fatturazione.arrotondamento_importi_dec%TYPE;
    v_metodo   vendite.articolo_regole_fatturazione.metodo_arrotondamento_importi%TYPE;
BEGIN
    -- Regole dell'articolo con FALLBACK ai default: LEFT JOIN da
    -- una riga-base cosi' si ottiene SEMPRE una riga. Un SELECT
    -- diretto darebbe zero righe quando l'articolo non ha regole,
    -- e i COALESCE non servirebbero a nulla (stesso pattern di
    -- vendite.fn_group_attivita_fatturabili).
    SELECT COALESCE(r.arrotondamento_importi_dec, 2),
           COALESCE(r.metodo_arrotondamento_importi, 'HALF_UP')
      INTO v_decimali, v_metodo
      FROM (SELECT 1) base
      LEFT JOIN vendite.articolo_regole_fatturazione r
             ON r.articolo_id = NEW.articolo_id;

    -- La regola di arrotondamento vive in un punto solo.
    NEW.imponibile_riga := script.fn_arrotonda_importo(
        NEW.qta
          * NEW.prezzo_unitario
          * (1 - COALESCE(NEW.sconto_percentuale, 0) / 100),
        v_decimali,
        v_metodo
    );

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fatture_righe_importo()
IS 'Calcola vendite.fatture_righe.imponibile_riga a ogni INSERT/UPDATE: qta * prezzo_unitario * (1 - sconto/100), arrotondato con decimali e metodo configurati su vendite.articolo_regole_fatturazione per l''articolo della riga (fallback 2 / HALF_UP). L''arrotondamento e'' delegato a script.fn_arrotonda_importo, unico punto in cui vive la regola. ⚠️ Sostituisce la colonna generata del 20260728-01, che era il presidio piu'' forte ma non poteva leggere le regole per articolo — una GENERATED usa solo dati della propria riga. Un valore passato dall''esterno viene SOVRASCRITTO (con la colonna generata veniva rifiutato): il risultato e'' lo stesso, la segnalazione no, ed e'' compensata da un pgTAP dedicato. NON tocca qta: l''arrotondamento delle quantita'' e'' una regola della singola attivita'' a monte, mai dell''aggregato di riga. brief-fix-importi-riga-fattura-zero §4.1 (D1), rev 2026-07-28.';
```

---
{% include-markdown "signature-core.md" %}
