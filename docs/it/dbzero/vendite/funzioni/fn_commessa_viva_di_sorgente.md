{% include-markdown "it/dbzero/vendite/manual/fn_commessa_viva_di_sorgente.md" %}
# ⚙️ Funzione `fn_commessa_viva_di_sorgente`

```sql
CREATE FUNCTION fn_commessa_viva_di_sorgente(p_sorgente_tipo_id bigint, p_sorgente_chiave text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_commessa_viva_di_sorgente(p_sorgente_tipo_id bigint, p_sorgente_chiave text)
 RETURNS bigint
 LANGUAGE sql
 STABLE
AS $function$
    -- Aperta = lo stato non chiude la commessa: lo stesso predicato
    -- del riuso in vendite.fn_get_or_create_commessa.
    SELECT cs.commessa_id
      FROM vendite.commesse_sorgenti cs
      JOIN vendite.commesse c        ON c.id  = cs.commessa_id
      JOIN vendite.stati_commessa sc ON sc.id = c.stato_commessa_id
     WHERE cs.sorgente_tipo_id = p_sorgente_tipo_id
       AND cs.sorgente_uid     = p_sorgente_chiave
       AND sc.chiude_commessa  = false
     ORDER BY cs.commessa_id DESC
     LIMIT 1
$function$

COMMENT ON FUNCTION vendite.fn_commessa_viva_di_sorgente(p_sorgente_tipo_id bigint, p_sorgente_chiave text)
IS 'Building block (2026-10-12, brief-db-annullo-a-valle-riapre-a-monte §10.6, D-12/D-14 di Tid): la commessa APERTA in cui sta un documento sorgente, o NULL. Aperta = vendite.stati_commessa.chiude_commessa = false, lo stesso predicato con cui vendite.fn_get_or_create_commessa riusa una commessa: una commessa che il push non riusa non trattiene il documento. Dal 20261012-43 il link documento -> commessa resta come storia dopo la chiusura e l''annullo, quindi un documento puo'' avere piu'' link: questa funzione dice quale conta. p_sorgente_chiave e'' la chiave CANONICA di vendite.commesse_sorgenti (config.sorgenti.key_selector: id::text o uuid testuale), quella che vendite.fn_link_commessa_sorgente normalizza in scrittura. Lettori: vendite.fn_link_commessa_sorgente (un secondo invio e'' rifiutato solo se il documento sta in un''altra commessa aperta), vendite.trgfn_guard_fatturazione_immediata_immutabile (il flag si blocca solo con una commessa aperta), il backend. SECURITY INVOKER: le policy di commesse e commesse_sorgenti filtrano per emittente e una commessa ha l''emittente del documento (vendite.trgfn_commesse_sorgenti_guard_emittente), quindi chi vede il documento vede tutte le sue commesse. ORDER BY + LIMIT 1: la porta ne garantisce al piu'' una aperta; l''ordine rende la risposta deterministica. CHIUSA e ANNULLATA sono terminali nella matrice: se un giorno non lo fossero, la riapertura andrebbe controllata.';
```

</div>

---
{% include-markdown "signature-core.md" %}
