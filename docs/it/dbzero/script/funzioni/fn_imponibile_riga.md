{% include-markdown "it/dbzero/script/manual/fn_imponibile_riga.md" %}
# ⚙️ Funzione `fn_imponibile_riga`

```sql
CREATE FUNCTION fn_imponibile_riga(p_quantita numeric, p_prezzo_unitario numeric, p_sconto_percentuale numeric)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_imponibile_riga(p_quantita numeric, p_prezzo_unitario numeric, p_sconto_percentuale numeric)
 RETURNS numeric
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    -- ⭐ La forma e' quella che le otto copie scrivevano, byte per
    --   byte nell'aritmetica: prima quantita' x prezzo, poi il
    --   fattore di sconto. Cambiare l'ordine delle moltiplicazioni
    --   non cambia il valore esatto ma cambia la SCALA del numeric
    --   risultante, cioe' come esce a video un valore non arrotondato.
    -- ⛔ Nessun COALESCE su prezzo o quantita': NULL deve uscire NULL.
    SELECT (p_quantita * p_prezzo_unitario)
         * (1::numeric - COALESCE(p_sconto_percentuale, 0::numeric) / 100::numeric);
$function$

COMMENT ON FUNCTION script.fn_imponibile_riga(p_quantita numeric, p_prezzo_unitario numeric, p_sconto_percentuale numeric)
IS 'Sede UNICA dell''imponibile di una riga di documento: quantita'' x prezzo x (1 - sconto/100), a precisione PIENA. Nasce il 2026-09-28 (brief-db-liste-righe-documento, D-8.8) perche'' la stessa formula era scritta a mano in otto oggetti del database (righe preventivo, viste IVA di ordini e DDT, tre viste cruscotto, ricalcolo IVA del preventivo, trigger dell''imponibile di fattura) e in tre repository: oggi coincidevano, ma una regola in undici posti diverge alla prima modifica, e una lista che mostra un importo mentre il riepilogo IVA ne somma un altro non da'' nessun errore. ⭐ SEMANTICA: prezzo o quantita'' NULL -> NULL, MAI zero (regola V-2/DEC-6 del DDT senza prezzo: lo zero sarebbe indistinguibile da una riga che vale zero); sconto NULL -> nessuno sconto. ⚠️ NESSUN ARROTONDAMENTO: e'' politica di chi consuma — round(…, 2) per mostrare, somma piena poi arrotondata per il riepilogo IVA, script.fn_arrotonda_importo con la regola configurata per l''imponibile di fattura. ⚠️ Tipi espliciti numeric, non %TYPE: serve righe di documenti diversi con typmod diversi (e servira'' acquisti), e ancorarla a una tabella direbbe il falso. Pura (IMMUTABLE, LANGUAGE sql, PARALLEL SAFE): il pianificatore la inlinea nelle viste. NON e'' STRICT: lo sconto NULL e'' un caso normale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
