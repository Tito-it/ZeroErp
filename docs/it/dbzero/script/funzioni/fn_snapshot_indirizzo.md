{% include-markdown "it/dbzero/script/manual/fn_snapshot_indirizzo.md" %}
# ⚙️ Funzione `fn_snapshot_indirizzo`

```sql
CREATE FUNCTION fn_snapshot_indirizzo(p_indirizzo_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_snapshot_indirizzo(p_indirizzo_id bigint)
 RETURNS TABLE(snapshot jsonb, origine_soggetto_ruolo_id bigint)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_r        record;
    v_via      text;
BEGIN
    -- Guard input (ID: errore se NULL o <= 0).
    IF p_indirizzo_id IS NULL OR p_indirizzo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_snapshot_indirizzo', 'E_VALIDAZIONE',
            jsonb_build_object('p_indirizzo_id', p_indirizzo_id),
            NULL::uuid, 'p_indirizzo_id deve essere > 0');
    END IF;

    -- Risoluzione dell'indirizzo di ruolo + intestazione soggetto.
    SELECT r.soggetto_ruolo_id,
           r.soggetto_id,
           r.is_normalizzato,
           r.via_norm,
           r.civico,
           r.cap,
           r.comune_descrizione,
           r.provincia_sigla,
           r.stato_iso2,
           r.indirizzo_display,
           r.indirizzo_libero,
           s.ragione_sociale_completa
      INTO v_r
      FROM anagrafiche.vw_indirizzi_resolved_ruolo r
      LEFT JOIN anagrafiche.soggetti s ON s.id = r.soggetto_id
     WHERE r.indirizzo_id = p_indirizzo_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_snapshot_indirizzo',
            'E_INDIRIZZO_SNAPSHOT_NOT_FOUND',
            jsonb_build_object('indirizzo_id', p_indirizzo_id),
            NULL::uuid, p_indirizzo_id::text);
    END IF;

    -- Componente "via": normalizzato -> via_norm + civico;
    -- libero -> indirizzo_libero.
    v_via := CASE
               WHEN v_r.is_normalizzato
                 THEN NULLIF(trim(both ' ' FROM
                        COALESCE(v_r.via_norm::text, '') || ' ' ||
                        COALESCE(v_r.civico::text, '')), '')
               ELSE v_r.indirizzo_libero
             END;

    -- Shape canonico (Q1): etichette umane + display.
    -- jsonb_strip_nulls: le chiavi nulle non compaiono.
    -- ⚠️ NULLIF(btrim(...)) su OGNI valore: `prov` arriva da un
    -- character(10) e `stato` da un character(n), quindi senza
    -- btrim lo snapshot congelerebbe "AV        " per sempre.
    -- Applicato a tutti i campi, non solo ai due colpevoli: cosi'
    -- la domanda «questo e' a larghezza fissa?» non si ripresenta.
    snapshot := jsonb_strip_nulls(jsonb_build_object(
        'intestazione', NULLIF(btrim(v_r.ragione_sociale_completa::text), ''),
        'via',          NULLIF(btrim(v_via), ''),
        'cap',          NULLIF(btrim(v_r.cap::text), ''),
        'citta',        NULLIF(btrim(v_r.comune_descrizione::text), ''),
        'prov',         NULLIF(btrim(v_r.provincia_sigla::text), ''),
        'stato',        NULLIF(btrim(v_r.stato_iso2::text), ''),
        'display',      NULLIF(btrim(v_r.indirizzo_display::text), '')
    ));

    origine_soggetto_ruolo_id := v_r.soggetto_ruolo_id;

    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION script.fn_snapshot_indirizzo(p_indirizzo_id bigint)
IS 'Compone lo snapshot canonico (intestazione, via, cap, citta, prov, stato, display) di un indirizzo del layer RUOLO, a partire dal suo id. Ogni valore passa da NULLIF(btrim(...)): `prov` arriva da config.province.sigla che e'' un character(10) e `stato` da config.stati.codice_iso2 — senza il btrim lo snapshot congelerebbe il riempimento a spazi per sempre, e la Provincia della FatturaPA e'' di due caratteri (fix 2026-07-31, segnalazione BE su giro reale). Le chiavi vuote diventano NULL e spariscono con jsonb_strip_nulls. Gemella: script.fn_snapshot_indirizzo_soggetto, che deve restare identica nello shape.';
```

</div>

---
{% include-markdown "signature-core.md" %}
