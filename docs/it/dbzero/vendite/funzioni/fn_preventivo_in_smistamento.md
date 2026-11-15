{% include-markdown "it/dbzero/vendite/manual/fn_preventivo_in_smistamento.md" %}
# ⚙️ Funzione `fn_preventivo_in_smistamento`

```sql
CREATE FUNCTION fn_preventivo_in_smistamento(p_accettazione boolean, p_stato character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_preventivo_in_smistamento(p_accettazione boolean, p_stato character varying)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
AS $function$
-- Scopo: «il preventivo in questo stato e' uno che si smista?».
--   Dallo stato di accettazione (un significato: la colonna) e da EVASO (la
--   destinazione del processo: il codice, come la nomina la matrice).
--   Due IS TRUE: un argomento NULL da' falso, mai NULL.
  SELECT (p_accettazione IS TRUE) OR (p_stato = 'EVASO') IS TRUE;
$function$

COMMENT ON FUNCTION vendite.fn_preventivo_in_smistamento(p_accettazione boolean, p_stato character varying)
IS 'Il preventivo in questo stato e'' uno che si smista? Vero dallo stato di accettazione (la colonna accettazione di config.stati_doc_preventivi, passata in p_accettazione) e da EVASO, la destinazione del processo di smistamento, che si nomina col codice (p_stato, il codice_interno); falso altrove, e falso anche con un argomento NULL (mai NULL). Riceve i valori dello stato, non l''id: non legge tabelle. Sede unica della risposta: la leggono vendite.fn_preventivo_proietta_stato_smistamento, da cui la proiezione parte, e script.fn_available_actions_preventivo, che ne fa in_smistamento.';
```

</div>

---
{% include-markdown "signature-core.md" %}
