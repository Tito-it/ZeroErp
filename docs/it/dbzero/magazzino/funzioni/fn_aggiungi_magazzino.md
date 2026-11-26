{% include-markdown "it/dbzero/magazzino/manual/fn_aggiungi_magazzino.md" %}
# ⚙️ Funzione `fn_aggiungi_magazzino`

```sql
CREATE FUNCTION fn_aggiungi_magazzino(p_codice character varying, p_descrizione character varying, p_indirizzo_dettaglio_id bigint, p_campi jsonb)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_aggiungi_magazzino(p_codice character varying, p_descrizione character varying, p_indirizzo_dettaglio_id bigint, p_campi jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
BEGIN
    -- Scopo: il gesto «nuovo magazzino» dell'operatore: livello
    --   TUTTO sull'oggetto, poi il BB. Ritorna l'id.
    PERFORM script.fn_guard_livello(
        script.fn_utente_di_sessione('magazzino.fn_aggiungi_magazzino'),
        'magazzino', 'magazzini', 'TUTTO');

    RETURN magazzino.fn_crea_magazzino(
               p_codice, p_descrizione, p_indirizzo_dettaglio_id, p_campi);
END;
$function$

COMMENT ON FUNCTION magazzino.fn_aggiungi_magazzino(p_codice character varying, p_descrizione character varying, p_indirizzo_dettaglio_id bigint, p_campi jsonb)
IS 'VERBO: il gesto «nuovo magazzino» dell''operatore. Prima riga script.fn_guard_livello(utente, magazzino, magazzini, TUTTO): sotto il livello, o senza utente, E_PERMESSO_NEGATO. Poi magazzino.fn_crea_magazzino con l''emittente della sessione: colonne ammesse in p_campi, default, perimetro (trgfn_guard_emittente_scope) e vincoli sono del BB e della tabella. SECURITY DEFINER del proprietario, search_path bloccato: l''applicazione non scrive magazzino.magazzini da sola. Ritorna l''id.';
```

</div>

---
{% include-markdown "signature-core.md" %}
