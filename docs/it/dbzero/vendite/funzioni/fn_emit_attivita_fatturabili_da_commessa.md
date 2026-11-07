{% include-markdown "it/dbzero/vendite/manual/fn_emit_attivita_fatturabili_da_commessa.md" %}
# ⚙️ Funzione `fn_emit_attivita_fatturabili_da_commessa`

```sql
CREATE FUNCTION fn_emit_attivita_fatturabili_da_commessa(p_commessa_id bigint, p_only_approved boolean, p_dry_run boolean, p_gruppi text[], p_emit_batch_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_emit_attivita_fatturabili_da_commessa(p_commessa_id bigint, p_only_approved boolean DEFAULT true, p_dry_run boolean DEFAULT false, p_gruppi text[] DEFAULT NULL::text[], p_emit_batch_id uuid DEFAULT NULL::uuid)
 RETURNS TABLE(total_candidate integer, inserted_rows integer, updated_rows integer, skipped_rows integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: emette righe da commesse_attivita verso attivita_fatturabili
--        in modalita' idempotente: una attivita' fatturabile per riga di
--        commessa, ritrovata per commessa_attivita_id (FK NOT NULL, unica).
--        Propaga lo snapshot audit pricing v5 (8 colonne) 1:1 e il
--        registro tipo_movimento (colonna dal 2026-07-17).
-- Sottosistema lotto rimosso (deprecato 20260227-16).
-- rev 2026-09-12 (brief-db-rilancio-step-non-rivede-le-proprie-commesse, D1):
--        l'auto-esclusione del proprio lotto NON e' piu' scritta qui: la
--        classe si legge da vendite.fn_classe_emittibilita_per_giro e il
--        lotto da vendite.fn_lotto_da_emit_batch — le stesse due righe che
--        legge fn_list_commesse_emittibili. Fino a oggi il predicato viveva
--        in DUE copie, e la discovery ne aveva una senza identita': al
--        rilancio di un pull fallito scartava i PROPRI documenti e questa
--        funzione, che li avrebbe ripresi, non veniva mai chiamata.
-- rev 2026-10-09 (brief-db-riga-listino-propagata-dalla-commessa, R-2):
--        propaga anche listino_riga_id, la riga di listino che ha dato
--        il prezzo. Senza, il legame si fermava sulla commessa: un
--        riallineamento che sposta la commessa su un'altra riga
--        liberava quella gia' FATTURATA, perche' nessuna AF la citava.
-- rev 2026-07-17: propaga tipo_movimento (brief immutabilita §4c.2);
--        e' il filtro con cui il contatore tenuti-fatturati tiene
--        fuori dal libro mastro della merce le righe non-NORMALE.
-- rev 2026-07-27 (brief emissione mirata A3): p_gruppi restringe
--        l'emissione ai soli GRUPPI FATTURABILI richiesti. NULL =
--        nessuna restrizione (comportamento storico). E' il primo
--        dei due punti in cui il perimetro mirato va applicato:
--        l'altro e' fn_select_attivita_fatturabili, che filtra le
--        AF gia' esistenti (senza quello, le righe di un altro
--        gruppo rimaste da un giro precedente verrebbero comunque
--        rastrellate — garanzia G12).
-- rev 2026-08-18 (brief nota di credito N1b+N5): propaga anche
--        natura_doc_id e fattura_riga_rettificata_id. La natura
--        deve arrivare fino alla TESTATA (e' li' che la FatturaPA
--        chiedera' TD01 o TD04): se si fermasse qui, la chiave
--        documento non avrebbe cosa separare.
-- rev 2026-09-04 (brief-residuo-fatturabili-e-bandiere-esito-parziale,
--        D1+D2): `p_emit_batch_id` e' l'IDENTITA' DEL GIRO che sta
--        consegnando queste righe, e la funzione la scrive su ogni
--        riga che accetta — su ENTRAMBI i rami.
--        ⭐ Il ramo che conta e' l'UPDATE: e' li' che passano i
--        RESIDUI, cioe' le righe prodotte da un giro poi disfatto,
--        rimaste libere e in competenza. Senza il marchio quelle
--        righe sono indistinguibili da una consegna appena fatta, e
--        lo step a valle le fattura anche quando il pull di quella
--        commessa, in QUESTO giro, e' stato respinto.
--        ⛔ NON e' `lock_batch_id`, che esiste gia' e risponde a
--        un'altra domanda: quello dice CHI TI HA LUCCHETTATO e viene
--        azzerato da fn_libera_attivita_fatturabili; questo dice CHI
--        TI HA CONSEGNATO e deve sopravvivere alla liberazione — se
--        non sopravvivesse, un residuo tornerebbe anonimo e saremmo
--        al punto di prima.
--        ⚠️ Sul ramo di UPDATE il marchio si scrive solo se il giro
--        ce l'ha: con `p_emit_batch_id` NULL si TIENE quello di prima
--        invece di cancellarlo. Un chiamante che non passa il giro
--        (i pgTAP storici, il backend finche' non passa il
--        parametro) non deve poter smarchiare righe gia' marchiate.
DECLARE
    v_commessa              vendite.commesse%ROWTYPE;
    v_root_id               vendite.commesse_sorgenti.id%TYPE;
    v_existing_id           vendite.attivita_fatturabili.id%TYPE;
    v_existing_fatturato    vendite.attivita_fatturabili.fatturato%TYPE;
    -- ⭐ IL LOTTO DI QUESTO GIRO, risolto dal marchio che il chiamante passa
    --   gia' (vendite.fn_lotto_da_emit_batch). Serve a non escludere le righe
    --   che il giro sta trattenendo DA SE' — vedi il JOIN piu' sotto.
    v_lotto_corrente        vendite.fatturazione_lotti.id%TYPE;
    v_row                   RECORD;
BEGIN
    total_candidate := 0;
    inserted_rows := 0;
    updated_rows := 0;
    skipped_rows := 0;

    -- Guard: parametri
    IF p_commessa_id IS NULL OR p_commessa_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_emit_attivita_fatturabili_da_commessa', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_commessa_id', 'valore', p_commessa_id),
            NULL::uuid, 'p_commessa_id obbligatorio e > 0'
        );
    END IF;

    -- Recupera commessa
    SELECT c.* INTO v_commessa
      FROM vendite.commesse c WHERE c.id = p_commessa_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_emit_attivita_fatturabili_da_commessa', 'E_VALORE_MANCANTE',
            jsonb_build_object('commessa_id', p_commessa_id),
            NULL::uuid, concat('commessa_id ', p_commessa_id)
        );
    END IF;

    -- ROOT source obbligatoria
    SELECT cs.id INTO v_root_id
      FROM vendite.commesse_sorgenti cs
     WHERE cs.commessa_id = p_commessa_id AND cs.ruolo_link = 'ROOT'
     LIMIT 1;

    IF v_root_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_emit_attivita_fatturabili_da_commessa', 'E_VALORE_MANCANTE',
            jsonb_build_object('commessa_id', p_commessa_id),
            NULL::uuid, concat('ROOT source mancante per commessa ', p_commessa_id)
        );
    END IF;

    -- ⭐ IL LOTTO DI QUESTO GIRO (rev 2026-09-09; dal 2026-09-12 in una sede
    --   sola, vendite.fn_lotto_da_emit_batch: `lock_batch_id` ha un UNIQUE).
    -- ⚠️ Puo' restare NULL, ed e' legittimo: un chiamante fuori pipeline
    --   (backfill, riconciliazione) non ha un lotto. In quel caso NON c'e'
    --   nessuna auto-esclusione da fare, e le righe trattenute restano tutte
    --   fuori — che e' la risposta prudente.
    v_lotto_corrente := vendite.fn_lotto_da_emit_batch(p_emit_batch_id);

    -- Loop emissione righe
    FOR v_row IN
        SELECT ca.id, ca.segment_key, ca.articolo_id, ca.istanza_utility_id,
               ca.data_attivita, ca.uom_id, ca.quantita, ca.qta_operativa,
               ca.uom_operativa_id, ca.factor_to_base, ca.competenza_mese,
               ca.competenza_dal, ca.competenza_al, ca.posticipa_al,
               ca.tipo_doc_fiscale_id, ca.valuta_id, ca.area_geografica_id,
               ca.prezzo_snapshot, ca.prezzo_bloccato, ca.stato_approvazione, ca.meta,
               ca.tipo_movimento,
               ca.natura_doc_id, ca.fattura_riga_rettificata_id,
               -- Snapshot audit pricing v5 (propagati 1:1)
               ca.prezzo_base_snapshot, ca.origine_prezzo,
               ca.tipo_variazione_applicata, ca.valore_variazione_applicata,
               ca.promo_id, ca.contratto_id,
               ca.categoria_cliente_id_snapshot, ca.classe_utenza_id_snapshot,
               -- La riga di listino da cui viene il prezzo (rev 2026-10-09)
               ca.listino_riga_id
          FROM vendite.commesse_attivita ca
          -- ⭐ rev 2026-09-09 — LA SEDE UNICA DEL CRITERIO (changeSet -59).
          --   Qui non si scrive piu' quali righe si possono emettere: si
          --   legge la CLASSE. La vista risponde «puo' entrare in un giro?»,
          --   questa funzione resta padrona di COSA COPIARE — ed e' il motivo
          --   per cui il JOIN c'e' ma le colonne restano quelle di `ca`.
          JOIN vendite.vw_commesse_attivita_emittibilita e
            ON e.commessa_attivita_id = ca.id
         WHERE ca.commessa_id = p_commessa_id
           AND (
                -- ⭐⭐ LA CLASSE VISTA DAL GIRO, e non la classe nuda (rev
                --   2026-09-12). Una riga TRATTENUTA soltanto dal MIO lotto e',
                --   per il mio lotto, PRONTA: e' il proprio documento di un
                --   tentativo precedente — il giro ha fallito la commessa, il
                --   savepoint ha rimesso le righe a NON_EMESSA, l'esito e'
                --   rimasto FUORI dal savepoint — e al rilancio va ripreso.
                --   Senza, il rilancio salterebbe esattamente le righe che
                --   deve riprovare: in silenzio, con un lotto che riparte e
                --   non produce niente.
                -- ⛔ L'auto-esclusione NON e' piu' scritta qui: vive in
                --   vendite.fn_classe_emittibilita_per_giro, la stessa riga che
                --   legge fn_list_commesse_emittibili. Due copie si erano gia'
                --   sfilate una volta — la discovery non la aveva, e questa
                --   funzione non veniva mai raggiunta.
                vendite.fn_classe_emittibilita_per_giro(
                    e.classe_emittibilita, e.trattenuta_da_lotti, v_lotto_corrente) = 'PRONTA'
                -- Il chiamante ha chiesto di prendere anche il non approvato:
                -- e' la vecchia `p_only_approved IS FALSE`, scritta per classi.
                -- ⚠️ Qui la classe NUDA basta: una riga non approvata non e'
                --   mai TRATTENUTA (ordine del CASE della vista), quindi non ha
                --   niente da vedere «dal giro».
                OR (p_only_approved IS FALSE
                    AND e.classe_emittibilita IN ('NON_APPROVATA', 'RIFIUTATA'))
               )
           -- EMISSIONE MIRATA (rev 2026-07-27): NULL = nessuna
           -- restrizione; array vuoto = richiesta vuota -> zero righe;
           -- chiave inesistente -> zero righe, nessun errore (G6).
           -- ⭐ La chiave arriva gia' costruita dal classificatore, dalla
           --   sola fonte di verita': qui non si ricostruisce piu'.
           AND (p_gruppi IS NULL OR e.gruppo_key = ANY (p_gruppi))
         ORDER BY ca.id
    LOOP
        total_candidate := total_candidate + 1;

        -- ⭐ La riga gia' emessa si ritrova per commessa_attivita_id: e' la FK
        --   NOT NULL della provenienza, unica (uq_attivita_fatturabili_commessa_attivita).
        --   Non dipende dal formato di segment_key, che puo' cambiare sotto una
        --   riga gia' emessa, e non esce dalla commessa.
        SELECT a.id, a.fatturato INTO v_existing_id, v_existing_fatturato
          FROM vendite.attivita_fatturabili a
         WHERE a.commessa_attivita_id = v_row.id
           FOR UPDATE;

        IF p_dry_run THEN
            IF v_existing_id IS NULL THEN inserted_rows := inserted_rows + 1;
            ELSE updated_rows := updated_rows + 1; END IF;
            CONTINUE;
        END IF;

        IF v_existing_id IS NULL THEN
            INSERT INTO vendite.attivita_fatturabili (
                articolo_id, billing_account_id, istanza_utility_id, data_attivita,
                quantita, competenza_mese, approvato, meta,
                posticipa_al, uom_id, qta_operativa,
                uom_operativa_id, factor_to_base, valuta_id, prezzo_unitario,
                tipo_doc_fiscale_id, competenza_dal, competenza_al,
                area_geografica_id, stato_esecuzione, prezzo_bloccato,
                commessa_id, commessa_attivita_id,
                tipo_movimento,
                natura_doc_id, fattura_riga_rettificata_id,
                prezzo_base_snapshot, origine_prezzo, tipo_variazione_applicata,
                valore_variazione_applicata, promo_id, contratto_id,
                categoria_cliente_id_snapshot, classe_utenza_id_snapshot,
                listino_riga_id,
                emit_batch_id
            )
            VALUES (
                v_row.articolo_id, v_commessa.billing_account_id, v_row.istanza_utility_id,
                v_row.data_attivita, v_row.quantita, v_row.competenza_mese,
                (v_row.stato_approvazione = 'APPROVATA'),
                COALESCE(v_row.meta, '{}'::jsonb) || jsonb_build_object(
                    'scope', 'COMMESSE', 'commessa_id', p_commessa_id,
                    'commessa_attivita_id', v_row.id, 'segment_key', v_row.segment_key
                ),
                v_row.posticipa_al,
                v_row.uom_id, v_row.qta_operativa, v_row.uom_operativa_id, v_row.factor_to_base,
                v_row.valuta_id, v_row.prezzo_snapshot,
                v_row.tipo_doc_fiscale_id, v_row.competenza_dal, v_row.competenza_al,
                v_row.area_geografica_id, 'PENDING', v_row.prezzo_bloccato,
                p_commessa_id, v_row.id,
                v_row.tipo_movimento,
                v_row.natura_doc_id, v_row.fattura_riga_rettificata_id,
                v_row.prezzo_base_snapshot, v_row.origine_prezzo, v_row.tipo_variazione_applicata,
                v_row.valore_variazione_applicata, v_row.promo_id, v_row.contratto_id,
                v_row.categoria_cliente_id_snapshot, v_row.classe_utenza_id_snapshot,
                v_row.listino_riga_id,
                -- Il giro che consegna questa riga. NULL = nessun giro l'ha
                -- rivendicata: e' cio' che la vista di presidio elenca.
                p_emit_batch_id
            );
            inserted_rows := inserted_rows + 1;
        ELSE
            -- Riga esistente: errore se gia' fatturata
            IF COALESCE(v_existing_fatturato, false) IS TRUE THEN
                PERFORM script.fn_log_and_raise_error(
                    'vendite', 'fn_emit_attivita_fatturabili_da_commessa', 'E_RIGA_GIA_FATTURATA',
                    jsonb_build_object('attivita_fatturabili_id', v_existing_id, 'commessa_attivita_id', v_row.id),
                    NULL::uuid, v_existing_id::text
                );
            END IF;

            UPDATE vendite.attivita_fatturabili a
               SET articolo_id = v_row.articolo_id,
                   billing_account_id = v_commessa.billing_account_id,
                   istanza_utility_id = v_row.istanza_utility_id,
                   data_attivita = v_row.data_attivita,
                   quantita = v_row.quantita,
                   competenza_mese = v_row.competenza_mese,
                   approvato = (v_row.stato_approvazione = 'APPROVATA'),
                   meta = COALESCE(a.meta, '{}'::jsonb) || COALESCE(v_row.meta, '{}'::jsonb) || jsonb_build_object(
                       'scope', 'COMMESSE', 'commessa_id', p_commessa_id,
                       'commessa_attivita_id', v_row.id, 'segment_key', v_row.segment_key
                   ),
                   posticipa_al = v_row.posticipa_al,
                   uom_id = v_row.uom_id,
                   qta_operativa = v_row.qta_operativa,
                   uom_operativa_id = v_row.uom_operativa_id,
                   factor_to_base = v_row.factor_to_base,
                   valuta_id = v_row.valuta_id,
                   prezzo_unitario = v_row.prezzo_snapshot,
                   tipo_doc_fiscale_id = v_row.tipo_doc_fiscale_id,
                   competenza_dal = v_row.competenza_dal,
                   competenza_al = v_row.competenza_al,
                   area_geografica_id = v_row.area_geografica_id,
                   prezzo_bloccato = v_row.prezzo_bloccato,
                   commessa_id = p_commessa_id,
                   commessa_attivita_id = v_row.id,
                   -- Registro della riga: lo specchio segue la CA
                   -- (la riga gia' fatturata e' respinta sopra).
                   tipo_movimento = v_row.tipo_movimento,
                   -- Natura e riga rettificata: stesso specchio.
                   natura_doc_id = v_row.natura_doc_id,
                   -- rev 2026-10-31 (20261031-47, D-1): la natura torna quella della
                   -- commessa, la marca del segno cade.
                   natura_dal_segno = false,
                   fattura_riga_rettificata_id = v_row.fattura_riga_rettificata_id,
                   -- Refresh snapshot audit pricing v5 (riga non ancora fatturata)
                   prezzo_base_snapshot = v_row.prezzo_base_snapshot,
                   origine_prezzo = v_row.origine_prezzo,
                   tipo_variazione_applicata = v_row.tipo_variazione_applicata,
                   valore_variazione_applicata = v_row.valore_variazione_applicata,
                   promo_id = v_row.promo_id,
                   contratto_id = v_row.contratto_id,
                   categoria_cliente_id_snapshot = v_row.categoria_cliente_id_snapshot,
                   classe_utenza_id_snapshot = v_row.classe_utenza_id_snapshot,
                   -- La riga di listino segue la CA come lo snapshot: la
                   -- riga gia' fatturata e' respinta sopra, quindi qui non
                   -- si stacca mai il legame di un documento emesso.
                   listino_riga_id = v_row.listino_riga_id,
                   -- ⭐ IL RAMO CHE CHIUDE D1+D2. Questa e' la ri-adozione di
                   --   un residuo: la riga c'era gia', il giro la riprende e
                   --   ci scrive sopra il PROPRIO nome. Da qui in poi non e'
                   --   piu' «una riga libera in competenza», e' «la riga che
                   --   il giro X ha consegnato».
                   -- ⚠️ COALESCE e non assegnazione secca: un chiamante senza
                   --   giro non smarchia cio' che un giro aveva marchiato.
                   emit_batch_id = COALESCE(p_emit_batch_id, a.emit_batch_id)
             WHERE a.id = v_existing_id;
            updated_rows := updated_rows + 1;
        END IF;

        UPDATE vendite.commesse_attivita ca SET stato_emissione = 'EMESSA' WHERE ca.id = v_row.id;
    END LOOP;

    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION vendite.fn_emit_attivita_fatturabili_da_commessa(p_commessa_id bigint, p_only_approved boolean, p_dry_run boolean, p_gruppi text[], p_emit_batch_id uuid)
IS 'Il PULL: emette le righe di una commessa in vendite.attivita_fatturabili, una attivita'' fatturabile per riga di commessa, in modo idempotente: la riga gia'' emessa si ritrova per commessa_attivita_id (FK NOT NULL, unica per uq_attivita_fatturabili_commessa_attivita) e si aggiorna, quella nuova si inserisce; una riga gia'' fatturata solleva E_RIGA_GIA_FATTURATA. La provenienza dell''attivita'' e'' la riga di commessa (commessa_id, commessa_attivita_id): il documento da cui nasce si legge da li''. Propaga snapshot del prezzo, riga di listino, tipo_movimento, natura e riga rettificata. Quali righe: la CLASSE di vendite.vw_commesse_attivita_emittibilita vista DAL GIRO con vendite.fn_classe_emittibilita_per_giro, per cui una riga trattenuta soltanto dal lotto corrente (vendite.fn_lotto_da_emit_batch(p_emit_batch_id)) e'' PRONTA e il rilancio riprende i propri documenti; con p_only_approved = false entrano anche NON_APPROVATA e RIFIUTATA. p_gruppi restringe alle chiavi richieste (emissione mirata). p_emit_batch_id e'' il marchio del giro su ogni riga consegnata; senza giro, l''aggiornamento tiene il marchio di prima. p_dry_run conta senza scrivere.';
```

</div>

---
{% include-markdown "signature-core.md" %}
