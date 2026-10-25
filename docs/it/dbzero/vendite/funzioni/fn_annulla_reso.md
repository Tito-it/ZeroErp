{% include-markdown "it/dbzero/vendite/manual/fn_annulla_reso.md" %}
# ⚙️ Funzione `fn_annulla_reso`

```sql
CREATE FUNCTION fn_annulla_reso(p_reso_id bigint)
```

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
DECLARE
    v_utente            config.user_override_azioni.auth_user_id%TYPE;
    v_reso              vendite.resi%ROWTYPE;
    v_muove             boolean;   -- calcolato, nessuna colonna
    v_stato            config.stati_doc_reso.codice_interno%TYPE;
    v_stato_ann_id     config.stati_doc_reso.id%TYPE;
    v_ddt_uid          vendite.resi.sorgente_uid%TYPE;
    v_ddt_id           vendite.ddt.id%TYPE;
    v_ddt_stato        config.stati_doc_ddt.codice_interno%TYPE;
    v_stato_cons_id    config.stati_doc_ddt.id%TYPE;
    v_tutto_reso       boolean;
    v_ord              RECORD;
    v_sorgente_id      config.sorgenti.id%TYPE;
    v_rientri          bigint[];   -- array di resi_righe_rientri.id: %TYPE non vale per un array
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
    v_ddt_uid := v_reso.sorgente_uid;

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
         WHERE d.uid = v_ddt_uid;

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
               AND dr.attivo IS TRUE;

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
            SELECT s.id INTO v_sorgente_id
              FROM config.sorgenti s
             WHERE s.codice_interno = 'RESO_VENDITA_RIENTRO';
            SELECT COALESCE(array_agg(x.id), '{}'::bigint[]) INTO v_rientri
              FROM vendite.resi_righe_rientri x
              JOIN vendite.resi_righe rr ON rr.id = x.resi_riga_id
             WHERE rr.reso_id = p_reso_id;
            IF v_sorgente_id IS NOT NULL THEN
                PERFORM 1 FROM magazzino.fn_storna_movimenti_sorgente(v_sorgente_id, v_rientri);
            END IF;
        END IF;
    END IF;
END;
$function$

COMMENT ON FUNCTION vendite.fn_annulla_reso(p_reso_id bigint)
IS 'Madre annullo reso con storno: -> ANNULLATO, ri-proiezione stato ordine, ri-flip DDT RESO->CONSEGNATO se non piu totale. Simmetrica a fn_conferma_reso. brief S2/S5. ⛔ DUE guardie di RIFIUTO, gemelle fra loro e tutte e due prima di qualunque scrittura: E_RESO_ANNULLO_CON_RICONSEGNE (la merce e'' gia'' ripartita) e - dal 2026-08-19 - E_RESO_ANNULLO_CON_ACCREDITO (esiste almeno una riga di ponte in vendite.resi_righe_accrediti). ⚠️ Senza la seconda un reso accreditato si annullava lasciando VIVE le rettifiche a quantita'' negativa in vendite.commesse_attivita, e il primo giro di fatturazione emetteva una nota di credito per un reso annullato: i due lister (fn_list_emittibili_lane, fn_emit_attivita_fatturabili_da_commessa) non nominano mai il reso e non riparano a valle. Il predicato e'' l''ESISTENZA del ponte, non lo stato delle rettifiche: se l''accredito e'' ormai troppo tardi per essere disfatto lo dice la sua madre con E_ACCREDITO_ANNULLO_NON_AMMESSO, e ricalcolare qui «tutte NON_EMESSA» sarebbe una seconda copia della stessa regola. ⛔ Si RIFIUTA e non si cascata: vendite.fn_annulla_accredito_riga_reso pretende un motivo obbligatorio che una cascata automatica dovrebbe inventarsi, e se una sola rettifica non e'' piu'' NON_EMESSA l''annullo del reso non deve avvenire affatto - non avvenire a meta''. ⭐⚠️ VINCOLO RECIPROCO su TRE posti (C-3), con script.fn_check_rinuncia_reversibile e vendite.fn_annulla_accredito_riga_reso: la guardia si auto-ripara perche'' l''annullo dell''accredito CANCELLA le righe di ponte - se un giorno diventasse un soft-delete i tre posti si cambiano INSIEME. rev 2026-07-13. rev 2026-07-17 (step 2b): il ri-flip conta solo i resi CONFERMATI. rev 2026-07-17 (step 2): il ri-flip legge l helper unico vw_resi_righe_effettive. rev 2026-08-19: guardia accredito (brief-design-note-credito-resi; segnalazione BE del 2026-08-19). ⭐ rev 2026-09-28 (brief-db-magazzino-lotto-3-bis-carico-da-reso, D-3b-f, M-8): VERBO. SECURITY DEFINER con search_path bloccato; testata FOR UPDATE nel perimetro (fuori perimetro E_RESO_NOT_FOUND); permesso conferma_reso su OGNI annullo (script.fn_guard_azione). Lo stato si scrive con la porta del registro aperta (GUC zeroerp.reso_cambio_stato); annullando un reso CONFERMATO che aveva fatto rientrare merce, i suoi carichi si stornano (magazzino.fn_storna_movimenti_sorgente sui rientri, sorgente RESO_VENDITA_RIENTRO) al costo del carico — se la merce e'' gia'' uscita di nuovo, la primitiva rifiuta. Le due guardie di rifiuto (ri-consegne, accrediti) restano prima di ogni scrittura. La firma non cambia (RETURNS void). ⭐ rev 2026-10-11 (brief-db-ddt-righe-evase-dall-ordine §5.2): la proiezione dello stato dell''ordine e'' il building block vendite.fn_ordine_proietta_stato_evasione; la copia scritta a mano qui si ritira (regola del 2). Comportamento invariato. ⭐ rev 2026-10-25 (20261025-18, brief-modello-documento-vendita §7): il permesso dalla riga del passaggio con script.fn_guard_passaggio, al posto di script.fn_guard_azione scritto nel corpo: CONFERMATO -> ANNULLATO chiede conferma_reso (config.transizioni_stati_reso.azione_processo_codename), DRAFT -> ANNULLATO il solo permesso sul documento, che controlla il backend (M-4 di Tid: chi fa disfa, l''annullo di una bozza non e'' un passaggio pesante). Lo stato del reso e il ri-flip della bolla (RESO -> CONSEGNATO, passaggio di processo) dalla scrittura comune script.fn_doc_scrivi_stato, attraverso la porta script.trgfn_doc_stato_solo_dal_verbo: la GUC zeroerp.reso_cambio_stato si ritira.';
```

</div>

---
{% include-markdown "signature-core.md" %}
