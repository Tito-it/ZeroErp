{% include-markdown "it/dbzero/vendite/manual/fn_annulla_reso.md" %}
# ⚙️ Funzione `fn_annulla_reso`

```sql
CREATE FUNCTION fn_annulla_reso(p_reso_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_annulla_reso(p_reso_id bigint)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_stato            config.stati_doc_reso.codice_interno%TYPE;
    v_stato_ann_id     config.stati_doc_reso.id%TYPE;
    v_ddt_uid          vendite.resi.sorgente_uid%TYPE;
    v_ddt_id           vendite.ddt.id%TYPE;
    v_ddt_stato        config.stati_doc_ddt.codice_interno%TYPE;
    v_stato_target_id  config.stati_doc_ordini.id%TYPE;
    v_stato_cons_id    config.stati_doc_ddt.id%TYPE;
    v_tutto_reso       boolean;
    v_ord              RECORD;
BEGIN
    IF p_reso_id IS NULL OR p_reso_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_annulla_reso','E_VALIDAZIONE',
            jsonb_build_object('p_reso_id', p_reso_id),
            NULL::uuid, 'p_reso_id deve essere > 0');
    END IF;

    SELECT sdr.codice_interno, r.sorgente_uid
      INTO v_stato, v_ddt_uid
      FROM vendite.resi r
      JOIN config.stati_doc_reso sdr ON sdr.id = r.stato_doc_reso_id
     WHERE r.id = p_reso_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_annulla_reso','E_RESO_NOT_FOUND',
            jsonb_build_object('reso_id', p_reso_id),
            NULL::uuid, p_reso_id::text);
    END IF;

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

    -- Transizione -> ANNULLATO.
    SELECT id INTO v_stato_ann_id FROM config.stati_doc_reso
     WHERE codice_interno = 'ANNULLATO' AND attivo IS TRUE;
    UPDATE vendite.resi
       SET stato_doc_reso_id = v_stato_ann_id
     WHERE id = p_reso_id;

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
            IF vendite.fn_ordine_ha_residuo_evasione(v_ord.ordine_id) THEN
                SELECT id INTO v_stato_target_id FROM config.stati_doc_ordini
                 WHERE codice_interno = 'PARZIALMENTE_EVASO' AND attivo IS TRUE;
            ELSE
                SELECT id INTO v_stato_target_id FROM config.stati_doc_ordini
                 WHERE codice_interno = 'EVASO' AND attivo IS TRUE;
            END IF;
            UPDATE vendite.ordini
               SET stato_doc_ordine_id = v_stato_target_id
             WHERE id = v_ord.ordine_id
               AND stato_doc_ordine_id IS DISTINCT FROM v_stato_target_id;
        END LOOP;

        -- Ri-flip DDT RESO->CONSEGNATO se non piu' reso totale.
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
                UPDATE vendite.ddt
                   SET stato_doc_ddt_id = v_stato_cons_id
                 WHERE id = v_ddt_id;
            END IF;
        END IF;
    END IF;
END;
$function$

COMMENT ON FUNCTION vendite.fn_annulla_reso(p_reso_id bigint)
IS 'Madre annullo reso con storno: -> ANNULLATO, ri-proiezione stato ordine, ri-flip DDT RESO->CONSEGNATO se non piu totale. Simmetrica a fn_conferma_reso. brief S2/S5. ⛔ DUE guardie di RIFIUTO, gemelle fra loro e tutte e due prima di qualunque scrittura: E_RESO_ANNULLO_CON_RICONSEGNE (la merce e'' gia'' ripartita) e - dal 2026-08-19 - E_RESO_ANNULLO_CON_ACCREDITO (esiste almeno una riga di ponte in vendite.resi_righe_accrediti). ⚠️ Senza la seconda un reso accreditato si annullava lasciando VIVE le rettifiche a quantita'' negativa in vendite.commesse_attivita, e il primo giro di fatturazione emetteva una nota di credito per un reso annullato: i due lister (fn_list_emittibili_lane, fn_emit_attivita_fatturabili_da_commessa) non nominano mai il reso e non riparano a valle. Il predicato e'' l''ESISTENZA del ponte, non lo stato delle rettifiche: se l''accredito e'' ormai troppo tardi per essere disfatto lo dice la sua madre con E_ACCREDITO_ANNULLO_NON_AMMESSO, e ricalcolare qui «tutte NON_EMESSA» sarebbe una seconda copia della stessa regola. ⛔ Si RIFIUTA e non si cascata: vendite.fn_annulla_accredito_riga_reso pretende un motivo obbligatorio che una cascata automatica dovrebbe inventarsi, e se una sola rettifica non e'' piu'' NON_EMESSA l''annullo del reso non deve avvenire affatto - non avvenire a meta''. ⭐⚠️ VINCOLO RECIPROCO su TRE posti (C-3), con script.fn_check_rinuncia_reversibile e vendite.fn_annulla_accredito_riga_reso: la guardia si auto-ripara perche'' l''annullo dell''accredito CANCELLA le righe di ponte - se un giorno diventasse un soft-delete i tre posti si cambiano INSIEME. rev 2026-07-13. rev 2026-07-17 (step 2b): il ri-flip conta solo i resi CONFERMATI. rev 2026-07-17 (step 2): il ri-flip legge l helper unico vw_resi_righe_effettive. rev 2026-08-19: guardia accredito (brief-design-note-credito-resi; segnalazione BE del 2026-08-19).';
```

---
{% include-markdown "signature-core.md" %}
