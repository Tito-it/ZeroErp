{% include-markdown "it/dbzero/vendite/manual/fn_snapshot_indirizzi_fattura.md" %}
# ⚙️ Funzione `fn_snapshot_indirizzi_fattura`

```sql
CREATE FUNCTION fn_snapshot_indirizzi_fattura(p_fattura_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_snapshot_indirizzi_fattura(p_fattura_id bigint)
 RETURNS TABLE(inserted_rows integer, updated_rows integer)
 LANGUAGE plpgsql
AS $function$
-- rev 2026-10-20 (20261020-59, brief-db-grammatica-unica-documenti, 2d G-6):
--   l'ambito degli indirizzi FATTURE diventa FATTURA, il codice della
--   sorgente; firma e RETURNS ancorati.
-- Scopo: fissare lo snapshot degli indirizzi di UNA fattura,
--        risolvendoli dall'anagrafica del cliente del billing
--        account di testata. Deterministica e fail-loud: se manca
--        un indirizzo obbligatorio la fattura si ferma qui.
-- Uso:   task snapshot_indirizzi_lotto (step DRAFT), via il
--        wrapper di lotto vendite.fn_snapshot_indirizzi_lotto.
DECLARE
    v_soggetto_ruolo_id  anagrafiche.billing_account.soggetto_ruolo_id%TYPE;
    v_istanza_utility_id anagrafiche.billing_account.istanza_utility_id%TYPE;
    v_tx_id              vendite.fatture.tx_id%TYPE;
    v_tipo               record;
    v_res                record;
    v_is_insert          boolean;
    v_inserted           integer := 0;
    v_updated            integer := 0;
    v_tipi_presenti      integer[];   -- niente colonna%TYPE[]: PG non lo supporta
    v_mancanti           text[];
BEGIN
    -- ===== Guard parametro =====
    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_snapshot_indirizzi_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id),
            NULL::uuid, 'p_fattura_id obbligatorio e > 0');
    END IF;

    -- ===== Controparte: il BA di TESTATA, cosi' com'e' (D-P) =====
    -- In gerarchia e' gia' il BA padre: ce l'ha messo
    -- fn_build_fattura_key. Qui non si guarda parent_account_id,
    -- e non e' una dimenticanza — e' la decisione.
    SELECT ba.soggetto_ruolo_id, ba.istanza_utility_id, f.tx_id
      INTO v_soggetto_ruolo_id, v_istanza_utility_id, v_tx_id
      FROM vendite.fatture f
      JOIN anagrafiche.billing_account ba ON ba.id = f.billing_account_id
     WHERE f.id = p_fattura_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_snapshot_indirizzi_fattura', 'E_FATTURA_NON_TROVATA',
            jsonb_build_object('fattura_id', p_fattura_id),
            NULL::uuid, p_fattura_id::text);
    END IF;

    -- ===== Un giro per ogni tipo ammesso in ambito FATTURE =====
    -- L'elenco viene dal seed, non dal codice: vedi testata.
    FOR v_tipo IN
        SELECT a.tipo_indirizzo_id, t.codice_interno
          FROM config.tipi_indirizzi_allowed a
          JOIN config.tipi_indirizzi t ON t.id = a.tipo_indirizzo_id
         WHERE a.ambito = 'FATTURA'
           AND a.attivo IS TRUE
         ORDER BY a.tipo_indirizzo_id
    LOOP
        -- Catena unica di risoluzione (C-14b): layer RUOLO con
        -- precedenza per istanza, poi layer SOGGETTO.
        SELECT r.snapshot, r.origine_indirizzo_id, r.origine_soggetto_ruolo_id
          INTO v_res
          FROM script.fn_resolve_indirizzo_documento(
                   v_soggetto_ruolo_id,
                   v_istanza_utility_id,
                   v_tipo.codice_interno) r;

        -- Zero righe = quel tipo non e' risolvibile per questo
        -- cliente. Non e' un errore: se sia obbligatorio si
        -- decide dopo il ciclo, sul seed.
        CONTINUE WHEN NOT FOUND;

        v_is_insert := NULL;

        INSERT INTO vendite.fatture_indirizzi (
                    fattura_id, tipo_indirizzo_id, snapshot,
                    origine_indirizzo_id, origine_soggetto_ruolo_id)
        VALUES (p_fattura_id, v_tipo.tipo_indirizzo_id, v_res.snapshot,
                v_res.origine_indirizzo_id, v_res.origine_soggetto_ruolo_id)
        ON CONFLICT (fattura_id, tipo_indirizzo_id) DO UPDATE
           SET snapshot                  = EXCLUDED.snapshot,
               origine_indirizzo_id      = EXCLUDED.origine_indirizzo_id,
               origine_soggetto_ruolo_id = EXCLUDED.origine_soggetto_ruolo_id
         WHERE vendite.fatture_indirizzi.snapshot
                   IS DISTINCT FROM EXCLUDED.snapshot
            OR vendite.fatture_indirizzi.origine_indirizzo_id
                   IS DISTINCT FROM EXCLUDED.origine_indirizzo_id
            OR vendite.fatture_indirizzi.origine_soggetto_ruolo_id
                   IS DISTINCT FROM EXCLUDED.origine_soggetto_ruolo_id
        RETURNING (xmax = 0) INTO v_is_insert;

        -- xmax = 0 -> riga inserita; xmax valorizzato -> aggiornata.
        -- Nessuna riga di ritorno -> il WHERE ha filtrato: dato
        -- gia' allineato, nessuno dei due contatori si muove.
        IF v_is_insert IS TRUE THEN
            v_inserted := v_inserted + 1;
        ELSIF v_is_insert IS FALSE THEN
            v_updated := v_updated + 1;
        END IF;
    END LOOP;

    -- ===== Obbligatori mancanti: fail-loud (C-14d) =====
    -- Si guarda il contenuto della tabella, che e' la stessa
    -- domanda che fara' il guard di 2.5: due punti che rispondono
    -- alla stessa cosa devono leggere la stessa cosa.
    SELECT array_agg(fi.tipo_indirizzo_id)
      INTO v_tipi_presenti
      FROM vendite.fatture_indirizzi fi
     WHERE fi.fattura_id = p_fattura_id;

    v_mancanti := script.fn_indirizzi_obbligatori_mancanti(
                      'FATTURA', v_tipi_presenti);

    IF COALESCE(array_length(v_mancanti, 1), 0) > 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_snapshot_indirizzi_fattura',
            'E_INDIRIZZO_FATTURA_MANCANTE',
            jsonb_build_object(
                'fattura_id',         p_fattura_id,
                'soggetto_ruolo_id',  v_soggetto_ruolo_id,
                'istanza_utility_id', v_istanza_utility_id,
                'mancanti',           v_mancanti),
            v_tx_id,
            p_fattura_id::text,
            v_soggetto_ruolo_id::text,
            v_istanza_utility_id::text);
    END IF;

    RETURN QUERY SELECT v_inserted, v_updated;
END;
$function$

COMMENT ON FUNCTION vendite.fn_snapshot_indirizzi_fattura(p_fattura_id bigint)
IS 'Fissa lo snapshot degli indirizzi di UNA fattura risolvendoli dall''anagrafica del cliente del billing account di TESTATA — che in gerarchia e'' gia'' il BA padre (D-P): la fattura e'' del padre, quindi gli indirizzi sono del padre, e la funzione non conosce la gerarchia. Risolve sempre dall''anagrafica e mai copiando dai documenti sorgente (D-A): una fattura aggrega N sorgenti e le attivita'' sourceless non hanno snapshot da copiare. I tipi da risolvere e la loro obbligatorieta'' vengono da config.tipi_indirizzi_allowed (ambito FATTURE), mai da un elenco scritto nel codice: la stessa fonte che interroga il guard di emissione. Upsert idempotente su (fattura_id, tipo_indirizzo_id) con WHERE IS DISTINCT FROM, quindi un rerun a dati invariati e'' un vero no-op (0,0) che non tocca l''audit ne'' sveglia il guard di congelamento; non cancella mai (perimetro batch ''iu''). Assenza di un tipo non obbligatorio = nessuna riga e nessun errore; assenza di un obbligatorio = E_INDIRIZZO_FATTURA_MANCANTE, perche'' nel giro notturno non c''e'' nessun operatore davanti e il documento e'' fiscale (C-14d). La soglia di stato non e'' ricontrollata qui: la presidia il trigger a10 di 1.2, per qualunque scrittore. Ritorna (inserted_rows, updated_rows). piano-db-satelliti-fattura Fase 2.1. Rev 2026-10-20 (20261020-59, brief-db-grammatica-unica-documenti 2d, G-6): l''ambito degli indirizzi FATTURE diventa FATTURA, il codice della sorgente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
