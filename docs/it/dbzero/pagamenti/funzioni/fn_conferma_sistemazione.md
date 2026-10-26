{% include-markdown "it/dbzero/pagamenti/manual/fn_conferma_sistemazione.md" %}
# ⚙️ Funzione `fn_conferma_sistemazione`

```sql
CREATE FUNCTION fn_conferma_sistemazione(p_sistemazione_id bigint, p_ente_incasso_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.fn_conferma_sistemazione(p_sistemazione_id bigint, p_ente_incasso_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(contabile_id bigint, fondo_source_id bigint, esito text)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_atto            pagamenti.sistemazioni%ROWTYPE;
    v_fattura         vendite.fatture%ROWTYPE;
    v_saldo           vendite.fatture.totale_a_pagare%TYPE;
    v_eccedenza       vendite.fatture.totale_a_pagare%TYPE;
    v_importo_riga    pagamenti.vendite_contabili_righe.importo%TYPE;
    v_centro_id       pagamenti.centri_riscossione.id%TYPE;
    v_stato_bozza_id  pagamenti.vendite_contabili_stati.id%TYPE;
    v_stato_riga_id   pagamenti.vendite_contabili_righe_stati.id%TYPE;
    v_tipo_fondo_id   vendite.tipi_fondi_fattura.id%TYPE;
    v_contabile_id    pagamenti.vendite_contabili.id%TYPE;
    v_fondo_id        vendite.fatture_fondi_fattura_source.id%TYPE;
    v_mancante        text;
    v_operatore       pagamenti.sistemazioni.user_esecuzione%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Eseguire un atto di sistemazione: sceglie la strada e ci
    --   mette sopra il denaro. ⭐ Non inventa nessuna macchina —
    --   le tre esistevano gia' tutte (D15-a).
    --
    -- ⭐ E' una MADRE: scrive la distinta, le sue righe e l'atto,
    --   e o riescono tutte o non ne resta nessuna. Sta nel
    --   database perche' e' tutto SQL: nessuna orchestrazione
    --   Python, l'atomicita' e' dentro la funzione.
    --
    -- Rev 2026-09-15 (brief distinta-numerata-sul-registro, L7):
    --   la distinta non porta piu' un codice composto qui
    --   (SIS_…): lo assegna il trigger sul registro DISTINTA
    --   dell'emittente dell'ATTO, che entra nell'INSERT (D5).
    -- =========================================================

    -- ── 1. L'atto, e il lucchetto ───────────────────────────
    -- ⚠️ FOR UPDATE: due conferme in parallelo sullo stesso atto
    --   creerebbero due documenti per la stessa decisione.
    SELECT * INTO v_atto
      FROM pagamenti.sistemazioni
     WHERE id = p_sistemazione_id
       FOR UPDATE;

    -- ⚠️ «Non esiste» e «non e' tuo» danno lo stesso messaggio di
    --   proposito: distinguerli direbbe a chi e' fuori perimetro
    --   che quell'atto c'e'. Stessa scelta di E_FATTURA_NON_TROVATA
    --   e di E_RATA_NON_TROVATA.
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_conferma_sistemazione',
            'E_SISTEMAZIONE_NON_TROVATA',
            jsonb_build_object('detail', 'sistemazione inesistente o fuori perimetro',
                               'sistemazione_id', p_sistemazione_id),
            NULL::uuid,
            p_sistemazione_id::text
        );
    END IF;

    IF v_atto.stato <> 'BOZZA' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_conferma_sistemazione',
            'E_SISTEMAZIONE_NON_CONFERMABILE',
            jsonb_build_object('detail', 'si conferma solo una sistemazione in bozza',
                               'sistemazione_id', v_atto.id,
                               'stato', v_atto.stato),
            NULL::uuid,
            v_atto.id::text, v_atto.stato::text
        );
    END IF;

    -- ── 2. L'eccedenza, ADESSO ──────────────────────────────
    SELECT * INTO v_fattura
      FROM vendite.fatture
     WHERE id = v_atto.fattura_origine_id;

    SELECT s.saldo INTO v_saldo
      FROM pagamenti.fn_get_saldo_fattura(v_atto.fattura_origine_id) s;

    -- ⭐ «Il residuo ha cambiato segno», la stessa condizione della
    --   vista e senza estremi fissi: vale identica su una fattura
    --   e su una nota di credito.
    v_eccedenza := CASE
        WHEN sign(v_saldo) = -sign(v_fattura.totale_a_pagare) THEN abs(v_saldo)
        ELSE 0
    END;

    IF abs(v_atto.importo) > v_eccedenza THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_conferma_sistemazione',
            'E_SISTEMAZIONE_ECCEDENZA_INSUFFICIENTE',
            jsonb_build_object(
                'detail', 'eccedenza attuale insufficiente',
                'sistemazione_id', v_atto.id,
                'fattura_origine_id', v_atto.fattura_origine_id,
                'eccedenza', v_eccedenza,
                'importo', v_atto.importo
            ),
            NULL::uuid,
            v_atto.fattura_origine_id::text,
            to_char(v_eccedenza, 'FM999999990.00'),
            to_char(abs(v_atto.importo), 'FM999999990.00')
        );
    END IF;

    v_operatore := COALESCE(
        NULLIF(current_setting('app.jwt_user', true), ''), CURRENT_USER);

    -- ⭐ Il segno lo da' il SALDO, non il tipo di documento: su una
    --   fattura sovra-incassata (saldo negativo) la riga esce
    --   negativa, su una nota sovra-rimborsata (saldo positivo)
    --   esce positiva. Nessun IF su «fattura o nota».
    v_importo_riga := sign(v_saldo) * abs(v_atto.importo);

    -- ── 3. La strada ───────────────────────────────────────
    IF v_atto.destinazione = 'RIPORTO' THEN
        -- ⚠️ Le tre colonne che il fondo pretende NOT NULL sono
        --   NULLABILI su vendite.fatture: il riporto e' il punto in
        --   cui le due regole si incontrano, e un 23502 direbbe il
        --   nome della colonna senza dire quale documento la ha
        --   vuota.
        v_mancante := CASE
            WHEN v_fattura.utility_id IS NULL          THEN 'il servizio (utility)'
            WHEN v_fattura.tipo_doc_fiscale_id IS NULL THEN 'il tipo di documento fiscale'
            WHEN v_fattura.valuta_id IS NULL           THEN 'la valuta'
            ELSE NULL
        END;

        IF v_mancante IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'pagamenti.fn_conferma_sistemazione',
                'E_SISTEMAZIONE_RIPORTO_NON_POSSIBILE',
                jsonb_build_object(
                    'detail', 'la fattura di partenza non ha i dati che un fondo pretende',
                    'fattura_origine_id', v_atto.fattura_origine_id,
                    'mancante', v_mancante
                ),
                NULL::uuid,
                v_atto.fattura_origine_id::text, v_mancante
            );
        END IF;

        -- ⚠️ Unico tipo generico a catalogo. L'altro e' CANONE_RAI,
        --   che e' un'altra cosa. Se il dominio ne vorra' uno
        --   dedicato al riporto, e' un seed e questa riga.
        SELECT t.id INTO v_tipo_fondo_id
          FROM vendite.tipi_fondi_fattura t
         WHERE t.codice_interno = 'F_F_ADD_ACC' AND t.attivo IS TRUE
         ORDER BY t.id LIMIT 1;

        IF v_tipo_fondo_id IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'pagamenti.fn_conferma_sistemazione', 'E_CONFIG_MANCANTE',
                jsonb_build_object('detail', 'tipo fondo fattura F_F_ADD_ACC assente o spento'),
                NULL::uuid,
                'il tipo di fondo fattura per addebiti e accrediti (F_F_ADD_ACC)'
            );
        END IF;

        -- ⭐ Nasce ASSEGNATO, non DISPONIBILE: il riporto nomina gia'
        --   la fattura di destinazione, e un fondo disponibile
        --   sarebbe un credito che aspetta una decisione gia' presa.
        INSERT INTO vendite.fatture_fondi_fattura_source (
            fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
            fattura_figlia_id, data_assegnazione, user_assegnazione,
            billing_account_id, utility_id, tipo_doc_fiscale_id,
            emittente_soggetto_ruolo_id, valuta_id, origine, motivo, meta
        ) VALUES (
            v_atto.fattura_origine_id, v_tipo_fondo_id, abs(v_atto.importo), 'ASSEGNATO',
            v_atto.fattura_destinazione_id, now(), v_operatore,
            v_fattura.billing_account_id, v_fattura.utility_id, v_fattura.tipo_doc_fiscale_id,
            v_atto.emittente_soggetto_ruolo_id, v_fattura.valuta_id, 'MANUALE', v_atto.motivo,
            jsonb_build_object('origine', 'SISTEMAZIONE', 'sistemazione_id', v_atto.id)
        )
        RETURNING id INTO v_fondo_id;

    ELSE
        -- RIMBORSO e COMPENSAZIONE: tutte e due producono una distinta.
        IF v_atto.destinazione = 'RIMBORSO' THEN
            -- ⚠️ Da quale conto esce il bonifico e' una decisione del
            --   momento in cui si paga, non di quando si decide: per
            --   questo e' un parametro e non una colonna dell'atto.
            IF p_ente_incasso_id IS NULL THEN
                PERFORM script.fn_log_and_raise_error(
                    'database', 'pagamenti.fn_conferma_sistemazione',
                    'E_CONTABILE_DATI_OBBLIGATORI',
                    jsonb_build_object('detail', 'rimborso senza canale di uscita',
                                       'campo', 'ente_incasso_id',
                                       'sistemazione_id', v_atto.id),
                    NULL::uuid,
                    'il canale da cui esce il rimborso'
                );
            END IF;

            SELECT e.centro_riscossione_id INTO v_centro_id
              FROM pagamenti.enti_incasso e
             WHERE e.id = p_ente_incasso_id;
        ELSE
            -- ⚠️ Il centro di compensazione e' UNICO per costruzione
            --   dal lotto 1 (indice unico parziale su is_compensazione).
            SELECT c.id INTO v_centro_id
              FROM pagamenti.centri_riscossione c
             WHERE c.is_compensazione IS TRUE AND c.attivo IS TRUE;
        END IF;

        IF v_centro_id IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'pagamenti.fn_conferma_sistemazione', 'E_CONFIG_MANCANTE',
                jsonb_build_object('detail', 'centro di riscossione non risolvibile',
                                   'destinazione', v_atto.destinazione,
                                   'ente_incasso_id', p_ente_incasso_id),
                NULL::uuid,
                'il centro di riscossione della sistemazione'
            );
        END IF;

        SELECT s.id INTO v_stato_bozza_id
          FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'BOZZA' AND s.attivo IS TRUE
         ORDER BY s.id LIMIT 1;

        SELECT s.id INTO v_stato_riga_id
          FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'ABBINATA' AND s.attivo IS TRUE
         ORDER BY s.id LIMIT 1;

        IF v_stato_bozza_id IS NULL OR v_stato_riga_id IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'pagamenti.fn_conferma_sistemazione', 'E_CONFIG_MANCANTE',
                jsonb_build_object('detail', 'stati contabili BOZZA/ABBINATA assenti o spenti'),
                NULL::uuid,
                'gli stati contabili BOZZA e ABBINATA'
            );
        END IF;

        -- ⭐ La distinta si crea DIRETTA e non con
        --   fn_get_or_create_vendite_contabile, che e' costruita per
        --   CONDIVIDERE: due rimborsi sullo stesso canale nello
        --   stesso giorno riuserebbero la stessa testata, e il
        --   secondo atto sbatterebbe su uq_sistemazioni_contabile con
        --   un 23505 muto.
        -- ⭐ Rev 2026-09-15 (D5): il codice NON si compone qui. Lo
        --   assegna il trigger sul registro DISTINTA dell'emittente
        --   dell'ATTO — che entra nell'INSERT: e' NOT NULL su
        --   sistemazioni ed e' lo stesso valore scritto sul fondo
        --   nel ramo RIPORTO, una sorgente sola dentro la stessa
        --   madre. L'atto si ritrova da meta.sistemazione_id e da
        --   sistemazioni.contabile_id; l'unicita' «una contabile per
        --   atto» la tiene uq_sistemazioni_contabile.
        INSERT INTO pagamenti.vendite_contabili (
            centro_riscossione_id, ente_incasso_id, emittente_soggetto_ruolo_id,
            data_contabile, data_registrazione, stato_id, origine, meta
        ) VALUES (
            v_centro_id,
            CASE WHEN v_atto.destinazione = 'RIMBORSO' THEN p_ente_incasso_id END,
            v_atto.emittente_soggetto_ruolo_id,
            (SELECT script.fn_data_operativa()), (SELECT script.fn_data_operativa()), v_stato_bozza_id, 'GENERATA',
            jsonb_build_object('origine', 'SISTEMAZIONE',
                               'sistemazione_id', v_atto.id,
                               'destinazione', v_atto.destinazione)
        )
        RETURNING id INTO v_contabile_id;

        -- ⚠️ Statement SEPARATO, non una CTE: padre e figlio nella
        --   stessa CTE non passano sotto la row security — il padre
        --   non e' ancora visibile e il WITH CHECK del figlio nega.
        --   Lezione pagata nel lotto 4.
        INSERT INTO pagamenti.vendite_contabili_righe (
            contabile_id, riferimento_ente, data_pagamento, importo,
            fattura_id, billing_account_id, stato_id, meta
        ) VALUES (
            v_contabile_id,
            concat('SIS_', v_atto.id, '_ORIGINE'),
            (SELECT script.fn_data_operativa()),
            v_importo_riga,
            v_atto.fattura_origine_id,
            v_fattura.billing_account_id,
            v_stato_riga_id,
            jsonb_build_object('origine', 'SISTEMAZIONE', 'sistemazione_id', v_atto.id)
        );

        IF v_atto.destinazione = 'COMPENSAZIONE' THEN
            -- ⭐ L'opposto esatto della prima: due righe che sommano a
            --   zero, che e' letteralmente che cosa vuol dire compensare.
            INSERT INTO pagamenti.vendite_contabili_righe (
                contabile_id, riferimento_ente, data_pagamento, importo,
                fattura_id, billing_account_id, stato_id, meta
            )
            SELECT v_contabile_id,
                   concat('SIS_', v_atto.id, '_DESTINAZIONE'),
                   (SELECT script.fn_data_operativa()),
                   - v_importo_riga,
                   f.id,
                   f.billing_account_id,
                   v_stato_riga_id,
                   jsonb_build_object('origine', 'SISTEMAZIONE', 'sistemazione_id', v_atto.id)
              FROM vendite.fatture f
             WHERE f.id = v_atto.fattura_destinazione_id;
        END IF;
    END IF;

    -- ── 4. L'atto diventa un fatto ─────────────────────────
    UPDATE pagamenti.sistemazioni s
       SET stato           = 'CONFERMATA',
           data_esecuzione = now(),
           user_esecuzione = v_operatore,
           contabile_id    = v_contabile_id,
           fondo_source_id = v_fondo_id
     WHERE s.id = v_atto.id;

    RETURN QUERY
    SELECT v_contabile_id,
           v_fondo_id,
           CASE v_atto.destinazione
               WHEN 'RIPORTO'       THEN 'FONDO_CREATO'
               WHEN 'RIMBORSO'      THEN 'DISTINTA_RIMBORSO_CREATA'
               ELSE                      'DISTINTA_COMPENSAZIONE_CREATA'
           END::text;
END
$function$

COMMENT ON FUNCTION pagamenti.fn_conferma_sistemazione(p_sistemazione_id bigint, p_ente_incasso_id bigint)
IS 'La MADRE che esegue un atto di sistemazione: sceglie la strada e ci mette sopra il denaro. ⭐ Non inventa nessuna macchina — le tre esistevano gia'' tutte (D15-a): il RIPORTO e'' un fondo fattura con origine MANUALE, il RIMBORSO una distinta a importi negativi (D3-d, «il denaro non ha versi, ha segni»), la COMPENSAZIONE una distinta sul centro dedicato con due righe che sommano a zero. ⭐ Il segno della riga lo da'' il SALDO — sign(saldo) x |importo| — e non un IF sul tipo di documento: la formula non nomina ne'' fatture ne'' note di credito, ed e'' la stessa famiglia della regola di capienza del lotto 5. 🔴 Il controllo dell''eccedenza sta alla CONFERMA e non alla registrazione: fra decidere e confermare puo'' arrivare un altro incasso, e una garanzia data prima e'' una garanzia che scade (stessa forma di D13). ⭐ Ogni atto ha la SUA distinta e non passa da fn_get_or_create_vendite_contabile, che e'' costruita per condividere: due rimborsi lo stesso giorno sbatterebbero su uq_sistemazioni_contabile con un 23505 muto. ⭐ Rev 2026-09-15 (brief distinta-numerata-sul-registro, L7): la distinta di una sistemazione prende il numero dal registro DISTINTA dell''emittente dell''ATTO (DIS-<sigla>-<anno>-<progressivo>, assegnato dal trigger a10_gen_codice) e non porta piu'' un codice composto qui (SIS_<atto>_<ts>): l''atto si ritrova da meta.sistemazione_id e da sistemazioni.contabile_id. L''emittente entra nell''INSERT dall''atto — NOT NULL, ed e'' lo stesso valore scritto sul fondo nel ramo RIPORTO. ⚠️ Il canale del rimborso e'' un PARAMETRO e non una colonna dell''atto: da quale conto esce il bonifico si decide quando si paga. ⚠️ Distinta e righe si scrivono in due istruzioni separate: padre e figlio nella stessa CTE non passano sotto la row security.';
```

</div>

---
{% include-markdown "signature-core.md" %}
