{% include-markdown "it/dbzero/script/manual/fn_prima_chiave_estranea.md" %}
# ⚙️ Funzione `fn_prima_chiave_estranea`

```sql
CREATE FUNCTION fn_prima_chiave_estranea(p_dati jsonb, p_ammesse text[])
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_prima_chiave_estranea(p_dati jsonb, p_ammesse text[])
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- Scopo: la prima chiave (alfabetica) di p_dati fuori da
    --   p_ammesse, o NULL. Un elenco NULL non ammette niente.
    SELECT k
      FROM jsonb_object_keys(p_dati) AS k
     WHERE k <> ALL (COALESCE(p_ammesse, ARRAY[]::text[]))
     ORDER BY k
     LIMIT 1;
$function$

COMMENT ON FUNCTION script.fn_prima_chiave_estranea(p_dati jsonb, p_ammesse text[])
IS 'BB (2026-10-17): la prima chiave di p_dati, in ordine alfabetico, che non sta in p_ammesse; NULL se sono tutte ammesse. p_ammesse NULL = nessuna ammessa. p_dati deve essere un oggetto jsonb (un array o uno scalare fanno fallire jsonb_object_keys: lo controlla chi chiama). Pura e IMMUTABLE: il codice d''errore e il contesto li sceglie il verbo che rifiuta. Regola del 2: la usano config.fn_pannello_scrivi (passo 2, D-P3) e i verbi di creazione della 2b-1. Non la usa vendite.fn_create_contratto, che una chiave estranea la scarta. Brief: brief-db-processi-accensione-per-ambiente (2b-1).';
```

---
{% include-markdown "signature-core.md" %}
