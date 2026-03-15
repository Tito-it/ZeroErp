## Documentazione Concettuale -- Funzione `anagrafiche.fn_crea_indirizzo_soggetto()`

> **Vedi anche**
>
> **Approfondimento tabelle:**
>
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti)
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)
> * [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi)
> * [config.tipi_soggetto_dettaglio_tipi_indirizzo](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo)
>
> **Approfondimento funzioni:**
>
> * [anagrafiche.fn_get_or_create_indirizzo_dettaglio](/dbzero/anagrafiche/manual/fn_get_or_create_indirizzo_dettaglio)
> * [anagrafiche.fn_crea_operatore](/dbzero/anagrafiche/manual/fn_crea_operatore)
>
> **Guide:**
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi)

---

### Scopo Principale

(latest review 13-03-2026)

Building block per la creazione di un indirizzo soggetto (`anagrafiche.indirizzi_soggetti`).
Supporta due modalita':

- **Normalizzata** (preferita): riceve `p_indirizzo_dettaglio_id` (da `fn_get_or_create_indirizzo_dettaglio`)
- **Libera** (eccezione): riceve `p_indirizzo_libero` + campi geografici

La funzione esegue il lookup del `tipo_indirizzo_id` da `codice_interno`, applica guard
espliciti per XOR e completezza, e delega ai trigger la validazione tipo, normalizzazione,
sync geoloc, audit e storicizzazione.

---

### Parametri

| Parametro                  | Tipo                                              | Obbligatorio | Default | Note                                                     |
| -------------------------- | ------------------------------------------------- | :----------: | ------- | -------------------------------------------------------- |
| `p_soggetto_id`            | `anagrafiche.soggetti.id%TYPE`                    |     Si       |         | UUID soggetto destinatario                               |
| `p_tipo_indirizzo_codice`  | `config.tipi_indirizzi.codice_interno%TYPE`       |     Si       |         | Es. `'RESID'`, `'DOMFISC'`, `'SEDEOP'`                  |
| `p_indirizzo_dettaglio_id` | `anagrafiche.indirizzi_dettaglio.id%TYPE`         |     No*      | `NULL`  | Modalita' normalizzata (da `fn_get_or_create_...`)       |
| `p_indirizzo_libero`       | `anagrafiche.indirizzi_soggetti.indirizzo_libero%TYPE` | No*    | `NULL`  | Modalita' libera (eccezione)                             |
| `p_stato_id`               | `anagrafiche.indirizzi_soggetti.stato_id%TYPE`    |     No**     | `NULL`  | Obbligatorio se modalita' libera                         |
| `p_comune_id`              | `anagrafiche.indirizzi_soggetti.comune_id%TYPE`   |     No**     | `NULL`  | Obbligatorio se modalita' libera                         |
| `p_codice_postale_id`      | `anagrafiche.indirizzi_soggetti.codice_postale_id%TYPE` | No**  | `NULL`  | Obbligatorio se modalita' libera                         |

> \* Esattamente uno tra `p_indirizzo_dettaglio_id` e `p_indirizzo_libero` deve essere valorizzato (XOR).
> \** Obbligatori solo in modalita' libera (guard esplicito + check constraint DB).

---

### Valore di ritorno

`anagrafiche.indirizzi_soggetti.id%TYPE` — ID del record creato.

---

### Logica di funzionamento

1. **Guard** `p_soggetto_id` e `p_tipo_indirizzo_codice` obbligatori
2. **Guard XOR**: esattamente uno tra `p_indirizzo_dettaglio_id` e `p_indirizzo_libero`
3. **Guard completezza libero**: se `p_indirizzo_libero`, obbligatori `p_stato_id` + `p_comune_id` + `p_codice_postale_id`
4. **Lookup** `tipo_indirizzo_id` da `config.tipi_indirizzi.codice_interno`
5. **INSERT** in `anagrafiche.indirizzi_soggetti`

---

### Vincoli e trigger che scattano automaticamente

| Vincolo/Trigger                                          | Tipo    | Scopo                                      |
| -------------------------------------------------------- | ------- | ------------------------------------------ |
| `chk_indirizzi_soggetti_xor_norm_libero`                 | CHECK   | XOR dettaglio/libero                       |
| `chk_indirizzi_soggetti_free_requirements`               | CHECK   | Completezza indirizzo libero               |
| `uq_indirizzi_soggetti_soggetto_tipo`                    | UNIQUE  | Un indirizzo per tipo per soggetto         |
| `trgfn_indirizzi_soggetti_guard_tipo_indirizzo`          | BEFORE  | Verifica tipo ammesso per tipo_soggetto    |
| `trgfn_child_requires_active_parent` (soggetti)          | AFTER   | Soggetto deve essere attivo                |
| `trgfn_child_requires_active_parent` (indirizzi_dettaglio)| AFTER  | Indirizzo dettaglio deve essere attivo     |
| `trgfn_indirizzi_base_normalize`                         | BEFORE  | Normalizzazione campi                      |
| `trgfn_indirizzi_sync_geoloc`                            | BEFORE  | Sync coordinate geoloc                     |
| `trgfn_audit_data_user_generic`                          | BEFORE  | Audit data_insert/user_insert              |
| `trgfn_tx_id_managed`                                    | BEFORE  | Generazione tx_id                          |
| `trgfn_storico_generic`                                  | BEFORE  | Storicizzazione su UPDATE/DELETE           |

---

### Esempi di utilizzo

```sql
-- 1) Indirizzo normalizzato (caso standard)
SELECT anagrafiche.fn_crea_indirizzo_soggetto(
    p_soggetto_id            := 'a1b2c3d4-...'::uuid,
    p_tipo_indirizzo_codice  := 'RESID',
    p_indirizzo_dettaglio_id := 12345
);

-- 2) Indirizzo libero (eccezione — es. estero non normalizzabile)
SELECT anagrafiche.fn_crea_indirizzo_soggetto(
    p_soggetto_id            := 'a1b2c3d4-...'::uuid,
    p_tipo_indirizzo_codice  := 'RESID',
    p_indirizzo_libero       := '123 Main Street, Springfield',
    p_stato_id               := 2,   -- USA
    p_comune_id              := 4517,
    p_codice_postale_id      := 100
);

-- 3) Errore: entrambi specificati
SELECT anagrafiche.fn_crea_indirizzo_soggetto(
    p_soggetto_id            := 'a1b2c3d4-...'::uuid,
    p_tipo_indirizzo_codice  := 'RESID',
    p_indirizzo_dettaglio_id := 12345,
    p_indirizzo_libero       := 'testo'
);
-- -> E_ADMIN_VALIDAZIONE: specificare uno solo
```

---

### Riusabilita'

Questa funzione e' un building block puro: non sa chi la chiama.
Viene usata da:

- `anagrafiche.fn_crea_operatore` (orchestratore) per creare RESID + DOMFISC
- Qualsiasi futuro orchestratore o service che deve creare indirizzi soggetto

---

### Caratteristiche tecniche

* **Volatilita'**: `VOLATILE` — modifica dati
* **Linguaggio**: PL/pgSQL
* **Tipi colonne**: `%TYPE` per allineamento automatico
* **Error handling**: `script.fn_log_and_raise_error` (log persistente + raise)

---

{% include-markdown "signature-core.md" %}
