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
    v_uid            vendite.preventivi.uid%TYPE;
    v_billing_id     vendite.preventivi.billing_account_id%TYPE;
    v_istanza_id     vendite.preventivi.istanza_utility_id%TYPE;
    v_emittente_id   anagrafiche.emittenti_fiscali.id%TYPE;
    v_soggetto_id    anagrafiche.soggetti_ruoli.soggetto_id%TYPE;
    v_soggetto_ruolo anagrafiche.billing_account.soggetto_ruolo_id%TYPE;
    v_sorgente_tipo  config.sorgenti.id%TYPE;
    v_pratica_id     pratiche.pratiche.id%TYPE;
BEGIN
    -- Contesto dal preventivo (esistenza + uid + BA + istanza).
    SELECT p.uid, p.billing_account_id, p.istanza_utility_id
      INTO v_uid, v_billing_id, v_istanza_id
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

    -- Tipo sorgente PREVENTIVO (attivo imposto dal trigger sul link).
    SELECT s.id INTO v_sorgente_tipo
      FROM config.sorgenti s
     WHERE s.codice_interno = 'PREVENTIVO';
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_genera_pratica_da_preventivo',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'config.sorgenti.PREVENTIVO'),
            NULL::uuid,
            VARIADIC ARRAY['tipo sorgente PREVENTIVO (config.sorgenti)']);
    END IF;

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
        pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link
    ) VALUES (
        v_pratica_id, v_sorgente_tipo, v_uid::text, 'ROOT'
    );

    RETURN QUERY SELECT v_pratica_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_genera_pratica_da_preventivo(p_preventivo_id bigint, p_tipo_prestazione_id integer, p_priorita_id integer, p_descrizione text)
IS 'Funzione madre atomica: crea la pratica (via figlia pratiche.fn_crea_pratica) e il link ROOT preventivo->pratica in un''unica statement (o tutto o rollback). SECURITY INVOKER. Ritorna pratica_id. Il check stato ACCETTATO resta pre-check del service. Piano: analisi-fix-transazioni Classe A #3. rev 2026-10-08 (20261008-68): la pratica nasce col BA del preventivo (la sorgente e'' il cliente di cui parla); via il ramo «preventivo senza BA», irraggiungibile dal 20261008-52. Brief: brief-db-istanza-nasce-col-ba (R-8, D-9).';
```

</div>

---
{% include-markdown "signature-core.md" %}
