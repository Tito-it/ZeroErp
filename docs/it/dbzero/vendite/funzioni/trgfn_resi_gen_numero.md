{% include-markdown "it/dbzero/vendite/manual/trgfn_resi_gen_numero.md" %}
# ⚙️ Funzione `trgfn_resi_gen_numero`

```sql
CREATE FUNCTION trgfn_resi_gen_numero()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_resi_gen_numero()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: assegna resi.numero alla transizione a CONFERMATO,
--   fuori dal framework sistema_codici (mirror ddt/fatture).
DECLARE
    v_stato  config.stati_doc_reso.codice_interno%TYPE;
    v_prefix config.sistema_codici.prefisso%TYPE;
    v_sep    config.sistema_codici.separatore%TYPE;
    v_len    config.sistema_codici.lunghezza_numero%TYPE;
    v_seq    bigint;
BEGIN
    -- Gia' numerato -> no-op (immutabilita' da trgfn_v_resi_protect_num).
    IF NEW.numero IS NOT NULL AND btrim(NEW.numero::text) <> '' THEN
        RETURN NEW;
    END IF;

    -- Numero solo a CONFERMATO (no buchi da bozze DRAFT scartate).
    SELECT sdr.codice_interno INTO v_stato
      FROM config.stati_doc_reso sdr
     WHERE sdr.id = NEW.stato_doc_reso_id;
    IF v_stato IS DISTINCT FROM 'CONFERMATO' THEN
        RETURN NEW;
    END IF;

    -- Formato data-driven dalla riga sistema_codici 'reso'
    -- (usa_sequenza=false; default se la riga non esiste ancora).
    SELECT prefisso, separatore, lunghezza_numero
      INTO v_prefix, v_sep, v_len
      FROM config.sistema_codici
     WHERE codice_interno = 'reso';

    v_seq := nextval('vendite.resi_numero_seq');
    NEW.numero := COALESCE(v_prefix, 'RESO')
               || COALESCE(v_sep, '')
               || lpad(v_seq::text, COALESCE(v_len, 7), '0');
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_resi_gen_numero()
IS 'Assegna resi.numero alla transizione a CONFERMATO, fuori dal framework sistema_codici (mirror trgfn_ddt_gen_numero_emesso). Formato da config.sistema_codici riga reso + sequenza vendite.resi_numero_seq. Immutabilita: trgfn_v_resi_protect_num. rev 2026-07-13.';
```

---
{% include-markdown "signature-core.md" %}
