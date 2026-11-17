# ⚙️ Funzione `fn_tipo_indirizzo_obbligatorio_per_ruolo`

```sql
CREATE FUNCTION fn_tipo_indirizzo_obbligatorio_per_ruolo(p_tipo_ruolo_id integer, p_tipo_soggetto_dettaglio_id bigint, p_tipo_indirizzo_id integer, p_oggi date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo(p_tipo_ruolo_id integer, p_tipo_soggetto_dettaglio_id bigint, p_tipo_indirizzo_id integer, p_oggi date)
 RETURNS boolean
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT ((EXISTS ( SELECT 1
            FROM config.tipi_ruolo_tipi_indirizzo m
           WHERE ((m.tipo_ruolo_id = fn_tipo_indirizzo_obbligatorio_per_ruolo.p_tipo_ruolo_id) AND (m.tipo_indirizzo_id = fn_tipo_indirizzo_obbligatorio_per_ruolo.p_tipo_indirizzo_id) AND m.obbligatorio))) AND anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo((p_tipo_ruolo_id)::bigint, p_tipo_indirizzo_id, p_oggi) AND anagrafiche.fn_tipo_indirizzo_ammesso_per_natura(p_tipo_soggetto_dettaglio_id, p_tipo_indirizzo_id, p_oggi));
END

COMMENT ON FUNCTION anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo(p_tipo_ruolo_id integer, p_tipo_soggetto_dettaglio_id bigint, p_tipo_indirizzo_id integer, p_oggi date)
IS 'Vero se il tipo di indirizzo e'' obbligatorio per il tipo di ruolo, su un soggetto della natura data, il giorno dato: la riga (ruolo, tipo) di config.tipi_ruolo_tipi_indirizzo e'' obbligatoria, il tipo di ruolo ammette il tipo (anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo) e la natura lo ammette (anagrafiche.fn_tipo_indirizzo_ammesso_per_natura). Un tipo che la natura non ammette non e'' obbligatorio: nessuna scrittura lo accetterebbe. Natura NULL: la natura non conta. Lo leggono la copia degli obbligatori di anagrafiche.fn_crea_indirizzi_ruolo e la colonna obbligatorio dei picker anagrafiche.fn_tipi_indirizzo_proponibili_ruolo e anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo. Non e'' il requisito del guard anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required. STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
