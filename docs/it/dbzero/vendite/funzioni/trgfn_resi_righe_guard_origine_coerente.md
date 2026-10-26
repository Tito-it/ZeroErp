{% include-markdown "it/dbzero/vendite/manual/trgfn_resi_righe_guard_origine_coerente.md" %}
# ⚙️ Funzione `trgfn_resi_righe_guard_origine_coerente`

```sql
CREATE FUNCTION trgfn_resi_righe_guard_origine_coerente()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_resi_righe_guard_origine_coerente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: coerenza fra il riferimento all'ordine portato dalla riga
--   di reso e il fulfillment della riga di DDT da cui la merce e'
--   tornata. `ordine_riga_id` e' una denormalizzazione, e un
--   riferimento che non descrive la merce lascia il residuo
--   dell'ordine non riaperto (fn_ordine_riga_qta_riconsegna).
DECLARE
    v_n_origini  integer;
    v_combacia   boolean;
BEGIN
    -- Quante righe d'ordine sono evase da questa riga di DDT, e se
    -- il valore proposto e' fra quelle. Una sola scansione.
    SELECT COUNT(*),
           COALESCE(bool_or(f.ordine_riga_id = NEW.ordine_riga_id), false)
      INTO v_n_origini, v_combacia
      FROM vendite.ordini_righe_fulfillment f
     WHERE f.ddt_riga_id = NEW.ddt_riga_id;

    -- Riga di merce ORDER-BACKED: il riferimento va valorizzato, e
    -- dev'essere UNA delle origini. Non «la prima»: il fulfillment
    -- ne ammette piu' di una, e scegliere sarebbe arbitrio.
    IF v_n_origini > 0 AND NOT v_combacia THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_resi_righe_guard_origine_coerente','E_RESO_ORIGINE_INCOERENTE',
        jsonb_build_object('ddt_riga_id',    NEW.ddt_riga_id,
                           'ordine_riga_id', NEW.ordine_riga_id,
                           'origini_valide', v_n_origini,
                           'motivo',         CASE WHEN NEW.ordine_riga_id IS NULL
                                                  THEN 'mancante su merce ordinata'
                                                  ELSE 'non fra le origini della riga DDT' END),
        NEW.tx_id,
        -- ⚠️ Il valore VARIADIC non e' decorativo: senza almeno un
        -- argomento la risoluzione dell'overload fallisce e l'errore
        -- che esce e' «la funzione non esiste» (42883) invece del
        -- codice di dominio. Un `throws_ok` senza SQLSTATE lo
        -- accetterebbe, e il guard sembrerebbe funzionare.
        NEW.ddt_riga_id::text, NEW.ordine_riga_id::text);
    END IF;

    -- Riga di merce SENZA ordine (standalone, o aggiunta a mano):
    -- un riferimento qui riaprirebbe il residuo di un ordine che
    -- non ha spedito questa merce.
    IF v_n_origini = 0 AND NEW.ordine_riga_id IS NOT NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_resi_righe_guard_origine_coerente','E_RESO_ORIGINE_INCOERENTE',
        jsonb_build_object('ddt_riga_id',    NEW.ddt_riga_id,
                           'ordine_riga_id', NEW.ordine_riga_id,
                           'origini_valide', 0,
                           'motivo',         'valorizzato su merce senza ordine'),
        NEW.tx_id,
        NEW.ddt_riga_id::text, NEW.ordine_riga_id::text);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_resi_righe_guard_origine_coerente()
IS 'Guard di coerenza dell''origine sul reso (partita merce generalizzata S6a): resi_righe.ordine_riga_id deve combaciare col fulfillment di resi_righe.ddt_riga_id — valorizzato e coincidente con UNA delle origini se la riga di DDT e'' order-backed, VUOTO se non lo e''. Bicondizionale: le due direzioni sono lo stesso errore visto dai due lati. Perche'' serve: `ordine_riga_id` e'' una denormalizzazione ricavabile dal fulfillment, e la legge fn_ordine_riga_qta_riconsegna per riaprire il residuo dell''ordine — sbagliata o vuota, la merce torna e l''ordine non se ne accorge. ⚠️ Il fulfillment ammette piu'' righe d''ordine per una riga di DDT (unicita'' sulla COPPIA): si chiede che il valore sia una delle origini, non «la prima». Il backend deriva gia'' il campo dallo snapshot della riga DDT: questo guard copre le scritture che non passano dal service. Errore E_RESO_ORIGINE_INCOERENTE (DATO_ERRATO).';
```

</div>

---
{% include-markdown "signature-core.md" %}
