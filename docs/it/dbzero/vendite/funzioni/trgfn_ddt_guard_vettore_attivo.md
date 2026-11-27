{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_guard_vettore_attivo.md" %}
# ⚙️ Funzione `trgfn_ddt_guard_vettore_attivo`

```sql
CREATE FUNCTION trgfn_ddt_guard_vettore_attivo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_guard_vettore_attivo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_attivo  anagrafiche.vettori.attivo%TYPE;
    v_codice  anagrafiche.vettori.codice%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: la bolla che sceglie un vettore, nascendo o
    --   cambiandolo, lo vuole acceso.
    --   Montata BEFORE INSERT OR UPDATE OF vettore_soggetto_ruolo_id.
    --
    -- ⭐ Il vettore gia' scritto non si rigiudica: la bolla e'
    --   storia, e un vettore spento dopo resta su di lei.
    -- ⚠️ Un id che non e' un vettore lo rifiuta la FK: qui si
    --   esce, e la FK parla a fine istruzione.
    -- =========================================================
    IF NEW.vettore_soggetto_ruolo_id IS NULL THEN
        RETURN NEW;
    END IF;

    IF TG_OP = 'UPDATE'
       AND OLD.vettore_soggetto_ruolo_id IS NOT DISTINCT FROM NEW.vettore_soggetto_ruolo_id THEN
        RETURN NEW;
    END IF;

    SELECT v.attivo, v.codice
      INTO v_attivo, v_codice
      FROM anagrafiche.vettori v
     WHERE v.soggetto_ruolo_id = NEW.vettore_soggetto_ruolo_id;

    IF FOUND AND v_attivo IS NOT TRUE THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'vendite.trgfn_ddt_guard_vettore_attivo',
            'E_DDT_VETTORE_NON_ATTIVO',
            jsonb_build_object(
                'campo', 'vettore_soggetto_ruolo_id',
                'ddt_id', NEW.id,
                'vettore_soggetto_ruolo_id', NEW.vettore_soggetto_ruolo_id
            ),
            NULL::uuid,
            v_codice::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_guard_vettore_attivo()
IS 'Guard BEFORE INSERT OR UPDATE OF vettore_soggetto_ruolo_id di vendite.ddt: la bolla che nasce con un vettore, o lo cambia, lo vuole acceso (E_DDT_VETTORE_NON_ATTIVO). Il vettore gia'' scritto non si rigiudica: la bolla e'' storia, e un vettore spento dopo resta su di lei. Che sia un vettore lo dice la FK verso anagrafiche.vettori.';
```

</div>

---
{% include-markdown "signature-core.md" %}
