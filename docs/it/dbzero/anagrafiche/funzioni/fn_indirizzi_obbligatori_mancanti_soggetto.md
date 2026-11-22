{% include-markdown "it/dbzero/anagrafiche/manual/fn_indirizzi_obbligatori_mancanti_soggetto.md" %}
# ⚙️ Funzione `fn_indirizzi_obbligatori_mancanti_soggetto`

```sql
CREATE FUNCTION fn_indirizzi_obbligatori_mancanti_soggetto(p_soggetto_id uuid, p_tipo_soggetto_dettaglio_id bigint, p_oggi date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto(p_soggetto_id uuid, p_tipo_soggetto_dettaglio_id bigint, p_oggi date)
 RETURNS TABLE(tipo_indirizzo_id integer, ripiego_tipo_indirizzo_id integer)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT m.tipo_indirizzo_id,
     m.fallback_tipo_indirizzo_id
    FROM config.tipi_soggetto_dettaglio_tipi_indirizzo m
   WHERE ((m.tipo_soggetto_dettaglio_id = fn_indirizzi_obbligatori_mancanti_soggetto.p_tipo_soggetto_dettaglio_id) AND m.obbligatorio AND anagrafiche.fn_tipo_indirizzo_ammesso_per_natura(fn_indirizzi_obbligatori_mancanti_soggetto.p_tipo_soggetto_dettaglio_id, m.tipo_indirizzo_id, fn_indirizzi_obbligatori_mancanti_soggetto.p_oggi) AND (EXISTS ( SELECT 1
            FROM anagrafiche.soggetti s
           WHERE (s.id = fn_indirizzi_obbligatori_mancanti_soggetto.p_soggetto_id))) AND (NOT (EXISTS ( SELECT 1
            FROM anagrafiche.indirizzi_soggetti i
           WHERE ((i.soggetto_id = fn_indirizzi_obbligatori_mancanti_soggetto.p_soggetto_id) AND ((i.tipo_indirizzo_id = m.tipo_indirizzo_id) OR (i.tipo_indirizzo_id = m.fallback_tipo_indirizzo_id)))))))
   ORDER BY m.tipo_indirizzo_id;
END

COMMENT ON FUNCTION anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto(p_soggetto_id uuid, p_tipo_soggetto_dettaglio_id bigint, p_oggi date)
IS 'Gli indirizzi obbligatori che mancano a un soggetto su una natura data, il giorno dato: le righe obbligatorie di config.tipi_soggetto_dettaglio_tipi_indirizzo per la natura passata (non quella del soggetto), attive e valide (anagrafiche.fn_tipo_indirizzo_ammesso_per_natura), per cui il soggetto non ha in anagrafiche.indirizzi_soggetti un indirizzo ne'' del tipo ne'' del ripiego della riga; col tipo richiesto e il ripiego. Ordinate per tipo. Soggetto che non esiste, o natura NULL: nessuna riga. La leggono il guard anagrafiche.fn_guard_indirizzi_obbligatori_soggetto (sulla natura del soggetto) e anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli (sulla natura proposta da un cambio). Gemella di anagrafiche.fn_indirizzi_obbligatori_mancanti_ruolo. STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
