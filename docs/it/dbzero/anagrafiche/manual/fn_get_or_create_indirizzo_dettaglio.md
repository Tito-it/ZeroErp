## Documentazione Concettuale -- Funzione `anagrafiche.fn_get_or_create_indirizzo_dettaglio()`

> **Vedi anche**
>
> **Approfondimento tabelle:**
>
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)
> * [config.stradario](/dbzero/config/tabelle/stradario)
>
> **Approfondimento funzioni:**
>
> * [anagrafiche.fn_search_indirizzi_dettaglio](/dbzero/anagrafiche/manual/fn_search_indirizzi_dettaglio)
> * [anagrafiche.fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/manual/fn_crea_indirizzo_soggetto) (futuro)
>
> **Guide:**
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi)

---

### Scopo Principale

(latest review 13-03-2026)
Building block atomico per l'upsert di un civico normalizzato in
`anagrafiche.indirizzi_dettaglio`.

Cerca per chiave naturale (stradario_id + civico + estensione + palazzina +
scala + piano + interno); se non esiste, lo crea. La deduplicazione e'
garantita dal vincolo `uq_indirizzi_dettaglio_norm`.

---

### Parametri

| Parametro             | Tipo                                     | Obbligatorio | Default | Note                                       |
| --------------------- | ---------------------------------------- | :----------: | ------- | ------------------------------------------ |
| `p_stradario_id`      | `config.stradario.id%TYPE`               |      Si      | —       | Guard: NULL o <= 0 bloccato.               |
| `p_civico`            | `indirizzi_dettaglio.civico%TYPE`        |      No      | `NULL`  | Numero civico.                             |
| `p_estensione_civico` | `indirizzi_dettaglio.estensione_civico%TYPE` |  No      | `NULL`  | Es. A, B, bis.                             |
| `p_palazzina`         | `indirizzi_dettaglio.palazzina%TYPE`     |      No      | `NULL`  | Palazzina / corpo di fabbrica.             |
| `p_scala`             | `indirizzi_dettaglio.scala%TYPE`         |      No      | `NULL`  | Scala.                                     |
| `p_piano`             | `indirizzi_dettaglio.piano%TYPE`         |      No      | `NULL`  | Piano.                                     |
| `p_interno`           | `indirizzi_dettaglio.interno%TYPE`       |      No      | `NULL`  | Interno / unita'.                          |

---

### Valore di ritorno

`anagrafiche.indirizzi_dettaglio.id%TYPE` (BIGINT) -- ID del civico esistente o appena creato.

---

### Logica di funzionamento

1. **Guard** `p_stradario_id`: obbligatorio e > 0. Errore `E_ADMIN_VALIDAZIONE`.
2. **Guard esistenza stradario**: verifica che `config.stradario.id` esista.
   Errore `E_GENERICO`.
3. **Ricerca per chiave naturale**: allineata al vincolo `uq_indirizzi_dettaglio_norm`.
   Usa `IS NOT DISTINCT FROM` per `civico` (nullable) e `COALESCE('', ...)` per
   i campi opzionali.
4. **Se trovato**: restituisce l'id esistente (nessuna modifica).
5. **Se non trovato**: INSERT + RETURNING id. I trigger calcolano
   automaticamente `via_norm`, `civico_norm`, `indirizzo_normalizzato`.
6. **Race condition**: gestita con `EXCEPTION WHEN unique_violation` →
   re-SELECT per ottenere il record inserito dall'altra sessione.

---

### Trigger coinvolti (INSERT)

| Trigger                                   | Fase          | Effetto                                          |
| ----------------------------------------- | ------------- | ------------------------------------------------ |
| `trgfn_indirizzi_dettaglio_normalize`     | BEFORE INSERT | Calcola `via_norm`, `civico_norm`, `indirizzo_normalizzato` |
| `trgfn_audit_data_user_generic`           | BEFORE INSERT | Imposta `data_insert`, `user_insert`             |
| `trgfn_tx_id_managed`                     | BEFORE INSERT | Assegna `tx_id` di sessione                      |

---

### Vincolo di deduplicazione

`uq_indirizzi_dettaglio_norm` su:
```
(stradario_id, civico,
 COALESCE(estensione_civico, ''),
 COALESCE(palazzina, ''),
 COALESCE(scala, ''),
 COALESCE(piano, ''),
 COALESCE(interno, ''))
```

---

### Riusabilita'

| Chiamante                        | Uso                                              |
| -------------------------------- | ------------------------------------------------ |
| `fn_crea_indirizzo_soggetto`     | Verifica/crea civico prima di associarlo          |
| `fn_crea_operatore` (futuro)     | Indirizzo residenza tramite building block        |
| Backend (Django)                 | Dopo selezione via + civico dall'autocomplete     |

---

### Esempi di utilizzo

```sql
-- 1) Get o crea un civico semplice
SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(
    p_stradario_id := 42,
    p_civico := 10
);

-- 2) Get o crea con dettagli completi
SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(
    p_stradario_id := 42,
    p_civico := 10,
    p_estensione_civico := 'A',
    p_palazzina := 'B',
    p_scala := '1',
    p_piano := '2',
    p_interno := '3'
);

-- 3) Errore: stradario_id NULL
SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(
    p_stradario_id := NULL
);
-- → E_ADMIN_VALIDAZIONE
```

---

### Caratteristiche tecniche

* **Volatilita'**: VOLATILE (esegue INSERT)
* **Linguaggio**: PL/pgSQL
* **Tipi colonne**: `%TYPE` per allineamento automatico
* **Error handling**: `script.fn_log_and_raise_error` (log persistente + raise)
* **Concorrenza**: sicura grazie a gestione `unique_violation`

---

{% include-markdown "signature-core.md" %}
