# ⚙️ Funzione `fn_titolo_iva_vigente`

```sql
CREATE FUNCTION fn_titolo_iva_vigente(p_attivo boolean, p_valido_al date, p_oggi date)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_titolo_iva_vigente(p_attivo boolean, p_valido_al date, p_oggi date)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- Vigente: attivo e valido almeno fino a oggi. Non STRICT:
    -- valido_al NULL e' «senza scadenza», non «nessuna risposta».
    SELECT COALESCE(p_attivo, false)
       AND (p_valido_al IS NULL OR p_valido_al >= p_oggi);
$function$

COMMENT ON FUNCTION anagrafiche.fn_titolo_iva_vigente(p_attivo boolean, p_valido_al date, p_oggi date)
IS 'Un titolo IVA e'' VIGENTE se e'' attivo e la sua finestra arriva almeno a oggi: attivo AND (valido_al IS NULL OR valido_al >= oggi). Il criterio e'' la validita'', non il solo attivo (D-5): un titolo con movimenti non si disattiva mai, e uno scaduto non blocca niente; si esce chiudendo valido_al. Un titolo che comincia domani e'' vigente. Sui VALORI: oggi lo passa chi chiama (script.fn_giorno_operativo(now())), quindi IMMUTABLE e indipendente dal fuso della sessione. Non STRICT. Brief: brief-db-dati-fiscali-e-societari-del-soggetto (Parte D).';
```

</div>

---
{% include-markdown "signature-core.md" %}
