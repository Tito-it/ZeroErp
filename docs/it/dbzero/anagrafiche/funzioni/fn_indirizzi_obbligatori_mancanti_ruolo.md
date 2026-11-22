{% include-markdown "it/dbzero/anagrafiche/manual/fn_indirizzi_obbligatori_mancanti_ruolo.md" %}
# ⚙️ Funzione `fn_indirizzi_obbligatori_mancanti_ruolo`

```sql
CREATE FUNCTION fn_indirizzi_obbligatori_mancanti_ruolo(p_soggetto_ruolo_id bigint, p_tipo_soggetto_dettaglio_id bigint, p_oggi date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_indirizzi_obbligatori_mancanti_ruolo(p_soggetto_ruolo_id bigint, p_tipo_soggetto_dettaglio_id bigint, p_oggi date)
 RETURNS TABLE(tipo_indirizzo_id integer, ripiego_tipo_indirizzo_id integer)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT o.tipo_indirizzo_id,
     o.ripiego_tipo_indirizzo_id
    FROM (anagrafiche.soggetti_ruoli sr
      CROSS JOIN LATERAL anagrafiche.fn_indirizzi_obbligatori_ruolo(sr.tipo_ruolo_id, fn_indirizzi_obbligatori_mancanti_ruolo.p_tipo_soggetto_dettaglio_id, fn_indirizzi_obbligatori_mancanti_ruolo.p_oggi) o(tipo_indirizzo_id, ripiego_tipo_indirizzo_id))
   WHERE ((sr.id = fn_indirizzi_obbligatori_mancanti_ruolo.p_soggetto_ruolo_id) AND (NOT (EXISTS ( SELECT 1
            FROM anagrafiche.indirizzi i
           WHERE ((i.soggetto_ruolo_id = sr.id) AND ((i.tipo_indirizzo_id = o.tipo_indirizzo_id) OR (i.tipo_indirizzo_id = o.ripiego_tipo_indirizzo_id)))))))
   ORDER BY o.tipo_indirizzo_id;
END

COMMENT ON FUNCTION anagrafiche.fn_indirizzi_obbligatori_mancanti_ruolo(p_soggetto_ruolo_id bigint, p_tipo_soggetto_dettaglio_id bigint, p_oggi date)
IS 'Gli indirizzi obbligatori che mancano a un ruolo su una natura data, il giorno dato: i requisiti del ruolo (anagrafiche.fn_indirizzi_obbligatori_ruolo, sul tipo di ruolo e sulla natura passata, non su quella del soggetto) che nessun indirizzo del ruolo (anagrafiche.indirizzi, istanze comprese) soddisfa, col tipo richiesto e il ripiego che lo sostituisce. Ordinati per tipo richiesto. Ruolo che non esiste: nessuna riga. Natura NULL: la natura non conta. La leggono il guard anagrafiche.fn_guard_indirizzi_obbligatori_ruolo (sulla natura del soggetto) e anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli (sulla natura proposta da un cambio). Gemella di anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto. STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
