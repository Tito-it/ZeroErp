{% include-markdown "it/dbzero/script/manual/fn_get_indirizzo.md" %}
# ⚙️ Funzione `fn_get_indirizzo`

```sql
CREATE FUNCTION fn_get_indirizzo(p_soggetto_ruolo_id integer, p_tipo_codice character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzo(p_soggetto_ruolo_id integer, p_tipo_codice character varying)
 RETURNS TABLE(indirizzo_completo text, geoloc geometry)
 LANGUAGE sql
 STABLE
AS $function$
  /*
    Funzione: script.fn_get_indirizzo(p_soggetto_ruolo_id int, p_tipo_codice varchar)
    Scopo:
      Restituisce UN solo indirizzo (testo + geoloc) per un dato soggetto_ruolo e
      per un tipo di indirizzo identificato da config.tipi_indirizzi.codice_interno.

    Come funziona:
      - Richiama script.fn_get_indirizzi_by_ruolo(p_soggetto_ruolo_id)
      - Filtra per tipo_indirizzo = p_tipo_codice
      - Limita il risultato a 1 riga (LIMIT 1)

    Output:
      - indirizzo_completo (text): stringa human-readable costruita secondo le priorità
        della funzione sottostante (dettaglio normalizzato → libero → estero).
      - geoloc (geometry, tipicamente POINT SRID 4326): privilegia la geoloc puntuale del civico,
        altrimenti usa la geoloc dell’indirizzo (logica ereditata dalla funzione sottostante).

    Note:
      - Se esistono più indirizzi dello stesso tipo, senza ORDER BY la scelta non è garantita
        in modo deterministico: viene restituita “una” riga conforme al filtro.
        Se serve una regola di scelta (es. preferire quelli con geoloc non NULL),
        aggiungere un ORDER BY coerente prima del LIMIT.
      - STABLE, senza effetti collaterali. Dipendenze indirette:
        anagrafiche.indirizzi, anagrafiche.indirizzi_dettaglio,
        config.tipi_indirizzi, config.comuni, config.codici_postali.
  */


SELECT indirizzo_completo, geoloc
FROM script.fn_get_indirizzi_by_ruolo(p_soggetto_ruolo_id)
WHERE tipo_indirizzo = p_tipo_codice
LIMIT 1;
$function$
```
---
{% include-markdown "signature-core.md" %}
