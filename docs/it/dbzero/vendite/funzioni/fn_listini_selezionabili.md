# ⚙️ Funzione `fn_listini_selezionabili`

```sql
CREATE FUNCTION fn_listini_selezionabili(p_utility_id integer, p_emittente_fiscale_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_listini_selezionabili(p_utility_id integer, p_emittente_fiscale_id bigint)
 RETURNS TABLE(id bigint, codice character varying, descrizione character varying)
 LANGUAGE sql
 STABLE
AS $function$
    -- Il predicato e' quello del guard del documento: la check pura
    -- sui valori del form. In piu' il solo listino attivo.
    SELECT l.id, l.codice, l.descrizione
      FROM vendite.listini l
     WHERE l.attivo
       AND script.fn_check_listino_documento(l.id, p_utility_id, p_emittente_fiscale_id)
           = jsonb_build_array()
     ORDER BY l.descrizione, l.id;
$function$

COMMENT ON FUNCTION vendite.fn_listini_selezionabili(p_utility_id integer, p_emittente_fiscale_id bigint)
IS 'Lettura per il form di contratto e offerta (richiesta F-2.3): i listini attivi che un documento di questa utility e di questo emittente (emittente_fiscale_id) può scegliere, {id, codice, descrizione}, ordinati per descrizione e id. Sui valori del form, perché in creazione il documento non esiste. Il predicato è script.fn_check_listino_documento, lo stesso del guard script.trgfn_doc_guard_listino_documento: la tendina non propone ciò che il DB rifiuta. Non filtra sulla versione: in DRAFT/BOZZA un listino senza versione in vigore si sceglie, lo rifiutano attivazione ed emissione. Utility o emittente NULL: nessun listino. Sotto RLS (SECURITY INVOKER). Prende il posto dell''SQL di ListiniRepository.list_lookup_selezionabili_contratti (backend). Nasce il 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
