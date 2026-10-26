{% include-markdown "it/dbzero/vendite/manual/fn_componi_numero_documento.md" %}
# ⚙️ Funzione `fn_componi_numero_documento`

```sql
CREATE FUNCTION fn_componi_numero_documento(p_prefisso character varying, p_corpo text, p_progressivo bigint, p_lunghezza integer, p_suffisso character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_componi_numero_documento(p_prefisso character varying, p_corpo text, p_progressivo bigint, p_lunghezza integer, p_suffisso character varying)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- ⭐ Scritta sui VALORI e non sugli id: si prova in una riga
    --   di SQL, senza costruire un documento, e resta inlineabile.
    -- ⚠️ Il progressivo NULL da' NULL: chi compone senza numero
    --   sta sbagliando, e un numero a meta' sarebbe peggio di
    --   nessun numero.
    SELECT CASE WHEN p_progressivo IS NULL THEN NULL ELSE
           COALESCE(p_prefisso, '')
        || COALESCE(p_corpo, '')
        || lpad(p_progressivo::text, COALESCE(p_lunghezza, 7), '0')
        || COALESCE(p_suffisso, '')
    END;
$function$

COMMENT ON FUNCTION vendite.fn_componi_numero_documento(p_prefisso character varying, p_corpo text, p_progressivo bigint, p_lunghezza integer, p_suffisso character varying)
IS 'Compone il numero di un documento: prefisso || corpo || progressivo con le cifre di riempimento || suffisso. ⭐ PURA e IMMUTABLE, scritta sui VALORI e non sugli id: si verifica in una riga di SQL senza costruire un documento, si inlinea, e ci si potrebbe appoggiare un indice. E'' il pattern che il progetto usa gia'' per le funzioni di composizione. ⭐ Il `corpo` e'' la parte che varia fra le famiglie: VUOTO per DDT, ordini e resi, `<sigla>-<anno>-` per la commessa, il cui codice porta quei due pezzi dentro la stringa perche'' e'' l''unico dei cinque la cui IDENTITA'' e'' la stringa nuda. ⚠️ Un parametro che serve a un chiamante solo di solito e'' un cattivo segno; qui no, e la ragione e'' che dal 2026-08-31 anche la commessa ha prefisso E suffisso dal registro (decisione di Tid) — con quelli condivisi da tutti e quattro la forma e'' la STESSA, e il parametro non generalizza un caso: nomina la parte che varia. ⚠️ Il SEPARATORE non e'' piu'' un campo a se'': se serve si scrive dentro il prefisso (''CMM-''), e cosi'' sparisce il caso speciale della commessa, dove un prefisso vuoto lasciava un separatore ORFANO in testa — `-ACME-2026-000000001`, che spezzato sul trattino dava un primo pezzo vuoto. ⚠️ Progressivo NULL -> NULL: un numero a meta'' sarebbe peggio di nessun numero. Piano: brief-db-prefisso-sul-registro-e-allineamento-contatori, P-3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
