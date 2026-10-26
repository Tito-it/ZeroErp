{% include-markdown "it/dbzero/script/manual/fn_check_prezzi_autorizzati.md" %}
# ⚙️ Funzione `fn_check_prezzi_autorizzati`

```sql
CREATE FUNCTION fn_check_prezzi_autorizzati(p_testata regclass, p_documento_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_prezzi_autorizzati(p_testata regclass, p_documento_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi per cui un documento di vendita
--   contiene prezzi che nessuno ha autorizzato — in attesa di
--   approvazione (PENDING) o rifiutati (REJECTED) — su righe o
--   componenti BoM ATTIVI. Funzione PURA (fn_check_*): non
--   solleva sul contenuto, non scrive.
--   Il predicato sta qui; QUANDO chiederlo lo decide il
--   documento. Consumatori: fn_check_preventivo_emettibile,
--   trgfn_preventivi_guard_transizione (ACCETTATO),
--   fn_available_actions_preventivo, trgfn_contratti_guard_
--   transizione_stato, fn_available_actions_contratto,
--   trgfn_offerte_commerciali_guard_transizione,
--   fn_available_actions_offerta, fn_check_ordine_confermabile,
--   fn_check_ddt_emittibile.
--   Brief: brief-db-preventivi-congelamento-pricing.
-- Ritorna: [] se nessun prezzo e' da autorizzare; altrimenti
--   array ORDINATO di {codice, reason, reason_key, dettaglio,
--   valori}: prima il PENDING, poi il REJECTED.
DECLARE
    -- ⛔ Nudo: e' un elenco di {stato, riga_id, componente_id}
    --   costruito qui, non una colonna.
    v_prezzi  jsonb;
    v_motivi  jsonb := '[]'::jsonb;
    -- Conteggi: nessuna colonna di cui siano il riflesso.
    v_n_pend  integer;
    v_n_rif   integer;
    -- ⛔ Nudi: sono elementi di v_prezzi.
    v_primo_pend jsonb;
    v_primo_rif  jsonb;
    -- ⚠️ Array del tipo ESPLICITO: `colonna%TYPE[]` non esiste in
    --   PostgreSQL (linee-guida-sql §5b). E' l'enum della colonna
    --   stato_approvazione_prezzo, la stessa sulle otto tabelle.
    v_stati   config.stato_approvazione_prezzo[] :=
        ARRAY['PENDING', 'REJECTED']::config.stato_approvazione_prezzo[];
BEGIN
    IF p_documento_id IS NULL OR p_documento_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_prezzi_autorizzati', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'documento_id', 'valore', p_documento_id),
            NULL::uuid, 'documento_id obbligatorio (>0)');
    END IF;

    -- Una riga per prezzo da autorizzare. Ogni ramo porta le
    --   chiavi d'ordine del SUO documento, cosi' il primo della
    --   lista e' la prima riga a video: la riga prima dei suoi
    --   componenti, i componenti nel loro ordine.
    -- ⚠️ ORDER BY dentro l'aggregato: senza, quale riga finisca
    --   nel dettaglio dipende dal piano.
    IF p_testata = 'vendite.preventivi'::regclass THEN
        SELECT jsonb_agg(jsonb_build_object(
                   'stato', x.stato, 'riga_id', x.riga_id,
                   'componente_id', x.componente_id)
               ORDER BY x.k_riga NULLS LAST, x.riga_id,
                        x.k_comp NULLS FIRST, x.componente_id NULLS FIRST)
          INTO v_prezzi
          FROM (
            SELECT r.stato_approvazione_prezzo AS stato, r.id AS riga_id,
                   NULL::bigint AS componente_id,
                   r.ordine::integer AS k_riga, NULL::integer AS k_comp
              FROM vendite.preventivi_righe r
             WHERE r.preventivo_id = p_documento_id
               AND r.attivo IS TRUE
               AND r.stato_approvazione_prezzo = ANY (v_stati)
            UNION ALL
            SELECT c.stato_approvazione_prezzo, r.id, c.id,
                   r.ordine::integer, c.ordine::integer
              FROM vendite.preventivi_righe r
              JOIN vendite.preventivi_righe_componenti c
                ON c.riga_preventivo_id = r.id
             WHERE r.preventivo_id = p_documento_id
               AND r.attivo IS TRUE
               AND c.attivo IS TRUE
               AND c.stato_approvazione_prezzo = ANY (v_stati)
          ) x;

    ELSIF p_testata = 'vendite.contratti'::regclass THEN
        SELECT jsonb_agg(jsonb_build_object(
                   'stato', x.stato, 'riga_id', x.riga_id,
                   'componente_id', x.componente_id)
               ORDER BY x.k_riga NULLS LAST, x.riga_id,
                        x.k_comp NULLS FIRST, x.componente_id NULLS FIRST)
          INTO v_prezzi
          FROM (
            SELECT r.stato_approvazione_prezzo AS stato, r.id AS riga_id,
                   NULL::bigint AS componente_id,
                   r.ordine::integer AS k_riga, NULL::integer AS k_comp
              FROM vendite.contratti_righe r
             WHERE r.contratto_id = p_documento_id
               AND r.attivo IS TRUE
               AND r.stato_approvazione_prezzo = ANY (v_stati)
            UNION ALL
            SELECT c.stato_approvazione_prezzo, r.id, c.id,
                   r.ordine::integer, c.ordine::integer
              FROM vendite.contratti_righe r
              JOIN vendite.contratti_righe_componenti c
                ON c.riga_contratto_id = r.id
             WHERE r.contratto_id = p_documento_id
               AND r.attivo IS TRUE
               AND c.attivo IS TRUE
               AND c.stato_approvazione_prezzo = ANY (v_stati)
          ) x;

    ELSIF p_testata = 'vendite.offerte_commerciali'::regclass THEN
        -- Sull'offerta la «riga» con un prezzo e' l'ECCEZIONE.
        SELECT jsonb_agg(jsonb_build_object(
                   'stato', x.stato, 'riga_id', x.riga_id,
                   'componente_id', x.componente_id)
               ORDER BY x.k_riga NULLS LAST, x.riga_id,
                        x.k_comp NULLS FIRST, x.componente_id NULLS FIRST)
          INTO v_prezzi
          FROM (
            SELECT e.stato_approvazione_prezzo AS stato, e.id AS riga_id,
                   NULL::bigint AS componente_id,
                   e.ordine::integer AS k_riga, NULL::integer AS k_comp
              FROM vendite.offerte_commerciali_eccezioni e
             WHERE e.offerta_id = p_documento_id
               AND e.attivo IS TRUE
               AND e.stato_approvazione_prezzo = ANY (v_stati)
            UNION ALL
            SELECT c.stato_approvazione_prezzo, e.id, c.id,
                   e.ordine::integer, c.ordine::integer
              FROM vendite.offerte_commerciali_eccezioni e
              JOIN vendite.offerte_commerciali_eccezioni_componenti c
                ON c.eccezione_offerta_id = e.id
             WHERE e.offerta_id = p_documento_id
               AND e.attivo IS TRUE
               AND c.attivo IS TRUE
               AND c.stato_approvazione_prezzo = ANY (v_stati)
          ) x;

    ELSIF p_testata = 'vendite.ordini'::regclass THEN
        -- Sull'ordine lo stato di approvazione vive solo sui
        --   componenti: la riga non lo porta.
        SELECT jsonb_agg(jsonb_build_object(
                   'stato', c.stato_approvazione_prezzo, 'riga_id', r.id,
                   'componente_id', c.id)
               ORDER BY r.riga_nr, r.id, c.ordine, c.id)
          INTO v_prezzi
          FROM vendite.ordini_righe r
          JOIN vendite.ordini_righe_componenti c
            ON c.riga_ordine_id = r.id
         WHERE r.ordine_id = p_documento_id
           AND r.attivo IS TRUE
           AND c.attivo IS TRUE
           AND c.stato_approvazione_prezzo = ANY (v_stati);

    ELSIF p_testata = 'vendite.ddt'::regclass THEN
        -- Come l'ordine: solo i componenti.
        SELECT jsonb_agg(jsonb_build_object(
                   'stato', c.stato_approvazione_prezzo, 'riga_id', r.id,
                   'componente_id', c.id)
               ORDER BY r.riga_nr, r.id, c.ordine, c.id)
          INTO v_prezzi
          FROM vendite.ddt_righe r
          JOIN vendite.ddt_righe_componenti c
            ON c.riga_ddt_id = r.id
         WHERE r.ddt_id = p_documento_id
           AND r.attivo IS TRUE
           AND c.attivo IS TRUE
           AND c.stato_approvazione_prezzo = ANY (v_stati);

    ELSE
        -- ⛔ Un documento che questa funzione non conosce e' un
        --   chiamante sbagliato, non un «niente da dire»: un []
        --   qui farebbe passare tutto in silenzio.
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_prezzi_autorizzati', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'testata',
                               'valore', COALESCE(p_testata::text, 'NULL')),
            NULL::uuid, 'testata non gestita: ' || COALESCE(p_testata::text, 'NULL'));
    END IF;

    IF v_prezzi IS NULL THEN
        RETURN v_motivi;
    END IF;

    SELECT count(*) FILTER (WHERE p.elem ->> 'stato' = 'PENDING'),
           count(*) FILTER (WHERE p.elem ->> 'stato' = 'REJECTED'),
           (array_agg(p.elem ORDER BY p.ord)
                FILTER (WHERE p.elem ->> 'stato' = 'PENDING'))[1],
           (array_agg(p.elem ORDER BY p.ord)
                FILTER (WHERE p.elem ->> 'stato' = 'REJECTED'))[1]
      INTO v_n_pend, v_n_rif, v_primo_pend, v_primo_rif
      FROM jsonb_array_elements(v_prezzi) WITH ORDINALITY AS p(elem, ord);

    -- Un motivo per stato: prima il PENDING (si aspetta), poi il
    --   REJECTED (si corregge).
    -- ⭐ Nella frase va il CONTEGGIO: la riga precisa viaggia nel
    --   dettaglio, per chi diagnostica. Le tabelle non hanno
    --   tutte un numero di riga da mostrare (preventivi_righe e
    --   le eccezioni d'offerta non hanno riga_nr).
    -- ⚠️ Codice e reason_key LETTERALI, uno per motivo, e non in
    --   un CASE: dbops.vw_funzioni_check_codici e
    --   scripts/check_i18n_keys.py li riconoscono nella forma
    --   `'codice', 'E_…'` e `'reason_key', '…'`. Scritti in un
    --   CASE sarebbero invisibili, e una chiave assente dai
    --   locales passerebbe in silenzio.
    IF v_n_pend > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_DOC_PREZZO_PENDENTE',
            'reason',     'PREZZO_PENDENTE',
            'reason_key', 'common.azione_reason.prezzo_pendente',
            'dettaglio',  jsonb_build_object(
                              'n_prezzi',      v_n_pend,
                              'riga_id',       v_primo_pend -> 'riga_id',
                              'componente_id', v_primo_pend -> 'componente_id'),
            'valori',     jsonb_build_array(v_n_pend::text));
    END IF;

    IF v_n_rif > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_DOC_PREZZO_RIFIUTATO',
            'reason',     'PREZZO_RIFIUTATO',
            'reason_key', 'common.azione_reason.prezzo_rifiutato',
            'dettaglio',  jsonb_build_object(
                              'n_prezzi',      v_n_rif,
                              'riga_id',       v_primo_rif -> 'riga_id',
                              'componente_id', v_primo_rif -> 'componente_id'),
            'valori',     jsonb_build_array(v_n_rif::text));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_prezzi_autorizzati(p_testata regclass, p_documento_id bigint)
IS 'Building block: i motivi per cui un documento di vendita contiene prezzi che nessuno ha autorizzato — in attesa di approvazione (PENDING) o rifiutati (REJECTED) — su righe o componenti BoM ATTIVI. PURA: non solleva sul contenuto e non scrive. Ritorna [] oppure un array ordinato di {codice, reason, reason_key, dettaglio, valori}: prima E_DOC_PREZZO_PENDENTE, poi E_DOC_PREZZO_RIFIUTATO (entrambi CONFLITTO_STATO); nel dettaglio n_prezzi e la prima riga/componente, nei valori il conteggio. ⭐ Il documento si indica con la tabella di TESTATA (regclass): vendite.preventivi, vendite.contratti, vendite.offerte_commerciali (le righe con prezzo sono le eccezioni), vendite.ordini e vendite.ddt (solo i componenti portano lo stato). Un''altra tabella solleva E_PARAMETRO_INVALIDO: un [] farebbe passare tutto in silenzio. ⭐ Il predicato sta qui, la politica nel documento: QUANDO chiederlo (verso EMESSO/ACCETTATO, ATTIVO, EMESSA/ACCETTATA, CONFERMATO; il DDT solo se la causale vende) lo decidono le check e i guard di ciascun documento. ⚠️ Solo righe e componenti ATTIVI: i componenti si spengono invece di cancellarsi, e uno rifiutato e poi tolto bloccherebbe il documento per sempre. Prima di questa funzione la stessa domanda era scritta in cinque sedi che non dicevano la stessa cosa, e il REJECTED non lo guardava nessuna. Brief: brief-db-preventivi-congelamento-pricing (D-1, D-2, D-5, D-6).';
```

</div>

---
{% include-markdown "signature-core.md" %}
