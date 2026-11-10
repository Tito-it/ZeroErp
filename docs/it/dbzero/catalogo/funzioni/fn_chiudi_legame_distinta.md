{% include-markdown "it/dbzero/catalogo/manual/fn_chiudi_legame_distinta.md" %}
# ⚙️ Funzione `fn_chiudi_legame_distinta`

```sql
CREATE FUNCTION fn_chiudi_legame_distinta(p_legame_id uuid, p_valido_al date, p_prezzi_confermati integer)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_chiudi_legame_distinta(p_legame_id uuid, p_valido_al date, p_prezzi_confermati integer DEFAULT NULL::integer)
 RETURNS TABLE(legame_id uuid, valido_al_prima date, valido_al_dopo date, prezzi_chiusi integer, prezzi_tolti integer)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
#variable_conflict use_column
DECLARE
    v_utente     config.user_override_azioni.auth_user_id%TYPE;
    v_prima      catalogo.articoli_componenti.valido_al%TYPE;
    v_prodotto   catalogo.articoli_componenti.prodotto_id%TYPE;
    v_kit        catalogo.articoli.codice%TYPE;
    v_componente catalogo.articoli.codice%TYPE;
    -- Conteggi di righe: nessuna colonna dietro.
    v_prezzi     integer;
    v_versioni   integer;
    v_chiusi     integer := 0;
    v_tolti      integer := 0;
BEGIN
    -- =========================================================
    -- Scopo: chiudere il legame p_legame_id alla data p_valido_al
    --   insieme ai suoi prezzi bundle che vanno oltre, col permesso
    --   e la conferma. p_prezzi_confermati e' un CONTEGGIO: tipo
    --   nudo. Vedi l'intestazione del changeSet.
    -- Ritorna: il legame, la fine di prima e di adesso, i prezzi
    --   chiusi e quelli tolti.
    -- =========================================================
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    -- 1. Parametri e permesso sul catalogo.
    IF p_legame_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo', 'catalogo.fn_chiudi_legame_distinta', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_legame_id'),
            NULL::uuid,
            'il legame di distinta da chiudere');
    END IF;
    IF p_valido_al IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo', 'catalogo.fn_chiudi_legame_distinta', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_valido_al', 'campo', 'valido_al'),
            NULL::uuid,
            'la data di fine del legame');
    END IF;

    PERFORM script.fn_guard_livello(v_utente, 'catalogo', 'articolo', 'TUTTO');

    -- 2. Il legame e i suoi prezzi, fermi fino alla fine.
    SELECT ac.valido_al, ac.prodotto_id
      INTO v_prima, v_prodotto
      FROM catalogo.articoli_componenti ac
     WHERE ac.id = p_legame_id
       FOR UPDATE;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo', 'catalogo.fn_chiudi_legame_distinta', 'E_BOM_LEGAME_NOT_FOUND',
            jsonb_build_object('legame_id', p_legame_id),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    PERFORM 1
       FROM vendite.listini_righe_componenti lrc
      WHERE lrc.articolo_componente_id = p_legame_id
        FOR UPDATE;

    -- 3. Prima cio' che vieta.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'catalogo', 'catalogo.fn_chiudi_legame_distinta',
        script.fn_check_legame_distinta_chiudibile(p_legame_id, p_valido_al),
        'valido_al',
        NULL::uuid,
        jsonb_build_object('legame_id', p_legame_id));

    -- 4. I prezzi da chiudere o togliere: permesso sui listini e conferma.
    SELECT count(*)::integer,
           count(DISTINCT r.listino_versione_id)::integer
      INTO v_prezzi, v_versioni
      FROM vendite.fn_prezzi_legame_oltre_la_fine(p_legame_id, p_valido_al) r
     WHERE r.esito IN ('CHIUDE', 'TOGLIE');

    IF v_prezzi > 0 THEN
        PERFORM script.fn_guard_livello(v_utente, 'vendite', 'listino', 'TUTTO');

        IF p_prezzi_confermati IS DISTINCT FROM v_prezzi THEN
            SELECT p.codice, c.codice
              INTO v_kit, v_componente
              FROM catalogo.articoli_componenti ac
              JOIN catalogo.articoli p ON p.id = ac.prodotto_id
              JOIN catalogo.articoli c ON c.id = ac.componente_id
             WHERE ac.id = p_legame_id;

            PERFORM script.fn_log_and_raise_error(
                'catalogo', 'catalogo.fn_chiudi_legame_distinta', 'E_BOM_CHIUSURA_CON_PREZZI',
                jsonb_build_object(
                    'campo',              'valido_al',
                    'legame_id',          p_legame_id,
                    'valido_al',          p_valido_al,
                    'prezzi',             v_prezzi,
                    'versioni',           v_versioni,
                    'prezzi_confermati',  p_prezzi_confermati,
                    'bersaglio', jsonb_build_array(
                        jsonb_build_object('tipo', 'ARTICOLO', 'id', v_prodotto::text))),
                NULL::uuid,
                v_componente,
                v_kit,
                v_prezzi::text,
                v_versioni::text);
        END IF;

        -- 5. I prezzi, con la porta aperta per questo legame.
        PERFORM set_config('zeroerp.legame_distinta_chiudi', p_legame_id::text, true);

        UPDATE vendite.listini_righe_componenti lrc
           SET valido_al = p_valido_al
         WHERE lrc.id IN (SELECT r.riga_id
                            FROM vendite.fn_prezzi_legame_oltre_la_fine(p_legame_id, p_valido_al) r
                           WHERE r.esito = 'CHIUDE');
        GET DIAGNOSTICS v_chiusi = ROW_COUNT;

        DELETE FROM vendite.listini_righe_componenti lrc
         WHERE lrc.id IN (SELECT r.riga_id
                            FROM vendite.fn_prezzi_legame_oltre_la_fine(p_legame_id, p_valido_al) r
                           WHERE r.esito = 'TOGLIE');
        GET DIAGNOSTICS v_tolti = ROW_COUNT;

        PERFORM set_config('zeroerp.legame_distinta_chiudi', '', true);
    END IF;

    -- 6. Il legame. I guard della distinta parlano come sempre.
    UPDATE catalogo.articoli_componenti ac
       SET valido_al = p_valido_al
     WHERE ac.id = p_legame_id;

    RETURN QUERY SELECT p_legame_id, v_prima, p_valido_al, v_chiusi, v_tolti;
END;
$function$

COMMENT ON FUNCTION catalogo.fn_chiudi_legame_distinta(p_legame_id uuid, p_valido_al date, p_prezzi_confermati integer)
IS 'VERBO «Chiudi» di un legame di distinta (catalogo.articoli_componenti) insieme ai suoi prezzi bundle: il prezzo sta dentro il periodo del legame (FK temporale fk_listrighe_comp_articoli_comp_temporal), e chiudendo il legame i prezzi che vanno oltre la fine (vendite.fn_prezzi_legame_oltre_la_fine) si chiudono alla stessa data (esito CHIUDE) o, se cominciano dopo in una versione in bozza, si tolgono (TOGLIE). Prezzo, IVA e inizio restano quelli; la versione e le altre righe non si toccano. Ordine: parametri (E_PARAMETRO_INVALIDO); permesso sul catalogo (script.fn_guard_livello su catalogo.articolo, livello TUTTO; E_PERMESSO_NEGATO); il legame (E_BOM_LEGAME_NOT_FOUND) e i suoi prezzi FOR UPDATE; prima cio'' che vieta, il primo motivo di script.fn_check_legame_distinta_chiudibile sul campo valido_al (E_BOM_CHIUSURA_PREZZI_ALTRE_AZIENDE, E_BOM_CHIUSURA_PRIMA_DEI_PREZZI); se ci sono prezzi da chiudere o togliere, il permesso sui listini (vendite.listino, TUTTO) e la conferma: p_prezzi_confermati e'' il numero di prezzi che chi conferma ha visto, e se non e'' quello di adesso -> E_BOM_CHIUSURA_CON_PREZZI (l''avviso, coi numeri). Poi i prezzi, con la porta della GUC transazionale zeroerp.legame_distinta_chiudi = id del legame (la onora vendite.trgfn_listini_righe_comp_guard_immutabilita_v5 col proprietario della tabella, anche fuori dalla bozza, per la sola fine), e infine valido_al del legame, coi guard della distinta (catalogo.trgfn_articoli_componenti_block_modifica_struttura: E_BOM_LEGAME_CHIUSO, E_BOM_CHIUSURA_RETROATTIVA). Senza prezzi da toccare non serve il diritto sui listini, e la conferma non si chiede. Ritorna il legame, la fine di prima e di adesso, i prezzi chiusi e quelli tolti. SECURITY DEFINER con search_path bloccato; EXECUTE solo all''applicazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
