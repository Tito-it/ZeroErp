# ⚙️ Funzione `fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli`

```sql
CREATE FUNCTION fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli(p_soggetto_id uuid, p_tipo_soggetto_dettaglio_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli(p_soggetto_id uuid, p_tipo_soggetto_dettaglio_id bigint)
 RETURNS TABLE(soggetto_ruolo_id bigint, tipo_ruolo_id integer, tipo_indirizzo_id integer, ripiego_tipo_indirizzo_id integer)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT x.soggetto_ruolo_id,
     x.tipo_ruolo_id,
     x.tipo_indirizzo_id,
     x.ripiego_tipo_indirizzo_id
    FROM ( SELECT sr.id AS soggetto_ruolo_id,
             sr.tipo_ruolo_id,
             r.tipo_indirizzo_id,
             r.ripiego_tipo_indirizzo_id
            FROM (anagrafiche.soggetti_ruoli sr
              CROSS JOIN LATERAL anagrafiche.fn_indirizzi_obbligatori_mancanti_ruolo(sr.id, fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli.p_tipo_soggetto_dettaglio_id, script.fn_data_operativa()) r(tipo_indirizzo_id, ripiego_tipo_indirizzo_id))
           WHERE (sr.soggetto_id = fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli.p_soggetto_id)
         UNION ALL
          SELECT NULL::bigint AS int8,
             NULL::integer AS int4,
             s.tipo_indirizzo_id,
             s.ripiego_tipo_indirizzo_id
            FROM anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto(fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli.p_soggetto_id, fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli.p_tipo_soggetto_dettaglio_id, script.fn_data_operativa()) s(tipo_indirizzo_id, ripiego_tipo_indirizzo_id)) x
   ORDER BY x.soggetto_ruolo_id NULLS FIRST, x.tipo_indirizzo_id;
END

COMMENT ON FUNCTION anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli(p_soggetto_id uuid, p_tipo_soggetto_dettaglio_id bigint)
IS 'Gli indirizzi obbligatori che la natura data (proposta da un cambio di natura, o quella di oggi) chiede e il soggetto non ha: prima quelli del soggetto (soggetto_ruolo_id e tipo_ruolo_id NULL; anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto), poi quelli di ogni suo ruolo in ordine di id (anagrafiche.fn_indirizzi_obbligatori_mancanti_ruolo), col tipo richiesto e il ripiego che lo sostituisce, il giorno di script.fn_data_operativa(). Sono le letture dei guard degli obbligatori: cio'' che la lista chiede di dare e'' cio'' che i guard pretendono al commit. Serve al form del cambio di natura, che chiede questi indirizzi e li manda nello stesso salvataggio, scritti dopo la natura. La natura non ha default: NULL vuol dire che la natura non conta, e sul soggetto non chiede niente. Soggetto che non esiste: nessuna riga. Gli indirizzi che la natura vieta non sono qui: sono motivi di anagrafiche.fn_check_cambio_natura_soggetto. STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
