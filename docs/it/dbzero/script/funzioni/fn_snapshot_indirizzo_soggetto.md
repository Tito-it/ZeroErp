{% include-markdown "it/dbzero/script/manual/fn_snapshot_indirizzo_soggetto.md" %}
# ⚙️ Funzione `fn_snapshot_indirizzo_soggetto`

```sql
CREATE FUNCTION fn_snapshot_indirizzo_soggetto(p_soggetto_id uuid, p_tipo_indirizzo_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_snapshot_indirizzo_soggetto(p_soggetto_id uuid, p_tipo_indirizzo_id integer)
 RETURNS TABLE(snapshot jsonb)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: comporre lo snapshot canonico di un indirizzo del layer
--        SOGGETTO (anagrafiche.indirizzi_soggetti), che non ha
--        riga in anagrafiche.indirizzi e quindi non e'
--        raggiungibile da script.fn_snapshot_indirizzo.
-- Uso:   fallback della catena di risoluzione, dopo il layer RUOLO
--        (script.fn_resolve_indirizzo_documento).
DECLARE
    v_r   record;
    v_via text;
BEGIN
    -- Guard input. Il soggetto e' un uuid: si controlla solo il
    -- NULL; il tipo e' un id numerico e vale la regola generale
    -- (errore se NULL o <= 0, mai normalizzazione silenziosa).
    IF p_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_snapshot_indirizzo_soggetto', 'E_VALIDAZIONE',
            jsonb_build_object('p_soggetto_id', p_soggetto_id),
            NULL::uuid, 'p_soggetto_id obbligatorio');
    END IF;

    IF p_tipo_indirizzo_id IS NULL OR p_tipo_indirizzo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_snapshot_indirizzo_soggetto', 'E_VALIDAZIONE',
            jsonb_build_object('p_tipo_indirizzo_id', p_tipo_indirizzo_id),
            NULL::uuid, 'p_tipo_indirizzo_id deve essere > 0');
    END IF;

    -- Risoluzione: la coppia (soggetto, tipo) e' UNIQUE
    -- (uq_indirizzi_soggetti_soggetto_tipo), quindi la riga e'
    -- una sola per costruzione — nessun LIMIT 1 da giustificare.
    SELECT r.is_normalizzato,
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
      FROM anagrafiche.vw_indirizzi_resolved_soggetto r
      LEFT JOIN anagrafiche.soggetti s ON s.id = r.soggetto_id
     WHERE r.soggetto_id = p_soggetto_id
       AND r.tipo_indirizzo_id = p_tipo_indirizzo_id;

    -- Assenza = zero righe, NON errore: e' il caso normale di un
    -- fallback. Differenza deliberata dalla gemella, che invece
    -- riceve un id che deve esistere e solleva se non lo trova.
    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Componente "via": normalizzato -> via_norm + civico;
    -- libero -> indirizzo_libero. Identica alla gemella.
    v_via := CASE
               WHEN v_r.is_normalizzato
                 THEN NULLIF(trim(both ' ' FROM
                        COALESCE(v_r.via_norm::text, '') || ' ' ||
                        COALESCE(v_r.civico::text, '')), '')
               ELSE v_r.indirizzo_libero
             END;

    -- Shape canonico (Q1), identico alla gemella — btrim incluso:
    -- la parita' vale anche per le correzioni, altrimenti lo
    -- stesso indirizzo cambierebbe forma a seconda del layer.
    snapshot := jsonb_strip_nulls(jsonb_build_object(
        'intestazione', NULLIF(btrim(v_r.ragione_sociale_completa::text), ''),
        'via',          NULLIF(btrim(v_via), ''),
        'cap',          NULLIF(btrim(v_r.cap::text), ''),
        'citta',        NULLIF(btrim(v_r.comune_descrizione::text), ''),
        'prov',         NULLIF(btrim(v_r.provincia_sigla::text), ''),
        'stato',        NULLIF(btrim(v_r.stato_iso2::text), ''),
        'display',      NULLIF(btrim(v_r.indirizzo_display::text), '')
    ));

    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION script.fn_snapshot_indirizzo_soggetto(p_soggetto_id uuid, p_tipo_indirizzo_id integer)
IS 'Gemella di script.fn_snapshot_indirizzo per il layer SOGGETTO: compone lo STESSO shape canonico (intestazione, via, cap, citta, prov, stato, display) a partire da (soggetto_id, tipo_indirizzo_id). Esiste perche'' gli indirizzi di soggetto stanno in anagrafiche.indirizzi_soggetti e non hanno riga in anagrafiche.indirizzi: non c''e'' un p_indirizzo_id da passare alla gemella, e la colonna indirizzo_id della vista soggetto e'' la PK di un''ALTRA tabella — passarla alla gemella restituirebbe in silenzio l''indirizzo di ruolo con lo stesso numero. Prende la coppia (soggetto, tipo) proprio per rendere impossibile quello scambio. Assenza = zero righe e non errore: e'' il fallback della catena e il chiamante deve poter scendere di livello. Determinismo garantito da uq_indirizzi_soggetti_soggetto_tipo. Ogni valore passa da NULLIF(btrim(...)) come nella gemella (fix 2026-07-31: prov da character(10) congelava il riempimento a spazi). STABLE. piano-db-satelliti-fattura D-O, Fase 2.0-a.';
```

</div>

---
{% include-markdown "signature-core.md" %}
