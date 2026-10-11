# ⚙️ Funzione `fn_ordine_riga_spedita`

```sql
CREATE FUNCTION fn_ordine_riga_spedita(p_ordine_riga_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ordine_riga_spedita(p_ordine_riga_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
    -- Scopo: la riga d'ordine e' gia' partita con un DDT? Vero se un
    --   suo legame porta a una riga di DDT il cui documento e' uscito
    --   dalla bozza (stato con ordine >= EMESSO) e non e' abortito:
    --   l'espressione di vendite.fn_partite_merce. Basta un DDT, anche
    --   per una parte della riga (P-1). Un id assente risponde falso.
    SELECT EXISTS (
        SELECT 1
          FROM vendite.ordini_righe_fulfillment f
          JOIN vendite.ddt_righe dr  ON dr.id = f.ddt_riga_id
          JOIN vendite.ddt d         ON d.id  = dr.ddt_id
          JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id
         WHERE f.ordine_riga_id = p_ordine_riga_id
           AND NOT s.is_abortito
           AND s.ordine >= (SELECT e.ordine
                              FROM config.stati_doc_ddt e
                             WHERE e.codice_interno = 'EMESSO'));
$function$

COMMENT ON FUNCTION vendite.fn_ordine_riga_spedita(p_ordine_riga_id bigint)
IS 'Lettore (2026-10-11, brief-db-date-consegna-righe-in-blocco D-7, P-1): la riga d''ordine e'' gia'' partita con un DDT? Vero se almeno un suo legame (vendite.ordini_righe_fulfillment) porta a una riga di DDT il cui documento e'' uscito dalla bozza e non e'' abortito: stato con ordine >= quello di EMESSO e non is_abortito, l''espressione di vendite.fn_partite_merce (seconda sede, estrazione dichiarata nel brief). Basta un DDT, anche per una parte della riga: una spedizione parziale ferma la data confermata come una totale (P-1 di Tid). Un DDT in bozza non conta. Un id assente risponde falso. ⛔ SECURITY DEFINER: la legge il guard della data di consegna confermata, e DDT e righe di DDT hanno RLS; sotto la RLS di chi scrive un DDT fuori perimetro sparirebbe e il guard diventerebbe fail-open (stessa scelta di script.fn_get_stato_testata_documento). PERIMETRO: un booleano su una riga d''ordine, nessuna colonna esposta. Consumatore: script.fn_check_ordine_riga_data_consegna_confermata.';
```

---
{% include-markdown "signature-core.md" %}
