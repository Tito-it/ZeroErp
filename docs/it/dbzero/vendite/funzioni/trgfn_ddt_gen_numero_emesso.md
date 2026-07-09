# ⚙️ Funzione `trgfn_ddt_gen_numero_emesso`

```sql
CREATE FUNCTION trgfn_ddt_gen_numero_emesso()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_gen_numero_emesso()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: assegna ddt.numero alla transizione a EMESSO (C6), fuori dal
--   framework sistema_codici (che numera all'INSERT). Mirror spirito
--   fatture: numerazione bespoke a emissione.
DECLARE
    v_stato  config.stati_doc_ddt.codice_interno%TYPE;
    v_prefix config.sistema_codici.prefisso%TYPE;
    v_sep    config.sistema_codici.separatore%TYPE;
    v_len    config.sistema_codici.lunghezza_numero%TYPE;
    v_seq    bigint;
BEGIN
    -- Gia' numerato -> no-op (immutabilita' da trgfn_v_ddt_protect_num).
    IF NEW.numero IS NOT NULL AND btrim(NEW.numero::text) <> '' THEN
        RETURN NEW;
    END IF;

    -- Numero solo a EMESSO (no buchi da bozze DRAFT scartate).
    SELECT sdd.codice_interno INTO v_stato
      FROM config.stati_doc_ddt sdd
     WHERE sdd.id = NEW.stato_doc_ddt_id;
    IF v_stato IS DISTINCT FROM 'EMESSO' THEN
        RETURN NEW;
    END IF;

    -- Formato data-driven dalla riga sistema_codici (usa_sequenza=false,
    -- ma prefisso/separatore/lunghezza restano validi).
    SELECT prefisso, separatore, lunghezza_numero
      INTO v_prefix, v_sep, v_len
      FROM config.sistema_codici
     WHERE codice_interno = 'ddt';

    v_seq := nextval('vendite.ddt_numero_seq');
    NEW.numero := COALESCE(v_prefix, 'DDT')
               || COALESCE(v_sep, '')
               || lpad(v_seq::text, COALESCE(v_len, 7), '0');
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_gen_numero_emesso()
IS 'Assegna ddt.numero alla transizione a EMESSO (C6), fuori dal framework sistema_codici (mirror fatture). Formato da config.sistema_codici riga ddt (usa_sequenza=false) + sequenza vendite.ddt_numero_seq. Immutabilita'': trgfn_v_ddt_protect_num. rev 2026-07-09.';
```

---
{% include-markdown "signature-core.md" %}
