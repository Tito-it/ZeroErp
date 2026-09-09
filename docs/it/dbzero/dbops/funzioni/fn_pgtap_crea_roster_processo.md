# ⚙️ Funzione `fn_pgtap_crea_roster_processo`

```sql
CREATE FUNCTION fn_pgtap_crea_roster_processo(p_processo_codice text, p_sigla character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_roster_processo(p_processo_codice text, p_sigla character varying DEFAULT NULL::character varying)
 RETURNS TABLE(emittente_fiscale_id bigint, emittente_codice character varying, emittente_soggetto_ruolo_id bigint, auth_user_id integer, identita_id bigint)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP una coppia (processo, azienda)
--   che compaia davvero in dbops.vw_processi_roster, costruendo
--   l'intera catena invece di cercarla fra i dati esistenti.
-- Uso:
--   CREATE TEMP TABLE tmp_roster AS
--   SELECT * FROM dbops.fn_pgtap_crea_roster_processo('chiusura_scadenze_daily');
DECLARE
    v_soggetto_id  anagrafiche.soggetti.id%TYPE;
    v_sr_id        anagrafiche.soggetti_ruoli.id%TYPE;
    v_codice       anagrafiche.emittenti_fiscali.codice%TYPE;
    v_ef_id        anagrafiche.emittenti_fiscali.id%TYPE;
    v_auth_user_id anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_identita_id  anagrafiche.identita_digitali.id%TYPE;
    v_try          integer := 0;
    v_libera       boolean := FALSE;
BEGIN
    IF p_processo_codice IS NULL OR btrim(p_processo_codice) = '' THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_roster_processo: p_processo_codice e'' obbligatorio';
    END IF;

    -- La sigla: se non la impone il chiamante se ne cerca una
    -- LIBERA. ⚠️ `uq:codice` e' UNIQUE senza filtro su `attivo`,
    -- quindi una sigla fissa farebbe collidere la seconda corsa
    -- con il residuo della prima — lo stesso difetto per cui
    -- esiste dbops.fn_pgtap_piva_libera.
    -- ⚠️ La forma la impone chk_emittenti_fiscali_codice_forma:
    -- solo maiuscole e cifre, da 2 a 10 caratteri.
    IF p_sigla IS NOT NULL THEN
        v_codice := p_sigla;
    ELSE
        LOOP
            v_try := v_try + 1;
            EXIT WHEN v_try > 9999;
            v_codice := 'PGTR' || lpad(v_try::text, 4, '0');
            IF NOT EXISTS (SELECT 1
                             FROM anagrafiche.emittenti_fiscali e
                            WHERE e.codice = v_codice) THEN
                v_libera := TRUE;
                EXIT;
            END IF;
        END LOOP;

        IF NOT v_libera THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_roster_processo: nessuna sigla PGTRnnnn libera';
        END IF;
    END IF;

    -- 1. L'azienda: soggetto persona giuridica + ruolo EF.
    --    I due helper aprono e richiudono da soli la finestra dei
    --    guard differiti, quindi qui non serve toccarla.
    v_soggetto_id := dbops.fn_pgtap_crea_soggetto_pg(
                         'Emittente pgTAP ' || v_codice);
    v_sr_id       := dbops.fn_pgtap_crea_soggetto_ruolo(
                         v_soggetto_id, 'EF'::character varying);

    -- 2. L'emittente fiscale. ⭐ Nascendo fa nascere anche i suoi
    --    registri di numerazione (vendite.fn_provision_registri_emittente):
    --    e' il percorso reale, e un test che ne avesse bisogno li
    --    trova gia' pronti.
    INSERT INTO anagrafiche.emittenti_fiscali (soggetto_ruolo_id, codice)
    VALUES (v_sr_id, v_codice)
    RETURNING id INTO v_ef_id;

    -- 3. ⭐ Da qui in poi NON si monta niente a mano: l'utente
    --    Django, il soggetto del processo, l'identita' OPERATORE
    --    tecnica, la riga di perimetro in
    --    config.user_emittenti_fiscali e il legame in
    --    dbops.processi_identita li scrive la funzione di
    --    produzione. Se quella catena cambia, il test se ne
    --    accorge invece di continuare a costruire un mondo
    --    che il modello non ammette piu'.
    --    ⚠️ Solleva lei, coi suoi codici registrati, se il
    --    processo non esiste o non e' eleggibile.
    --
    -- ⛔ E VA CHIAMATA DENTRO UNA FINESTRA DIFFERITA, o non parte.
    --   `fn_crea_utente_tecnico` e' a sua volta una SAGA: scrive
    --   il soggetto del processo e SOLO DOPO il suo contatto. Il
    --   guard `trgfn_soggetti_guard_soggetto_contatti` e'
    --   DEFERRABLE INITIALLY DEFERRED proprio per questo, ma qui
    --   i vincoli sono IMMEDIATE per due motivi che si sommano:
    --   il preambolo obbligatorio dei pgTAP (`SET CONSTRAINTS ALL
    --   IMMEDIATE`, presidiato in CI) e la richiusura che
    --   `fn_pgtap_crea_soggetto_pg` fa in uscita, dichiarata nel
    --   suo stesso COMMENT.
    --   ⇒ Senza queste due righe si muore su «Il soggetto non ha
    --   contatti validi» al primo INSERT, cioe' prima che la saga
    --   possa esistere. In produzione non succede: li' nessuno ha
    --   mai messo i vincoli IMMEDIATE.
    SET CONSTRAINTS ALL DEFERRED;

    v_auth_user_id := script.fn_crea_utente_tecnico(
                          p_processo_codice  := p_processo_codice,
                          p_emittente_codice := v_codice);

    -- Saga completa: i guard differiti scattano QUI, su un mondo
    -- finito. ⚠️ La richiusura non e' facoltativa — senza, il
    -- ROLLBACK del test se li porterebbe via NON verificati, e il
    -- test sarebbe verde per sottrazione.
    SET CONSTRAINTS ALL IMMEDIATE;

    SELECT idg.id
      INTO v_identita_id
      FROM anagrafiche.identita_digitali idg
     WHERE idg.auth_user_id = v_auth_user_id
       AND idg.attivo;

    -- ⚠️ Guard sul risultato, non sul parametro: se l'identita'
    --   non si trova la riga di roster non esiste, e restituire
    --   una tupla con un NULL dentro manderebbe il chiamante a
    --   cercare il difetto tre passi piu' in la'.
    IF v_identita_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_roster_processo: nessuna identita'' attiva per auth_user_id=%',
            v_auth_user_id;
    END IF;

    RETURN QUERY
    SELECT v_ef_id, v_codice, v_sr_id, v_auth_user_id, v_identita_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_roster_processo(p_processo_codice text, p_sigla character varying)
IS 'Helper di fixture pgTAP: crea un''azienda nuova (soggetto persona giuridica + ruolo EF + emittente fiscale con sigla PGTRnnnn libera) e le aggancia l''utente tecnico di un processo automatico, cosi'' la coppia (processo, azienda) compare in dbops.vw_processi_roster. Ritorna emittente_fiscale_id, emittente_codice, emittente_soggetto_ruolo_id, auth_user_id, identita_id. ⭐ La seconda meta'' del lavoro la fa script.fn_crea_utente_tecnico, cioe'' il percorso di produzione: utente Django, identita'' OPERATORE tecnica, riga di perimetro in config.user_emittenti_fiscali e legame in dbops.processi_identita. ⚠️ Pretende quindi django.auth_user, che costruisce manage.py migrate e non Liquibase: i test che la usano passano in CI e su un database di lavoro, e restano rossi sul database scratch di scripts/ci-local.sh finche'' non ci si lancia il migrate di Django. ⛔ Nasce perche'' tre test di dbops il roster lo CERCAVANO fra i dati esistenti: verdi su dbdev, rossi su qualunque database ricostruito dai changelog, dove emittenti e soggetti sono dati_macchina e non esistono.';
```

---
{% include-markdown "signature-core.md" %}
