# ⚙️ Funzione `fn_check_tipo_indirizzo_ruolo`

```sql
CREATE FUNCTION fn_check_tipo_indirizzo_ruolo(p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint, p_tipo_indirizzo_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_check_tipo_indirizzo_ruolo(p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint, p_tipo_indirizzo_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    c_chi        CONSTANT text := 'anagrafiche.fn_check_tipo_indirizzo_ruolo';
    v_tipo_ruolo anagrafiche.soggetti_ruoli.tipo_ruolo_id%TYPE;
    v_motivi     jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   I motivi per cui il tipo di indirizzo non si puo'
    --   scrivere sul ruolo salvato, sul ruolo stesso (istanza
    --   NULL) o su una sua istanza. Legge il contesto e lo
    --   passa alla meta' sui motivi; il giorno e'
    --   script.fn_data_operativa(), quello del guard.
    --
    -- Regole:
    --   - i tipi presenti si leggono sulla chiave dei due indici
    --     (istanza IS NOT DISTINCT FROM quella data): un tipo
    --     del ruolo non blocca la stessa istanza, e viceversa.
    -- =========================================================
    IF p_soggetto_ruolo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_soggetto_ruolo_id'),
            NULL::uuid,
            c_chi,
            'manca il ruolo');
    END IF;

    SELECT sr.tipo_ruolo_id
      INTO v_tipo_ruolo
      FROM anagrafiche.soggetti_ruoli sr
     WHERE sr.id = p_soggetto_ruolo_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_SOGGETTO_RUOLO_NON_TROVATO',
            jsonb_build_object('soggetto_ruolo_id', p_soggetto_ruolo_id),
            NULL::uuid,
            p_soggetto_ruolo_id::text);
    END IF;

    -- ⚠️ La delega si scrive come assegnazione (:=): e' la forma che
    --   dbops.vw_funzioni_check_codici sa leggere per legare i codici.
    v_motivi := anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto(
        v_tipo_ruolo,
        ARRAY(SELECT i.tipo_indirizzo_id
                FROM anagrafiche.indirizzi i
               WHERE i.soggetto_ruolo_id = p_soggetto_ruolo_id
                 AND i.istanza_utility_id IS NOT DISTINCT FROM p_istanza_utility_id),
        p_tipo_indirizzo_id,
        script.fn_data_operativa(),
        p_soggetto_ruolo_id);

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_check_tipo_indirizzo_ruolo(p_soggetto_ruolo_id bigint, p_istanza_utility_id bigint, p_tipo_indirizzo_id integer)
IS 'I motivi per cui il tipo di indirizzo non si puo'' scrivere sul ruolo salvato, sul ruolo stesso (istanza NULL) o su una sua istanza: legge il tipo di ruolo e i tipi che la chiave (ruolo, istanza) ha gia'' (la chiave di uq_indirizzi_ruolo_tipo_no_istanza e uq_indirizzi_ruolo_istanza_tipo) e li passa a anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto, col giorno di script.fn_data_operativa(). Array ordinato di motivi, [] se ammesso: il tipo gia'' presente (E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE), poi il tipo che il tipo di ruolo non ammette (E_TIPO_INDIRIZZO_NON_PERMESSO). Ruolo mancante E_SCRIPT_CHIAMATA_NON_VALIDA, inesistente E_SOGGETTO_RUOLO_NON_TROVATO. SECURITY INVOKER. La chiama anagrafiche.fn_crea_indirizzo_ruolo, che solleva il primo motivo prima di scrivere. Gemella di anagrafiche.fn_check_tipo_indirizzo_soggetto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
