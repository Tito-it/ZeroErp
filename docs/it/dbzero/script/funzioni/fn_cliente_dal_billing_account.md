{% include-markdown "it/dbzero/script/manual/fn_cliente_dal_billing_account.md" %}
# ⚙️ Funzione `fn_cliente_dal_billing_account`

```sql
CREATE FUNCTION fn_cliente_dal_billing_account(p_billing_account_id bigint, p_soggetto_ruolo_id bigint, p_utility_id integer, p_documento text, p_colonna_ruolo text, p_tx_id uuid, OUT soggetto_ruolo_id bigint, OUT utility_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_cliente_dal_billing_account(p_billing_account_id bigint, p_soggetto_ruolo_id bigint, p_utility_id integer, p_documento text, p_colonna_ruolo text DEFAULT 'soggetto_ruolo_id'::text, p_tx_id uuid DEFAULT NULL::uuid, OUT soggetto_ruolo_id bigint, OUT utility_id integer)
 RETURNS record
 LANGUAGE plpgsql
AS $function$
-- Scopo: il ruolo del cliente e la utility di un documento sono
--   COPIE di cio' che il suo billing account gia' dice. Dato il BA e
--   le due copie proposte dal chiamante (NULL = «non detta»), rende
--   quelle del BA: le scrive se mancano, rifiuta se dissentono.
-- Parametri:
--   p_documento     etichetta leggibile del documento, per la frase
--                   («Ordine ORD/12», «DDT #5», «Cliente #3»);
--   p_colonna_ruolo nome della colonna del ruolo sul documento
--                   (`destinatario_soggetto_ruolo_id` sul DDT), per il
--                   campo che il backend evidenzia;
--   p_tx_id         per il log dell'errore.
-- ⚠️ QUANDO chiamarla lo decide il chiamante: solo su INSERT, o
--   anche quando cambia il BA in bozza (il DDT). Una copia che il
--   chiamante non ha toccato, su un BA cambiato, la passa NULL.
-- ⚠️ Il BA si legge come INVOKER, sotto RLS: un BA invisibile e uno
--   inesistente rispondono uguale (E_CODICE). Non scrive niente di
--   sbagliato in nessuno dei due casi: le FK composte verso
--   uq_billing_account_id_cliente restano la rete sotto.
-- Volatile: solleva (e il log scrive).
DECLARE
    v_ba_ruolo    anagrafiche.billing_account.soggetto_ruolo_id%TYPE;
    v_ba_utility  anagrafiche.billing_account.utility_id%TYPE;
    v_ba_codice   anagrafiche.billing_account.codice%TYPE;
BEGIN
    soggetto_ruolo_id := p_soggetto_ruolo_id;
    utility_id        := p_utility_id;

    -- Senza BA non c'e' niente da copiare: il documento senza
    -- cliente (DDT di trasferimento) tiene i suoi valori.
    IF p_billing_account_id IS NULL THEN
        RETURN;
    END IF;

    SELECT ba.soggetto_ruolo_id, ba.utility_id, ba.codice
      INTO v_ba_ruolo, v_ba_utility, v_ba_codice
      FROM anagrafiche.billing_account ba
     WHERE ba.id = p_billing_account_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_cliente_dal_billing_account', 'E_CODICE',
            jsonb_build_object('campo',              'billing_account_id',
                               'billing_account_id', p_billing_account_id,
                               'documento',          p_documento),
            p_tx_id,
            p_billing_account_id::text,
            'anagrafiche.billing_account');
    END IF;

    IF p_soggetto_ruolo_id IS NOT NULL
       AND p_soggetto_ruolo_id IS DISTINCT FROM v_ba_ruolo THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_cliente_dal_billing_account',
            'E_DOC_CLIENTE_DIVERSO_DA_BA',
            jsonb_build_object('campo',              p_colonna_ruolo,
                               'documento',          p_documento,
                               'billing_account_id', p_billing_account_id,
                               'valore',             p_soggetto_ruolo_id,
                               'valore_ba',          v_ba_ruolo),
            p_tx_id,
            p_documento,
            'il cliente',
            v_ba_codice);
    END IF;

    IF p_utility_id IS NOT NULL
       AND p_utility_id IS DISTINCT FROM v_ba_utility THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_cliente_dal_billing_account',
            'E_DOC_CLIENTE_DIVERSO_DA_BA',
            jsonb_build_object('campo',              'utility_id',
                               'documento',          p_documento,
                               'billing_account_id', p_billing_account_id,
                               'valore',             p_utility_id,
                               'valore_ba',          v_ba_utility),
            p_tx_id,
            p_documento,
            'la utility',
            v_ba_codice);
    END IF;

    soggetto_ruolo_id := v_ba_ruolo;
    utility_id        := v_ba_utility;
END;
$function$

COMMENT ON FUNCTION script.fn_cliente_dal_billing_account(p_billing_account_id bigint, p_soggetto_ruolo_id bigint, p_utility_id integer, p_documento text, p_colonna_ruolo text, p_tx_id uuid, OUT soggetto_ruolo_id bigint, OUT utility_id integer)
IS 'Building block (2026-10-10, brief-db-esecutivi-ba-coppia §10.2 domanda 2): il ruolo del cliente e la utility di un documento sono COPIE di cio'' che il suo billing account dice. Dato il BA e le due copie proposte (NULL = non detta), rende (soggetto_ruolo_id, utility_id) del BA: le scrive se mancano, E_DOC_CLIENTE_DIVERSO_DA_BA se dissentono (VARIADIC: documento, «il cliente» | «la utility», codice del BA; nel contesto campo = p_colonna_ruolo o utility_id). BA NULL: rende le copie come sono (documento senza cliente). BA non trovato o invisibile sotto RLS: E_CODICE. QUANDO chiamarlo lo decide il chiamante (solo INSERT, o anche il cambio di BA in bozza). Volatile: solleva. Regola del 2: ritira le tre copie in anagrafiche.trgfn_clienti_sync_utility_from_ba, vendite.trgfn_ordini_normalize, vendite.trgfn_ddt_normalize. Rete sotto: le FK composte verso anagrafiche.billing_account (id, soggetto_ruolo_id, utility_id).';
```

</div>

---
{% include-markdown "signature-core.md" %}
