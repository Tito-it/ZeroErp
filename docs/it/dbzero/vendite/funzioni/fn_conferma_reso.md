{% include-markdown "it/dbzero/vendite/manual/fn_conferma_reso.md" %}
# ⚙️ Funzione `fn_conferma_reso`

```sql
CREATE FUNCTION fn_conferma_reso(p_reso_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_conferma_reso(p_reso_id bigint)
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
-- ⭐ rev 2026-10-25 (20261025-17, brief-modello-documento-vendita §7): il
--   permesso dalla riga del passaggio (script.fn_guard_passaggio: DRAFT ->
--   CONFERMATO chiede conferma_reso), prima di qualunque scrittura; lo
--   stato del reso e quello della bolla dalla scrittura comune
--   (script.fn_doc_scrivi_stato), attraverso la porta.
DECLARE
    v_utente            config.user_override_azioni.auth_user_id%TYPE;
    v_reso              vendite.resi%ROWTYPE;
    v_muove             boolean;   -- calcolato, nessuna colonna
    v_stato             config.stati_doc_reso.codice_interno%TYPE;
    v_stato_conf_id     config.stati_doc_reso.id%TYPE;
    v_ddt_uid           vendite.resi.sorgente_uid%TYPE;
    v_ddt_id            vendite.ddt.id%TYPE;
    v_ddt_stato         config.stati_doc_ddt.codice_interno%TYPE;
    v_stato_reso_ddt_id config.stati_doc_ddt.id%TYPE;
    v_tutto_reso        boolean;
    v_ord               RECORD;
BEGIN
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    -- 1) Guard input + reso in DRAFT + almeno una riga.
    IF p_reso_id IS NULL OR p_reso_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_conferma_reso','E_VALIDAZIONE',
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
            'vendite','fn_conferma_reso','E_RESO_NOT_FOUND',
            jsonb_build_object('reso_id', p_reso_id),
            NULL::uuid, p_reso_id::text);
    END IF;

    SELECT sdr.codice_interno INTO v_stato
      FROM config.stati_doc_reso sdr
     WHERE sdr.id = v_reso.stato_doc_reso_id;
    v_ddt_uid := v_reso.sorgente_uid;

    -- Il permesso del passaggio, prima di scrivere qualunque cosa: dalla
    -- riga DRAFT -> CONFERMATO della matrice (M-3), su OGNI conferma,
    -- anche di un reso che non muove merce (D-3b-f).
    SELECT id INTO v_stato_conf_id FROM config.stati_doc_reso
     WHERE codice_interno = 'CONFERMATO' AND attivo IS TRUE;
    PERFORM script.fn_guard_passaggio(v_utente, 'vendite.resi'::regclass,
                                      v_reso.stato_doc_reso_id, v_stato_conf_id);

    IF v_stato IS DISTINCT FROM 'DRAFT' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_conferma_reso','E_RESO_STATO_NON_CONFERMABILE',
            jsonb_build_object('reso_id', p_reso_id, 'stato', v_stato),
            NULL::uuid, p_reso_id::text, v_stato);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM vendite.resi_righe
                    WHERE reso_id = p_reso_id AND attivo IS TRUE) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_conferma_reso','E_RESO_SENZA_RIGHE',
            jsonb_build_object('reso_id', p_reso_id),
            NULL::uuid, p_reso_id::text);
    END IF;

    -- 1-bis) La merce che rientra (rev 2026-09-28, D-3b-b/-c). Su un reso
    --    che fa rientrare merce: il lock della bolla d'origine (il tetto per
    --    prelievo somma i rientri di tutti i suoi resi: due conferme
    --    concorrenti si serializzano qui), la conferma che parla (primo
    --    motivo di script.fn_check_reso_merce, che conta gia' gli
    --    automatici), poi i rientri automatici, finche' il reso e' in bozza.
    v_muove := vendite.fn_reso_muove_merce(v_reso);
    IF v_muove THEN
        PERFORM 1 FROM vendite.ddt d WHERE d.uid = v_reso.sorgente_uid FOR UPDATE;
        PERFORM script.fn_raise_primo_motivo_se_presente(
            'vendite', 'vendite.fn_conferma_reso',
            script.fn_check_reso_merce(v_reso), NULL, NULL::uuid,
            jsonb_build_object('reso_id', p_reso_id));
        INSERT INTO vendite.resi_righe_rientri (resi_riga_id, ddt_riga_prelievo_id, qta)
        SELECT m.resi_riga_id, m.prelievo_unico_id, m.qta
          FROM vendite.fn_reso_merce_da_rientrare(v_reso) m
         WHERE m.automatico;
    END IF;

    -- 2) Transizione a CONFERMATO (gen_numero + guard_transizione), dalla
    --    scrittura comune: la porta si apre per QUESTO reso.
    PERFORM script.fn_doc_scrivi_stato('vendite.resi'::regclass, p_reso_id, v_stato_conf_id);

    -- 3) Proiezione stato ordine per ogni ordine coinvolto (solo
    --    righe ri-consegna: quelle che riaprono il residuo).
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

    -- 4) Flip DDT origine -> RESO se reso TOTALE (tutte le qta
    --    consegnate del DDT rese da resi EFFETTIVI). Solo se il
    --    DDT e' CONSEGNATO (matrice CONSEGNATO->RESO, passaggio di
    --    processo: lo scrive questo verbo, con la sola scrittura comune).
    SELECT d.id, sdd.codice_interno
      INTO v_ddt_id, v_ddt_stato
      FROM vendite.ddt d
      JOIN config.stati_doc_ddt sdd ON sdd.id = d.stato_doc_ddt_id
     WHERE d.uid = v_ddt_uid;

    IF v_ddt_id IS NOT NULL AND v_ddt_stato = 'CONSEGNATO' THEN
        SELECT bool_and(COALESCE(reso_riga.tot, 0) >= dr.quantita)
          INTO v_tutto_reso
          FROM vendite.ddt_righe dr
          LEFT JOIN (
              -- rev 2026-07-17 (step 2): fonte unica
              -- vw_resi_righe_effettive (CONFERMATE + attive, tutti
              -- i tipi). Il flip non filtra il tipo: conta tutta la
              -- merce tornata indietro su ogni riga DDT.
              SELECT e.ddt_riga_id, SUM(e.quantita) AS tot
                FROM vendite.vw_resi_righe_effettive e
               GROUP BY e.ddt_riga_id
          ) reso_riga ON reso_riga.ddt_riga_id = dr.id
         WHERE dr.ddt_id = v_ddt_id
           AND dr.attivo IS TRUE;

        IF COALESCE(v_tutto_reso, false) THEN
            SELECT id INTO v_stato_reso_ddt_id FROM config.stati_doc_ddt
             WHERE codice_interno = 'RESO' AND attivo IS TRUE;
            PERFORM script.fn_doc_scrivi_stato('vendite.ddt'::regclass, v_ddt_id, v_stato_reso_ddt_id);
        END IF;
    END IF;

    -- 5) I carichi (rev 2026-09-28, D-3b-c): uno per rientro, al costo
    --    dell'uscita d'origine, nella stessa transazione della conferma.
    IF v_muove THEN
        PERFORM 1 FROM vendite.fn_posta_reso(p_reso_id);
    END IF;
END;
$function$

COMMENT ON FUNCTION vendite.fn_conferma_reso(p_reso_id bigint)
IS 'Madre conferma reso: DRAFT->CONFERMATO (numero+guard), proiezione stato ordine (residuo reso-aware -> PARZIALMENTE_EVASO/EVASO), flip DDT origine CONSEGNATO->RESO se reso totale. brief §5. rev 2026-07-13. rev 2026-07-17 (step 2b): il flip conta solo i resi CONFERMATI. rev 2026-07-17 (step 2): il flip legge l helper unico vw_resi_righe_effettive (CONFERMATE+attive, tutti i tipi). ⭐ rev 2026-09-28 (brief-db-magazzino-lotto-3-bis-carico-da-reso, D-3b-b/-c/-f): VERBO. SECURITY DEFINER con search_path bloccato; testata FOR UPDATE nel perimetro (script.fn_scope_ef_whitelist_via_reso nella WHERE, fuori perimetro E_RESO_NOT_FOUND); permesso conferma_reso su OGNI conferma (script.fn_guard_azione, E_PERMESSO_NEGATO). Su un reso che fa rientrare merce (vendite.fn_reso_muove_merce): lock della bolla d''origine, primo motivo di script.fn_check_reso_merce, rientri automatici, poi lo stato con la porta del registro aperta (GUC zeroerp.reso_cambio_stato) e in coda i carichi (vendite.fn_posta_reso, CARICO_RESO_VEN al costo dell''uscita). UNA transazione. La firma non cambia (RETURNS void). rev 2026-10-01 (brief-db-magazzino-registro-anello-interno, D-2): il posting sta in vendite, non nel registro. ⭐ rev 2026-10-11 (brief-db-ddt-righe-evase-dall-ordine §5.2): la proiezione dello stato dell''ordine e'' il building block vendite.fn_ordine_proietta_stato_evasione; la copia scritta a mano qui si ritira (regola del 2). Comportamento invariato. ⭐ rev 2026-10-25 (20261025-17, brief-modello-documento-vendita §7): il permesso dalla riga DRAFT -> CONFERMATO della matrice (config.transizioni_stati_reso.azione_processo_codename = conferma_reso) con script.fn_guard_passaggio, al posto di script.fn_guard_azione scritto nel corpo; un reso fuori bozza risponde E_RESO_STATO_NON_CONFERMABILE anche a chi non ha l''azione. Lo stato del reso e il flip della bolla (CONSEGNATO -> RESO, passaggio di processo) dalla scrittura comune script.fn_doc_scrivi_stato, attraverso la porta script.trgfn_doc_stato_solo_dal_verbo: la GUC zeroerp.reso_cambio_stato si ritira.';
```

</div>

---
{% include-markdown "signature-core.md" %}
