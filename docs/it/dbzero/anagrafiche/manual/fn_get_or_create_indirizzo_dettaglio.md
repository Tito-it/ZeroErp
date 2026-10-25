## Documentazione Concettuale -- Funzione `anagrafiche.fn_get_or_create_indirizzo_dettaglio()`

> **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)
> [config.stradario](/dbzero/config/tabelle/stradario)
>
**Approfondimento funzioni:**
>
[anagrafiche.fn_search_indirizzi_dettaglio](/dbzero/anagrafiche/manual/fn_search_indirizzi_dettaglio)
> [anagrafiche.fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/manual/fn_crea_indirizzo_soggetto) (futuro)
>
**Guide:**
>
[Gestione degli indirizzi](/guide/gestione-degli-indirizzi)

---
### 🎯 Scopo Principale
(ultima revisione 25-10-2026 — brief-db-unicita-civico-indirizzi-dettaglio, D1, D4, D5)

Building block del «trova o crea» di un civico in `anagrafiche.indirizzi_dettaglio`:
restituisce l'id della riga che corrisponde all'indirizzo fisico, creandola se manca.
**Mai `NULL`.**

La chiave naturale (stradario_id + civico + estensione + palazzina + scala + piano +
interno) si confronta sui valori **come li salva il trigger**: i parametri passano per
`fn_build_indirizzo_normalizzato`, la stessa funzione del trigger. Un'estensione `a`, `A`
o `/A` e un interno minuscolo trovano la stessa riga. La deduplicazione la garantisce
l'indice `uq_indirizzi_dettaglio_norm_v2` (`NULLS NOT DISTINCT`).

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
2. **Guard esistenza stradario**: `config.stradario.id` deve esistere. Errore `E_CODICE`.
3. **Normalizzazione**: i parametri passano per `fn_build_indirizzo_normalizzato`.
   Se la via non si risolve in `script.vw_indirizzo_completo` (per esempio un comune
   senza provincia), tutti i valori tornano `NULL` e la funzione si ferma con
   `E_INDIRIZZO_VIA_NON_RISOLTA`, invece di cercare con una chiave vuota.
4. **Ricerca per chiave naturale**: `IS NOT DISTINCT FROM` su tutte le colonne,
   coi valori normalizzati, allineata all'indice.
5. **Se non trovato**: `INSERT` coi valori normalizzati. I trigger calcolano
   `via_norm`, `civico_norm`, `indirizzo_normalizzato` e giudicano la chiave
   (`trgfn_indirizzi_dettaglio_guard_chiave`: civico > 0, dettaglio con lettere o cifre).
6. **Corsa concorrente**: `EXCEPTION WHEN unique_violation` → nuova ricerca. Se non
   trova niente è un'invariante rotta: `E_INDIRIZZO_DETTAGLIO_NON_RILETTO` (TECNICO).
7. **Riga trovata ma disattivata**: si riattiva (`attivo = true`) e se ne restituisce
   l'id. Chi usa di nuovo un indirizzo fisico lo rimette in uso; un indirizzo spento
   non si potrebbe collegare (`trgfn_child_requires_active_parent`).

---

### Trigger coinvolti (INSERT)

| Trigger                                   | Fase          | Effetto                                          |
| ----------------------------------------- | ------------- | ------------------------------------------------ |
| `trgfn_indirizzi_dettaglio_normalize`     | BEFORE INSERT | Calcola `via_norm`, `civico_norm`, `indirizzo_normalizzato` |
| `trgfn_audit_data_user_generic`           | BEFORE INSERT | Imposta `data_insert`, `user_insert`             |
| `trgfn_tx_id_managed`                     | BEFORE INSERT | Assegna `tx_id` di sessione                      |
| `trgfn_indirizzi_dettaglio_guard_chiave`  | BEFORE INSERT | Giudica la chiave dopo la normalizzazione (z10)  |

---

### Vincolo di deduplicazione

`uq_indirizzi_dettaglio_norm_v2` sulle sette colonne nude, `NULLS NOT DISTINCT`
(definizione esatta nella pagina della tabella): due civici `SNC` con lo stesso
dettaglio collidono.

---

### Riusabilita'

| Chiamante                        | Uso                                              |
| -------------------------------- | ------------------------------------------------ |
| `fn_create_indirizzo`            | Crea via (se nuova) e civico in un'unica istruzione |
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
* **Sicurezza**: `SECURITY INVOKER`
* **Concorrenza**: sicura grazie a gestione `unique_violation` e alla ri-lettura

---

{% include-markdown "signature-core.md" %}
