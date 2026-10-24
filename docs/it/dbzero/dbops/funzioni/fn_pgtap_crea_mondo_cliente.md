{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_mondo_cliente.md" %}
# ⚙️ Funzione `fn_pgtap_crea_mondo_cliente`

```sql
CREATE FUNCTION fn_pgtap_crea_mondo_cliente(p_etichetta text, p_sigla character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_mondo_cliente(p_etichetta text DEFAULT 'pgTAP'::text, p_sigla character varying DEFAULT NULL::character varying)
 RETURNS TABLE(emittente_fiscale_id bigint, emittente_codice character varying, emittente_soggetto_ruolo_id bigint, auth_user_id integer, identita_id bigint, billing_account_id bigint, istanza_utility_id bigint, cliente_soggetto_ruolo_id bigint, cliente_soggetto_id uuid, utility_id integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP il mondo minimo di un test di
--   dominio in una chiamata — l'azienda con il suo operatore, il
--   contesto aperto su di lui e un cliente fatturabile legato a
--   QUELLA azienda — con la regola d'ordine dentro l'oggetto.
-- Uso, al posto del blocco «refs» e della riga di contesto:
--   CREATE TEMP TABLE tmp_mondo AS
--   SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('DASH');
-- ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper: chi vuole la
--   finestra differita la riapre subito dopo con
--   SET CONSTRAINTS ALL DEFERRED, e lo dichiara in testa al file.
-- Rev 2026-10-21 (20261021-68): con un contesto gia' aperto l'azienda
--   di chi agisce la dice script.fn_resolve_emittente_for_user, come
--   per il legame del BA: anche il super admin che ha scelto
--   l'emittente in alto (app.current_emittente_id) ha un mondo.
-- Rev 2026-10-24 (20261024-39, §4-octies): il ramo B legge l'azienda
--   dal building block dbops.fn_pgtap_azienda_di_chi_agisce.
DECLARE
    v_user_id   anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_identita  anagrafiche.identita_digitali.id%TYPE;
    v_ef_id     anagrafiche.emittenti_fiscali.id%TYPE;
    v_ef_codice anagrafiche.emittenti_fiscali.codice%TYPE;
    v_ef_sr_id  anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
    v_ba_id     anagrafiche.billing_account.id%TYPE;
    v_ist_id    anagrafiche.billing_account.istanza_utility_id%TYPE;
    v_cli_sr_id anagrafiche.billing_account.soggetto_ruolo_id%TYPE;
    v_cli_sog   anagrafiche.soggetti.id%TYPE;
    v_utility   anagrafiche.billing_account.utility_id%TYPE;
    v_link_sr   anagrafiche.emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id%TYPE;
BEGIN
    -- La domanda e' «c'e' un contesto?», e si fa alla GUC che le
    -- policy leggono davvero: non a script.fn_pgtap_emittente_operatore(),
    -- che ha un ripiego suo e risponderebbe un emittente anche
    -- senza contesto — qui servirebbe come discriminante, e non lo e'.
    v_user_id := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    IF v_user_id IS NULL THEN
        -- ── RAMO A: nessun contesto (CI, installazione nuova, o
        --    un file che chiama questa funzione per prima).
        --    Il mondo si COSTRUISCE, e il contesto si apre DOPO:
        --    e' l'ordine che il cliente pretende (vedi sotto).
        SELECT ceo.emittente_fiscale_id, ceo.emittente_codice,
               ceo.soggetto_ruolo_id, ceo.auth_user_id, ceo.identita_id
          INTO v_ef_id, v_ef_codice, v_ef_sr_id, v_user_id, v_identita
          FROM dbops.fn_pgtap_crea_emittente_operatore(p_sigla) ceo;

        PERFORM script.fn_pgtap_set_contesto_operatore(v_user_id);
    ELSE
        -- ── RAMO B: un contesto c'e' gia' (dbdev, o la riga di
        --    contesto del template chiamata prima). L'azienda NON
        --    si ricostruisce: il trigger z90 lega il BA a quella
        --    di CHI AGISCE, quindi costruirne una nuova lascerebbe
        --    il cliente legato all'altra e sotto RLS invisibile.
        IF p_sigla IS NOT NULL THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_mondo_cliente: p_sigla = % chiesta con un contesto gia'' aperto (auth_user_id = %): qui l''azienda non si sceglie, e'' quella di chi agisce. Per una SECONDA azienda si chiamano i builder atomici (dbops.fn_pgtap_crea_emittente_operatore + dbops.fn_pgtap_crea_cliente_ba col terzo parametro), prima del contesto',
                p_sigla, v_user_id;
        END IF;

        -- ⭐ L'azienda di chi agisce, dal building block estratto da
        --   qui (rev 20261024-39): la stessa regola di produzione del
        --   trigger z90 (script.fn_resolve_emittente_for_user), coi
        --   suoi controlli (azienda, identita' OPERATORE attiva).
        SELECT a.emittente_fiscale_id, a.emittente_codice,
               a.emittente_soggetto_ruolo_id, a.identita_id
          INTO v_ef_id, v_ef_codice, v_ef_sr_id, v_identita
          FROM dbops.fn_pgtap_azienda_di_chi_agisce('fn_pgtap_crea_mondo_cliente') a;
    END IF;

    -- Il cliente, in entrambi i rami DOPO il contesto e SENZA
    -- terzo parametro: il legame lo scrive il trigger z90 verso
    -- l'emittente di chi agisce, che qui e' quello giusto per
    -- costruzione. Chiederlo anche col parametro farebbe sbattere
    -- i due su uq_emittenti_fiscali_ba (rev 20260912-38).
    SELECT c.billing_account_id, c.istanza_utility_id,
           c.soggetto_ruolo_id, c.soggetto_id, c.utility_id
      INTO v_ba_id, v_ist_id, v_cli_sr_id, v_cli_sog, v_utility
      FROM dbops.fn_pgtap_crea_cliente_ba(p_etichetta) c;

    -- ⚠️ Il legame si VERIFICA, non si spera. Se il trigger ha
    --   legato il BA a un'altra azienda — succede quando il
    --   contesto e' aperto su un operatore di un altro emittente —
    --   il mondo che si sta tornando non e' coerente, e il file
    --   morirebbe venti righe piu' in la' su una policy.
    --   La tabella del legame non e' in RLS: la lettura vale anche
    --   come zeroerp_app.
    SELECT efba.emittente_soggetto_ruolo_id
      INTO v_link_sr
      FROM anagrafiche.emittenti_fiscali_billing_account efba
     WHERE efba.billing_account_id = v_ba_id;

    IF v_link_sr IS DISTINCT FROM v_ef_sr_id THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_mondo_cliente: il billing account % risulta legato all''emittente sr = % invece che a % (l''azienda di chi agisce): il mondo non e'' coerente',
            v_ba_id, v_link_sr, v_ef_sr_id;
    END IF;

    -- Contratto dichiarato, non fiducia nel chiamato: si esce con
    -- i vincoli IMMEDIATE come ogni helper. Oggi e' un no-op —
    -- fn_pgtap_crea_cliente_ba li richiude gia' — e domani e' la
    -- riga che tiene il contratto se quel corpo cambia.
    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN QUERY
    SELECT v_ef_id, v_ef_codice, v_ef_sr_id, v_user_id, v_identita,
           v_ba_id, v_ist_id, v_cli_sr_id, v_cli_sog, v_utility;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_mondo_cliente(p_etichetta text, p_sigla character varying)
IS 'Fixture pgTAP: il MONDO MINIMO di un test di dominio in una chiamata — azienda + operatore + contesto aperto + cliente fatturabile legato a quella azienda — e ritorna tutte le chiavi. ⭐ Esiste per la REGOLA D''ORDINE, non per fare l''elenco della spesa: prima il mondo, poi il contesto, e il legame BA -> emittente lo scrive il trigger z90 verso chi agisce (chiederlo anche col terzo parametro di fn_pgtap_crea_cliente_ba li fa sbattere su uq_emittenti_fiscali_ba). ⚠️ Con un contesto gia'' aperto RIUSA l''azienda di chi agisce e rifiuta p_sigla: una seconda azienda si costruisce coi builder atomici, prima del contesto. ⛔ NON comprende registro (script.fn_pgtap_registro_fattura si semina dal contesto), articolo (i flag sono il caso del test) ne'' i cataloghi di 80_data, che da zero ci sono e vanno scelti con un ORDER BY stabile. ⚠️ Esce con i vincoli IMMEDIATE: chi li vuole differiti riapre con SET CONSTRAINTS ALL DEFERRED e lo dichiara in testa al file (rev 20260921-18). Brief: brief-db-fixture-che-costruiscono-giro-2.md Rev 2026-10-21 (20261021-68, richiesta BE R-2): con un contesto gia'' aperto l''azienda di chi agisce la dice script.fn_resolve_emittente_for_user (l''emittente scelto in alto, app.current_emittente_id, se l''utente lo puo'' usare; altrimenti la riga in config.user_emittenti_fiscali), la stessa regola del trigger che lega il BA: il super admin che ha scelto l''emittente (dev.smoke negli smoke Python) ha un mondo, quello senza scelta e l''operatore senza riga sollevano come prima. Rev 2026-10-24 (20261024-39, brief-modello-documento-vendita §4-octies): quell''azienda viene dal building block dbops.fn_pgtap_azienda_di_chi_agisce, estratto da qui.';
```

</div>

---
{% include-markdown "signature-core.md" %}
