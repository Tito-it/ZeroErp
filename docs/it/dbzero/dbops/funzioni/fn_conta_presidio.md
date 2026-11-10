{% include-markdown "it/dbzero/dbops/manual/fn_conta_presidio.md" %}
# ⚙️ Funzione `fn_conta_presidio`

```sql
CREATE FUNCTION fn_conta_presidio(p_vista text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_conta_presidio(p_vista text)
 RETURNS bigint
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Contare le righe che CHIEDONO UN INTERVENTO su una vista
    --   di presidio: la somma dei gruppi del conteggio per
    --   variante.
    --
    -- ⛔ Il perimetro, il rifiuto di una vista non a catalogo e
    --   il filtro di stato NON si scrivono qui: stanno in
    --   dbops.fn_conta_presidio_per_variante, e solo li'. Una
    --   seconda copia del filtro divergerebbe dalla prima.
    -- ⚠️ coalesce: un presidio con variante e nessuna riga non
    --   ha gruppi, e la somma di niente e' NULL, non zero.
    -- =========================================================
    RETURN (SELECT coalesce(sum(c.conteggio), 0)::bigint
              FROM dbops.fn_conta_presidio_per_variante(p_vista) c);
END
$function$

COMMENT ON FUNCTION dbops.fn_conta_presidio(p_vista text)
IS 'Conta le righe che CHIEDONO UN INTERVENTO su una vista di presidio dichiarata in dbops.presidi: la somma dei gruppi di dbops.fn_conta_presidio_per_variante, che e'' la sede unica del perimetro (una vista non a catalogo solleva E_PRESIDIO_NON_A_CATALOGO, non torna zero) e del filtro (colonna_stato, stato_atteso) letto dal catalogo. SECURITY INVOKER: non legge le viste da se''; l''attraversamento della row level security (viste security_invoker su tabelle protette, che da un percorso senza GUC tornerebbero zero per cecita'') lo fa la sede, DEFINER del proprietario. ⛔ Torna un bigint e mai le righe. ⚠️ La colonna dbops.presidi.perimetro dice un''altra cosa, cioe'' se il chiamante puo'' anche ELENCARE le righe.';
```

</div>

---
{% include-markdown "signature-core.md" %}
