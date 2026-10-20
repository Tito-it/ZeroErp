{% include-markdown "it/dbzero/vendite/manual/fn_numero_documento_fattura.md" %}
# ⚙️ Funzione `fn_numero_documento_fattura`

```sql
CREATE FUNCTION fn_numero_documento_fattura(p_numero bigint, p_serie character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_numero_documento_fattura(p_numero bigint, p_serie character varying)
 RETURNS character varying
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- ⭐ I TRE CASI, in ordine di precedenza. L'ordine e' la regola:
    --   il «non numerato» viene PRIMA di tutto, perche' senza numero
    --   non c'e' niente da comporre — nemmeno con una serie valorizzata.
    SELECT CASE
        -- 1. non ancora numerata: NULL, e il consumatore usa la fallback
        --    che ha gia' (sul chip lineage: vendite.lineage.non_numerato).
        --    ⛔ NON si restituisce la stringa vuota: '' e' un valore, e
        --    un chip che riceve '' disegna una casella vuota invece di
        --    dire «non numerato».
        WHEN p_numero IS NULL THEN NULL

        -- 2. serie assente: il numero DA SOLO, senza trattino orfano.
        --    ⚠️ btrim + COALESCE perche' i due modi di «non avere serie»
        --    sono NULL e stringa vuota, e vanno trattati uguale: il primo
        --    e' il documento mai serializzato, il secondo il documento
        --    serializzato a vuoto. A video sono la stessa cosa.
        WHEN COALESCE(btrim(p_serie), '') = '' THEN p_numero::text

        -- 3. il caso pieno.
        ELSE p_numero::text || ' - ' || btrim(p_serie)
    END::character varying;
$function$

COMMENT ON FUNCTION vendite.fn_numero_documento_fattura(p_numero bigint, p_serie character varying)
IS 'Sede UNICA del numero documento parlante di una fattura: «numero - serie», senza anno. Nasce il 2026-08-29 perche'' per DDT, ordine, reso e preventivo la colonna numero E'' gia'' il numero parlante (un varchar tipo DDT0000031), mentre per la fattura numero e'' un BIGINT — un contatore — e l''identita'' sta in TRE colonne nullable (anno, serie, numero). Senza una sede, ogni consumatore se la inventava e il grafo mostrava il contatore nudo: un «1» che non e'' sbagliato, e'' AMBIGUO, perche'' nello stesso anno possono esistere una fattura 1 e una nota di credito 1. ⛔ L''ANNO E'' FUORI DI PROPOSITO: la regola dichiarata e'' «accanto c''e'' sempre la data», e ripetere l''anno dentro il codice lo direbbe due volte. ⚠️ I TRE CASI, ed e'' tutta la funzione: numero NULL -> NULL (non numerata, il consumatore usa la sua fallback — NON la stringa vuota, che un chip disegnerebbe come casella vuota); serie NULL o vuota -> il numero da solo, senza trattino orfano; altrimenti «numero - serie». ⛔ NON e'' STRICT, ed e'' la scelta che regge meta'' della regola: STRICT tornerebbe NULL appena un parametro e'' NULL, cioe'' proprio nel caso della serie assente, dove il risultato giusto e'' il numero. E una composizione scritta a mano sbaglia in silenzio: numero::text || '' - '' || serie con serie NULL non da'' «1», da'' NULL — il numero sparisce senza nessun errore. ⭐ E'' questa la ragione per cui la sede dev''essere UNA: non perche'' le composizioni fossero tante, ma perche'' la regola ha due rami che chi la riscrive non ha ragione di ricordare. ⚠️ PURA (IMMUTABLE, LANGUAGE sql) e prende i VALORI, non l''id: cosi'' il pianificatore la inlinea nella select list di una vista invece di fare una lettura per riga, ed e'' testabile senza nessuna fixture. ⛔ NON usarla per la stringa SDI: fn_prepare_sdi_payload compone anno||serie|| numero SENZA separatore (2026VX2103) ed e'' una stringa per una MACCHINA. Misurato il 2026-08-29: e'' l''unica altra composizione viva in tutto il DB, e resta deliberatamente diversa — sono due contratti con due committenti, e il giorno che uno cambia si scoprirebbe di averli legati.';
```

</div>

---
{% include-markdown "signature-core.md" %}
