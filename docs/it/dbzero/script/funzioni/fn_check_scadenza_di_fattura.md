{% include-markdown "it/dbzero/script/manual/fn_check_scadenza_di_fattura.md" %}
# ⚙️ Funzione `fn_check_scadenza_di_fattura`

```sql
CREATE FUNCTION fn_check_scadenza_di_fattura(p_scadenza_id bigint, p_fattura_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_scadenza_di_fattura(p_scadenza_id bigint, p_fattura_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Rispondere a UNA domanda di fatto — «la rata indicata
    --   appartiene alla fattura indicata?» — senza che la row
    --   security la trasformi in «...e riesco a vederla?».
    --
    -- ⚠️ NON solleva mai: e' una fn_check_*. Chi la chiama sa
    --    quale messaggio dare, questa sa solo il fatto.
    --
    -- ℹ️ Su un parametro nullo risponde NULL: «la domanda non si
    --    pone» non e' ne' vero ne' falso, e chi chiama non la fa
    --    mai con un nullo.
    -- =========================================================
    IF p_scadenza_id IS NULL OR p_fattura_id IS NULL THEN
        RETURN NULL;
    END IF;

    RETURN EXISTS (
        SELECT 1
          FROM vendite.fatture_scadenze s
         WHERE s.id = p_scadenza_id
           AND s.fattura_id = p_fattura_id
    );
END;
$function$

COMMENT ON FUNCTION script.fn_check_scadenza_di_fattura(p_scadenza_id bigint, p_fattura_id bigint)
IS 'Risponde «questa rata appartiene a questa fattura?» FUORI dalla row security. 🔴 Esiste perche'' vendite.fatture_scadenze ha la RLS attiva e un guard che legge sotto RLS NON DISTINGUE «non appartiene» da «non la vedo»: due verita'' opposte che producono lo stesso EXISTS falso — la prima e'' un''incoerenza da rifiutare, la seconda e'' una riga legittima che l''operatore non ha il diritto di guardare. Rifiutarle con lo stesso messaggio vorrebbe dire dirne una falsa. ℹ️ Diverso il caso della FK: i controlli di integrita'' referenziale PostgreSQL li esegue gia'' fuori dalla row security, quindi la FK sa che la rata ESISTE — questa sa DI CHI E''. ⚠️ Non allarga nessun perimetro: risponde un booleano su una coppia che il chiamante ha gia'' nominato, nessuna riga esce e nessun elenco si popola. ⚠️ fn_check_* per convenzione: verifica e risponde, non solleva — a decidere che farne e'' il guard che la chiama (pagamenti.trgfn_vendite_contabili_righe_guard_rata), che e'' anche l''unico che sa quale messaggio dare all''operatore. Su un parametro nullo risponde NULL: «la domanda non si pone» non e'' ne'' vero ne'' falso. ⚠️ SECURITY DEFINER con search_path fissato, come le altre del progetto; l''owner lo riallinea dbops.fn_sync_functions_owner in 90_end, ed e'' quello che la rende davvero definer. S2-3 del cantiere incassi, decisione D14-b del brief madre.';
```

</div>

---
{% include-markdown "signature-core.md" %}
