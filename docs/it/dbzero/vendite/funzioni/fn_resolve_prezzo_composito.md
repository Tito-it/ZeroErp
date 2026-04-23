{% include-markdown "it/dbzero/vendite/manual/fn_resolve_prezzo_composito.md" %}
# ⚙️ Funzione `fn_resolve_prezzo_composito`

```sql
CREATE FUNCTION fn_resolve_prezzo_composito(p_prodotto_id uuid, p_uom_id bigint, p_data_riferimento date, p_ba_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_classe_utenza_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resolve_prezzo_composito(p_prodotto_id uuid, p_uom_id bigint, p_data_riferimento date, p_ba_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_classe_utenza_id integer DEFAULT NULL::integer)
 RETURNS TABLE(componente_id uuid, uom_id bigint, prezzo_unitario numeric, iva_id bigint, descrizione_fattura character varying, esposto_in_fattura boolean, coeff_qta numeric)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- Flag "esiste almeno un componente con esposto=TRUE per questa BoM
    -- alla data di riferimento". Determina CASO A vs CASO B.
    v_has_esposti     boolean;

    -- Prezzo singolo del padre risolto da fn_resolve_prezzo_listino_v2
    -- nel CASO B1 (listino negoziato del padre presente).
    v_prezzo_padre    vendite.listini_righe.prezzo%TYPE;

    -- Accumulatore Sigma per il CASO B2 (somma pesata dei
    -- componenti quando il padre non ha riga listino propria).
    v_prezzo_totale   vendite.listini_righe.prezzo%TYPE := 0;

    -- Metadati del padre riutilizzati nei CASI B1/B2 (una sola riga
    -- ritornata che rappresenta il padre aggregato).
    v_articolo_iva_id catalogo.articoli.iva_id%TYPE;
    v_articolo_desc   catalogo.articoli.descrizione%TYPE;

    -- Record iteratori: v_rec per il loop sui componenti (tipo
    -- dipendente dalla SELECT interna, non tipizzabile); v_resolve
    -- per il risultato di fn_resolve_prezzo_listino_v2 (colonne
    -- dinamiche).
    v_rec             record;
    v_resolve         record;
BEGIN
    -- =========================================================
    -- Scopo (post 22-04-2026, DB-3 Sprint C):
    --   Resolver BoM ibrido pricing v5. N righe se composito
    --   ha componenti esposti (CASO A), 1 riga altrimenti
    --   (CASO B1 prezzo diretto, CASO B2 Sigma pesata).
    --   Espone anche coeff_qta per abilitare il calcolo
    --   quantita_componente = quantita_padre * coeff_qta
    --   lato BoMComponentExpander (DEC-3 §14.4.1).
    -- =========================================================

    -- Guard: p_prodotto_id obbligatorio. Gli altri ID vengono
    -- validati da fn_resolve_prezzo_listino_v2 a valle.
    IF p_prodotto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'fn_resolve_prezzo_composito',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_prodotto_id'),
            NULL::uuid,
            'p_prodotto_id obbligatorio'
        );
    END IF;

    -- Determina il caso: esiste almeno un componente con
    -- esposto_in_fattura=TRUE attivo alla data di riferimento?
    -- Se si', CASO A (N righe); altrimenti CASO B1/B2 (1 riga).
    SELECT EXISTS (
        SELECT 1
          FROM catalogo.articoli_componenti ac
         WHERE ac.prodotto_id            = p_prodotto_id
           AND ac.esposto_in_fattura     = TRUE
           AND COALESCE(ac.attivo, TRUE) = TRUE
           AND ac.valido_dal            <= p_data_riferimento
           AND (ac.valido_al IS NULL OR ac.valido_al >= p_data_riferimento)
    )
    INTO v_has_esposti;

    -- CASO A: almeno un componente esposto -> N righe, una per componente
    -- obbligatorio attivo. Il flag esposto e il coeff_qta vengono
    -- propagati dal BoM (coeff_qta aggiunto al SELECT post 22-04-2026).
    IF v_has_esposti THEN
        FOR v_rec IN
            SELECT ac.componente_id,
                   ac.esposto_in_fattura,
                   ac.coeff_qta,
                   a.uom_id      AS componente_uom_id,
                   a.iva_id      AS componente_iva_id,
                   a.descrizione AS componente_descrizione
              FROM catalogo.articoli_componenti ac
              JOIN catalogo.articoli a
                ON a.id = ac.componente_id
             WHERE ac.prodotto_id            = p_prodotto_id
               AND ac.obbligatorio           = TRUE
               AND COALESCE(ac.attivo, TRUE) = TRUE
               AND ac.valido_dal            <= p_data_riferimento
               AND (ac.valido_al IS NULL OR ac.valido_al >= p_data_riferimento)
        LOOP
            SELECT *
              INTO v_resolve
              FROM vendite.fn_resolve_prezzo_listino_v2(
                  v_rec.componente_id,
                  v_rec.componente_uom_id,
                  p_data_riferimento,
                  p_ba_id,
                  p_utility_id,
                  p_emittente_soggetto_ruolo_id,
                  p_classe_utenza_id
              );

            componente_id       := v_rec.componente_id;
            uom_id              := v_rec.componente_uom_id;
            prezzo_unitario     := v_resolve.prezzo_finale;
            iva_id              := v_rec.componente_iva_id;
            descrizione_fattura := v_rec.componente_descrizione;
            esposto_in_fattura  := v_rec.esposto_in_fattura;
            coeff_qta           := v_rec.coeff_qta;
            RETURN NEXT;
        END LOOP;

        RETURN;
    END IF;

    -- CASO B (no componenti esposti): serviranno i metadati
    -- del padre per la riga singola ritornata. Lookup lazy
    -- (saltato quando il CASO A ha gia' terminato).
    SELECT a.iva_id, a.descrizione
      INTO v_articolo_iva_id, v_articolo_desc
      FROM catalogo.articoli a
     WHERE a.id = p_prodotto_id;

    -- CASO B1: tentativo prezzo diretto sul composito. Se la
    -- riga listino non esiste, fn_resolve_prezzo_listino_v2
    -- raisa con SQLSTATE 'P0001' (via fn_log_and_raise_error);
    -- cattura ristretta -> fallback su CASO B2 (Sigma). Ogni
    -- altro SQLSTATE resta propagato al caller.
    BEGIN
        SELECT *
          INTO v_resolve
          FROM vendite.fn_resolve_prezzo_listino_v2(
              p_prodotto_id,
              p_uom_id,
              p_data_riferimento,
              p_ba_id,
              p_utility_id,
              p_emittente_soggetto_ruolo_id,
              p_classe_utenza_id
          );
        v_prezzo_padre := v_resolve.prezzo_finale;
    EXCEPTION
        WHEN SQLSTATE 'P0001' THEN
            v_prezzo_padre := NULL;
    END;

    -- CASO B1: esiste riga listino sul padre -> 1 riga con prezzo padre.
    -- coeff_qta = 1: il padre rappresenta se' stesso, moltiplicatore neutro.
    IF v_prezzo_padre IS NOT NULL THEN
        componente_id       := p_prodotto_id;
        uom_id              := p_uom_id;
        prezzo_unitario     := v_prezzo_padre;
        iva_id              := v_articolo_iva_id;
        descrizione_fattura := v_articolo_desc;
        esposto_in_fattura  := FALSE;
        coeff_qta           := 1::numeric;
        RETURN NEXT;
        RETURN;
    END IF;

    -- CASO B2: Sigma pesata dei componenti obbligatori attivi.
    -- Ritorno 1 riga rappresentando il padre aggregato; coeff_qta = 1
    -- (il moltiplicatore per i singoli componenti e' gia' stato
    -- applicato internamente nel calcolo v_prezzo_totale).
    FOR v_rec IN
        SELECT ac.componente_id,
               ac.coeff_qta,
               a.uom_id AS componente_uom_id
          FROM catalogo.articoli_componenti ac
          JOIN catalogo.articoli a
            ON a.id = ac.componente_id
         WHERE ac.prodotto_id            = p_prodotto_id
           AND ac.obbligatorio           = TRUE
           AND COALESCE(ac.attivo, TRUE) = TRUE
           AND ac.valido_dal            <= p_data_riferimento
           AND (ac.valido_al IS NULL OR ac.valido_al >= p_data_riferimento)
    LOOP
        SELECT *
          INTO v_resolve
          FROM vendite.fn_resolve_prezzo_listino_v2(
              v_rec.componente_id,
              v_rec.componente_uom_id,
              p_data_riferimento,
              p_ba_id,
              p_utility_id,
              p_emittente_soggetto_ruolo_id,
              p_classe_utenza_id
          );
        v_prezzo_totale := v_prezzo_totale + v_resolve.prezzo_finale * v_rec.coeff_qta;
    END LOOP;

    componente_id       := p_prodotto_id;
    uom_id              := p_uom_id;
    prezzo_unitario     := v_prezzo_totale;
    iva_id              := v_articolo_iva_id;
    descrizione_fattura := v_articolo_desc;
    esposto_in_fattura  := FALSE;
    coeff_qta           := 1::numeric;
    RETURN NEXT;
END
$function$

COMMENT ON FUNCTION vendite.fn_resolve_prezzo_composito(p_prodotto_id uuid, p_uom_id bigint, p_data_riferimento date, p_ba_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_classe_utenza_id integer)
IS 'Resolver BoM ibrido pricing v5 (post 22-04-2026): N righe se composito ha componenti esposti, 1 riga altrimenti (prezzo diretto o Sigma pesata). Espone coeff_qta per abilitare il calcolo quantita_componente = quantita_padre * coeff_qta in BoMComponentExpander (DEC-3 §14.4.1). Colonna coeff_qta in fondo al RETURNS TABLE per backward-compat by-position.';
```

---
{% include-markdown "signature-core.md" %}
