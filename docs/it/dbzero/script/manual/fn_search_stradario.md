## Documentazione Concettuale -- Funzione `script.fn_search_stradario()`

> **Vedi anche**
>
**Approfondimento tabelle:**
>
[config.stradario](/dbzero/config/tabelle/stradario)
> [config.stradario_generale](/dbzero/config/tabelle/stradario_generale)
> [config.toponomastica](/dbzero/config/tabelle/toponomastica)
> [config.comuni](/dbzero/config/tabelle/comuni)
> [config.codici_postali](/dbzero/config/tabelle/codici_postali)
>
**Approfondimento funzioni:**
>
[anagrafiche.fn_search_indirizzi_dettaglio](/dbzero/anagrafiche/manual/fn_search_indirizzi_dettaglio)
> [anagrafiche.fn_get_or_create_indirizzo_dettaglio](/dbzero/anagrafiche/manual/fn_get_or_create_indirizzo_dettaglio)
>
**Guide:**
>
[Gestione degli indirizzi](/guide/gestione-degli-indirizzi)

---
### 🎯 Scopo Principale
(latest review 13-03-2026)
Ricerca vie (stradario) per autocomplete frontend. L'utente seleziona
un comune e cerca una via nel comune selezionato.

Pattern coerente con `fn_search_soggetti_universale` e
`fn_search_indirizzi_dettaglio` — funzione STABLE in `script`,
usata dal backend come entry point di ricerca.

**Flusso utente tipico:**

1. Seleziona un comune (autocomplete comuni)
2. Cerca una via nel comune selezionato (questa funzione)
3. Inserisce il civico manualmente
4. Il backend chiama `fn_get_or_create_indirizzo_dettaglio` per ottenere/creare il civico

---

⭐ Restituisce solo le vie **vive**: una via soppressa (`obsoleto_dal` valorizzata, fusa in
un'altra) non si propone più.

### Parametri

| Parametro     | Tipo                      | Obbligatorio | Default | Note                                                     |
| ------------- | ------------------------- | :----------: | ------- | -------------------------------------------------------- |
| `p_comune_id` | `config.comuni.id%TYPE`   |    No*       | `NULL`  | Filtra per comune (caso principale). Guard: se fornito, > 0. |
| `p_search`    | `text`                    |    No*       | `NULL`  | Testo ILIKE su `indirizzo_normalizzato`. Normalizzato con BTRIM. |
| `p_limit`     | `integer`                 |    No        | `30`    | Max righe restituite.                                    |

> Almeno uno tra `p_comune_id` e `p_search` deve essere valorizzato.
> Errore `E_ADMIN_VALIDAZIONE` se entrambi NULL/vuoti.

---

### Valore di ritorno

RETURNS TABLE con le seguenti colonne:

| Colonna                  | Tipo                                          | Fonte                            |
| ------------------------ | --------------------------------------------- | -------------------------------- |
| `stradario_id`           | `config.stradario.id%TYPE`                    | PK stradario                     |
| `toponimo`               | `config.toponomastica.descrizione%TYPE`       | Es. "Via", "Piazza"             |
| `denominazione`          | `config.stradario_generale.descrizione%TYPE`  | Es. "Roma", "Garibaldi"         |
| `indirizzo_normalizzato` | `config.stradario_generale.indirizzo_normalizzato%TYPE` | Es. "VIA ROMA"      |
| `comune_id`              | `config.comuni.id%TYPE`                       | ID comune                        |
| `comune_descrizione`     | `config.comuni.descrizione%TYPE`              | Es. "ROMA"                      |
| `provincia_sigla`        | `config.province.sigla%TYPE`                  | Es. "RM"                        |
| `codice_postale_id`      | `config.codici_postali.id%TYPE`               | ID codice postale                |
| `cap`                    | `config.codici_postali.codice%TYPE`           | Es. "00100"                     |

---

### Logica di funzionamento

1. **Normalizzazione** `p_search`: `NULLIF(BTRIM(...), '')`.
2. **Guard**: almeno un criterio (p_comune_id o p_search). `p_comune_id > 0` se fornito.
3. **JOIN**:
   `stradario` → `stradario_generale` → `toponomastica`
   `stradario` → `comuni` → `province` (LEFT JOIN)
   `stradario` → `codici_postali`
4. **Filtri**:
   - `toponomastica.attivo = TRUE` (esclude toponimi disattivati)
   - `comune_id = p_comune_id` (se fornito)
   - `indirizzo_normalizzato ILIKE '%' || v_search || '%'` (se fornito)
5. **ORDER BY** `indirizzo_normalizzato`, `stradario.id`
6. **LIMIT** `p_limit`

---

### Indici utilizzati

| Indice                                | Tabella                    | Tipo     | Scopo                          |
| ------------------------------------- | -------------------------- | -------- | ------------------------------ |
| `ix_stradario_generale_norm_trgm`     | `config.stradario_generale`| GIN trgm | ILIKE su indirizzo_normalizzato|
| `ix_config_stradario_comune_id`       | `config.stradario`         | B-Tree   | Filtro per comune              |
| `ix_config_stradario_codice_postale_id` | `config.stradario`       | B-Tree   | JOIN codici_postali            |

---

### Esempi di utilizzo

```sql
-- 1) Ricerca vie in un comune specifico
SELECT * FROM script.fn_search_stradario(
    p_comune_id := 4517,
    p_limit := 20
);

-- 2) Ricerca fuzzy per nome via in un comune
SELECT * FROM script.fn_search_stradario(
    p_comune_id := 4517,
    p_search := 'ROMA',
    p_limit := 10
);

-- 3) Ricerca solo per nome via (tutti i comuni)
SELECT * FROM script.fn_search_stradario(
    p_search := 'GARIBALDI',
    p_limit := 30
);

-- 4) Errore: nessun criterio
SELECT * FROM script.fn_search_stradario();
-- → E_ADMIN_VALIDAZIONE
```

---

### Caratteristiche tecniche

* **Volatilita'**: `STABLE` + `PARALLEL SAFE` — non modifica dati
* **Linguaggio**: PL/pgSQL
* **Tipi colonne**: `%TYPE` per allineamento automatico
* **Error handling**: `script.fn_log_and_raise_error` (log persistente + raise)
* **Performance**: con `p_comune_id` il numero di vie e' contenuto
  (un comune ha mediamente poche centinaia di vie). L'indice trigram su
  `stradario_generale.indirizzo_normalizzato` supporta la ricerca fuzzy.

---

{% include-markdown "signature-core.md" %}
