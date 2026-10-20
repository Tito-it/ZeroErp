{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_efba_guard_storia_emittente.md" %}
# ⚙️ Funzione `trgfn_efba_guard_storia_emittente`

```sql
CREATE FUNCTION trgfn_efba_guard_storia_emittente()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_efba_guard_storia_emittente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_default anagrafiche.emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id%TYPE;
    -- ⛔ Serve una VARIABILE e non `OLD.id` dentro la query: in
    --    PL/pgSQL i riferimenti a OLD/NEW sono parametri
    --    sostituiti PRIMA dell'esecuzione, quindi un
    --    `TG_OP <> 'DELETE' OR e.id <> OLD.id` non corto-circuita
    --    e su INSERT alzerebbe «record old is not assigned yet».
    v_old_id  anagrafiche.emittenti_fiscali_billing_account.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Presidia i movimenti che cambiano l'emittente di un
    --   billing account e li blocca se quel cliente ha gia'
    --   della storia (fatture o commesse).
    --
    -- Tassonomia dei movimenti — la stessa, gia' scritta, di
    -- anagrafiche.trgfn_efba_guard_albero_emittente:
    --   INSERT mapping specifico  -> prima = gestore globale
    --   UPDATE dell'emittente     -> prima = OLD, dopo = NEW
    --   UPDATE che sposta il BA   -> due volte, uno per BA
    --   DELETE mapping specifico  -> dopo  = gestore globale
    --   riga senza BA (default)   -> raggio N
    --
    -- ⚠️ La CANCELLAZIONE non e' un caso di scuola: il backend
    --   non ha nessun UPDATE sul mapping, e «spostare un BA» si
    --   fa con DELETE + INSERT.
    -- =========================================================

    -- L'emittente del gestore globale, cioe' dove ricade un BA
    -- che non ha (o non ha piu') un mapping suo.
    -- ⛔ Si legge dalla riga is_default e NON con il risolutore:
    --   in un BEFORE DELETE la riga che si sta cancellando c'e'
    --   ancora, e il risolutore risponderebbe proprio quella.
    IF TG_OP = 'DELETE' THEN
        v_old_id := OLD.id;
    END IF;

    SELECT e.emittente_soggetto_ruolo_id
      INTO v_default
      FROM anagrafiche.emittenti_fiscali_billing_account e
     WHERE e.is_default IS TRUE
       AND (v_old_id IS NULL OR e.id <> v_old_id);

    IF TG_OP = 'INSERT' THEN
        IF NEW.billing_account_id IS NOT NULL THEN
            -- Movimento 1: il BA passa dal gestore globale a un
            -- mapping specifico.
            PERFORM anagrafiche.fn_guard_ba_cambio_emittente(
                NEW.billing_account_id, v_default, NEW.emittente_soggetto_ruolo_id);
        ELSE
            -- Riga senza BA = nuovo gestore globale. Raggio N.
            PERFORM anagrafiche.fn_guard_ba_gestore_globale_storia(
                v_default, NEW.emittente_soggetto_ruolo_id);
        END IF;
        RETURN NEW;
    END IF;

    IF TG_OP = 'UPDATE' THEN
        IF NEW.billing_account_id IS DISTINCT FROM OLD.billing_account_id THEN
            -- Il mapping viene spostato da un BA a un altro: sono
            -- DUE cambi di emittente, e si guardano entrambi.
            -- (La UNIQUE lo rende raro, non impossibile.)
            IF OLD.billing_account_id IS NOT NULL THEN
                PERFORM anagrafiche.fn_guard_ba_cambio_emittente(
                    OLD.billing_account_id, OLD.emittente_soggetto_ruolo_id, v_default);
            END IF;
            IF NEW.billing_account_id IS NOT NULL THEN
                PERFORM anagrafiche.fn_guard_ba_cambio_emittente(
                    NEW.billing_account_id, v_default, NEW.emittente_soggetto_ruolo_id);
            END IF;
            RETURN NEW;
        END IF;

        IF NEW.billing_account_id IS NOT NULL THEN
            -- Movimento 2: cambia l'emittente sul mapping.
            PERFORM anagrafiche.fn_guard_ba_cambio_emittente(
                NEW.billing_account_id,
                OLD.emittente_soggetto_ruolo_id,
                NEW.emittente_soggetto_ruolo_id);
        ELSE
            -- Il gestore globale cambia emittente. Raggio N.
            PERFORM anagrafiche.fn_guard_ba_gestore_globale_storia(
                OLD.emittente_soggetto_ruolo_id,
                NEW.emittente_soggetto_ruolo_id);
        END IF;
        RETURN NEW;
    END IF;

    -- TG_OP = 'DELETE'
    IF OLD.billing_account_id IS NOT NULL THEN
        -- Movimento 3: tolto il mapping, il BA ricade sul gestore
        -- globale. E' il primo dei due passi con cui il frontend
        -- «sposta» un cliente, ed e' gia' uno spostamento.
        PERFORM anagrafiche.fn_guard_ba_cambio_emittente(
            OLD.billing_account_id, OLD.emittente_soggetto_ruolo_id, v_default);
    ELSE
        -- Sparisce il gestore globale: i non mappati restano
        -- senza emittente risolvibile. Raggio N.
        PERFORM anagrafiche.fn_guard_ba_gestore_globale_storia(
            OLD.emittente_soggetto_ruolo_id, NULL);
    END IF;

    -- ⛔ In un BEFORE DELETE si ritorna OLD: `NEW` e' NULL e un
    --    RETURN NULL annullerebbe la cancellazione IN SILENZIO.
    RETURN OLD;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_efba_guard_storia_emittente()
IS 'Trigger BEFORE INSERT/UPDATE/DELETE su anagrafiche.emittenti_fiscali_billing_account: presidia i movimenti che cambiano l''emittente di un billing account e li blocca quando quel cliente ha gia'' della storia (fatture o commesse), delegando ad anagrafiche.fn_guard_ba_cambio_emittente e, per il raggio N, ad anagrafiche.fn_guard_ba_gestore_globale_storia. La tassonomia dei movimenti e'' la stessa gia'' scritta in anagrafiche.trgfn_efba_guard_albero_emittente e non e'' stata reinventata: INSERT di un mapping specifico (prima = gestore globale), UPDATE dell''emittente sul mapping (prima = OLD, dopo = NEW), UPDATE che sposta il mapping da un BA a un altro (si guardano ENTRAMBI i billing account), DELETE del mapping specifico (dopo = gestore globale), riga senza billing account = gestore globale (raggio N). ⚠️ La CANCELLAZIONE non e'' un caso di scuola: verificato il 2026-08-26, il backend non ha nessun UPDATE sul mapping — la sotto-risorsa espone create_mapping e delete_mapping — quindi «spostare un BA da un emittente all''altro» si fa con DELETE + INSERT, e un guard sul solo INSERT lascerebbe passare tutto perche'' il danno lo fa la cancellazione. ⚠️ BEFORE e non AFTER come il fratello, ed e'' una differenza motivata: quello e'' z95 AFTER perche'' RILEGGE il mapping per risolvere l''emittente e gli serve lo stato finale, questo ricava «prima» e «dopo» da OLD/NEW e sta in a10, la fase dei guard di blocco. ⛔ Sul DELETE il «dopo» NON si calcola con script.fn_get_ba_emittente_sr_id: in un BEFORE DELETE la riga c''e'' ancora e il risolutore risponderebbe il mapping che si sta cancellando — «prima» e «dopo» coinciderebbero e il guard non scatterebbe mai. Si legge direttamente dalla riga is_default, escludendo quella in cancellazione. ⛔ E in un BEFORE DELETE si ritorna OLD: NEW li'' e'' NULL, e un RETURN NULL annullerebbe la cancellazione in silenzio — la differenza fra un guard che blocca dicendolo e uno che fa sparire il gesto senza errori. ⚠️ Convive con trg_emittenti_fiscali_ba_z95_guard_albero_emittente_ins_upd_dlt senza ordine critico (a10 prima di z95): i due sono complementari — uno dice «l''albero non puo'' diventare misto», l''altro «la storia non si sposta». Piano: brief-db-billing-account-cambio-emittente, M3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
