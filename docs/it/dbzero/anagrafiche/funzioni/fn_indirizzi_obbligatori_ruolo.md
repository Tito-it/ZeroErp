{% include-markdown "it/dbzero/anagrafiche/manual/fn_indirizzi_obbligatori_ruolo.md" %}
# ⚙️ Funzione `fn_indirizzi_obbligatori_ruolo`

```sql
CREATE FUNCTION fn_indirizzi_obbligatori_ruolo(p_tipo_ruolo_id integer, p_tipo_soggetto_dettaglio_id bigint, p_oggi date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_indirizzi_obbligatori_ruolo(p_tipo_ruolo_id integer, p_tipo_soggetto_dettaglio_id bigint, p_oggi date)
 RETURNS TABLE(tipo_indirizzo_id integer, ripiego_tipo_indirizzo_id integer)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT
         CASE
             WHEN r.tipo_ok THEN r.tipo
             ELSE r.ripiego
         END AS ripiego,
         CASE
             WHEN (r.tipo_ok AND r.ripiego_ok) THEN r.ripiego
             ELSE NULL::integer
         END AS "case"
    FROM ( SELECT m.tipo_indirizzo_id AS tipo,
             m.fallback_tipo_indirizzo_id AS ripiego,
             anagrafiche.fn_tipo_indirizzo_ammesso_per_natura(fn_indirizzi_obbligatori_ruolo.p_tipo_soggetto_dettaglio_id, m.tipo_indirizzo_id, fn_indirizzi_obbligatori_ruolo.p_oggi) AS tipo_ok,
             ((m.fallback_tipo_indirizzo_id IS NOT NULL) AND (m.fallback_tipo_indirizzo_id <> m.tipo_indirizzo_id) AND anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo((fn_indirizzi_obbligatori_ruolo.p_tipo_ruolo_id)::bigint, m.fallback_tipo_indirizzo_id, fn_indirizzi_obbligatori_ruolo.p_oggi) AND anagrafiche.fn_tipo_indirizzo_ammesso_per_natura(fn_indirizzi_obbligatori_ruolo.p_tipo_soggetto_dettaglio_id, m.fallback_tipo_indirizzo_id, fn_indirizzi_obbligatori_ruolo.p_oggi)) AS ripiego_ok
            FROM config.tipi_ruolo_tipi_indirizzo m
           WHERE ((m.tipo_ruolo_id = fn_indirizzi_obbligatori_ruolo.p_tipo_ruolo_id) AND m.obbligatorio AND anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo((fn_indirizzi_obbligatori_ruolo.p_tipo_ruolo_id)::bigint, m.tipo_indirizzo_id, fn_indirizzi_obbligatori_ruolo.p_oggi))) r
   WHERE (r.tipo_ok OR r.ripiego_ok)
   ORDER BY
         CASE
             WHEN r.tipo_ok THEN r.tipo
             ELSE r.ripiego
         END;
END

COMMENT ON FUNCTION anagrafiche.fn_indirizzi_obbligatori_ruolo(p_tipo_ruolo_id integer, p_tipo_soggetto_dettaglio_id bigint, p_oggi date)
IS 'Il requisito degli indirizzi obbligatori di un ruolo, per il tipo di ruolo, sulla natura del soggetto, il giorno dato: una riga per ogni riga obbligatoria di config.tipi_ruolo_tipi_indirizzo attiva e valida (anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo), col tipo richiesto (tipo_indirizzo_id) e il ripiego che lo sostituisce (ripiego_tipo_indirizzo_id). Se la natura ammette il tipo della riga (anagrafiche.fn_tipo_indirizzo_ammesso_per_natura), si chiede il tipo, col ripiego della riga se il ruolo e la natura lo ammettono, altrimenti senza; se la natura non lo ammette e ammette il ripiego, si chiede il ripiego, da solo; se non ammette nessuno dei due, la riga non chiede niente. Natura NULL: la natura non conta. Ordinato per tipo richiesto. Sede unica del requisito del layer RUOLO: la leggono anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo (auto-clone e picker), anagrafiche.fn_guard_indirizzi_obbligatori_ruolo (i guard) e la fixture dbops.fn_pgtap_crea_soggetto_ruolo. STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
