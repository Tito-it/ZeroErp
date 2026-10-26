# ⚙️ Funzione `fn_get_emittente_distinta`

```sql
CREATE FUNCTION fn_get_emittente_distinta(p_emittente_soggetto_ruolo_id bigint, p_ente_incasso_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.fn_get_emittente_distinta(p_emittente_soggetto_ruolo_id bigint, p_ente_incasso_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ef_dato      anagrafiche.emittenti_fiscali.id%TYPE;
    v_ef_canale    anagrafiche.emittenti_fiscali.id%TYPE;
    v_ef_sessione  anagrafiche.emittenti_fiscali.id%TYPE;
    v_sr           pagamenti.vendite_contabili.emittente_soggetto_ruolo_id%TYPE;
    v_user_id      anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_sigla_dato   anagrafiche.emittenti_fiscali.codice%TYPE;
    v_sigla_canale anagrafiche.emittenti_fiscali.codice%TYPE;
    -- NUDA di proposito: e' la frase per l'operatore, composta da
    -- un COALESCE fra il codice del canale (se visibile) e il suo id.
    v_nome_canale  text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire DI CHI E' una distinta contabile, in una sede sola,
    --   e tornare il soggetto_ruolo dell'emittente. Solleva
    --   quando non puo' rispondere senza inventare.
    --
    --   Livelli, in ordine (D4 del brief):
    --     0) dato ma non e' un emittente      -> TECNICO
    --     1) dato, coerente col canale        -> il dato
    --     2) solo il canale                   -> il suo emittente
    --     3) l'operatore in sessione          -> il suo emittente
    --     4) niente                           -> rifiuto parlante
    --   ⛔ Nessun «default dell'installazione».
    --
    -- ⭐ E' una funzione e non solo un trigger perche' la
    --   chiave di riuso di fn_get_or_create_vendite_contabile
    --   vuole l'emittente PRIMA dell'INSERT (vedi intestazione
    --   del changeSet 20260915-22).
    -- ⚠️ SECURITY INVOKER: la lettura del canale passa dal
    --   risolutore, che e' DEFINER — enti_incasso ha la RLS e
    --   da qui «non lo vedo» diventerebbe «non esiste».
    -- =========================================================

    -- ── Il canale, se c'e': SOLO attraverso il risolutore ───
    IF p_ente_incasso_id IS NOT NULL THEN
        v_ef_canale := script.fn_resolve_emittente_fiscale_id(
                           'ente_incasso', p_ente_incasso_id);

        -- ⚠️ Un canale che non porta a un emittente (inesistente,
        --   o con il conto intestato a un soggetto-ruolo che non e'
        --   un emittente) e' una configurazione rotta: NON si cade
        --   sulla sessione. Attribuire il denaro di un canale a chi
        --   agisce e' esattamente l'attribuzione che D4 vieta.
        IF v_ef_canale IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'pagamenti.fn_get_emittente_distinta',
                'E_CONFIG_MANCANTE',
                jsonb_build_object(
                    'detail', 'il canale di incasso non porta a nessun emittente fiscale',
                    'ente_incasso_id', p_ente_incasso_id),
                NULL::uuid,
                concat('il canale di incasso ', p_ente_incasso_id::text,
                       ' non porta a nessun emittente fiscale ',
                       '(canale inesistente, o conto di incasso non intestato a un emittente)'));
        END IF;
    END IF;

    -- ── Livelli 0 e 1: l'emittente DATO ──────────────────────
    IF p_emittente_soggetto_ruolo_id IS NOT NULL THEN
        v_ef_dato := script.fn_resolve_emittente_fiscale_id(
                         'soggetto_ruolo', p_emittente_soggetto_ruolo_id);

        -- 0) La FK verso soggetti_ruoli non garantisce che sia un
        --    emittente: un SR qualsiasi lo produce solo un chiamante
        --    rotto. TECNICO, e il messaggio nomina il parametro di
        --    proposito: il suo lettore e' chi ha scritto la chiamata.
        IF v_ef_dato IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'pagamenti.fn_get_emittente_distinta',
                'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
                jsonb_build_object(
                    'detail', 'emittente_soggetto_ruolo_id non e'' un emittente fiscale',
                    'emittente_soggetto_ruolo_id', p_emittente_soggetto_ruolo_id),
                NULL::uuid,
                'pagamenti.fn_get_emittente_distinta',
                'emittente_soggetto_ruolo_id (non e'' il soggetto-ruolo di un emittente fiscale)');
        END IF;

        -- 1) Se c'e' anche il canale, deve essere il suo. Il campo da
        --    accendere e' il canale: si corregge quello, o si cambia
        --    emittente — lo dice la soluzione a catalogo.
        IF v_ef_canale IS NOT NULL AND v_ef_canale <> v_ef_dato THEN
            SELECT ef.codice INTO v_sigla_dato
              FROM anagrafiche.emittenti_fiscali ef WHERE ef.id = v_ef_dato;
            SELECT ef.codice INTO v_sigla_canale
              FROM anagrafiche.emittenti_fiscali ef WHERE ef.id = v_ef_canale;
            -- ⚠️ enti_incasso ha la RLS: da qui il codice puo' non
            --   vedersi. La frase non deve dipendere dalla visibilita'.
            SELECT COALESCE(
                       (SELECT e.codice FROM pagamenti.enti_incasso e
                         WHERE e.id = p_ente_incasso_id),
                       p_ente_incasso_id::text)
              INTO v_nome_canale;

            PERFORM script.fn_log_and_raise_error(
                'database', 'pagamenti.fn_get_emittente_distinta',
                'E_CONTABILE_CANALE_DI_ALTRO_EMITTENTE',
                jsonb_build_object(
                    'detail', 'il canale di incasso appartiene a un altro emittente',
                    'campo', 'ente_incasso_id',
                    'ente_incasso_id', p_ente_incasso_id,
                    'emittente_fiscale_id_canale', v_ef_canale,
                    'emittente_fiscale_id_indicato', v_ef_dato),
                NULL::uuid,
                v_nome_canale, v_sigla_canale::text, v_sigla_dato::text);
        END IF;

        RETURN p_emittente_soggetto_ruolo_id;
    END IF;

    -- ── Livello 2: il canale dice di chi e' il denaro ────────
    IF v_ef_canale IS NOT NULL THEN
        SELECT ef.soggetto_ruolo_id INTO v_sr
          FROM anagrafiche.emittenti_fiscali ef WHERE ef.id = v_ef_canale;
        RETURN v_sr;
    END IF;

    -- ── Livello 3: la riserva e' di chi agisce (D13) ─────────
    -- ⚠️ fn_resolve_emittente_for_user SOLLEVA su utente NULL:
    --   si chiama solo con un utente in sessione.
    v_user_id := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    IF v_user_id IS NOT NULL THEN
        v_ef_sessione := script.fn_resolve_emittente_for_user(v_user_id);
        IF v_ef_sessione IS NOT NULL THEN
            SELECT ef.soggetto_ruolo_id INTO v_sr
              FROM anagrafiche.emittenti_fiscali ef WHERE ef.id = v_ef_sessione;
            RETURN v_sr;
        END IF;
    END IF;

    -- ── Livello 4: nessuno puo' rispondere — si CHIEDE ───────
    -- E' il super admin / admin globale «tutti gli emittenti» che
    -- apre una manuale senza canale: il form deve fargli scegliere.
    -- Messaggio senza segnaposti: variadico vuoto ESPLICITO.
    PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.fn_get_emittente_distinta',
        'E_CONTABILE_EMITTENTE_OBBLIGATORIO',
        jsonb_build_object(
            'detail', 'nessun emittente: ne'' dato, ne'' dal canale, ne'' dalla sessione',
            'campo', 'emittente_fiscale_id',
            'auth_user_id', v_user_id),
        NULL::uuid,
        VARIADIC ARRAY[]::text[]);

    RETURN NULL;  -- irraggiungibile: il raise sopra non torna
END;
$function$

COMMENT ON FUNCTION pagamenti.fn_get_emittente_distinta(p_emittente_soggetto_ruolo_id bigint, p_ente_incasso_id bigint)
IS 'La SEDE UNICA che dice DI CHI E'' una distinta contabile (D4 del brief distinta-numerata-sul-registro) e torna il soggetto_ruolo dell''emittente. Quattro livelli, in ordine: (0) l''emittente dato non e'' un emittente fiscale -> E_PAGAMENTI_CHIAMATA_NON_VALIDA, TECNICO, perche'' la FK verso soggetti_ruoli non lo ferma e lo produce solo un chiamante rotto; (1) dato, e se c''e'' anche il canale deve essere il suo, altrimenti E_CONTABILE_CANALE_DI_ALTRO_EMITTENTE (DATO_ERRATO, campo ente_incasso_id); (2) solo il canale -> il suo emittente, per la catena canale -> conto -> soggetto_ruolo -> emittente (il conto ha un solo padrone); un canale che non porta a un emittente e'' E_CONFIG_MANCANTE e NON si cade sulla sessione; (3) l''operatore in sessione, via script.fn_resolve_emittente_for_user (che legge prima app.current_emittente_id: un super admin con un emittente attivo scelto risolve qui); (4) niente -> E_CONTABILE_EMITTENTE_OBBLIGATORIO (DATO_ERRATO, campo emittente_fiscale_id). ⛔ NESSUN livello «default dell''installazione»: dichiarare di un emittente il denaro di un altro e'' l''attribuzione che la numerazione per emittente esiste per impedire. ⭐ E'' una FUNZIONE e non solo un trigger perche'' la chiave di riuso di fn_get_or_create_vendite_contabile deve includere l''emittente PRIMA dell''INSERT; il trigger pagamenti.trgfn_vendite_contabili_emittente la applica a ogni scrittura, la madre la chiama per cercare. Due copie della risoluzione sarebbero la seconda sede che D4 esiste per impedire. ⚠️ SECURITY INVOKER: il canale si legge SOLO dal risolutore script.fn_resolve_emittente_fiscale_id, che e'' DEFINER — enti_incasso ha la row security, e da qui «canale di un altro» diventerebbe «canale inesistente». Rev 2026-09-15.';
```

</div>

---
{% include-markdown "signature-core.md" %}
