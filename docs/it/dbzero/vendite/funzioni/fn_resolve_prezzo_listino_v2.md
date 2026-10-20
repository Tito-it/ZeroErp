{% include-markdown "it/dbzero/vendite/manual/fn_resolve_prezzo_listino_v2.md" %}
# ⚙️ Funzione `fn_resolve_prezzo_listino_v2`

```sql
CREATE FUNCTION fn_resolve_prezzo_listino_v2(p_articolo_id uuid, p_uom_id bigint, p_data_riferimento date, p_ba_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_classe_utenza_id integer, p_articolo_padre_contesto uuid, p_listino_versione_id_preferito bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resolve_prezzo_listino_v2(p_articolo_id uuid, p_uom_id bigint, p_data_riferimento date, p_ba_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_classe_utenza_id integer DEFAULT NULL::integer, p_articolo_padre_contesto uuid DEFAULT NULL::uuid, p_listino_versione_id_preferito bigint DEFAULT NULL::bigint)
 RETURNS TABLE(prezzo_finale numeric, prezzo_base_snapshot numeric, tipo_variazione_applicata character varying, valore_variazione_applicata numeric, origine character varying, listino_id bigint, listino_versione_id bigint, listino_riga_id bigint, contratto_id bigint, promo_id bigint, categoria_cliente_listino_id bigint, categoria_cliente_id_snapshot smallint, classe_utenza_id_snapshot integer, tipo_eccezione vendite.tipo_eccezione_contratto)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: guscio storico del resolver prezzi. Delega TUTTA la
--   risoluzione a fn_resolve_prezzo_listino_v2_esito e converte
--   l'esito in eccezione, che e' il contratto che i chiamanti
--   esistenti si aspettano da sempre.
--   La logica di risoluzione NON sta piu' qui: sta nel nucleo, in
--   un posto solo. Chi vuole modificarla va li'.
DECLARE
    v_esito record;
BEGIN
    SELECT * INTO v_esito
      FROM vendite.fn_resolve_prezzo_listino_v2_esito(
               p_articolo_id,
               p_uom_id,
               p_data_riferimento,
               p_ba_id,
               p_utility_id,
               p_emittente_soggetto_ruolo_id,
               p_classe_utenza_id,
               p_articolo_padre_contesto,
               p_listino_versione_id_preferito
           );

    -- Il nucleo ritorna SEMPRE una riga: se INTO non trova nulla
    -- e' successo qualcosa che non deve passare in silenzio.
    -- ⚠️ Guard necessario perche' SELECT INTO senza righe non
    --   solleva: azzera le variabili e prosegue, e qui
    --   proseguire vorrebbe dire restituire un prezzo NULL come
    --   se fosse un prezzo risolto.
    -- ⚠️ Codice DEDICATO, non piu' E_PARAMETRO_INVALIDO come nella
    --   prima stesura (20260819-08): qui nessun parametro e'
    --   invalido, e' un'invariante interna rotta, e l'operatore
    --   non puo' nemmeno provocarla. Il rubinetto degli
    --   accumulatori (B-7) ha bocciato l'uso precedente in CI —
    --   E_PARAMETRO_INVALIDO acquistava la famiglia NOT_FOUND —
    --   e aveva ragione: un codice che copre condizioni sempre
    --   piu' diverse smette di dire qualcosa a chi lo legge.
    --
    --   ⚠️ E il commento sta QUI e non fra gli argomenti della
    --   chiamata: infilato li' in mezzo, il classificatore non
    --   riesce piu' ad agganciare il codice alla guardia e il
    --   punto sparisce dal presidio — verde per sottrazione.
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'fn_resolve_prezzo_listino_v2',
            'E_VENDITE_PRICING_ESITO_ASSENTE',
            jsonb_build_object(
                'motivo',      'il nucleo _esito non ha restituito righe',
                'articolo_id', p_articolo_id,
                'ba_id',       p_ba_id
            ),
            NULL::uuid,
            'fn_resolve_prezzo_listino_v2_esito non ha restituito righe'
        );
    END IF;

    -- Esito valorizzato: si solleva col codice, il contesto e i
    -- valori che il nucleo ha preparato. Identico a com'era
    -- quando il raise stava dentro al corpo.
    IF v_esito.esito_codice IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'fn_resolve_prezzo_listino_v2',
            v_esito.esito_codice,
            v_esito.esito_context,
            NULL::uuid,
            VARIADIC v_esito.esito_valori
        );
    END IF;

    -- Risolto: proiezione delle 14 colonne storiche. Le tre
    -- colonne di esito restano nel nucleo e non escono di qui.
    prezzo_finale                 := v_esito.prezzo_finale;
    prezzo_base_snapshot          := v_esito.prezzo_base_snapshot;
    tipo_variazione_applicata     := v_esito.tipo_variazione_applicata;
    valore_variazione_applicata   := v_esito.valore_variazione_applicata;
    origine                       := v_esito.origine;
    listino_id                    := v_esito.listino_id;
    listino_versione_id           := v_esito.listino_versione_id;
    listino_riga_id               := v_esito.listino_riga_id;
    contratto_id                  := v_esito.contratto_id;
    promo_id                      := v_esito.promo_id;
    categoria_cliente_listino_id  := v_esito.categoria_cliente_listino_id;
    categoria_cliente_id_snapshot := v_esito.categoria_cliente_id_snapshot;
    classe_utenza_id_snapshot     := v_esito.classe_utenza_id_snapshot;
    tipo_eccezione                := v_esito.tipo_eccezione;

    RETURN NEXT;
END
$function$

COMMENT ON FUNCTION vendite.fn_resolve_prezzo_listino_v2(p_articolo_id uuid, p_uom_id bigint, p_data_riferimento date, p_ba_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_classe_utenza_id integer, p_articolo_padre_contesto uuid, p_listino_versione_id_preferito bigint)
IS 'GUSCIO del resolver prezzi v5 — 9 param, firma e RETURNS invariati dal 20260520-01. Dal 20260819-08 non contiene piu'' la logica di risoluzione: delega a vendite.fn_resolve_prezzo_listino_v2_esito (il NUCLEO) e converte l''esito in eccezione via script.fn_log_and_raise_error. Per i chiamanti non cambia nulla — stesso prezzo, stesso codice, stessa riga di log — ed e'' voluto: ordini, preventivi, contratti e offerte DEVONO continuare a rifiutare il prezzo non risolvibile. Chi ha bisogno della risoluzione NON obbligatoria (il DDT) chiama il nucleo. ⚠️ Modifiche alla risoluzione vanno fatte nel NUCLEO, non qui: qui si romperebbe l''unicita'' del corpo, che e'' la ragione per cui le due funzioni esistono. Brief: brief-ddt-righe-senza-prezzo §9 slice A.';
```

</div>

---
{% include-markdown "signature-core.md" %}
