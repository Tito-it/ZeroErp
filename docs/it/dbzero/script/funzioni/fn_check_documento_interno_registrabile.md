{% include-markdown "it/dbzero/script/manual/fn_check_documento_interno_registrabile.md" %}
# ⚙️ Funzione `fn_check_documento_interno_registrabile`

```sql
CREATE FUNCTION fn_check_documento_interno_registrabile(p_famiglia text, p_documento_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_documento_interno_registrabile(p_famiglia text, p_documento_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono di REGISTRARE un documento
--        interno di magazzino — un inventario o una rettifica. Funzione
--        PURA (fn_check_*): nessuna scrittura, nessun raise di dominio
--        salvo i due guard di chiamata (parametro, documento non letto).
-- Consumatori: magazzino.fn_posta_inventario e magazzino.fn_posta_rettifica,
--        che sollevano il codice del PRIMO motivo, e
--        script.fn_available_actions_inventario / _rettifica, che dallo
--        stesso primo motivo accendono o spengono «Registra» con la sua
--        reason_key. Una sede sola: il pulsante non puo' promettere cio'
--        che la madre rifiutera' (linee-guida-sql §12.1, §12.5.2).
-- Ritorna: [] se si puo' registrare, altrimenti array ORDINATO di
--        {codice, reason, reason_key, dettaglio, valori}.
-- Precedenza DICHIARATA (§12.2 punto 3): stato > righe > postabilita'.
--        Si esce al primo motivo: gli altri parlerebbero di un documento
--        che comunque non si registra, e il lavoro (il piano) non e'
--        gratis.
-- ⚠️ p_documento_id e' `bigint` e non un %TYPE, ed e' voluto: la funzione
--        e' PARAMETRICA su due tabelle (inventari, rettifiche), come il
--        guard di famiglia. Il %TYPE di una delle due direbbe una cosa
--        falsa dell'altra.
-- Brief: brief-db-magazzino-lotto-2-bis-be-fe R-1;
--        brief-db-magazzino-lotto-2-motore sezione 4.5 (le due madri).
DECLARE
    v_motivi       jsonb := '[]'::jsonb;
    v_magazzino_id magazzino.inventari.magazzino_id%TYPE;
    v_stato        text;
    v_n_righe      bigint;
    v_riga_id      magazzino.inventari_righe.id%TYPE;
    v_articolo_id  magazzino.inventari_righe.articolo_id%TYPE;
    v_lotto_id     magazzino.inventari_righe.lotto_id%TYPE;
    v_asset_id     magazzino.inventari_righe.asset_id%TYPE;
    v_ubicazione   magazzino.inventari_righe.ubicazione_id%TYPE;
    v_motivi_riga  jsonb;
    v_primo        jsonb;
    -- rev 2026-09-28: il magazzino di ARRIVO del trasferimento interno.
    v_magazzino_to magazzino.trasferimenti.magazzino_id_to%TYPE;
BEGIN
    -- ⛔ Guard di PARAMETRO: forme che nessuna interfaccia produce. TECNICO,
    --    e non E_PARAMETRO_INVALIDO, che e' un debito e non una sede.
    IF p_famiglia IS NULL
       OR p_famiglia NOT IN ('INVENTARIO', 'RETTIFICA', 'TRASFERIMENTO')
       OR p_documento_id IS NULL OR p_documento_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_check_documento_interno_registrabile',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'famiglia INVENTARIO, RETTIFICA o TRASFERIMENTO, documento maggiore di zero',
                               'p_famiglia', p_famiglia,
                               'p_documento_id', p_documento_id),
            NULL::uuid,
            'script.fn_check_documento_interno_registrabile',
            'p_famiglia (INVENTARIO | RETTIFICA | TRASFERIMENTO), p_documento_id (obbligatorio, maggiore di zero)');
    END IF;

    -- La testata, sotto RLS. ⚠️ «Non trovata» vuol dire «non esiste» oppure
    -- «non e' nel tuo perimetro», e le due risposte restano indistinguibili
    -- (convenzione no-leak).
    IF p_famiglia = 'INVENTARIO' THEN
        SELECT i.magazzino_id, i.stato_mag_inventario
          INTO v_magazzino_id, v_stato
          FROM magazzino.inventari i
         WHERE i.id = p_documento_id;
    ELSIF p_famiglia = 'RETTIFICA' THEN
        SELECT t.magazzino_id, t.stato_mag_rettifiche
          INTO v_magazzino_id, v_stato
          FROM magazzino.rettifiche t
         WHERE t.id = p_documento_id;
    ELSE
        -- rev 2026-09-28: il trasferimento interno (D-L2-g). Il magazzino di
        -- riferimento e' quello di PARTENZA; l'arrivo serve al motivo 3.
        SELECT t.magazzino_id_from, t.magazzino_id_to, t.stato_trasferimento
          INTO v_magazzino_id, v_magazzino_to, v_stato
          FROM magazzino.trasferimenti t
         WHERE t.id = p_documento_id;
    END IF;

    -- ⛔ Non si risponde [] su un documento che non si legge: sarebbe «si
    --    puo' registrare» detto di una cosa che non si vede. Stesso codice
    --    e stessa frase della madre. (Lo stato e' NOT NULL: NULL qui vuol
    --    dire che la riga non c'e'.)
    IF v_stato IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_check_documento_interno_registrabile',
            'E_MAG_DOCUMENTO_NON_TROVATO',
            jsonb_build_object('famiglia', p_famiglia, 'documento_id', p_documento_id),
            NULL::uuid,
            p_documento_id::text);
    END IF;

    -- ============================================================
    -- MOTIVO 1 — lo stato: si registra da CONFIRM, e solo da li'.
    -- ============================================================
    IF v_stato <> 'CONFIRM' THEN
        -- ⚠️ Il CODICE e' uno solo — e' quello che la madre solleva, e la
        --    frase per l'operatore e' la sua. Ma il `reason` che accende il
        --    tooltip del pulsante NO: «il documento non e' confermato»
        --    detto di un documento GIA' REGISTRATO e' una frase falsa, e un
        --    motivo sbagliato e' peggio di nessun motivo (§12.1). Tre stati,
        --    tre motivi: da fare (DRAFT), gia' fatto (POSTED), non si fa piu'
        --    (CANCEL).
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA',
            'reason',     CASE v_stato
                              WHEN 'POSTED' THEN 'DOCUMENTO_GIA_REGISTRATO'
                              WHEN 'CANCEL' THEN 'DOCUMENTO_ANNULLATO'
                              ELSE 'DOCUMENTO_NON_CONFERMATO'
                          END,
            'reason_key', CASE v_stato
                              WHEN 'POSTED' THEN 'magazzino.documenti_interni.registra_reason.gia_registrato'
                              WHEN 'CANCEL' THEN 'magazzino.documenti_interni.registra_reason.annullato'
                              ELSE 'magazzino.documenti_interni.registra_reason.non_confermato'
                          END,
            'dettaglio',  jsonb_build_object('detail', 'il posting parte da CONFIRM',
                                             'famiglia', p_famiglia,
                                             'documento_id', p_documento_id,
                                             'stato', v_stato),
            -- «Il documento e' in stato %s: il passaggio a %s non e' ammesso.»
            'valori',     jsonb_build_array(v_stato, 'POSTED'));
        RETURN v_motivi;
    END IF;

    -- ============================================================
    -- MOTIVO 2 — almeno una riga: un documento vuoto non registra niente.
    -- ============================================================
    IF p_famiglia = 'INVENTARIO' THEN
        SELECT count(*) INTO v_n_righe
          FROM magazzino.inventari_righe r
         WHERE r.inventario_id = p_documento_id;
    ELSIF p_famiglia = 'RETTIFICA' THEN
        SELECT count(*) INTO v_n_righe
          FROM magazzino.rettifiche_righe r
         WHERE r.rettifica_id = p_documento_id;
    ELSE
        SELECT count(*) INTO v_n_righe
          FROM magazzino.trasferimenti_righe r
         WHERE r.trasferimento_id = p_documento_id;
    END IF;

    IF v_n_righe = 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_MAG_DOCUMENTO_SENZA_RIGHE',
            'reason',     'DOCUMENTO_SENZA_RIGHE',
            'reason_key', 'magazzino.documenti_interni.registra_reason.senza_righe',
            'dettaglio',  jsonb_build_object('famiglia', p_famiglia,
                                             'documento_id', p_documento_id),
            -- «Il documento %s non ha righe: niente da registrare.»
            'valori',     jsonb_build_array(p_documento_id::text));
        RETURN v_motivi;
    END IF;

    -- ============================================================
    -- MOTIVO 3 — la prima riga che la primitiva rifiuterebbe.
    --   Inventario: dal PIANO (fn_inventario_piano), che e' la sede che
    --   fn_posta_inventario legge — l'esito NON_POSTABILE lo calcola gia'
    --   con script.fn_check_riga_magazzino.
    --   Rettifica: non ha un piano (i delta sono dati), quindi la stessa
    --   check riga per riga, in ordine di id: la prima che parla vince.
    -- ============================================================
    IF p_famiglia = 'INVENTARIO' THEN
        SELECT pi.riga_id, pi.articolo_id, pi.lotto_id, pi.asset_id, pi.ubicazione_id
          INTO v_riga_id, v_articolo_id, v_lotto_id, v_asset_id, v_ubicazione
          FROM magazzino.fn_inventario_piano(p_documento_id) pi
         WHERE pi.esito = 'NON_POSTABILE'
           AND pi.riga_id IS NOT NULL
         ORDER BY pi.riga_id
         LIMIT 1;
    ELSIF p_famiglia = 'RETTIFICA' THEN
        SELECT r.id, r.articolo_id, r.lotto_id, r.asset_id, r.ubicazione_id
          INTO v_riga_id, v_articolo_id, v_lotto_id, v_asset_id, v_ubicazione
          FROM magazzino.rettifiche_righe r
         WHERE r.rettifica_id = p_documento_id
           AND jsonb_array_length(
                   script.fn_check_riga_magazzino(v_magazzino_id, r.articolo_id,
                                                  r.lotto_id, r.asset_id, r.ubicazione_id)) > 0
         ORDER BY r.id
         LIMIT 1;
    ELSE
        -- rev 2026-09-28 — il TRASFERIMENTO INTERNO (D-L2-g), tre domande per
        -- riga, in ordine di id: la prima che parla vince.
        -- (a) Nello stesso magazzino una riga deve andare da un'ubicazione a
        --     un'ALTRA: senza le due ubicazioni partenza e arrivo coincidono.
        --     (Due ubicazioni uguali le rifiuta gia' il CHECK di riga.)
        IF v_magazzino_to = v_magazzino_id THEN
            SELECT r.id INTO v_riga_id
              FROM magazzino.trasferimenti_righe r
             WHERE r.trasferimento_id = p_documento_id
               AND (r.ubicazione_id_da IS NULL OR r.ubicazione_id_a IS NULL)
             ORDER BY r.id
             LIMIT 1;
            IF v_riga_id IS NOT NULL THEN
                v_motivi := v_motivi || jsonb_build_object(
                    'codice',     'E_MAG_TRASFERIMENTO_STESSA_POSIZIONE',
                    'reason',     'RIGHE_NON_POSTABILI',
                    'reason_key', 'magazzino.documenti_interni.registra_reason.righe_non_postabili',
                    'dettaglio',  jsonb_build_object('famiglia', p_famiglia,
                                                     'documento_id', p_documento_id,
                                                     'riga_id', v_riga_id,
                                                     'riga_reason', 'STESSA_POSIZIONE'),
                    -- «Riga %s del trasferimento: partenza e arrivo coincidono. ...»
                    'valori',     jsonb_build_array(v_riga_id::text));
                RETURN v_motivi;
            END IF;
        END IF;
        -- (b) la partenza, come la vedrebbe la primitiva (uscita)...
        SELECT r.id, r.articolo_id, r.lotto_id, r.asset_id, r.ubicazione_id_da
          INTO v_riga_id, v_articolo_id, v_lotto_id, v_asset_id, v_ubicazione
          FROM magazzino.trasferimenti_righe r
         WHERE r.trasferimento_id = p_documento_id
           AND jsonb_array_length(
                   script.fn_check_riga_magazzino(v_magazzino_id, r.articolo_id,
                                                  r.lotto_id, r.asset_id, r.ubicazione_id_da)) > 0
         ORDER BY r.id
         LIMIT 1;
        -- (c) ...e l'arrivo (entrata). Il motivo comune sotto rilegge la riga
        --     col magazzino giusto: per l'arrivo e' quello di destinazione.
        IF v_riga_id IS NULL THEN
            SELECT r.id, r.articolo_id, r.lotto_id, r.asset_id, r.ubicazione_id_a
              INTO v_riga_id, v_articolo_id, v_lotto_id, v_asset_id, v_ubicazione
              FROM magazzino.trasferimenti_righe r
             WHERE r.trasferimento_id = p_documento_id
               AND jsonb_array_length(
                       script.fn_check_riga_magazzino(v_magazzino_to, r.articolo_id,
                                                      r.lotto_id, r.asset_id, r.ubicazione_id_a)) > 0
             ORDER BY r.id
             LIMIT 1;
            IF v_riga_id IS NOT NULL THEN
                v_magazzino_id := v_magazzino_to;
            END IF;
        END IF;
    END IF;

    IF v_riga_id IS NOT NULL THEN
        -- Il motivo della riga, dalla STESSA funzione che la primitiva
        -- chiama: il codice e i valori restano i suoi, cosi' la frase che
        -- l'operatore legge e' quella di sempre.
        v_motivi_riga := script.fn_check_riga_magazzino(
                             v_magazzino_id, v_articolo_id,
                             v_lotto_id, v_asset_id, v_ubicazione);
        v_primo := v_motivi_riga -> 0;

        IF v_primo IS NOT NULL THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     v_primo ->> 'codice',
                -- reason e reason_key sono del DOCUMENTO: il tooltip del
                -- pulsante dice che ci sono righe da sistemare, il dettaglio
                -- della singola riga sta nella lista delle righe (e qui sotto).
                'reason',     'RIGHE_NON_POSTABILI',
                'reason_key', 'magazzino.documenti_interni.registra_reason.righe_non_postabili',
                'dettaglio',  COALESCE(v_primo -> 'dettaglio', '{}'::jsonb)
                              || jsonb_build_object('famiglia', p_famiglia,
                                                    'documento_id', p_documento_id,
                                                    'riga_id', v_riga_id,
                                                    'riga_reason', v_primo ->> 'reason',
                                                    'riga_reason_key', v_primo ->> 'reason_key'),
                'valori',     COALESCE(v_primo -> 'valori', '[]'::jsonb));
        END IF;
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_documento_interno_registrabile(p_famiglia text, p_documento_id bigint)
IS 'I motivi che impediscono di REGISTRARE un documento interno di magazzino (p_famiglia = INVENTARIO | RETTIFICA). Funzione PURA: torna [] se si puo'' registrare, altrimenti un array ORDINATO di {codice, reason, reason_key, dettaglio, valori}. I motivi sono i TRE rifiuti delle madri del posting, in quest''ordine (precedenza dichiarata, si esce al primo): stato diverso da CONFIRM (E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA, con reason DOCUMENTO_NON_CONFERMATO | DOCUMENTO_GIA_REGISTRATO | DOCUMENTO_ANNULLATO secondo lo stato: un codice, tre tooltip), nessuna riga (E_MAG_DOCUMENTO_SENZA_RIGHE), una riga che la primitiva rifiuterebbe — li'' il `codice` e i `valori` sono quelli del PRIMO motivo di script.fn_check_riga_magazzino (la stessa funzione che magazzino.fn_scrivi_movimento chiama), mentre `reason` e `reason_key` sono del documento (RIGHE_NON_POSTABILI). ⭐ La chiamano le due madri (fn_posta_inventario, fn_posta_rettifica) e le due capability (script.fn_available_actions_inventario / _rettifica): una sede sola, perche'' un pulsante non puo'' promettere cio'' che la madre rifiutera'' (linee-guida-sql §12.1, §12.5.2). INVOKER e STABLE: sotto RLS un documento fuori perimetro NON C''E'' e si solleva E_MAG_DOCUMENTO_NON_TROVATO, mai [] (sarebbe un fail-open). Brief: brief-db-magazzino-lotto-2-bis-be-fe R-1. rev 2026-09-28 (brief-db-magazzino-lotto-3-scarico-da-ddt, P-10): terza famiglia TRASFERIMENTO (il trasferimento interno, D-L2-g). Stato stato_trasferimento, righe trasferimenti_righe; al motivo 3 tre domande per riga: nello stesso magazzino servono due ubicazioni (E_MAG_TRASFERIMENTO_STESSA_POSIZIONE), poi la partenza (magazzino di origine, ubicazione_id_da) e l''arrivo (magazzino di destinazione, ubicazione_id_a) con script.fn_check_riga_magazzino.';
```

</div>

---
{% include-markdown "signature-core.md" %}
