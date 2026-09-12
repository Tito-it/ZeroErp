# ⚙️ Funzione `fn_pgtap_crea_cliente_ba`

```sql
CREATE FUNCTION fn_pgtap_crea_cliente_ba(p_etichetta text, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_cliente_ba(p_etichetta text DEFAULT 'pgTAP'::text, p_utility_id integer DEFAULT NULL::integer, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(billing_account_id bigint, istanza_utility_id bigint, soggetto_ruolo_id bigint, soggetto_id uuid, utility_id integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un cliente FATTURABILE, cioe'
--   la catena minima che i documenti pretendono: soggetto ->
--   ruolo CL -> istanza utility -> billing account.
-- Uso:
--   CREATE TEMP TABLE tmp_cli AS
--   SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('RLS preventivi');
-- ⭐ Terzo parametro (2026-09-09): l'emittente a cui LEGARE il BA.
--   Serve alle testate con `billing_account_id` NOT NULL —
--   contratti e offerte_commerciali — il cui guard
--   `trgfn_<doc>_guard_emittente_ba` confronta l'emittente del
--   documento con `anagrafiche.fn_get_emittente_fiscale_pk(ba)`.
--   Senza legame quella funzione NON fallisce: ricade
--   sull'emittente di DEFAULT, cioe' risponde un'altra azienda.
DECLARE
    v_soggetto_id anagrafiche.soggetti.id%TYPE;
    v_sr_id       anagrafiche.soggetti_ruoli.id%TYPE;
    v_ist_id      anagrafiche.billing_account.istanza_utility_id%TYPE;
    v_ba_id       anagrafiche.billing_account.id%TYPE;
    v_utility_id  anagrafiche.billing_account.utility_id%TYPE;
    v_codice      text;
    v_link_sr     anagrafiche.emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id%TYPE;
BEGIN
    v_utility_id := COALESCE(
        p_utility_id,
        (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1));

    IF v_utility_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_cliente_ba: nessuna utility a catalogo';
    END IF;

    -- Codice libero: `codice` e' UNIQUE e non filtra su nessuno
    -- stato, quindi una sigla fissa farebbe collidere la seconda
    -- chiamata con la prima — lo stesso motivo per cui esistono
    -- fn_pgtap_piva_libera e la sigla PGTRnnnn dell'emittente.
    SELECT 'PGTAPBA' || lpad((COALESCE(max(substring(b.codice from 8)::bigint), 0) + 1)::text, 5, '0')
      INTO v_codice
      FROM anagrafiche.billing_account b
     WHERE b.codice ~ '^PGTAPBA[0-9]{5}$';
    v_codice := COALESCE(v_codice, 'PGTAPBA00001');

    v_soggetto_id := dbops.fn_pgtap_crea_soggetto_pg(
                         'Cliente ' || p_etichetta || ' ' || v_codice);
    v_sr_id       := dbops.fn_pgtap_crea_soggetto_ruolo(
                         v_soggetto_id, 'CL'::character varying);

    -- ⛔ LA FINESTRA DIFFERITA. `trgfn_istanze_utilities_require_utility_dichiarata`
    --   verifica al COMMIT che l'istanza abbia un satellite
    --   (BA / dato precontrattuale / cliente). Con i vincoli
    --   IMMEDIATE — come li mette il preambolo obbligatorio dei
    --   pgTAP — scatterebbe sul primo INSERT, cioe' prima che il
    --   billing account possa esistere.
    SET CONSTRAINTS ALL DEFERRED;

    -- ⚠️ `fittizia = true`: chk_istanza_fittizia_indirizzo vuole
    --   O il flag O un indirizzo di dettaglio, e a una fixture
    --   l'indirizzo non serve.
    INSERT INTO anagrafiche.istanze_utilities (codice, soggetto_id, fittizia)
    VALUES (v_codice, v_soggetto_id, TRUE)
    RETURNING id INTO v_ist_id;

    -- ⚠️ `validita` NON si nomina: e' GENERATED (PG18).
    -- ⚠️ `valuta_id` VALORIZZATA, e non e' pignoleria.
    --   La risoluzione della valuta di un documento e' una
    --   catena «BA -> emittente -> gestore»: su dbdev regge
    --   l'ultimo anello, perche' un gestore c'e'. Su un database
    --   ricostruito dai changelog non c'e' nessuno dei tre, e il
    --   primo documento muore con «Configurazione mancante:
    --   valuta non risolta (BA/emittente/gestore)».
    --   ⭐ Misurato il 2026-09-09: e' la causa di 11 dei 185 file
    --   di vendite che sullo scratch morivano nel fixture.
    --   Chiudendo l'anello piu' vicino al documento, la fixture
    --   non dipende piu' da com'e' configurata la macchina.
    -- ⛔ SENZA `RETURNING` (rev 20260912-38), ed e' il punto che rende
    --   l'helper usabile anche come `zeroerp_app`. La policy di
    --   lettura del BA risolve l'emittente dal legame in
    --   emittenti_fiscali_billing_account, e quel legame lo scrive
    --   il trigger AFTER `z90_link_ef` — cioe' DOPO che il
    --   RETURNING ha gia' chiesto di vedere la riga: sotto la RLS il
    --   BA non ancora mappato ricade sull'emittente di DEFAULT, e
    --   se chi agisce non e' quello, l'INSERT muore con «la nuova
    --   riga viola la regola di sicurezza». Riletto dal `codice`
    --   (UNIQUE) a istruzione finita, il legame c'e' e la riga si
    --   vede. Da owner non cambia niente.
    INSERT INTO anagrafiche.billing_account
        (istanza_utility_id, soggetto_ruolo_id, utility_id,
         codice, categoria_cliente_id, valuta_id)
    VALUES (v_ist_id, v_sr_id, v_utility_id, v_codice,
            (SELECT cc.id FROM anagrafiche.categorie_clienti cc
              ORDER BY cc.id LIMIT 1),
            (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1));

    SELECT b.id INTO v_ba_id
      FROM anagrafiche.billing_account b
     WHERE b.codice = v_codice;

    IF v_ba_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_cliente_ba: il billing account % e'' stato scritto ma non si legge: sotto la RLS serve un operatore in sessione (il trigger z90 lo lega al SUO emittente), oppure il legame va chiesto col terzo parametro da owner',
            v_codice;
    END IF;

    -- ⭐ IL LEGAME BA -> EMITTENTE, se il chiamante lo chiede.
    --   `is_default = false`: e' un legame PER QUESTO BA, non
    --   l'emittente di default dell'installazione — quello e' una
    --   riga con `billing_account_id IS NULL` e non va toccata da
    --   una fixture.
    -- ⚠️ Con un operatore in sessione il legame lo ha GIA' scritto
    --   il trigger z90, verso l'emittente di chi agisce: si
    --   rispetta (uq_emittenti_fiscali_ba non ammette il secondo)
    --   e si verifica che sia quello chiesto — un BA legato a
    --   un'altra azienda per silenzio sarebbe la fixture sbagliata
    --   contro cui questo parametro esiste.
    IF p_emittente_soggetto_ruolo_id IS NOT NULL THEN
        SELECT efba.emittente_soggetto_ruolo_id INTO v_link_sr
          FROM anagrafiche.emittenti_fiscali_billing_account efba
         WHERE efba.billing_account_id = v_ba_id;

        IF v_link_sr IS NULL THEN
            INSERT INTO anagrafiche.emittenti_fiscali_billing_account
                (emittente_soggetto_ruolo_id, billing_account_id, is_default)
            VALUES (p_emittente_soggetto_ruolo_id, v_ba_id, false);
        ELSIF v_link_sr <> p_emittente_soggetto_ruolo_id THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_cliente_ba: il billing account % e'' gia'' legato all''emittente % (trigger z90, operatore in sessione), non a % come chiesto: costruire il cliente PRIMA di aprire il contesto, o non passare il terzo parametro',
                v_ba_id, v_link_sr, p_emittente_soggetto_ruolo_id;
        END IF;
    END IF;

    -- Saga completa: i guard differiti scattano QUI, su un mondo
    -- finito. ⚠️ Senza la richiusura il ROLLBACK del test se li
    -- porterebbe via NON verificati.
    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN QUERY
    SELECT v_ba_id, v_ist_id, v_sr_id, v_soggetto_id, v_utility_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_cliente_ba(p_etichetta text, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint)
IS 'Fixture pgTAP: crea la catena minima di un cliente fatturabile (soggetto -> ruolo CL -> istanza utility -> billing account). Il terzo parametro, opzionale, e'' il soggetto_ruolo dell''EMITTENTE a cui legare il billing account in anagrafiche.emittenti_fiscali_billing_account: serve alle testate con billing_account_id NOT NULL (contratti, offerte_commerciali), il cui guard confronta l''emittente del documento con anagrafiche.fn_get_emittente_fiscale_pk(ba). ⚠️ Senza legame quella funzione non fallisce: ricade sull''emittente di DEFAULT, cioe'' risponde un''altra azienda. ⭐ Rev 20260912-38: usabile anche come zeroerp_app CON un operatore in sessione — l''INSERT del BA non fa piu'' RETURNING (sotto la RLS la riga non ancora mappata non si vede) e il legame lo lascia scrivere al trigger z90 verso l''emittente di chi agisce, verificando che coincida con quello chiesto. Da owner: costruire il cliente PRIMA di aprire il contesto, o il trigger e il terzo parametro si scontrano. Brief: brief-db-perimetro-emittente-righe-documento.md';
```

---
{% include-markdown "signature-core.md" %}
