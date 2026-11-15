# ⚙️ Funzione `fn_indirizzo_elemento_da_riga`

```sql
CREATE FUNCTION fn_indirizzo_elemento_da_riga(p_indirizzo_dettaglio_id bigint, p_indirizzo_libero text, p_stato_id integer, p_comune_id integer, p_codice_postale_id integer, p_administrative_area character varying, p_locality character varying, p_sublocality character varying, p_postal_code character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_indirizzo_elemento_da_riga(p_indirizzo_dettaglio_id bigint, p_indirizzo_libero text, p_stato_id integer, p_comune_id integer, p_codice_postale_id integer, p_administrative_area character varying, p_locality character varying, p_sublocality character varying, p_postal_code character varying)
 RETURNS jsonb
 LANGUAGE sql
 IMMUTABLE
BEGIN ATOMIC
 SELECT
         CASE
             WHEN (p_indirizzo_dettaglio_id IS NOT NULL) THEN jsonb_build_object('indirizzo_dettaglio_id', p_indirizzo_dettaglio_id)
             ELSE jsonb_strip_nulls(jsonb_build_object('indirizzo_libero', p_indirizzo_libero, 'stato_id', p_stato_id, 'comune_id', p_comune_id, 'codice_postale_id', p_codice_postale_id, 'administrative_area', p_administrative_area, 'locality', p_locality, 'sublocality', p_sublocality, 'postal_code', p_postal_code))
         END AS jsonb_strip_nulls;
END

COMMENT ON FUNCTION anagrafiche.fn_indirizzo_elemento_da_riga(p_indirizzo_dettaglio_id bigint, p_indirizzo_libero text, p_stato_id integer, p_comune_id integer, p_codice_postale_id integer, p_administrative_area character varying, p_locality character varying, p_sublocality character varying, p_postal_code character varying)
IS 'Building block: l''elemento di un indirizzo, nella grammatica di anagrafiche.fn_indirizzo_elemento e senza il tipo, ricostruito dalle colonne di una riga salvata (indirizzi_soggetti o indirizzi, che hanno gli stessi tipi). Con il dettaglio: solo indirizzo_dettaglio_id (il dettaglio si condivide, non si duplica). Altrimenti la forma libera: indirizzo_libero, stato_id, comune_id, codice_postale_id, administrative_area, locality, sublocality, postal_code, quelli valorizzati. geoloc, tx_id, audit e storicizza non si copiano: sono quelli della riga nuova. Lo usano i verbi della copia anagrafiche.fn_copia_indirizzo_soggetto e fn_copia_indirizzo_ruolo, che aggiungono il tipo e scrivono con la madre singolare. Pura, IMMUTABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
