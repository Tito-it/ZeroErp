{% include-markdown "it/dbzero/script/manual/fn_available_actions_reso.md" %}
# ⚙️ Funzione `fn_available_actions_reso`

```sql
CREATE FUNCTION fn_available_actions_reso(p_reso_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_available_actions_reso(p_reso_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: capability reso per il detail API (data-driven,
--   config.transizioni_stati_reso). Mirror ridotto di
--   fn_available_actions_ddt (no push_commessa, no pdf).
--   rev 2026-07-16: + enabled/reason/reason_key da meta.requires_righe
--   (documento vuoto non avanza di stato).
--   rev 2026-08-06: + target_state_descrizione, la forma leggibile
--   dello stato di destinazione. Serve alla frase di conferma
--   «portare il documento nello stato X»: il codice_interno non e'
--   quella forma (DRAFT -> Bozza) e tradurlo nel FE sarebbe una
--   seconda copia del vocabolario degli stati.
--   rev 2026-08-11: + stato_info_key, la nota che spiega cosa sta
--   succedendo quando il documento e' in uno stato chiuso. Arriva dal
--   `meta` dello stato, e viene emessa SEMPRE che lo stato la dichiari —
--   anche accanto a un'azione ancora abilitata: la nota spiega lo STATO,
--   non risponde a una barra vuota (decisione §5 di Tid, gia' applicata a
--   preventivo/ordine/DDT con 20260810-04/-05/-06). Questo dominio era
--   fra i cinque che non emettevano affatto il campo, mentre il drawer lo
--   legge gia': il cablaggio c'era ed era inerte.
--   ⭐ rev 2026-08-20: la transizione ad ANNULLATO si DISABILITA COL
--   MOTIVO quando il reso ha un accredito registrato. Applica la regola
--   di frontend-standards — «permesso => nascondi, STATO => disabilita
--   col motivo» — ora scritta anche per il DB in linee-guida-sql §12:
--   avere un accredito e' uno stato che CAMBIA (si disfa l'accredito e
--   l'annullo torna possibile), quindi il bottone resta a video e
--   spiega. Cambia la decisione del §38.6 del brief nota di credito, che
--   lo lasciava acceso e muto.
--   ⭐ Nessun flag di testata `ha_accrediti`: la terna
--   enabled/reason/reason_key esiste gia' PER AZIONE, e un flag di
--   documento spegnerebbe anche le transizioni che non c'entrano.
--   Modello: fn_available_actions_ddt, che disabilita la sola
--   transizione EMESSO con un motivo suo.
--   ⚠️ Il predicato e' lo STESSO EXISTS della guardia di
--   vendite.fn_annulla_reso (E_RESO_ANNULLO_CON_ACCREDITO, 933): se i
--   due divergono, il bottone e' grigio quando l'annullo passerebbe — o
--   peggio il contrario.
--   ⚠️ La PROPRIETA' nel meta si chiama `nessuna_azione_key` mentre il
--   campo del blob si chiama `stato_info_key`. L'asimmetria e' voluta:
--   scripts/check_i18n_keys.py trova le chiavi seminate per QUEL nome
--   (RE_SEED_KEY sui CSV, elenco _PROP_KEY), e rinominarla senza toccare
--   il guard lo renderebbe verde per cecita'.
--   ⚠️ Il campo e' SEMPRE presente nel blob, col valore a null quando non
--   si applica: filtrare per presenza risponde vero per tutti i documenti,
--   va guardato il valore.
--   brief-db-vie-uscita-operatore §12.6; attivita-urgenti-del-10-08 §3;
--   brief-design-note-credito-resi §43.
--   ⭐ rev 2026-09-28 (brief-db-magazzino-lotto-3-bis-carico-da-reso, P-6):
--   la transizione a CONFERMATO si DISABILITA COL MOTIVO quando la merce
--   non puo' rientrare — il primo motivo di script.fn_check_reso_merce, la
--   STESSA funzione che solleva vendite.fn_conferma_reso. E' uno stato che
--   cambia (si sceglie il magazzino, si scrivono i rientri): disabilita,
--   non nasconde.
--   ⭐ rev 2026-10-14 (brief-db-reso-motivi-conferma-con-valori): la
--   CONFERMATO porta anche `reasons`, l'array intero dei motivi della
--   merce coi loro `valori` (i segnaposti {0}, {1}, {2} delle frasi),
--   come la EMESSO della bolla. Il primo motivo si deriva dall'array.
--   La precedenza fra i motivi sta UNA volta nelle LATERAL `p`/`m`, e
--   la leggono enabled, reason, reason_key e reasons.
--   ⭐ rev 2026-10-25 (20261025-21, brief-modello-documento-vendita §7, M-3):
--   il PERMESSO del passaggio nasconde l'azione (linee-guida-sql §12.1:
--   permesso => nascondi). L'azione che il passaggio chiede la dice la sua
--   riga della matrice, letta da script.fn_doc_passaggio (il lettore unico,
--   lo stesso del verbo e del backend); chi non ce l'ha
--   (script.fn_check_azione_processo, la stessa regola del verbo) non vede il
--   bottone. Una riga senza azione resta a tutti: il permesso sul documento
--   lo controlla il backend.
DECLARE
    -- Tipi nudi solo per valori CALCOLATI (azioni e motivi jsonb, flag,
    -- motivi e chiavi i18n composti): nessuna colonna di cui siano il riflesso.
    v_stato_id   vendite.resi.stato_doc_reso_id%TYPE;
    v_utente     config.user_override_azioni.auth_user_id%TYPE;
    v_stato_cod  config.stati_doc_reso.codice_interno%TYPE;
    v_stato_info_key text;
    v_actions    jsonb;
    v_can_change boolean := false;
    v_ha_righe   boolean := false;
    v_ha_accrediti boolean := false;
    v_reso         vendite.resi%ROWTYPE;
    v_motivi_merce jsonb := '[]'::jsonb;
    v_motivo_merce jsonb;
    c_non_edit_draft CONSTANT jsonb :=
        '["numero","sorgente_tipo_id","sorgente_uid","billing_account_id","emittente_fiscale_id"]'::jsonb;
    -- La testata nello stato, dal montaggio del lock (rev 2026-10-10):
    -- {modificabile, non_modificabili}.
    v_testata jsonb;
BEGIN
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    SELECT r.stato_doc_reso_id, sdr.codice_interno,
           sdr.meta->>'nessuna_azione_key'
      INTO v_stato_id, v_stato_cod, v_stato_info_key
      FROM vendite.resi r
      JOIN config.stati_doc_reso sdr ON sdr.id = r.stato_doc_reso_id
     WHERE r.id = p_reso_id;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    -- ⭐ Il primo motivo FISICO della conferma (rev 2026-09-28): solo in
    -- bozza, l'unico stato da cui si conferma. NULL = nessun motivo.
    IF v_stato_cod = 'DRAFT' THEN
        SELECT r.* INTO v_reso FROM vendite.resi r WHERE r.id = p_reso_id;
        -- L'array intero va in `reasons`; il primo motivo si deriva da
        -- lui, cosi' le due letture non si separano (rev 2026-10-14).
        v_motivi_merce := script.fn_check_reso_merce(v_reso);
        v_motivo_merce := v_motivi_merce -> 0;
    END IF;

    -- Precondizione "documento non vuoto" per le transizioni che la
    -- esigono (meta.requires_righe). La fn sa solo COME contare le
    -- proprie righe: specchia il guard di fn_conferma_reso
    -- (E_RESO_SENZA_RIGHE): riga attiva.
    v_ha_righe := EXISTS (
        SELECT 1 FROM vendite.resi_righe rr
         WHERE rr.reso_id = p_reso_id
           AND rr.attivo IS TRUE
    );

    -- ⭐ Precondizione "nessun accredito registrato" per la
    -- transizione ad ANNULLATO. STESSO PREDICATO della guardia in
    -- vendite.fn_annulla_reso: l'ESISTENZA di una riga di ponte, non
    -- lo stato delle rettifiche — se l'accredito e' ormai troppo
    -- tardi per essere disfatto lo dice la sua madre con
    -- E_ACCREDITO_ANNULLO_NON_AMMESSO, e ricalcolarlo qui sarebbe
    -- una seconda copia della stessa regola.
    -- ⚠️ vendite.resi_righe_accrediti NON ha RLS (verificato
    -- 2026-08-20): questa lettura vede tutto il ponte anche da
    -- SECURITY INVOKER. Se un domani la RLS ci arrivasse, chi non
    -- vedesse il ponte leggerebbe «nessun accredito» e si
    -- troverebbe il bottone acceso e il 409 in faccia: allora
    -- servirebbe una SECURITY DEFINER, non un COALESCE.
    v_ha_accrediti := EXISTS (
        SELECT 1
          FROM vendite.resi_righe_accrediti rra
          JOIN vendite.resi_righe rr ON rr.id = rra.resi_riga_id
         WHERE rr.reso_id = p_reso_id
    );

    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'key',              t.meta->>'action_key',
                'target_state',     sa.codice_interno,
                -- Forma leggibile della destinazione: la colonna
                -- accanto, nello stesso JOIN. Il FE non puo'
                -- derivarla dal codice.
                'target_state_descrizione', sa.descrizione,
                'label_key',        t.meta->>'label_key',
                'requires_confirm', COALESCE((t.meta->>'requires_confirm')::boolean, false),
                'outlined',         COALESCE((t.meta->>'outlined')::boolean, false),
                -- I tre motivi e la loro PRECEDENZA stanno nelle
                -- LATERAL `p`/`m` qui sotto: i quattro campi li
                -- leggono e basta, cosi' non possono dissentire.
                'enabled',          NOT (m.con_accrediti OR m.senza_righe OR m.merce),
                'reason',           CASE
                                      WHEN m.con_accrediti THEN 'RESO_CON_ACCREDITI'
                                      WHEN m.senza_righe   THEN 'DOCUMENTO_SENZA_RIGHE'
                                      WHEN m.merce         THEN v_motivo_merce ->> 'reason'
                                    END,
                'reason_key',       CASE
                                      WHEN m.con_accrediti THEN 'vendite.reso.annulla_reason.con_accrediti'
                                      WHEN m.senza_righe   THEN 'common.azione_reason.senza_righe'
                                      WHEN m.merce         THEN v_motivo_merce ->> 'reason_key'
                                    END,
                -- Elenco completo dei motivi della merce, coi loro
                -- `valori` (rev 2026-10-14): la forma della EMESSO
                -- della bolla. La chiave c'e' sempre, null quando a
                -- spegnere l'azione non e' la merce.
                'reasons',          CASE WHEN m.merce THEN v_motivi_merce END
            )
            ORDER BY sa.ordine
        ),
        '[]'::jsonb
    )
    INTO v_actions
    FROM config.transizioni_stati_reso t
    JOIN config.stati_doc_reso sa ON sa.id = t.stato_a_id
    -- L'azione del passaggio dal lettore unico (rev 2026-10-25, M-3).
    CROSS JOIN LATERAL script.fn_doc_passaggio('vendite.resi'::regclass, t.stato_da_id, t.stato_a_id) pz
    -- ⚠️ PRECEDENZA DICHIARATA fra i motivi, scritta UNA volta:
    -- lo SPECIFICO batte il generico.
    --   1. ANNULLATO + accrediti  -> RESO_CON_ACCREDITI
    --   2. requires_righe + vuoto -> DOCUMENTO_SENZA_RIGHE
    --   3. CONFERMATO + merce     -> il motivo fisico (e `reasons`)
    -- Oggi l'1 e il 2 non si incontrano (le `annulla` non dichiarano
    -- requires_righe, e un reso con accrediti ha righe), e nemmeno il
    -- 2 e il 3 (fn_check_reso_merce con zero righe non ha voci). Ma
    -- e' un incastro fra funzioni, non una regola: `m.merce` esclude
    -- i due che lo precedono, o il giorno che la check guardasse il
    -- magazzino prima delle righe `reasons` porterebbe un motivo
    -- accanto a reason = DOCUMENTO_SENZA_RIGHE.
    -- ⚠️ Il match e' su `codice_interno`, la colonna IMMUTABILE: su
    -- `codice` si romperebbe al primo rename fatto dall'utente.
    CROSS JOIN LATERAL (
        SELECT (sa.codice_interno = 'ANNULLATO' AND v_ha_accrediti) AS con_accrediti,
               (COALESCE((t.meta->>'requires_righe')::boolean, false)
                AND NOT v_ha_righe)                                AS senza_righe
    ) p
    CROSS JOIN LATERAL (
        SELECT p.con_accrediti, p.senza_righe,
               (sa.codice_interno = 'CONFERMATO' AND v_motivo_merce IS NOT NULL
                AND NOT p.con_accrediti AND NOT p.senza_righe)     AS merce
    ) m
    WHERE t.stato_da_id = v_stato_id
      AND t.attivo IS TRUE
      -- Permesso => nascondi: chi non ha l'azione del passaggio non vede il bottone.
      AND (pz.azione_processo_codename IS NULL
           OR script.fn_check_azione_processo(v_utente, pz.azione_processo_codename))
      AND COALESCE((t.meta->>'manuale')::boolean, true) IS TRUE
      AND t.meta ? 'action_key'
      AND t.meta ? 'label_key';

    -- Conta anche le azioni disabilitate: la barra azioni deve
    -- comparire proprio per mostrare il pulsante grigio + tooltip.
    v_can_change := jsonb_array_length(v_actions) > 0;

    -- La testata nello stato, letta dal montaggio del lock di testata
    -- (rev 2026-10-10): le colonne «sempre» della capability, poi quelle
    -- che il lock blocca in questo stato. Nessuno stato scritto qui.
    v_testata := script.fn_doc_testata_in_stato('vendite.resi'::regclass, v_stato_cod, c_non_edit_draft);

    RETURN jsonb_build_object(
        'available_actions',   v_actions,
        'can_change_state',    v_can_change,
        'can_edit_testata',  (v_testata ->> 'modificabile')::boolean,
        'can_edit_righe',      (v_stato_cod = 'DRAFT'),
        'non_editable_fields', v_testata -> 'non_modificabili',
        'stato_info_key',      v_stato_info_key,
        'stato_codice',        v_stato_cod
    );
END;
$function$

COMMENT ON FUNCTION script.fn_available_actions_reso(p_reso_id bigint)
IS 'Capability reso per detail API: available_actions (matrice transizioni_stati_reso, filtro manuale) + can_change_state + can_edit_* + non_editable_fields + stato_codice. Mirror ridotto di fn_available_actions_ddt (no push/pdf). rev 2026-07-16: ogni azione espone enabled/reason/reason_key; se la transizione ha meta.requires_righe e il reso non ha righe attive -> enabled=false + reason DOCUMENTO_SENZA_RIGHE (predicato specchiato dal guard E_RESO_SENZA_RIGHE). rev 2026-08-06: + target_state_descrizione accanto a target_state. rev 2026-08-11: + stato_info_key, la nota di stato letta dal meta dello stato corrente ed emessa SEMPRE che lo stato la dichiari. ⭐ rev 2026-08-20 (segnalazione BE): la transizione ad ANNULLATO si DISABILITA COL MOTIVO quando il reso ha un accredito registrato -> enabled=false, reason RESO_CON_ACCREDITI, reason_key vendite.reso.annulla_reason.con_accrediti. Applica la regola di frontend-standards, ora scritta anche per il DB in linee-guida-sql §12: «permesso => nascondi, STATO => disabilita col motivo». Avere un accredito e'' uno stato che CAMBIA — si disfa l''accredito e l''annullo torna possibile — quindi il bottone non va nascosto ne'' lasciato acceso e muto: resta a video e spiega. Cambia la decisione del §38.6 del brief nota di credito. ⭐ NIENTE flag di testata `ha_accrediti`, che il BE aveva chiesto: la terna enabled/reason/reason_key esiste gia'' PER AZIONE ed e'' gia'' letta dal FE, mentre un flag di documento spegnerebbe anche le transizioni che non c''entrano e vorrebbe cablaggio nuovo. Modello: fn_available_actions_ddt, che disabilita la sola transizione EMESSO con un motivo suo. ⚠️ Il predicato e'' lo STESSO EXISTS della guardia di vendite.fn_annulla_reso (933): capability e guard devono dire la stessa cosa, o il bottone e'' grigio quando l''annullo passerebbe — o peggio il contrario. ⚠️ vendite.resi_righe_accrediti NON ha RLS (verificato): se un domani ce l''avesse, chi non vede il ponte leggerebbe «nessun accredito» e si troverebbe il bottone acceso e il 409 in faccia, e servirebbe una SECURITY DEFINER. ⚠️ PRECEDENZA fra motivi dichiarata nel corpo: lo SPECIFICO (accrediti) batte il generico (senza righe). ⚠️ La PROPRIETA'' nel meta resta nessuna_azione_key mentre il campo del blob si chiama stato_info_key. 🔴 Richiede la chiave i18n vendite.reso.annulla_reason.con_accrediti in it.json e en.json: senza, check_i18n_keys.py diventa rosso e il tooltip resta vuoto. brief-db-vie-uscita-operatore §12.6; attivita-urgenti-del-10-08 §3; brief-design-note-credito-resi §43. rev 2026-09-27 (20260927-15): le azioni non portano piu'' la chiave icon. Il DB manda il SIGNIFICATO (key), il frontend sceglie il segno dal key con una mappa verbo -> icona in core/ (decisione D-1 di Tid, opzione A): un segno scritto qui era l''unico dell''app che non passava dalle costanti del frontend, e lo stesso verbo ne portava due. Brief: brief-db-icone-azioni-per-significato (D-1). rev 2026-09-28 (20260928-12): le azioni non portano piu'' la chiave severity. Come l''icona, il colore del pulsante lo decide il VERBO, uguale in tutti i domini, e il frontend lo ricava dal key (mappa verbo -> aspetto in core/, decisione di Tid): lo stesso verbo portava colori diversi fra i domini. label_key e outlined restano dati. Brief: brief-db-icone-azioni-per-significato (§9). ⭐ rev 2026-09-28 (brief-db-magazzino-lotto-3-bis-carico-da-reso, P-6): la transizione a CONFERMATO si disabilita col PRIMO MOTIVO FISICO di script.fn_check_reso_merce (magazzino di rientro mancante, rientri incompleti, merce non ricollocabile, rientro oltre l''uscito), la stessa funzione che solleva vendite.fn_conferma_reso: reason e reason_key del motivo, chiavi vendite.reso.azione_reason.*. Precedenza: accrediti, poi righe, poi merce. rev 2026-10-10 (brief-db-testata-dopo-emissione fase 2): non_editable_fields e can_edit_testata si leggono dal montaggio del lock di testata con script.fn_doc_testata_in_stato: le colonne «sempre» della capability seguite da quelle che il lock blocca nello stato, e can_edit_testata vero se nello stato almeno una colonna nominata si cambia. Ritirate le liste scritte a mano dei campi bloccati fuori bozza (la terza copia della regola, accanto a lock e backend): con D-8/D-10 le colonne aperte dopo l''emissione (note, trasporto, valido_al e CIG/CUP del contratto…) si cambiano negli stati del montaggio e si fermano a documento chiuso. ⭐ rev 2026-10-14 (brief-db-reso-motivi-conferma-con-valori): l''azione CONFERMATO porta anche reasons, l''array intero di script.fn_check_reso_merce coi valori dei motivi (i segnaposti delle frasi vendite.reso.azione_reason.*), con la forma della EMESSO di fn_available_actions_ddt; null quando a spegnere l''azione non e'' la merce. Il primo motivo (reason, reason_key) si deriva dallo stesso array. La precedenza fra i tre motivi sta una volta nelle LATERAL delle condizioni, letta da enabled, reason, reason_key e reasons. ⭐ rev 2026-10-25 (20261025-21, brief-modello-documento-vendita §7, M-3): un passaggio con un''azione di processo sulla sua riga della matrice (letta da script.fn_doc_passaggio) si NASCONDE a chi non ha l''azione (script.fn_check_azione_processo, utente da app.current_user_id): permesso => nascondi, stato => disabilita col motivo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
