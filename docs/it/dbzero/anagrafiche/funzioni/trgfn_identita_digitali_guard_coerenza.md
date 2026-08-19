{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_identita_digitali_guard_coerenza.md" %}
# ⚙️ Funzione `trgfn_identita_digitali_guard_coerenza`

```sql
CREATE FUNCTION trgfn_identita_digitali_guard_coerenza()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_identita_digitali_guard_coerenza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- %TYPE sulle colonne sorgente per coerenza automatica col DDL.
    v_soggetto_id anagrafiche.soggetti_ruoli.soggetto_id%TYPE;
BEGIN
    -- ------------------------------------------------------------
    -- Trigger function: guard coerenza ruolo_applicativo <-> soggetto_ruolo
    -- su anagrafiche.identita_digitali (fase a10, BEFORE INSERT/UPDATE).
    --
    -- Logica (ottimizzata):
    --   - API_CLIENT / DISABILITATO: early-exit, nessuna query.
    --   - OPERATORE: SELECT soggetto_id + guard RIS_UMANA + guard PF pura.
    --   - Altri ruoli: delega a fn_guard_soggetto_ruolo passando NULL
    --     come p_soggetto_id (parametro opzionale supportato dalla
    --     funzione) — evita una query ridondante.
    -- ------------------------------------------------------------

    -- 1) Early-exit per ruoli senza vincoli di coerenza.
    --    Evita SELECT e chiamate inutili nel caso piu' frequente
    --    di disattivazione (DISABILITATO) o integrazione API.
    IF NEW.ruolo_applicativo IN ('API_CLIENT', 'DISABILITATO') THEN
        RETURN NEW;
    END IF;

    -- 2) Dispatch per gli altri ruoli applicativi.
    --    fn_guard_soggetto_ruolo verifica che il soggetto_ruolo
    --    abbia tipo_ruolo.codice_interno == valore atteso; solleva
    --    eccezione E_SOGGETTI_RUOLI se non coerente.
    CASE NEW.ruolo_applicativo
        WHEN 'OPERATORE' THEN
            -- Operatore interno: serve anche il soggetto_id per
            -- verificare che sia persona fisica pura. Unica query.
            SELECT sr.soggetto_id
              INTO v_soggetto_id
              FROM anagrafiche.soggetti_ruoli sr
             WHERE sr.id = NEW.soggetto_ruolo_id;

            IF NOT FOUND THEN
                -- Caso limite (record cancellato da altra transazione):
                -- la FK lo impedirebbe, ma fail-fast esplicito per chiarezza.
                PERFORM script.fn_log_and_raise_error(
                    'database',
                    TG_NAME,
                    'E_SOGGETTI_RUOLI',
                    jsonb_build_object(
                        'table', TG_TABLE_NAME,
                        'soggetto_ruolo_id', NEW.soggetto_ruolo_id,
                        'nota', 'soggetto_ruolo_id non trovato in anagrafiche.soggetti_ruoli'
                    ),
                    NULL::uuid,
                    -- ⚠️ ARITA' (2026-08-18): E_SOGGETTI_RUOLI ha tre segnaposto
                    --   (id, soggetto_id, ruolo_id) e qui ne arrivava uno solo
                    --   -> format() alzava 22023 al posto del P0001.
                    --   Gli altri due NON si possono valorizzare, ed e' il punto:
                    --   si arriva qui **perche' la riga non e' stata trovata**,
                    --   quindi soggetto_id e ruolo_id non esistono da leggere.
                    --   Si passa 'NULL' esplicito, che e' la convenzione gia' in
                    --   uso in script.fn_guard_soggetto_ruolo — l'altro
                    --   chiamante di questo stesso codice.
                    --   ⚠️ Resta un difetto di MERITO, non toccato qui: la
                    --   condizione e' «soggetto_ruolo_id non trovato», mentre il
                    --   messaggio dice «non e' stata assegnata la relazione».
                    --   E' materia del quarto lato
                    --   (scripts/sql/check_messaggio_vs_condizione.sql).
                    NEW.soggetto_ruolo_id::text,
                    'NULL',
                    'NULL'
                );
            END IF;

            PERFORM script.fn_guard_soggetto_ruolo(
                v_soggetto_id,
                NEW.soggetto_ruolo_id,
                'RIS_UMANA'
            );
            PERFORM script.fn_guard_soggetto_pf_pura(v_soggetto_id);

        WHEN 'CLIENTE_PORTALE', 'SHOP_CUSTOMER' THEN
            -- Entrambi i ruoli condividono lo stesso tipo_ruolo
            -- anagrafico 'CL': la differenza tra portale B2B e
            -- shop self-service e' solo a livello di namespace API
            -- e profilo capability, non di anagrafica.
            -- NULL come p_soggetto_id: la funzione non lo verifica.
            PERFORM script.fn_guard_soggetto_ruolo(
                NULL,
                NEW.soggetto_ruolo_id,
                'CL'
            );

        WHEN 'FORNITORE_PORTALE' THEN
            -- Fornitore portale: ruolo FORNITORE (codice interno 'FO').
            PERFORM script.fn_guard_soggetto_ruolo(
                NULL,
                NEW.soggetto_ruolo_id,
                'FO'
            );

        ELSE
            -- Nuovo valore enum senza regola qui: fail-fast esplicito
            -- (evita bypass silenzioso quando si estende l'enum in
            -- futuro — il guard non deve "aprire" per omissione).
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME,
                'E_RUOLO_APPLICATIVO_NON_GESTITO',
                jsonb_build_object(
                    'table', TG_TABLE_NAME,
                    'ruolo_applicativo', NEW.ruolo_applicativo,
                    'nota', 'Ruolo applicativo sconosciuto al guard di coerenza'
                ),
                NULL::uuid,
                NEW.ruolo_applicativo::text
            );
    END CASE;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_identita_digitali_guard_coerenza()
IS 'Guard a10 BEFORE INSERT/UPDATE su anagrafiche.identita_digitali: verifica coerenza tra ruolo_applicativo e codice_interno del tipo_ruolo del soggetto_ruolo; per OPERATORE richiede anche che il soggetto sia persona fisica pura. Dispatch esplicito per ogni valore dell''enum config.ruolo_applicativo.';
```

---
{% include-markdown "signature-core.md" %}
