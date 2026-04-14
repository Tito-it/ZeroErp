## 📘 Documentazione Concettuale – Funzione `vendite.fn_resolve_prezzo_composito`

> 👀 **Vedi anche**
>
**Guide generali:**
>
• [Gestione listini](/guide/gestione-listini)
>
**Approfondimento tabelle:**
>
• [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
> • [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti)
> • [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe)
>
**Approfondimento funzioni:**
>
• [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2)
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---

### 🎯 Scopo Principale
(latest review 14-04-2026)

`vendite.fn_resolve_prezzo_composito` risolve il prezzo di un articolo **composito** (con distinta base in `catalogo.articoli_componenti`). La logica e' **ibrida**: decide tra due regimi distinti in base al flag `esposto_in_fattura` dei componenti.

Caratteristiche:

* **Delega** la risoluzione del prezzo di ogni singolo componente a `fn_resolve_prezzo_listino_v2` (stessi 3 stadi pricing v5).
* Ritorna un `SETOF` di **una o N righe** a seconda della semantica del BoM.
* Non duplica logica di pricing: mantiene coerenza con il resolver principale.

---

### Comportamento

| Caso   | Condizione                                                    | Output                                                                                                        |
| ------ | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| **A**  | Esiste almeno un componente attivo con `esposto_in_fattura=TRUE` | **N righe**: una per ogni componente obbligatorio attivo alla data; ciascuna con prezzo risolto separatamente e il proprio flag `esposto_in_fattura`. |
| **B1** | Nessun componente esposto, esiste riga listino per il composito | **1 riga**: prezzo dell'articolo composito negoziato (risolto via `fn_resolve_prezzo_listino_v2` sul padre).     |
| **B2** | Nessun componente esposto, nessuna riga listino per il padre   | **1 riga**: prezzo calcolato come `Σ(prezzo_componente * coeff_qta)` sui componenti obbligatori attivi.       |

Quando si ricade dal ramo B1 al B2 il passaggio e' governato da un `EXCEPTION WHEN SQLSTATE 'P0001'`: cattura *solo* le eccezioni di `fn_log_and_raise_error` (riga listino mancante), non errori generici.

---

### Firma

```sql
vendite.fn_resolve_prezzo_composito(
    p_prodotto_id                 uuid,
    p_uom_id                      bigint,
    p_data_riferimento            date,
    p_ba_id                       bigint,
    p_utility_id                  integer,
    p_emittente_soggetto_ruolo_id bigint,
    p_classe_utenza_id            integer DEFAULT NULL
)
RETURNS TABLE (
    componente_id         uuid,
    uom_id                bigint,
    prezzo_unitario       numeric,
    iva_id                bigint,
    descrizione_fattura   varchar,
    esposto_in_fattura    boolean
)
```

---

### Output per colonna

| Campo                | CASO A (per componente)              | CASO B (riga singola)                       |
| -------------------- | ------------------------------------ | ------------------------------------------- |
| `componente_id`      | `articoli_componenti.componente_id`  | `p_prodotto_id` (stesso articolo padre)     |
| `uom_id`             | UoM dell'articolo componente         | `p_uom_id` (UoM richiesta in input)         |
| `prezzo_unitario`    | Prezzo risolto dal v2                | Prezzo padre risolto oppure `Σ(componenti)` |
| `iva_id`             | IVA del componente                   | IVA del prodotto padre                      |
| `descrizione_fattura`| Descrizione del componente           | Descrizione del prodotto padre              |
| `esposto_in_fattura` | Flag dal BoM (true o false)          | Sempre `FALSE`                              |

Nota: nel CASO A sono incluse **tutte** le righe componente obbligatorie, non solo quelle esposte. Le righe non esposte concorrono comunque al totale fatturato — il flag determina solo la **visibilita'** in fattura, non l'esclusione.

---

### Espansione in `commesse_attivita` (CASO A)

Quando si crea un'attivita' in commessa per un articolo composito con almeno un componente esposto, la pipeline di creazione attivita' **espande** in N righe figlie in `commesse_attivita`, una per componente. Questo garantisce:

* tracciabilita' piena prima della fatturazione
* `prezzo_bloccato` per-riga funziona in modo naturale
* lo step fatturazione resta semplice (1 attivita' -> 1 riga fattura)

La pipeline di espansione e' gestita lato Django (Fase 2 backend).

---

### Errori sollevati

Tutti via `script.fn_log_and_raise_error`.

| Codice                              | Quando                                                                                            |
| ----------------------------------- | ------------------------------------------------------------------------------------------------- |
| `E_PARAMETRO_INVALIDO`              | `p_prodotto_id` NULL; gli altri ID sono validati dal resolver v2 durante le chiamate delegate     |

Tutti gli altri errori del pricing (articolo non negoziato su contratto C, categoria non mappata, riga listino mancante sui componenti) **si propagano dal v2 sottostante** alla chiamata composita. Eccezione: la riga listino mancante sul *padre* nel CASO B viene assorbita come fallback verso il calcolo Σ.

---

### Dipendenze DB

* Tabelle: `catalogo.articoli`, `catalogo.articoli_componenti`
* Funzioni: `vendite.fn_resolve_prezzo_listino_v2`, `script.fn_log_and_raise_error`

---

### Esempio

```sql
-- Composito con 3 componenti, uno esposto in fattura
-- Output: 3 righe (una per componente), ciascuna col proprio prezzo
SELECT *
  FROM vendite.fn_resolve_prezzo_composito(
      p_prodotto_id                 := 'b2e1...'::uuid,
      p_uom_id                      := 1,
      p_data_riferimento            := '2026-06-15',
      p_ba_id                       := 12345,
      p_utility_id                  := 1,
      p_emittente_soggetto_ruolo_id := 100,
      p_classe_utenza_id            := NULL
  );
```

```sql
-- Composito senza componenti esposti, senza riga listino per il padre
-- Output: 1 riga con prezzo_unitario = Σ(prezzo_componente * coeff_qta)
SELECT prezzo_unitario
  FROM vendite.fn_resolve_prezzo_composito(
      'c3d4...'::uuid, 1, '2026-06-15', 12345, 1, 100, NULL
  );
```

---

{% include-markdown "signature-core.md" %}
