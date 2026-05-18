# ⚙️ Funzione `trgfn_contratti_righe_guard_pending`

```sql
CREATE FUNCTION trgfn_contratti_righe_guard_pending()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_righe_guard_pending()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Quando una riga contratto ha stato_approvazione_prezzo =
    --   'PENDING' (richiesta L3 out-of-policy in attesa di
    --   esito), bloccare modifiche ai campi struttura.
    --   L'approvatore L3 deve decidere sulla riga esatta
    --   proposta: cambi di prezzo/qta/articolo/tipo tra
    --   richiesta ed esito violerebbero la catena decisionale.
    --
    -- Allowlist (modificabili in PENDING):
    --   stato_approvazione_prezzo, pratica_approvazione_prezzo_id,
    --   meta, data_update, user_update (audit framework).
    --
    -- Denylist (tutti gli altri campi struttura):
    --   contratto_id, articolo_id, tipo_erogazione,
    --   fonte_quantita_attesa, periodicita, generazione_canone,
    --   competenza_canone, prezzo_unitario, quantita, ordine,
    --   attivo, qta_operativa, uom_operativa_id, factor_to_base,
    --   tipo_eccezione.
    --   tx_id escluso: gestione framework, non applicativo.
    --
    -- Convivenza trigger _a10_: guard_pending (lessicograficamente
    --   3°) scatta prima di lock_post_attivazione (4°). Scenario
    --   canonico: riga PENDING solo in contratto DRAFT. Scenario
    --   difensivo: guard_pending fornisce E_RIGA_PREZZO_PENDENTE
    --   più specifico di E_CONTRATTO_CAMPI_BLOCCATI (lock).
    -- =========================================================

    -- Guard scope: attivo solo se la riga era PENDING.
    IF OLD.stato_approvazione_prezzo IS DISTINCT FROM
       'PENDING'::config.stato_approvazione_prezzo THEN
        RETURN NEW;
    END IF;

    -- OLD = PENDING. Qualsiasi modifica alla denylist -> raise.
    IF NEW.contratto_id             IS DISTINCT FROM OLD.contratto_id
       OR NEW.articolo_id           IS DISTINCT FROM OLD.articolo_id
       OR NEW.tipo_erogazione       IS DISTINCT FROM OLD.tipo_erogazione
       OR NEW.fonte_quantita_attesa IS DISTINCT FROM OLD.fonte_quantita_attesa
       OR NEW.periodicita           IS DISTINCT FROM OLD.periodicita
       OR NEW.generazione_canone    IS DISTINCT FROM OLD.generazione_canone
       OR NEW.competenza_canone     IS DISTINCT FROM OLD.competenza_canone
       OR NEW.prezzo_unitario       IS DISTINCT FROM OLD.prezzo_unitario
       OR NEW.quantita              IS DISTINCT FROM OLD.quantita
       OR NEW.ordine                IS DISTINCT FROM OLD.ordine
       OR NEW.attivo                IS DISTINCT FROM OLD.attivo
       OR NEW.qta_operativa         IS DISTINCT FROM OLD.qta_operativa
       OR NEW.uom_operativa_id      IS DISTINCT FROM OLD.uom_operativa_id
       OR NEW.factor_to_base        IS DISTINCT FROM OLD.factor_to_base
       OR NEW.tipo_eccezione        IS DISTINCT FROM OLD.tipo_eccezione
    THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            TG_NAME,
            'E_RIGA_PREZZO_PENDENTE',
            jsonb_build_object(
                'riga_id',       OLD.id,
                'contratto_id',  OLD.contratto_id,
                'hint', 'Attendere esito approvazione (APPROVED/REJECTED) o rifiutare la richiesta prima di modificare la riga.'
            ),
            NULL::uuid,
            OLD.id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_righe_guard_pending()
IS 'Trigger function: blocca modifiche ai campi struttura di contratti_righe quando la riga e'' in stato_approvazione_prezzo = PENDING. Allowlist: stato_approvazione_prezzo, pratica_approvazione_prezzo_id, meta, audit. Raise E_RIGA_PREZZO_PENDENTE (390). Simmetrico a trgfn_preventivi_righe_guard_pending. 2026-05-18.';
```

---
{% include-markdown "signature-core.md" %}
