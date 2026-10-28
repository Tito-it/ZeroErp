{% include-markdown "it/dbzero/anagrafiche/manual/fn_check_ba_coppia_emittente_omogenea.md" %}
# ⚙️ Funzione `fn_check_ba_coppia_emittente_omogenea`

```sql
CREATE FUNCTION fn_check_ba_coppia_emittente_omogenea(p_figlio_id bigint, p_padre_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_check_ba_coppia_emittente_omogenea(p_figlio_id bigint, p_padre_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ef_figlio anagrafiche.emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id%TYPE;
    v_ef_padre  anagrafiche.emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id%TYPE;
BEGIN
    -- Convenzione fn_check_*: boolean, nessun raise proprio.
    -- ⚠️ Puo' pero' PROPAGARE E_EMITTENTE_DEFAULT_MISSING dal
    --   risolutore: quello non e' un verdetto di dominio, e' un
    --   difetto di configurazione (nessun gestore globale), e
    --   mascherarlo qui lo renderebbe invisibile.

    -- Nessun padre = nessun albero = niente da presidiare.
    IF p_padre_id IS NULL THEN
        RETURN true;
    END IF;

    -- Auto-riferimento: gia' bloccato da E_PARENT_SELF, qui e'
    -- difensivo e non e' un albero misto.
    IF p_figlio_id = p_padre_id THEN
        RETURN true;
    END IF;

    v_ef_figlio := anagrafiche.fn_get_emittente_fiscale_id(p_figlio_id);
    v_ef_padre  := anagrafiche.fn_get_emittente_fiscale_id(p_padre_id);

    -- ⚠️ NULL = fail-closed, e NON `IS NOT DISTINCT FROM`.
    --   Il risolutore non torna mai NULL (solleva prima), ma se un
    --   giorno lo facesse, `NULL IS NOT DISTINCT FROM NULL` direbbe
    --   «omogeneo» — cioe' la stessa trappola del NULL nella
    --   chiave che P-3 ha appena chiuso, riaperta qui.
    IF v_ef_figlio IS NULL OR v_ef_padre IS NULL THEN
        RETURN false;
    END IF;

    RETURN v_ef_figlio = v_ef_padre;
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_check_ba_coppia_emittente_omogenea(p_figlio_id bigint, p_padre_id bigint)
IS 'Pure check (boolean, no raise): la coppia figlio/padre di billing_account appartiene allo STESSO emittente fiscale? L''emittente e'' quello RISOLTO da anagrafiche.fn_get_emittente_fiscale_id (mapping specifico oppure gestore globale) — la stessa funzione usata da vendite.fn_build_fattura_key, cosi'' «albero omogeneo» e «la fattura esce da un solo emittente» sono la stessa affermazione. Padre NULL -> true (nessun albero). Emittente non risolto -> false (fail-closed). Puo'' propagare E_EMITTENTE_DEFAULT_MISSING: e'' un difetto di configurazione, non un verdetto di dominio. Brief P-1 §3.5/§11.2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
