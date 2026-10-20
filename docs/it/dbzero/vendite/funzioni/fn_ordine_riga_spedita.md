# ⚙️ Funzione `fn_ordine_riga_spedita`

```sql
CREATE FUNCTION fn_ordine_riga_spedita(p_ordine_riga_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ordine_riga_spedita(p_ordine_riga_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
    -- Scopo: la riga d'ordine e' gia' partita con un DDT? Vero se un
    --   suo legame porta a una riga di DDT il cui stato dice «merce
    --   partita» (BB script.vw_stati_doc_ddt_merce_partita: uscito dalla
    --   bozza e non abortito). Basta un DDT, anche per una parte della
    --   riga (P-1). Un id assente risponde falso.
    SELECT EXISTS (
        SELECT 1
          FROM vendite.ordini_righe_fulfillment f
          JOIN vendite.ddt_righe dr ON dr.id = f.ddt_riga_id
          JOIN vendite.ddt d        ON d.id  = dr.ddt_id
          JOIN script.vw_stati_doc_ddt_merce_partita s ON s.id = d.stato_doc_ddt_id
         WHERE f.ordine_riga_id = p_ordine_riga_id
           AND s.merce_partita);
$function$

COMMENT ON FUNCTION vendite.fn_ordine_riga_spedita(p_ordine_riga_id bigint)
IS 'Lettore (2026-10-11, brief-db-date-consegna-righe-in-blocco D-7, P-1): la riga d''ordine e'' gia'' partita con un DDT? Vero se almeno un suo legame (vendite.ordini_righe_fulfillment) porta a una riga di DDT il cui stato dice merce partita: il BB script.vw_stati_doc_ddt_merce_partita (uscito dalla bozza, ordine >= EMESSO, e non abortito). Basta un DDT, anche per una parte della riga: una spedizione parziale ferma la data confermata come una totale (P-1 di Tid). Un DDT in bozza non conta. Un id assente risponde falso. ⛔ SECURITY DEFINER: la legge il guard della data di consegna confermata, e DDT e righe di DDT hanno RLS; sotto la RLS di chi scrive un DDT fuori perimetro sparirebbe e il guard diventerebbe fail-open (stessa scelta di script.fn_get_stato_testata_documento). PERIMETRO: un booleano su una riga d''ordine, nessuna colonna esposta. Consumatore: script.fn_check_ordine_riga_data_consegna_confermata. rev 2026-10-12 (20261012-31): lo stato dal BB, non piu'' la copia dell''espressione di vendite.fn_partite_merce (regola del 2, scelta (a) di Tid).';
```

</div>

---
{% include-markdown "signature-core.md" %}
