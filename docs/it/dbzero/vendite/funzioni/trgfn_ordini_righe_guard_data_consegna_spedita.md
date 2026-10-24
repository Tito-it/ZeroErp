# ⚙️ Funzione `trgfn_ordini_righe_guard_data_consegna_spedita`

```sql
CREATE FUNCTION trgfn_ordini_righe_guard_data_consegna_spedita()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ordini_righe_guard_data_consegna_spedita()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: la data di consegna confermata di una riga d'ordine gia'
--   partita con un DDT, anche in parte, non cambia (D-7, P-1 di
--   brief-db-date-consegna-righe-in-blocco). La regola sta in
--   script.fn_check_ordine_riga_data_consegna_confermata: qui si
--   solleva il suo primo motivo.
-- Uso: BEFORE UPDATE FOR EACH ROW WHEN la data cambia, fascia _a10_.
-- =========================================================
BEGIN
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', TG_NAME::text,
        script.fn_check_ordine_riga_data_consegna_confermata(OLD.id),
        'data_consegna_confermata',
        NEW.tx_id,
        jsonb_build_object('ordine_riga_id', OLD.id,
                           'ordine_id',      OLD.ordine_id));
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ordini_righe_guard_data_consegna_spedita()
IS 'Guard (2026-10-11, brief-db-date-consegna-righe-in-blocco D-7, P-1): la data di consegna confermata di una riga d''ordine gia'' partita con un DDT uscito dalla bozza, anche per una parte della riga, non cambia piu'': la data di consegna si scrive prima di spedire. Prima il lock delle righe la lasciava cambiare in PARZIALMENTE_EVASO guardando solo lo stato della testata. Il predicato non sta qui (linee-guida-sql §12.5.2): solleva con script.fn_raise_primo_motivo_se_presente il primo motivo di script.fn_check_ordine_riga_data_consegna_confermata, la stessa check che spegne il pulsante (vendite.vw_ordini_righe_dettaglio.data_consegna_confermata_blocco). Codice E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA (CONFLITTO_STATO), campo data_consegna_confermata. BEFORE UPDATE con WHEN sul cambio di valore, fascia _a10_ dopo il lock fuori bozza (_a05_).';
```

</div>

---
{% include-markdown "signature-core.md" %}
