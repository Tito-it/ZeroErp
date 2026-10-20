{% include-markdown "it/dbzero/vendite/manual/fn_check_fondo_fattura_capiente.md" %}
# ⚙️ Funzione `fn_check_fondo_fattura_capiente`

```sql
CREATE FUNCTION fn_check_fondo_fattura_capiente(p_capienza numeric, p_importo numeric)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_check_fondo_fattura_capiente(p_capienza numeric, p_importo numeric)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- ⚠️ Segno + valore assoluto, e non `p_capienza >= p_importo`:
    --    su una sorgente a credito la capienza e' negativa e un
    --    `>=` nudo direbbe sempre di no, spegnendo meta' del
    --    meccanismo (il capo a credito della banda delle soglie).
    --
    -- ⚠️ I due IS NOT NULL non sono difensivi: senza di loro il
    --    risultato sarebbe NULL, e un NULL fa sparire la riga
    --    dall'elenco che usa questa funzione NEGATA. Il caso piu'
    --    anomalo sarebbe l'unico invisibile.
    SELECT p_capienza IS NOT NULL
       AND p_importo  IS NOT NULL
       AND sign(p_capienza) = sign(p_importo)
       AND abs(p_capienza) >= abs(p_importo);
$function$

COMMENT ON FUNCTION vendite.fn_check_fondo_fattura_capiente(p_capienza numeric, p_importo numeric)
IS 'La sorgente regge ancora questo fondo? Predicato PURO sulla capienza: stesso segno dell''importo dell''atto e non inferiore in valore assoluto. ⚠️ Segno + valore assoluto e non un `>=` nudo: su una sorgente a credito la capienza e'' negativa e il confronto diretto direbbe sempre di no, spegnendo il capo a credito della banda. ⚠️ Con un argomento NULL ritorna FALSE e non NULL, ed e'' il dettaglio piu'' delicato: i due chiamanti la usano in versi opposti — fn_applica_fondi_fattura come `AND` (FALSE = non applico, fail-closed) e vw_fondi_fattura_da_decidere come `AND NOT` (FALSE = la mostro, fail-visible). Un ritorno NULL avrebbe fatto sparire dall''elenco proprio il caso piu'' anomalo. Estratta il 2026-08-15 dal WHERE di fn_applica_fondi_fattura al secondo uso (regola del 2): due copie della regola di capienza direbbero, senza nessun errore e nessun log, due verita'' diverse — l''elenco che dichiara inapplicabile cio'' che il giro applica. IMMUTABLE e in LANGUAGE sql di proposito: cosi'' il planner la inlinea dentro il WHERE. Serve a D-10 di brief-db-fondo-fattura-ricalcolo-e-governo §8.2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
