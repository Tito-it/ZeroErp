{% include-markdown "it/dbzero/vendite/manual/trgfn_fatture_righe_guard_congelamento.md" %}
# ⚙️ Funzione `trgfn_fatture_righe_guard_congelamento`

```sql
CREATE FUNCTION trgfn_fatture_righe_guard_congelamento()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatture_righe_guard_congelamento()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: la fattura e' un documento fiscale — superata la soglia
--        DRAFT/EMESSA le sue righe sono uno snapshot e non si
--        toccano piu', ne' in scrittura ne' in cancellazione.
-- Uso:   BEFORE INSERT OR UPDATE OR DELETE FOR EACH ROW
-- brief-fix-importi-riga-fattura-zero §4.1-bis (D1-bis).
DECLARE
    v_fattura_id  vendite.fatture.id%TYPE;
    v_riga_id     vendite.fatture_righe.id%TYPE;
    v_stato       config.stati_doc_fiscale.codice_interno%TYPE;
    v_allow_reset text;
BEGIN
    -- Bypass di manutenzione: stesso contratto degli altri guard
    -- della famiglia. fn_cleanup_fatture_by_ids (reset lotto)
    -- imposta questa GUC per attraversarli; la DELETE in cascata
    -- dalla testata fattura passa di qui.
    v_allow_reset := current_setting('zeroerp.maintenance_reset_lotto_draft', true);
    IF COALESCE(lower(v_allow_reset), 'off') IN ('on', 'true', '1') THEN
        IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
    END IF;

    IF TG_OP = 'DELETE' THEN
        v_fattura_id := OLD.fattura_id;
        v_riga_id    := OLD.id;
    ELSE
        v_fattura_id := NEW.fattura_id;
        v_riga_id    := NEW.id;
    END IF;

    -- Stato per codice_interno (immutabile), mai per codice.
    SELECT s.codice_interno
      INTO v_stato
      FROM vendite.fatture f
      JOIN config.stati_doc_fiscale s ON s.id = f.stato_doc_fiscale_id
     WHERE f.id = v_fattura_id;

    -- Fattura senza stato: non e' questo il guard che deve
    -- occuparsene: fallire qui darebbe un errore fuorviante su un
    -- problema che sta altrove.
    IF v_stato IS NULL THEN
        IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
    END IF;

    -- Stessa soglia di fn_ricalcola_riepilogo_iva_fattura.
    IF v_stato NOT IN ('DRAFT', 'EMESSA') THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'trgfn_fatture_righe_guard_congelamento',
            'E_FATTURA_RIGA_CONGELATA',
            jsonb_build_object(
                'operazione',  TG_OP,
                'fattura_id',  v_fattura_id,
                'riga_id',     v_riga_id,
                'stato',       v_stato,
                'soglia',      'DRAFT,EMESSA'),
            NULL::uuid,
            v_fattura_id::text, v_stato
        );
    END IF;

    IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fatture_righe_guard_congelamento()
IS 'Guard (BEFORE INSERT OR UPDATE OR DELETE su vendite.fatture_righe): oltre la soglia DRAFT/EMESSA le righe della fattura sono uno snapshot fiscale e non si toccano piu''. Congela gli INPUT (qta, prezzo_unitario, sconto_percentuale, iva_id) e non l''importo: imponibile_riga e'' una colonna GENERATA e segue sempre le colonne sorgente, quindi bloccare il solo importo lascerebbe passare una riga con qta=999 e imponibile=500 — incoerente e indistinguibile da un dato buono. Blocca anche INSERT e DELETE: aggiungere o togliere una riga a un documento emesso ne cambia il totale come modificarla. L''UPDATE e'' bloccato per intero, descrizione compresa: finisce sul PDF come tutto il resto. Soglia identica a fn_ricalcola_riepilogo_iva_fattura, per codice_interno. Bypass via GUC zeroerp.maintenance_reset_lotto_draft, che vendite.fn_cleanup_fatture_by_ids imposta per il reset lotto (la FK e'' ON DELETE CASCADE: cancellare una fattura fa scattare questo trigger su ogni riga). Errore: E_FATTURA_RIGA_CONGELATA. brief-fix-importi-riga-fattura-zero §4.1-bis, rev 2026-07-28.';
```

---
{% include-markdown "signature-core.md" %}
