{% include-markdown "it/dbzero/script/manual/fn_check_fatture_con_plafond_consumato.md" %}
# ⚙️ Funzione `fn_check_fatture_con_plafond_consumato`

```sql
CREATE FUNCTION fn_check_fatture_con_plafond_consumato(p_fatture_ids bigint[])
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_fatture_con_plafond_consumato(p_fatture_ids bigint[])
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: dire se queste fatture hanno gia' CONSUMATO il plafond di un
--   titolo IVA, cioe' se nel registro dei movimenti c'e' almeno una riga
--   che le nomina. Funzione PURA (fn_check_*): nessun raise di dominio,
--   nessuna scrittura.
--   Consumatori: le tre porte di reset, via le rispettive fn_check_*, e
--   per loro tramite fn_available_actions_lotto; e il guard di
--   vendite.fn_cleanup_fatture_by_ids.
--   Brief: brief-db-bom-flag-quantita-e-kit-in-fattura §14 (strada A di
--   Tid, 2026-10-04).
-- ⭐ PERCHE' E' UN PUNTO DI NON RITORNO, come il numero. Il plafond si
--   consuma all'emissione (task consuma_plafond_lotto, PRIMA della
--   numerazione). Un movimento e' un fatto contabile: il registro e'
--   append-only e le sue FK verso la fattura e la riga sono NO ACTION di
--   proposito. Disfare la fattura vorrebbe dire cancellare il fatto, e
--   uno storno non basterebbe: anche lo storno nominerebbe la fattura.
--   Il lotto in quel caso va AVANTI: il passaggio a DEFINITIVA riprende
--   fattura per fattura e il consumo e' idempotente.
-- Ritorna: [] se nessuna fattura ha consumato; altrimenti un array con
--   {codice, reason, reason_key, dettaglio} — dettaglio = quante fatture.
DECLARE
    v_motivi  jsonb := '[]'::jsonb;
    -- ⚠️ `integer` esplicito: e' un conteggio (count), non il valore di
    --    una colonna.
    v_fatture integer;
BEGIN
    -- Insieme vuoto: non c'e' niente da controllare, e NON e' un errore
    -- di parametro — i chiamanti passano legittimamente un lotto senza
    -- fatture.
    IF p_fatture_ids IS NULL
       OR array_length(p_fatture_ids, 1) IS NULL THEN
        RETURN v_motivi;
    END IF;

    -- ⚠️ Qualunque tipo di movimento che nomini la fattura (FATTURA o
    --   NOTA_CREDITO; una FORZATURA non nomina fatture per CHECK): e' la
    --   FK a bloccare la cancellazione, non il segno o il tipo. Anche un
    --   kit a netto zero (+50 e -50) ha due movimenti e quindi blocca.
    -- ⚠️ Si contano le FATTURE, non i movimenti: all'operatore serve
    --   sapere quali documenti sono intoccabili.
    -- ⚠️ Legge sotto ROW SECURITY (SECURITY INVOKER): un chiamante fuori
    --   perimetro potrebbe non vedere i movimenti e passare di qui. Non si
    --   perde niente in silenzio: e' la FK a fermare la cancellazione, con
    --   il 23503 di prima. Stessa disciplina di fn_check_fatture_con_rettifiche.
    SELECT count(DISTINCT m.fattura_id)
      INTO v_fatture
      FROM anagrafiche.soggetti_titoli_iva_movimenti m
     WHERE m.fattura_id = ANY (p_fatture_ids);

    IF COALESCE(v_fatture, 0) > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_FATTURE_PLAFOND_CONSUMATO',
            'reason',     'PLAFOND_CONSUMATO',
            -- ⚠️ La reason_key e' un debito verso il frontend finche' non
            --   esiste la voce i18n corrispondente (brief §14, R-FE-A1).
            'reason_key', 'vendite.lotti.azione_reason.plafond_consumato',
            'dettaglio',  v_fatture);
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_fatture_con_plafond_consumato(p_fatture_ids bigint[])
IS 'Funzione PURA (fn_check_*): dice se queste fatture hanno gia'' consumato il plafond di un titolo IVA, cioe'' se nel registro anagrafiche.soggetti_titoli_iva_movimenti c''e'' almeno una riga che le nomina. Ritorna [] oppure un array con {codice E_FATTURE_PLAFOND_CONSUMATO, reason PLAFOND_CONSUMATO, reason_key, dettaglio = quante fatture}. ⭐ Sede UNICA condivisa dalle tre porte di reset (riporta a draft, annulla lotto, elimina fattura) e dal guard di vendite.fn_cleanup_fatture_by_ids, sullo stampo di script.fn_check_fatture_con_rettifiche (brief-db-bom-flag-quantita-e-kit-in-fattura §14, strada A di Tid del 2026-10-04). ⭐ Il consumo del plafond e'' un PUNTO DI NON RITORNO come il numero: avviene all''emissione, PRIMA della numerazione, e un movimento e'' un fatto contabile — registro append-only, FK NO ACTION verso fattura e riga di proposito. Disfare la fattura vorrebbe dire cancellare il fatto, e uno storno non basterebbe perche'' nominerebbe anch''esso la fattura. Il lotto va AVANTI: il passaggio a DEFINITIVA riprende fattura per fattura e il consumo e'' idempotente. ⚠️ Conta qualunque movimento che nomini la fattura (anche un kit a netto zero ne ha due) e conta le FATTURE, non i movimenti. ⚠️ Legge sotto RLS: fuori perimetro non vede, e allora e'' la FK a fermare la cancellazione col 23503 di prima — nessun peggioramento.';
```

</div>

---
{% include-markdown "signature-core.md" %}
