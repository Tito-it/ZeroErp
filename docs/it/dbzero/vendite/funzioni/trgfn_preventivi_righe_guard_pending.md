# ⚙️ Funzione `trgfn_preventivi_righe_guard_pending`

```sql
CREATE FUNCTION trgfn_preventivi_righe_guard_pending()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_preventivi_righe_guard_pending()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Quando una riga preventivo ha stato_approvazione_prezzo =
    --   'PENDING' (richiesta L3 out-of-policy in attesa di
    --   esito), bloccare modifiche ai campi struttura.
    --   L'approvatore L3 deve decidere SULLA RIGA ESATTA che
    --   e' stata proposta: cambi di prezzo/qta/articolo tra
    --   richiesta ed esito violerebbero la catena decisionale.
    --
    -- Allowlist dei campi modificabili in stato PENDING:
    --   - stato_approvazione_prezzo      (workflow transition)
    --   - pratica_approvazione_prezzo_id (aggancio pratica)
    --   - meta                           (payload jsonb)
    --   - data_update, user_update       (audit - gestiti
    --     automaticamente da trgfn_audit_data_user_generic)
    --
    -- Denylist implementata sotto enumera TUTTI gli altri campi
    -- persistenti di preventivi_righe. Se la tabella viene
    -- estesa con nuove colonne struttura, questo trigger va
    -- aggiornato (pattern difensivo).
    -- =========================================================

    -- Guard scope: attivo solo se la riga era in PENDING.
    -- Ingresso in PENDING (es. prima apertura richiesta L3) o
    -- transizioni su righe non-PENDING: nessun vincolo qui.
    IF OLD.stato_approvazione_prezzo IS DISTINCT FROM
       'PENDING'::config.stato_approvazione_prezzo THEN
        RETURN NEW;
    END IF;

    -- OLD = PENDING. Enumero i campi struttura. Qualsiasi
    -- modifica a questi -> raise E_RIGA_PREZZO_PENDENTE.
    -- Le transizioni di stato_approvazione_prezzo e aggancio
    -- pratica sono ammesse (non sono in questa lista).
    IF NEW.preventivo_id       IS DISTINCT FROM OLD.preventivo_id
       OR NEW.articolo_id      IS DISTINCT FROM OLD.articolo_id
       OR NEW.descrizione      IS DISTINCT FROM OLD.descrizione
       OR NEW.quantita         IS DISTINCT FROM OLD.quantita
       OR NEW.prezzo_unitario  IS DISTINCT FROM OLD.prezzo_unitario
       OR NEW.sconto_percentuale IS DISTINCT FROM OLD.sconto_percentuale
       OR NEW.iva_id           IS DISTINCT FROM OLD.iva_id
       OR NEW.ordine           IS DISTINCT FROM OLD.ordine
       OR NEW.attivo           IS DISTINCT FROM OLD.attivo
       OR NEW.qta_operativa    IS DISTINCT FROM OLD.qta_operativa
       OR NEW.uom_operativa_id IS DISTINCT FROM OLD.uom_operativa_id
       OR NEW.factor_to_base   IS DISTINCT FROM OLD.factor_to_base
    THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_RIGA_PREZZO_PENDENTE',
            jsonb_build_object(
                'riga_id',       OLD.id,
                'preventivo_id', OLD.preventivo_id,
                'hint',          'Attendi esito approvazione (APPROVED/REJECTED) o rifiuta la richiesta prima di modificare la riga.'
            ),
            NULL::uuid,
            OLD.id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_preventivi_righe_guard_pending()
IS 'Trigger function: blocca modifiche ai campi struttura di preventivi_righe quando la riga e'' in stato_approvazione_prezzo = PENDING. Ammette solo workflow (stato_approvazione, pratica), meta e audit. Sprint E listini v5 §14.6 (DB-E-5). Raise E_RIGA_PREZZO_PENDENTE.';
```

---
{% include-markdown "signature-core.md" %}
