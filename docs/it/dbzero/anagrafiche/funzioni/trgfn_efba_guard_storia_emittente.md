{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_efba_guard_storia_emittente.md" %}
# ⚙️ Funzione `trgfn_efba_guard_storia_emittente`

```sql
CREATE FUNCTION trgfn_efba_guard_storia_emittente()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_efba_guard_storia_emittente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- La sola modifica che cambia l'azienda di un cliente: l'azienda
    -- sul collegamento di un BA. Libera finche' il BA non ha
    -- documenti, vietata dopo (anagrafiche.fn_guard_ba_cambio_emittente).
    -- Lo spostamento del collegamento su un altro conto lo rifiuta
    -- prima trg_emittenti_fiscali_ba_a05_block_sposta_upd.
    IF TG_OP = 'UPDATE'
       AND NEW.billing_account_id IS NOT NULL
       AND NEW.emittente_soggetto_ruolo_id IS DISTINCT FROM OLD.emittente_soggetto_ruolo_id THEN
        PERFORM anagrafiche.fn_guard_ba_cambio_emittente(
            NEW.billing_account_id,
            OLD.emittente_soggetto_ruolo_id,
            NEW.emittente_soggetto_ruolo_id);
    END IF;

    -- ⛔ In un BEFORE DELETE si ritorna OLD: un RETURN NEW (NULL)
    --    annullerebbe la cancellazione in silenzio.
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_efba_guard_storia_emittente()
IS 'Guard BEFORE INSERT, UPDATE, DELETE di anagrafiche.emittenti_fiscali_billing_account: la modifica dell''azienda sul collegamento di un billing account e'' rifiutata quando il billing account ha documenti (anagrafiche.fn_guard_ba_cambio_emittente, E_BA_EMITTENTE_CON_STORIA). La nascita del collegamento e'' la nascita del billing account e non ha storia; la cancellazione e lo spostamento su un altro conto li rifiutano i trigger a05; la riga dell''azienda predefinita non si giudica, perche'' spostarla non cambia l''azienda di nessun cliente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
