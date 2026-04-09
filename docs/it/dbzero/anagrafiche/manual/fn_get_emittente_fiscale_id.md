## Documentazione Concettuale -- Funzione `anagrafiche.fn_get_emittente_fiscale_id()`

> **Vedi anche**
>
> **Approfondimento tabelle:**
>
> [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/manual/emittenti_fiscali_billing_account)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/manual/emittenti_fiscali)
>
> **Funzione correlata:**
>
> [anagrafiche.fn_get_emittente_fiscale_pk](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk) -- restituisce la PK numerica reale di `emittenti_fiscali`

---

> ### ATTENZIONE -- valore di ritorno fuorviante
>
> **Nonostante il suffisso `_id`, questa funzione NON restituisce `anagrafiche.emittenti_fiscali.id`.**
>
> Restituisce **`emittente_soggetto_ruolo_id`** (= `anagrafiche.soggetti_ruoli.id`),
> cioe' il ruolo del soggetto nel modello anagrafico.
>
> Se ti serve la **PK numerica reale** di `emittenti_fiscali` (per FK,
> filtro permessi, JOIN diretti su `emittenti_fiscali.id`) usa
> [`fn_get_emittente_fiscale_pk`](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk).

---

### Scopo Principale

(last review 07-04-2026)

La funzione `anagrafiche.fn_get_emittente_fiscale_id()` risolve il **soggetto_ruolo_id**
dell'emittente fiscale associato a un `billing_account`. Se non esiste un mapping
specifico, ritorna l'emittente di default globale.

E' usata da circa 33 funzioni del dominio `vendite` che ragionano nativamente
in termini di `soggetto_ruolo_id` (es. JOIN con `emittenti_fiscali_utilities.emittente_soggetto_ruolo_id`).
Il modello e' coerente per quel dominio: per questo la funzione **non viene rinominata**
ne' modificata, ma affiancata dalla nuova `fn_get_emittente_fiscale_pk`.

---

### Firma

```sql
anagrafiche.fn_get_emittente_fiscale_id(
    p_billing_account_id  anagrafiche.billing_account.id%TYPE
)
RETURNS anagrafiche.soggetti_ruoli.id%TYPE
```

| Parametro              | Tipo     | Descrizione                                          |
|------------------------|----------|------------------------------------------------------|
| `p_billing_account_id` | `bigint` | ID del billing account per cui risolvere l'emittente |

**Ritorno**: `bigint` -- valore di `emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id`
(equivalente a `anagrafiche.soggetti_ruoli.id`).

---

### Regole applicate

1. Cerca un mapping specifico per `billing_account_id` in `emittenti_fiscali_billing_account`
2. Se assente, usa la riga con `is_default = true` (default globale)
3. Se anche il default manca, raise via `script.fn_log_and_raise_error('E_EMITTENTE_DEFAULT_MISSING')`

**Nota**: la funzione NON filtra per `emittenti_fiscali.attivo` -- ritorna anche
soggetto_ruolo_id di emittenti disattivati (per coerenza con i consumatori storici).

---

### Differenze con `fn_get_emittente_fiscale_pk`

| Aspetto                  | `fn_get_emittente_fiscale_id` | `fn_get_emittente_fiscale_pk`                        |
|--------------------------|-------------------------------|------------------------------------------------------|
| Valore restituito        | `soggetto_ruolo_id`           | `emittenti_fiscali.id` (PK reale)                    |
| Filtra per `attivo=true` | NO                            | SI                                                   |
| Guard input              | NO                            | SI (`NULL` o `<= 0` solleva `E_PARAMETRO_INVALIDO`)  |
| Usato da                 | ~33 funzioni vendite          | viste/funzioni che alimentano la UI permessi         |

---

{% include-markdown "signature-core.md" %}
