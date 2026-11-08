{% include-markdown "it/dbzero/vendite/manual/fn_genera_pratica_da_preventivo.md" %}
# ⚙️ Funzione `fn_genera_pratica_da_preventivo`

```sql
CREATE FUNCTION fn_genera_pratica_da_preventivo(p_preventivo_id bigint, p_tipo_prestazione_id integer, p_priorita_id integer, p_descrizione text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_genera_pratica_da_preventivo(p_preventivo_id bigint, p_tipo_prestazione_id integer, p_priorita_id integer DEFAULT NULL::integer, p_descrizione text DEFAULT NULL::text)
 RETURNS TABLE(pratica_id bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_billing_id     vendite.preventivi.billing_account_id%TYPE;
    v_istanza_id     vendite.preventivi.istanza_utility_id%TYPE;
    v_emittente_id   anagrafiche.emittenti_fiscali.id%TYPE;
    v_soggetto_id    anagrafiche.soggetti_ruoli.soggetto_id%TYPE;
    v_soggetto_ruolo anagrafiche.billing_account.soggetto_ruolo_id%TYPE;
    v_prov_tipo_id   pratiche.pratiche_sorgenti.sorgente_tipo_id%TYPE;
    v_prov_id        pratiche.pratiche_sorgenti.sorgente_id%TYPE;
    v_prov_uid       pratiche.pratiche_sorgenti.sorgente_uid%TYPE;
    v_pratica_id     pratiche.pratiche.id%TYPE;
BEGIN
    -- Contesto dal preventivo (esistenza + BA + istanza).
    SELECT p.billing_account_id, p.istanza_utility_id
      INTO v_billing_id, v_istanza_id
      FROM vendite.preventivi p
     WHERE p.id = p_preventivo_id;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_genera_pratica_da_preventivo',
            'E_PREV_NOT_FOUND',
            jsonb_build_object('preventivo_id', p_preventivo_id),
            NULL::uuid, VARIADIC ARRAY[p_preventivo_id::text]);
    END IF;

    -- Emittente (PK) + soggetto/ruolo dal billing account.
    v_emittente_id := anagrafiche.fn_get_emittente_fiscale_pk(v_billing_id);
    SELECT sr.soggetto_id, ba.soggetto_ruolo_id
      INTO v_soggetto_id, v_soggetto_ruolo
      FROM anagrafiche.billing_account ba
      JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
     WHERE ba.id = v_billing_id;

    -- La provenienza del link ROOT dal BB che scrive: il tipo PREVENTIVO e la
    -- chiave del suo key_selector. Prima della pratica, cosi' un tipo assente o
    -- spento ferma tutto subito (E_SORG_CONF, da script.fn_sorgente_chiave).
    SELECT p.sorgente_tipo_id, p.sorgente_id, p.sorgente_uid
      INTO v_prov_tipo_id, v_prov_id, v_prov_uid
      FROM script.fn_sorgente_provenienza('PREVENTIVO', p_preventivo_id::text) p;

    -- 1) Crea la pratica (figlia condivisa).
    --    Il BA del preventivo e' il cliente di cui parla la pratica
    --    (D-9): la sorgente glielo passa.
    v_pratica_id := pratiche.fn_crea_pratica(
        p_emittente_fiscale_id := v_emittente_id,
        p_tipo_prestazione_id  := p_tipo_prestazione_id,
        p_soggetto_id          := v_soggetto_id,
        p_soggetto_ruolo_id    := v_soggetto_ruolo,
        p_istanza_utility_id   := v_istanza_id,
        p_priorita_id          := p_priorita_id,
        p_descrizione          := p_descrizione,
        p_billing_account_id   := v_billing_id
    );

    -- 2) Link ROOT preventivo -> pratica.
    INSERT INTO pratiche.pratiche_sorgenti (
        pratica_id, sorgente_tipo_id, sorgente_id, sorgente_uid, ruolo_link
    ) VALUES (
        v_pratica_id, v_prov_tipo_id, v_prov_id, v_prov_uid, 'ROOT'
    );

    RETURN QUERY SELECT v_pratica_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_genera_pratica_da_preventivo(p_preventivo_id bigint, p_tipo_prestazione_id integer, p_priorita_id integer, p_descrizione text)
IS 'Funzione madre atomica: crea la pratica (con la figlia pratiche.fn_crea_pratica) e il link ROOT preventivo -> pratica in un''unica istruzione, o tutto o niente. La pratica nasce col billing account del preventivo: il cliente di cui parla. Il link porta la provenienza del preventivo dal BB che scrive (script.fn_sorgente_provenienza: tipo PREVENTIVO e la chiave del suo key_selector, in sorgente_uid), calcolata prima di creare la pratica. Il controllo dello stato ACCETTATO e'' un pre-check del service. Solleva E_PREV_NOT_FOUND su un preventivo che non c''e'' (o non visibile) e gli errori del BB (E_SORG_CONF su un tipo assente o spento). SECURITY INVOKER. Ritorna pratica_id.';
```

</div>

---
{% include-markdown "signature-core.md" %}
