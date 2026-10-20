# ⚙️ Funzione `fn_indirizzi_con_obbligatori`

```sql
CREATE FUNCTION fn_indirizzi_con_obbligatori(p_indirizzi jsonb, p_tipi_obbligatori integer[])
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_indirizzi_con_obbligatori(p_indirizzi jsonb, p_tipi_obbligatori integer[])
 RETURNS jsonb
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- La copia del PRIMO elemento, col tipo sostituito, per ogni
    -- tipo obbligatorio che l'elenco non ha; in ordine di tipo.
    SELECT COALESCE(p_indirizzi, '[]'::jsonb) || COALESCE(
        (SELECT jsonb_agg((p_indirizzi -> 0) || jsonb_build_object('tipo_indirizzo_id', t.tipo)
                          ORDER BY t.tipo)
           FROM (SELECT DISTINCT u.tipo
                   FROM unnest(p_tipi_obbligatori) AS u(tipo)
                  WHERE u.tipo IS NOT NULL) t
          WHERE (p_indirizzi -> 0) IS NOT NULL
            AND NOT EXISTS (
                  SELECT 1
                    FROM jsonb_array_elements(p_indirizzi) AS x
                   WHERE (x ->> 'tipo_indirizzo_id')::integer = t.tipo)),
        '[]'::jsonb);
$function$

COMMENT ON FUNCTION anagrafiche.fn_indirizzi_con_obbligatori(p_indirizzi jsonb, p_tipi_obbligatori integer[])
IS 'BB puro (2026-10-19): all''elenco di indirizzi gia'' normalizzati (ognuno col tipo_indirizzo_id, cioe'' passato da anagrafiche.fn_indirizzo_elemento) aggiunge, per ogni tipo obbligatorio che non c''e'', una copia del PRIMO indirizzo col tipo sostituito; in ordine di tipo, una per tipo. Elenco vuoto: nessuna copia. Non legge tabelle: gli obbligatori li legge chi chiama, ognuno dalla sua matrice. Lettori: anagrafiche.fn_crea_indirizzi_ruolo (config.tipi_ruolo_tipi_indirizzo) e anagrafiche.fn_crea_indirizzi_soggetto (config.tipi_soggetto_dettaglio_tipi_indirizzo). Regola del 2: era scritta nella plurale del ruolo e nella saga del backend SoggettiService._apply_auto_clone. R-BE-12, D-16a di Tid, brief-db-processi-accensione-per-ambiente §6.16.';
```

</div>

---
{% include-markdown "signature-core.md" %}
