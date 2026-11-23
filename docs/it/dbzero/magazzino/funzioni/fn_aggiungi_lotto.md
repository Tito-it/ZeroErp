{% include-markdown "it/dbzero/magazzino/manual/fn_aggiungi_lotto.md" %}
# ⚙️ Funzione `fn_aggiungi_lotto`

```sql
CREATE FUNCTION fn_aggiungi_lotto(p_articolo_id uuid, p_codice character varying, p_data_arrivo date, p_campi jsonb)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_aggiungi_lotto(p_articolo_id uuid, p_codice character varying, p_data_arrivo date, p_campi jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
BEGIN
    -- Scopo: il gesto «nuovo lotto» dell'operatore: livello TUTTO
    --   sull'oggetto, poi il BB. L'azienda del lotto la mette il
    --   default di sessione e la controlla il guard di perimetro
    --   della tabella. Ritorna l'id.
    PERFORM script.fn_guard_livello(
        script.fn_utente_di_sessione('magazzino.fn_aggiungi_lotto'),
        'magazzino', 'lotti', 'TUTTO');

    RETURN magazzino.fn_crea_lotto(p_articolo_id, p_codice, p_data_arrivo, p_campi);
END;
$function$

COMMENT ON FUNCTION magazzino.fn_aggiungi_lotto(p_articolo_id uuid, p_codice character varying, p_data_arrivo date, p_campi jsonb)
IS 'VERBO: il gesto «nuovo lotto» dell''operatore. Prima riga script.fn_guard_livello(utente, magazzino, lotti, TUTTO): sotto il livello, o senza utente, E_PERMESSO_NEGATO. Poi magazzino.fn_crea_lotto: colonne ammesse, articolo attivo, date e unicita'' sono del BB e della tabella. L''emittente non si sceglie: lo mette il default di sessione (trgfn_default_emittente_fiscale) e lo controlla il guard di perimetro della tabella. SECURITY DEFINER del proprietario, search_path bloccato. Ritorna l''id.';
```

</div>

---
{% include-markdown "signature-core.md" %}
