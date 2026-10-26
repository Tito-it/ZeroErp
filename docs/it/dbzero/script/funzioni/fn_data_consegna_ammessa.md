{% include-markdown "it/dbzero/script/manual/fn_data_consegna_ammessa.md" %}
# ⚙️ Funzione `fn_data_consegna_ammessa`

```sql
CREATE FUNCTION fn_data_consegna_ammessa(p_data_consegna date, p_data_documento date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_data_consegna_ammessa(p_data_consegna date, p_data_documento date)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    -- ⚠️ Tipi nudi DICHIARATI: la funzione serve tre colonne di
    --   consegna su due tabelle e la data di due testate; non c'e'
    --   UNA colonna da ancorare.
    SELECT p_data_consegna IS NULL
        OR p_data_documento IS NULL
        OR p_data_consegna >= p_data_documento;
$function$

COMMENT ON FUNCTION script.fn_data_consegna_ammessa(p_data_consegna date, p_data_documento date)
IS 'Regola (2026-10-13, collaudo date di consegna): una data di consegna e'' ammessa se non e'' anteriore alla data del documento. TRUE anche con la data di consegna NULL («nessuna data») e con la data del documento NULL (nessun riferimento: le testate l''hanno NOT NULL, il ramo e'' per chi chiama senza documento). Stessa data del documento: ammessa. Sede unica: la leggono script.fn_doc_date_consegna_anteriori (il lettore dei guard di riga e di testata) e le copie di righe vendite.fn_push_preventivo_a_ordine e vendite.fn_crea_revisione_preventivo, che con una data non ammessa la azzerano (decisione di Tid, 2026-10-13).';
```

</div>

---
{% include-markdown "signature-core.md" %}
