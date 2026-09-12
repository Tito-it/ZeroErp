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

(creata 07-04-2026 · latest review 13-09-2026)

Restituisce la **PK numerica reale** di `anagrafiche.emittenti_fiscali.id` per un dato
`billing_account`, e **solleva** se non è risolvibile.

⭐ **Dal 2026-09-13 (changeSet `20260913-03`, D13) non riscrive più la regola**: è
l'**involucro PK** del lettore
[`script.fn_get_ba_emittente_sr_id`](/dbzero/script/manual/fn_get_ba_emittente_sr_id),
esattamente come [`fn_get_emittente_fiscale_id`](/dbzero/anagrafiche/manual/fn_get_emittente_fiscale_id)
ne è l'involucro SR. Fino a quel giorno teneva una **copia** della regola a due
livelli (mapping specifico, altrimenti default): finché i livelli erano gli stessi
non si vedeva, ma con il terzo livello del lettore — *in sessione, l'emittente di
chi agisce* — le due copie avrebbero risposto cose diverse sullo stesso billing
account senza legame: la RLS lo mostra all'operatore, il guard di un preventivo
(`trgfn_preventivi_guard_emittente_ba`, che passa da qui) lo rifiuta perché «il BA
è del default». Una regola, un posto.

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

La regola vive nel lettore, e ha **tre livelli** (dettaglio e ragioni nella sua
pagina): mapping specifico; altrimenti, **in sessione**, l'emittente dell'operatore
che sta agendo; altrimenti il default dell'installazione.

Qui resta solo ciò che è *suo*:

1. il **guard sul parametro** (`E_PARAMETRO_INVALIDO` su `NULL` o `<= 0`);
2. la **traduzione** `soggetto_ruolo_id` → `emittenti_fiscali.id`, con il filtro
   `ef.attivo = true`. ⚠️ Il filtro c'era già, su entrambe le vecchie subquery, e
   resta come **difesa** e non come regola: sul modello un emittente con una riga
   di mapping non si può disattivare (`trgfn_prevent_deactivate_if_children`,
   `emittenti_fiscali_billing_account` non ha `attivo`) e una riga di mapping non
   può puntare a un emittente spento (`trgfn_child_requires_active_parent`), quindi
   il ramo non è raggiungibile. Se lo fosse, «non risolto» è la risposta giusta —
   non un ripiego silenzioso su un'altra azienda, che era il comportamento della
   copia;
3. il raise `E_EMITTENTE_DEFAULT_MISSING` quando nessun livello risponde.

Presidio: `db/pgtap/anagrafiche/test-fn-get-emittente-fiscale-pk.sql` — i test `6`
e `7` sono la coppia in sessione / senza sessione, il `9` dice che la delega è
esatta (PK → SR coincide con il lettore) e il `10` è l'anti-ritorno della copia
(il corpo nomina il lettore e non `is_default`).

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
| Ripiego senza BA           | SI (una query in più, portante per i lotti) | NO: il guard rifiuta il parametro     |
| Regola «quale emittente»   | delega al lettore             | delega al lettore (dal `20260913-03`; prima una copia) |

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
| `E_EMITTENTE_DEFAULT_MISSING` | Nessuno dei tre livelli del lettore risponde (o l'emittente risolto e' spento) |

---

{% include-markdown "signature-core.md" %}
