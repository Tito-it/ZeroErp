{% include-markdown "it/dbzero/vendite/manual/fn_annulla_reso.md" %}
# ⚙️ Funzione `fn_annulla_reso`

```sql
CREATE FUNCTION fn_annulla_reso(p_reso_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_annulla_reso(p_reso_id bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- ⭐ rev 2026-09-28 (brief-db-magazzino-lotto-3-bis-carico-da-reso, D-3b-f):
--   VERBO del modello «una scrittura = un verbo». SECURITY DEFINER con
--   search_path bloccato (ogni nome qui dentro e' qualificato), testata presa
--   FOR UPDATE con il predicato della policy nella WHERE (fuori perimetro:
--   E_RESO_NOT_FOUND, no-leak, come prima sotto RLS).
-- ⭐ rev 2026-10-25 (20261025-18, brief-modello-documento-vendita §7): il
--   permesso dalla riga del passaggio (script.fn_guard_passaggio:
--   CONFERMATO -> ANNULLATO chiede conferma_reso, DRAFT -> ANNULLATO il solo
--   permesso sul documento, M-4), prima di qualunque scrittura; lo stato del
--   reso e quello della bolla dalla scrittura comune (script.fn_doc_scrivi_stato),
--   attraverso la porta.
-- rev 2026-11-03 (20261103-32, brief-db-addebito-trasporto-ordine §8.1):
--   il ri-flip RESO -> CONSEGNATO (non piu' totale) conta solo la MERCE della bolla
--   (script.fn_natura_e_merce): un onere non si rende, e senza il
--   filtro una bolla con un onere non cambierebbe mai stato.
DECLARE
    v_utente            config.user_override_azioni.auth_user_id%TYPE;
    v_reso              vendite.resi%ROWTYPE;
    v_muove             boolean;   -- calcolato, nessuna colonna
    v_stato            config.stati_doc_reso.codice_interno%TYPE;
    v_stato_ann_id     config.stati_doc_reso.id%TYPE;
    v_ddt_id           vendite.ddt.id%TYPE;
    v_ddt_stato        config.stati_doc_ddt.codice_interno%TYPE;
    v_stato_cons_id    config.stati_doc_ddt.id%TYPE;
    v_tutto_reso       boolean;
    v_ord              RECORD;
    v_sorgente_id      config.sorgenti.id%TYPE;
BEGIN
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    IF p_reso_id IS NULL OR p_reso_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_annulla_reso','E_VALIDAZIONE',
            jsonb_build_object('p_reso_id', p_reso_id),
            NULL::uuid, 'p_reso_id deve essere > 0');
    END IF;

    -- La testata, FOR UPDATE, nel perimetro (predicato della policy: DEFINER).
    SELECT r.* INTO v_reso
      FROM vendite.resi r
     WHERE r.id = p_reso_id
       AND script.fn_scope_ef_whitelist_via_reso(v_utente, r.id)
       FOR UPDATE;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_annulla_reso','E_RESO_NOT_FOUND',
            jsonb_build_object('reso_id', p_reso_id),
            NULL::uuid, p_reso_id::text);
    END IF;

    SELECT sdr.codice_interno INTO v_stato
      FROM config.stati_doc_reso sdr
     WHERE sdr.id = v_reso.stato_doc_reso_id;

    -- Il permesso del passaggio, prima di scrivere qualunque cosa: dalla sua
    -- riga della matrice (M-3). Chi fa disfa: l'annullo di un reso CONFERMATO
    -- chiede conferma_reso; quello di una bozza solo il permesso sul documento,
    -- che controlla il backend (M-4).
    SELECT id INTO v_stato_ann_id FROM config.stati_doc_reso
     WHERE codice_interno = 'ANNULLATO' AND attivo IS TRUE;
    PERFORM script.fn_guard_passaggio(v_utente, 'vendite.resi'::regclass,
                                      v_reso.stato_doc_reso_id, v_stato_ann_id);

    IF v_stato NOT IN ('DRAFT','CONFERMATO') THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_annulla_reso','E_RESO_STATO_NON_ANNULLABILE',
            jsonb_build_object('reso_id', p_reso_id, 'stato', v_stato),
            NULL::uuid, p_reso_id::text, v_stato);
    END IF;

    -- Reso gia' ri-spedito -> storno complesso fuori scope.
    IF EXISTS (
        SELECT 1
          FROM vendite.resi_righe_riconsegne rrr
          JOIN vendite.resi_righe rr ON rr.id = rrr.resi_riga_id
         WHERE rr.reso_id = p_reso_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_annulla_reso','E_RESO_ANNULLO_CON_RICONSEGNE',
            jsonb_build_object('reso_id', p_reso_id),
            NULL::uuid, p_reso_id::text);
    END IF;

    -- ⛔ Reso gia' ACCREDITATO -> l'annullo si RIFIUTA.
    --    Gemella di E_RESO_ANNULLO_CON_RICONSEGNE: stessa classe di
    --    problema, un effetto gia' in viaggio. Qui l'effetto e' una
    --    rettifica a quantita' NEGATIVA in vendite.commesse_attivita,
    --    che il giro di fatturazione raccoglie da se': annullare il
    --    reso senza disfarla emetterebbe una nota di credito per un
    --    reso che non esiste piu'. E il lister non ripara a valle -
    --    vendite.fn_list_emittibili_lane e
    --    vendite.fn_emit_attivita_fatturabili_da_commessa non nominano
    --    mai il reso: per loro quella rettifica e' materia normale.
    --
    -- ⚠️ IL PREDICATO E' L'ESISTENZA DEL PONTE, NON LO STATO DELLE
    --    RETTIFICHE. Se l'accredito e' ormai troppo tardi per essere
    --    disfatto lo dice la sua madre con il proprio messaggio
    --    (E_ACCREDITO_ANNULLO_NON_AMMESSO): ricalcolare qui «tutte
    --    NON_EMESSA» sarebbe una seconda copia della stessa regola,
    --    destinata a divergere al primo ritocco.
    --
    -- ⛔ SI RIFIUTA, NON SI CASCATA. vendite.fn_annulla_accredito_riga_reso
    --    pretende un motivo obbligatorio (E_ACCREDITO_MOTIVO_OBBLIGATORIO)
    --    e la traccia del perche' vive solo in commesse_attivita_log:
    --    una cascata automatica dovrebbe inventarselo. E se anche una
    --    sola rettifica ha lasciato NON_EMESSA, quella madre rifiuta:
    --    li' l'annullo del reso non deve avvenire affatto, non avvenire
    --    a meta'.
    --
    -- ⭐⚠️ VINCOLO RECIPROCO, ora su TRE posti (C-3): questa guardia,
    --    script.fn_check_rinuncia_reversibile e la madre dell'annullo
    --    accredito. Si auto-ripara perche' l'annullo dell'accredito
    --    CANCELLA le righe di ponte - ed e' anche il motivo per cui
    --    E_ACCREDITO_NON_TROVATO copre insieme «mai accreditato» e
    --    «gia' annullato». Se un giorno diventasse un soft-delete,
    --    questo ramo continuerebbe a vedere la riga e vieterebbe PER
    --    SEMPRE l'annullo di un reso ormai annullabile, IN SILENZIO:
    --    i tre posti si cambiano INSIEME.
    --
    -- ⚠️ Sta DOPO le ri-consegne di proposito: un reso che ha entrambe
    --    rispondeva gia' con E_RESO_ANNULLO_CON_RICONSEGNE, e cambiargli
    --    messaggio adesso non direbbe nulla di piu' a chi lo legge.
    --    Nessuna delle due tabelle lette ha la RLS (ce l'ha solo
    --    vendite.resi, gia' attraversata sopra): qui uno zero e' un
    --    dato, non un fail-closed.
    IF EXISTS (
        SELECT 1
          FROM vendite.resi_righe rr
          JOIN vendite.resi_righe_accrediti a ON a.resi_riga_id = rr.id
         WHERE rr.reso_id = p_reso_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_annulla_reso','E_RESO_ANNULLO_CON_ACCREDITO',
            jsonb_build_object('reso_id', p_reso_id),
            NULL::uuid, p_reso_id::text);
    END IF;

    -- La merce che era rientrata (rev 2026-09-28): letta PRIMA di cambiare
    -- lo stato, sulla riga del reso com'e'.
    v_muove := vendite.fn_reso_muove_merce(v_reso);

    -- Transizione -> ANNULLATO, dalla scrittura comune: la porta si apre per
    -- QUESTO reso.
    PERFORM script.fn_doc_scrivi_stato('vendite.resi'::regclass, p_reso_id, v_stato_ann_id);

    -- Storno effetti solo se era CONFERMATO.
    IF v_stato = 'CONFERMATO' THEN
        FOR v_ord IN
            SELECT DISTINCT orr.ordine_id
              FROM vendite.resi_righe rr
              JOIN vendite.ordini_righe orr ON orr.id = rr.ordine_riga_id
              JOIN config.tipi_reso tr      ON tr.id = rr.tipo_reso_id
             WHERE rr.reso_id = p_reso_id
               AND tr.riapre_residuo IS TRUE
        LOOP
            -- ⭐ rev 2026-10-11: la proiezione e' il building block
            --    vendite.fn_ordine_proietta_stato_evasione (brief-db-ddt-righe-evase-dall-ordine).
            PERFORM vendite.fn_ordine_proietta_stato_evasione(v_ord.ordine_id);
        END LOOP;

        -- Ri-flip DDT RESO->CONSEGNATO se non piu' reso totale (passaggio di
        -- processo: lo scrive questo verbo, con la sola scrittura comune).
        SELECT d.id, sdd.codice_interno
          INTO v_ddt_id, v_ddt_stato
          FROM vendite.ddt d
          JOIN config.stati_doc_ddt sdd ON sdd.id = d.stato_doc_ddt_id
         WHERE (d.id = v_reso.sorgente_id OR d.uid = v_reso.sorgente_uid);

        IF v_ddt_id IS NOT NULL AND v_ddt_stato = 'RESO' THEN
            SELECT bool_and(COALESCE(reso_riga.tot, 0) >= dr.quantita)
              INTO v_tutto_reso
              FROM vendite.ddt_righe dr
              LEFT JOIN (
                  -- rev 2026-07-17 (step 2): fonte unica
                  -- vw_resi_righe_effettive (CONFERMATE + attive,
                  -- tutti i tipi). Il ri-flip non filtra il tipo.
                  SELECT e.ddt_riga_id, SUM(e.quantita) AS tot
                    FROM vendite.vw_resi_righe_effettive e
                   GROUP BY e.ddt_riga_id
              ) reso_riga ON reso_riga.ddt_riga_id = dr.id
             WHERE dr.ddt_id = v_ddt_id
               AND dr.attivo IS TRUE
               -- rev 2026-11-03: solo la merce (un onere non si rende).
               AND script.fn_natura_e_merce(dr.natura_vendita_id);

            IF NOT COALESCE(v_tutto_reso, false) THEN
                SELECT id INTO v_stato_cons_id FROM config.stati_doc_ddt
                 WHERE codice_interno = 'CONSEGNATO' AND attivo IS TRUE;
                PERFORM script.fn_doc_scrivi_stato('vendite.ddt'::regclass, v_ddt_id, v_stato_cons_id);
            END IF;
        END IF;

        -- Lo storno dei carichi (rev 2026-09-28, M-8): la merce riesce con
        -- una riga opposta, al costo del carico. Se nel frattempo e' gia'
        -- uscita di nuovo, la primitiva rifiuta l'uscita dello storno: il
        -- registro non va sotto zero per un annullo.
        IF v_muove THEN
            -- Lo storno per DOCUMENTO: i carichi del reso, tutti (righe NULL).
            -- ⛔ Il tipo che manca non e' «niente da stornare»: e' una
            --    configurazione rotta, e un annullo che non storna lascerebbe
            --    in giacenza merce che non c'e'.
            SELECT s.id INTO v_sorgente_id
              FROM config.sorgenti s
             WHERE s.codice_interno = 'RESO_VENDITA';
            IF v_sorgente_id IS NULL THEN
                PERFORM script.fn_log_and_raise_error('vendite', 'vendite.fn_annulla_reso',
                    'E_CONFIG_MANCANTE',
                    jsonb_build_object('config', 'config.sorgenti.RESO_VENDITA'),
                    NULL::uuid, VARIADIC ARRAY['sorgente RESO_VENDITA (config.sorgenti)']);
            END IF;
            PERFORM 1 FROM magazzino.fn_storna_movimenti_sorgente(
                               v_sorgente_id, NULL::bigint[], p_sorgente_id => p_reso_id);
        END IF;
    END IF;
END;
$function$

COMMENT ON FUNCTION vendite.fn_annulla_reso(p_reso_id bigint)
IS 'Il verbo dell''annullo di un reso, con storno: -> ANNULLATO, gemello di vendite.fn_conferma_reso. SECURITY DEFINER con search_path bloccato; testata FOR UPDATE nel perimetro (fuori perimetro E_RESO_NOT_FOUND); il permesso dalla riga del passaggio (script.fn_guard_passaggio): CONFERMATO -> ANNULLATO chiede conferma_reso, DRAFT -> ANNULLATO il solo permesso sul documento. Due rifiuti prima di qualunque scrittura: E_RESO_ANNULLO_CON_RICONSEGNE (la merce e'' gia'' ripartita) ed E_RESO_ANNULLO_CON_ACCREDITO (esiste una riga in vendite.resi_righe_accrediti: senza, le rettifiche negative resterebbero vive e la fatturazione emetterebbe una nota di credito per un reso annullato). Si rifiuta e non si cascata: l''annullo dell''accredito (vendite.fn_annulla_accredito_riga_reso) chiede un motivo, e un accredito non piu'' disfacibile lo dice lui (E_ACCREDITO_ANNULLO_NON_AMMESSO). Vincolo reciproco con script.fn_check_rinuncia_reversibile e vendite.fn_annulla_accredito_riga_reso: l''annullo dell''accredito cancella le righe di ponte, e i tre posti cambiano insieme. Annullando un reso confermato che aveva fatto rientrare merce, i carichi si stornano per documento (magazzino.fn_storna_movimenti_sorgente sul reso; un tipo RESO_VENDITA assente e'' E_CONFIG_MANCANTE, non uno storno saltato) al costo del carico; se la merce e'' gia'' uscita di nuovo, la primitiva rifiuta. Lo stato del reso e il ritorno della bolla RESO -> CONSEGNATO, se il reso non copre piu'' tutta la merce (le sole righe di merce; contano i resi confermati), dalla scrittura comune script.fn_doc_scrivi_stato. La bolla si cerca con la regola (doc.id = sorgente_id OR doc.uid = sorgente_uid). Lo stato dell''ordine lo proietta vendite.fn_ordine_proietta_stato_evasione. RETURNS void.';
```

</div>

---
{% include-markdown "signature-core.md" %}
