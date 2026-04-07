## Documentazione Concettuale -- Funzione `anagrafiche.fn_get_emittente_fiscale_pk()`

> **Vedi anche**
>
> **Approfondimento tabelle:**
>
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/manual/emittenti_fiscali)
> [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/manual/emittenti_fiscali_billing_account)
>
> **Funzione storica correlata:**
>
> [anagrafiche.fn_get_emittente_fiscale_id](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_id) -- restituisce `soggetto_ruolo_id` (NON la PK reale)

---

### Scopo Principale

(creata 07-04-2026)

Restituisce la **PK numerica reale** di `anagrafiche.emittenti_fiscali.id` per un dato
`billing_account`, applicando una catena di risoluzione con fallback al gestore globale.

E' la funzione **da usare** quando serve l'`id` reale dell'emittente fiscale, ad esempio per:

- FK verso `emittenti_fiscali.id` (es. `config.parameter_overrides.emittente_fiscale_id`)
- Filtro permessi backend basato sullo scope emittente
- JOIN diretti su `emittenti_fiscali` quando il dominio chiamante non ragiona su `soggetto_ruolo_id`

---

> ### Differenza con `fn_get_emittente_fiscale_id`
>
> Esiste una funzione storica omonima ma con suffisso `_id` che, **nonostante il nome**,
> NON restituisce `emittenti_fiscali.id` ma `emittente_soggetto_ruolo_id` (=`soggetti_ruoli.id`).
>
> **Quale usare**:
>
> - **`fn_get_emittente_fiscale_pk`** -- quando serve la PK reale di `emittenti_fiscali`
> - **`fn_get_emittente_fiscale_id`** -- quando serve il `soggetto_ruolo_id` (modello vendite, ~33 funzioni)
>
> Le due funzioni convivono per non rompere il dominio vendite (coerente sul suo modello).
> Non rinominiamo la vecchia per evitare un refactor invasivo.

---

### Firma

```sql
anagrafiche.fn_get_emittente_fiscale_pk(
    p_billing_account_id  anagrafiche.billing_account.id%TYPE
)
RETURNS anagrafiche.emittenti_fiscali.id%TYPE
LANGUAGE plpgsql
STABLE
```

| Parametro              | Tipo     | Descrizione                                          |
|------------------------|----------|------------------------------------------------------|
| `p_billing_account_id` | `bigint` | ID del billing account per cui risolvere l'emittente |

**Ritorno**: `bigint` -- valore di `anagrafiche.emittenti_fiscali.id` (PK reale).

---

### Logica di risoluzione

La funzione usa `COALESCE` con due subquery, valutate in **cortocircuito**:

1. **Mapping specifico** -- cerca in `emittenti_fiscali_billing_account` la riga
   con `billing_account_id = p_billing_account_id`, joina su `emittenti_fiscali` via
   `soggetto_ruolo_id`, filtra per `attivo = true`
2. **Fallback default globale** -- se la 1) non trova nulla, cerca la riga con
   `billing_account_id IS NULL AND is_default = true`, sempre con `attivo = true`

Se nemmeno il default risolve, raise `E_EMITTENTE_DEFAULT_MISSING`.

---

### Guard input

| Condizione | Errore |
|------------|--------|
| `p_billing_account_id IS NULL` | `E_PARAMETRO_INVALIDO` |
| `p_billing_account_id <= 0`    | `E_PARAMETRO_INVALIDO` |

---

### Indici utilizzati

| Indice                              | Tabella                              | Scopo                                  |
|-------------------------------------|--------------------------------------|----------------------------------------|
| `uq_emittenti_fiscali_ba`           | `emittenti_fiscali_billing_account`  | Lookup per `billing_account_id`        |
| `uq_emittenti_fiscali_ba_default`   | `emittenti_fiscali_billing_account`  | Lookup default (parziale `is_default`) |
| `uq_emittenti_fiscali_ruolo`        | `emittenti_fiscali`                  | JOIN su `soggetto_ruolo_id`            |
| `ix_emittenti_fiscali_attivo`       | `emittenti_fiscali`                  | Filtro `attivo = true`                 |

---

### Differenze comportamentali rispetto a `fn_get_emittente_fiscale_id`

| Aspetto                    | `fn_get_emittente_fiscale_id` | `fn_get_emittente_fiscale_pk`                       |
|----------------------------|-------------------------------|-----------------------------------------------------|
| Valore restituito          | `soggetto_ruolo_id`           | `emittenti_fiscali.id` (PK reale)                   |
| Filtra per `attivo = true` | NO                            | SI                                                  |
| Guard input                | NO                            | SI (`NULL` o `<= 0` solleva `E_PARAMETRO_INVALIDO`) |
| Volatility                 | (default `VOLATILE`)          | `STABLE`                                            |
| Convenzione default        | `is_default = true`           | `BA NULL + is_default = true`                       |

---

### Esempio d'uso

```sql
-- Risolve la PK emittente per un BA specifico
SELECT anagrafiche.fn_get_emittente_fiscale_pk(123);

-- Uso come campo derivato in una vista (es. vw_preventivi_list)
SELECT
    p.id,
    p.numero,
    anagrafiche.fn_get_emittente_fiscale_pk(p.billing_account_id) AS emittente_fiscale_id
FROM vendite.preventivi p;
```

---

### Errori sollevati

| Codice                       | Quando                                                |
|------------------------------|-------------------------------------------------------|
| `E_PARAMETRO_INVALIDO`       | `p_billing_account_id IS NULL` o `<= 0`               |
| `E_EMITTENTE_DEFAULT_MISSING` | Ne' mapping specifico ne' default globale risolvibili |

---

{% include-markdown "signature-core.md" %}
