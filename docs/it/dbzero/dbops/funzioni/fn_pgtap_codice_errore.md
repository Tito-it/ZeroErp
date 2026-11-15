{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_codice_errore.md" %}
# ⚙️ Funzione `fn_pgtap_codice_errore`

```sql
CREATE FUNCTION fn_pgtap_codice_errore(p_sql text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_codice_errore(p_sql text)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
-- Scopo: eseguire un'istruzione in un pgTAP e dire CHE COSA l'ha
--   rifiutata, per asserirlo con is(). Solo per i pgTAP.
-- Uso:
--   SELECT is(dbops.fn_pgtap_codice_errore($$SELECT schema.fn_verbo(…)$$),
--             'E_CODICE_ATTESO', 'descrizione');
--   SELECT is(dbops.fn_pgtap_codice_errore($$…$$), NULL, 'passa');
DECLARE
    -- valori della diagnostica, nessuna colonna li rispecchia
    v_sqlstate text;
    v_vincolo  text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_sqlstate = RETURNED_SQLSTATE,
                            v_vincolo  = CONSTRAINT_NAME;
    -- Il codice di dominio prima di tutto: la sua lettura sta in un
    -- posto solo. Poi il nome del vincolo, poi lo SQLSTATE.
    RETURN COALESCE(script.fn_codice_dominio(v_sqlstate, v_vincolo),
                    NULLIF(v_vincolo, ''),
                    v_sqlstate);
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_codice_errore(p_sql text)
IS 'Fixture pgTAP (building block): esegue p_sql e rende che cosa l''ha rifiutata, da asserire con is(). In ordine: NULL se l''istruzione passa; il codice di dominio se l''errore viene da script.fn_log_and_raise_error (letto da script.fn_codice_dominio); il nome del vincolo per un CHECK, UNIQUE o FK violato; altrimenti lo SQLSTATE. Un errore inatteso non interrompe il file: torna come valore e l''is() lo mostra. Le scritture di un''istruzione rifiutata si annullano col blocco EXCEPTION; quelle di un''istruzione che passa restano nella transazione del test. Solo per i pgTAP.';
```

</div>

---
{% include-markdown "signature-core.md" %}
