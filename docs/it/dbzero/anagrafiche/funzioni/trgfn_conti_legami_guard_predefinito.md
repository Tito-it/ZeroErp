# ⚙️ Funzione `trgfn_conti_legami_guard_predefinito`

```sql
CREATE FUNCTION trgfn_conti_legami_guard_predefinito()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_conti_legami_guard_predefinito()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_chi       CONSTANT dbops.error_log.function_name%TYPE := 'anagrafiche.trgfn_conti_legami_guard_predefinito';
    v_periodo   daterange;
    v_altro_id  anagrafiche.soggetti_conti_bancari.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: il predefinito di un legame di conto
    --   (anagrafiche.soggetti_conti_bancari,
    --   anagrafiche.soggetti_ruoli_conti_bancari).
    --   1) non e' bloccato: il blocco toglie il legame dalla
    --      scelta, il predefinito e' la scelta;
    --   2) non si sovrappone nel tempo a un altro predefinito
    --      dello stesso possessore e uso (date comprese, NULL =
    --      senza limite). Possessore: il soggetto; il ruolo e
    --      l'istanza (NULL = tutto il ruolo, confronto IS NOT
    --      DISTINCT FROM).
    -- Montata BEFORE INSERT OR UPDATE, WHEN (NEW.predefinito).
    -- I vincoli chk_*_predefinito_non_bloccato e
    --   ex_*_predefinito_*periodo dicono la stessa cosa e restano
    --   come rete: qui il codice di dominio e il campo.
    -- I valori giudicati sono quelli di NEW, mai riletti per id.
    -- =========================================================
    IF NEW.bloccato THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_CONTO_PREDEFINITO_BLOCCATO',
            jsonb_build_object('campo', 'bloccato',
                               'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'id', NEW.id),
            NEW.tx_id,
            NEW.uso::text);
    END IF;

    v_periodo := daterange(NEW.valido_dal, NEW.valido_al, '[]');

    IF TG_TABLE_NAME = 'soggetti_conti_bancari' THEN
        SELECT l.id INTO v_altro_id
          FROM anagrafiche.soggetti_conti_bancari l
         WHERE l.soggetto_id = NEW.soggetto_id
           AND l.uso = NEW.uso
           AND l.predefinito
           AND l.id IS DISTINCT FROM NEW.id
           AND daterange(l.valido_dal, l.valido_al, '[]') && v_periodo
         ORDER BY l.id
         LIMIT 1;
    ELSIF TG_TABLE_NAME = 'soggetti_ruoli_conti_bancari' THEN
        SELECT l.id INTO v_altro_id
          FROM anagrafiche.soggetti_ruoli_conti_bancari l
         WHERE l.soggetto_ruolo_id = NEW.soggetto_ruolo_id
           AND l.istanza_utility_id IS NOT DISTINCT FROM NEW.istanza_utility_id
           AND l.uso = NEW.uso
           AND l.predefinito
           AND l.id IS DISTINCT FROM NEW.id
           AND daterange(l.valido_dal, l.valido_al, '[]') && v_periodo
         ORDER BY l.id
         LIMIT 1;
    ELSE
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_DBOPS_CHIAMATA_NON_VALIDA',
            jsonb_build_object('campo', 'tabella',
                               'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME),
            NULL::uuid,
            v_chi, format('montata su %s.%s, che non e'' un legame di conto',
                          TG_TABLE_SCHEMA, TG_TABLE_NAME));
    END IF;

    IF v_altro_id IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_CONTO_PREDEFINITO_SOVRAPPOSTO',
            jsonb_build_object('campo', 'predefinito',
                               'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'id', NEW.id,
                               'altro_legame_id', v_altro_id,
                               'uso', NEW.uso),
            NEW.tx_id,
            NEW.uso::text);
    END IF;

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_conti_legami_guard_predefinito()
IS 'BEFORE INSERT OR UPDATE, WHEN (NEW.predefinito), sui due legami dei conti (anagrafiche.soggetti_conti_bancari, anagrafiche.soggetti_ruoli_conti_bancari). Un legame predefinito non e'' bloccato (E_CONTO_PREDEFINITO_BLOCCATO, campo bloccato) e non si sovrappone nel tempo a un altro predefinito dello stesso possessore e uso (E_CONTO_PREDEFINITO_SOVRAPPOSTO, campo predefinito): possessore e'' il soggetto, oppure il ruolo con la sua istanza (NULL = tutto il ruolo). Periodo: valido_dal e valido_al comprese, NULL = senza limite. I vincoli chk_*_predefinito_non_bloccato ed ex_*_predefinito_*periodo restano come rete per le scritture concorrenti. Su un''altra tabella solleva E_DBOPS_CHIAMATA_NON_VALIDA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
