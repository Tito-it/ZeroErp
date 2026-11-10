{% include-markdown "it/dbzero/dbops/manual/trgfn_tx_id_managed.md" %}
# ⚙️ Funzione `trgfn_tx_id_managed`

```sql
CREATE FUNCTION trgfn_tx_id_managed()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.trgfn_tx_id_managed()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_bypass_enabled BOOLEAN := FALSE;
    v_session_tx_id     UUID;
    v_new_tx_id      UUID;
BEGIN
    -- =========================================================
    -- USCITA ANTICIPATA (rev 2026-07-24,
    -- brief-db-tx-id-uscita-anticipata.md).
    -- Se il chiamante ha gia' valorizzato il tx_id non c'e' niente
    -- da gestire: tutto il corpo sottostante serve solo a calcolare
    -- v_new_tx_id, che e' consumato unicamente dalla COALESCE finale
    -- -- raggiunta solo quando NEW.tx_id IS NULL. Prima questi due
    -- blocchi stavano in fondo: la funzione faceva il giro completo
    -- (lettura di config.parameters + rami su script.*) per poi
    -- restituire NEW invariato.
    -- Due effetti: il trigger, installato su 280 tabelle, smette di
    -- pagare lavoro inutile; e la sessione remota del canale di log
    -- -- che fornisce sempre il proprio tx_id e ha grant sul solo
    -- schema dbops -- non chiede piu' permessi su config e script.
    --
    -- ORDINE VINCOLANTE: la normalizzazione DEVE precedere l'uscita,
    -- altrimenti un tx_id "stringa vuota" sfuggirebbe. Per una
    -- colonna UUID e' di fatto irraggiungibile, ma resta dov'era
    -- nella logica: spostato, non rimosso.
    -- =========================================================
    IF NEW.tx_id IS NOT NULL AND NEW.tx_id::text = '' THEN
      NEW.tx_id := NULL;
    END IF;

    IF NEW.tx_id IS NOT NULL THEN
      RETURN NEW;
    END IF;

    BEGIN
        SELECT default_value::BOOLEAN
          INTO v_bypass_enabled
          FROM config.parameters
        WHERE code = 'tx_id_bypass_enabled';

        -- Riga assente o valore NULL: SELECT INTO senza riga assegna NULL,
        -- non lascia il FALSE iniziale. Si avvisa e si prosegue col bypass
        -- spento: l'override di sessione (sotto) resta leggibile.
        IF v_bypass_enabled IS NULL THEN

            PERFORM script.fn_log_error_only(
                'database',
                'dbops.trgfn_tx_id_managed',
                'W_TXID_BYPASS_PARAMETRO_ASSENTE',
                jsonb_build_object(
                    'codice_parametro', 'tx_id_bypass_enabled',
                    'action', 'default bypass=false'
                ),
                  NULL::uuid,
                  'tx_id_bypass_enabled'
              );
            v_bypass_enabled := false;
        END IF;

    EXCEPTION WHEN OTHERS THEN

        PERFORM script.fn_log_and_raise_error(
            'database',
            'dbops.trgfn_tx_id_managed',
            'E_SQL_READ_TABLE',
            jsonb_build_object(
              'parameter', 'tx_id_bypass_enabled',
              'error', SQLERRM
            ),
            NULL::uuid,
            TG_TABLE_NAME::text,
            SQLERRM::text
        );
    END;

    IF NOT v_bypass_enabled THEN
        BEGIN
            v_bypass_enabled := current_setting('myapp.bypass_tx_id_check', TRUE)::BOOLEAN;
        EXCEPTION WHEN OTHERS THEN

            NULL;
        END;
    END IF;

    BEGIN
        v_session_tx_id := current_setting('dbops.tx_id', TRUE)::UUID;
    EXCEPTION WHEN OTHERS THEN
        v_session_tx_id := NULL;
    END;

    IF v_bypass_enabled THEN

        v_new_tx_id := COALESCE(v_session_tx_id, script.uuid_nil());

    ELSE
        IF v_session_tx_id IS NOT NULL THEN

            PERFORM 1
              FROM dbops.transaction_ids
            WHERE id = v_session_tx_id;
            IF FOUND THEN
                v_new_tx_id := v_session_tx_id;

            ELSE
                -- Caso C) id di sessione non presente nel registro.
                -- AVVERTE e prosegue con la sentinella: e' il comportamento che
                -- la guida descrive ("logga WARNING e assegna nil") e che il
                -- prefisso W_ promette. Prima qui si sollevava, quindi la riga
                -- uuid_nil() sotto era irraggiungibile e un id non registrato
                -- bloccava ogni scrittura tracciata.
                -- Vedi brief-db-coerenza-tx-id-non-registrato.md §4.2.
                -- NB dal 2026-07-24: questo ramo non viene piu' raggiunto dalle
                -- righe che portano gia' il proprio tx_id (uscita anticipata in
                -- testa). Resta la diagnosi di sessione: qualunque altra
                -- scrittura che lasci il tx_id vuoto la fa scattare lo stesso.
                PERFORM script.fn_log_error_only(
                    'database',
                    'dbops.trgfn_tx_id_managed',
                    'W_TXID_NOT_REGISTERED',
                    jsonb_build_object( 'tx_id', v_session_tx_id ),
                    NULL::uuid,
                    VARIADIC ARRAY[]::text[]
                );
                v_new_tx_id := script.uuid_nil();

            END IF;

        ELSE

            BEGIN

              v_new_tx_id := dbops.fn_get_or_create_session_tx_id();

            EXCEPTION WHEN OTHERS THEN

                PERFORM script.fn_log_and_raise_error(
                    'database',
                    'dbops.trgfn_tx_id_managed',
                    'E_TXID_GENERATION',
                    jsonb_build_object(
                      'error', SQLERRM
                    ) ,
                    NULL::uuid,
                    VARIADIC ARRAY[]::text[]
                );
                v_new_tx_id := script.uuid_nil();
            END;
        END IF;
    END IF;

    -- Qui si arriva solo con NEW.tx_id NULL (vedi uscita in testa).
    -- Il valore e' quello calcolato dai rami sopra, che hanno gia' letto la
    -- GUC dbops.tx_id (e l'hanno scartata se malformata o non registrata):
    -- rileggerla qui faceva vincere un id non registrato sulla sentinella.
    NEW.tx_id := COALESCE(v_new_tx_id, uuidv7());
  RETURN NEW;

END;
$function$

COMMENT ON FUNCTION dbops.trgfn_tx_id_managed()
IS 'Trigger function di audit: valorizza NEW.tx_id. Se NEW.tx_id e'' gia'' valorizzato normalizza la stringa vuota e ritorna subito, senza leggere config.parameters ne'' script.*: il resto del corpo serve solo a calcolare il valore quando manca. Quando NEW.tx_id IS NULL: bypass a due livelli, il parametro config.parameters.tx_id_bypass_enabled e poi la GUC myapp.bypass_tx_id_check, che si legge sempre quando il parametro non accende il bypass; parametro assente o NULL vale spento e lascia W_TXID_BYPASS_PARAMETRO_ASSENTE nel log, senza fermare la scrittura. Col bypass: il tx_id di sessione (GUC dbops.tx_id) o script.uuid_nil(). Senza bypass: se la GUC dbops.tx_id e'' impostata, l''id deve esistere in dbops.transaction_ids, altrimenti avverte (W_TXID_NOT_REGISTERED) e assegna script.uuid_nil(); una GUC che non e'' un uuid vale assente; se la GUC e'' assente chiama dbops.fn_get_or_create_session_tx_id(), e se quella fallisce solleva E_TXID_GENERATION. Il valore assegnato e'' quello di questi rami, con uuidv7() come ripiego se resta NULL: la GUC non si rilegge alla fine. Una lettura del parametro che fallisce solleva E_SQL_READ_TABLE. Convenzione: E_ = errore bloccante, W_ = avviso scritto solo nel log.';
```

</div>

---
{% include-markdown "signature-core.md" %}
