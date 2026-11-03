{% include-markdown "it/dbzero/maintenance/manual/proc_bump_indirizzi_dettaglio.md" %}
# ⚙️ Procedura `proc_bump_indirizzi_dettaglio`

```sql
CREATE PROCEDURE proc_bump_indirizzi_dettaglio(IN p_stradario_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_bump_indirizzi_dettaglio(IN p_stradario_id integer)
 LANGUAGE plpgsql
AS $procedure$
-- Scopo: rinormalizzare anagrafiche.indirizzi_dettaglio di una via
--   (via_norm, civico_norm, indirizzo_normalizzato) dopo che e'
--   cambiato qualcosa da cui dipendono: il nome della via, il
--   toponimo, il comune.
--
-- ⭐ L'aggiornamento e' NEUTRO: riscrive lo stesso stradario_id.
--   Basta a far girare su ogni riga il trigger di normalizzazione,
--   che rilegge la via da script.vw_indirizzo_completo.
--
-- ℹ️ Niente flag di manutenzione: il guard
--   trgfn_indirizzi_dettaglio_protect_update blocca solo un
--   CAMBIO di stradario_id, e qui non ce n'e'. Il flag resta la
--   porta del verbo che spostera' gli indirizzi su un'altra via,
--   quando nascera'. Brief: brief-db-revisione-maintenance D8.
BEGIN
  UPDATE anagrafiche.indirizzi_dettaglio
     SET stradario_id = stradario_id
   WHERE stradario_id = p_stradario_id;
END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_bump_indirizzi_dettaglio(IN p_stradario_id integer)
IS 'Rinormalizza anagrafiche.indirizzi_dettaglio di una via con un aggiornamento neutro (stesso stradario_id): il trigger di normalizzazione ricalcola via_norm, civico_norm e indirizzo_normalizzato da script.vw_indirizzo_completo. Non accende il flag zeroerp.maintenance_indirizzi_dettaglio: il guard su stradario_id blocca solo un cambio di via, e qui la via non cambia. La chiama anche maintenance.proc_bump_toponomastica, per ogni via del toponimo corretto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
