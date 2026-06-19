## Documentazione Concettuale – Funzione `vendite.fn_list_emittibili_lane`

> **Vedi anche**
>
**Tabelle correlate:**
>
[vendite.commesse](/dbzero/vendite/tabelle/commesse),
[vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita),
[vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)
>
**Funzioni correlate:**
>
[vendite.fn_list_commesse_emittibili](/dbzero/vendite/funzioni/fn_list_commesse_emittibili),
[vendite.fn_select_attivita_fatturabili](/dbzero/vendite/funzioni/fn_select_attivita_fatturabili),
[vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa)

---
### 🎯 Scopo Principale
(latest review 19-06-2026 — discovery corsie per il driver batch; grana estesa a `utility_id`)

La funzione **`vendite.fn_list_emittibili_lane`** è la **discovery delle corsie** per il
driver batch di fatturazione. Risponde a:

> «Per questa corsia/perimetro, quali **terne distinte
> `(emittente_soggetto_ruolo_id, tipo_doc_fiscale_id, utility_id)`** hanno lavoro pronto da
> fatturare, e **fino a quale `competenza_mese`** creare il lotto?»

Serve perché un **lotto** è segregato per `(emittente, tipo_doc_fiscale, utility, competenza_mese)`:
oltre a emittente e tipo_doc, `fn_create_fatturazione_lotto` **pretende `utility_id` NOT NULL**
e `fn_select_attivita_fatturabili` **filtra le AF per `ba.utility_id`** (gas/ee/idrico →
documenti distinti). Il driver deve aprire **un lotto per ogni terna** presente, altrimenti
le righe delle altre utility/tipo_doc — pullate ma non catturate — resterebbero orfane
(fatturato perso in silenzio). È **separata** da `fn_list_commesse_emittibili` (che resta
la discovery per-commessa dello step di pull): qui si raggruppa per corsia, non per commessa.

> **Coerenza grana ↔ select (perché la terna è sicura).** La discovery raggruppa per
> `c.utility_id` (`vendite.commesse`), mentre la select a valle filtra per `ba.utility_id`
> (`anagrafiche.billing_account`). I due **coincidono per costruzione**: `fn_get_or_create_commessa`
> impone `commessa.utility_id = billing_account.utility_id` (altrimenti
> `E_CLIENTE_UTILITY_MISMATCH_BA`). Quindi una terna scoperta qui non potrà mai essere
> scartata dalla select per disallineamento di utility — per questo non serve alcun guard
> aggiuntivo su questo asse.

---

### Parametri di input

| Parametro                       | Tipo                                                     | Default | Descrizione                                                        |
| ------------------------------- | -------------------------------------------------------- | ------- | ------------------------------------------------------------------ |
| `p_competenza_mese`             | `vendite.commesse_attivita.competenza_mese%TYPE`         | `NULL`  | **Limite superiore** della competenza (cumulativo, vedi sotto). NULL = nessun limite. |
| `p_billing_account_id`          | `vendite.commesse.billing_account_id%TYPE`               | `NULL`  | Filtro perimetro BA.                                               |
| `p_utility_id`                  | `vendite.commesse.utility_id%TYPE`                        | `NULL`  | Filtro perimetro utility (opzionale).                             |
| `p_emittente_soggetto_ruolo_id` | `vendite.commesse.emittente_soggetto_ruolo_id%TYPE`      | `NULL`  | Filtro perimetro emittente.                                       |
| `p_fatturazione_immediata`      | `vendite.commesse.fatturazione_immediata%TYPE`           | `NULL`  | Corsia: true=immediata / false=differita / NULL=indifferente.     |
| `p_limit`                       | `integer`                                                | `1000`  | Normalizzato (default 1000, max 10000); si applica alle **terne**. |

---

### Output

`RETURNS TABLE(emittente_soggetto_ruolo_id, tipo_doc_fiscale_id, utility_id, competenza_mese, total_candidate)`:

* **`utility_id`** = utility della terna. **Mai NULL** (`commesse.utility_id` è NOT NULL a
  monte): nessuna terna da escludere su questo asse.
* **`competenza_mese`** = `max(competenza_mese)` fra le righe candidate della terna → la
  competenza con cui il driver crea il lotto.
* **`total_candidate`** = numero di righe candidate (per dry-run/diagnostica).

---

### Criteri di inclusione (allineati alla pull e alla select)

1. Commessa in stato **emittibile** (`stati_commessa.emittibile = true`).
2. Righe `commesse_attivita` **`stato_approvazione = 'APPROVATA'` AND `stato_emissione =
   'NON_EMESSA'`** — allineato alla pull (`fn_emit_attivita_fatturabili_da_commessa` con
   `p_only_approved = true`). *Differenza* con `fn_list_commesse_emittibili`, che non filtra
   l'approvazione.
3. **`tipo_doc_fiscale_id IS NOT NULL`** (il lotto lo richiede NOT NULL; le righe con
   tipo_doc NULL sono escluse — il default si risolve all'upsert, non qui).
4. **Competenza cumulativa**: `competenza_mese <= p_competenza_mese` — coerente con
   `fn_select_attivita_fatturabili` (che filtra `<= v_competenza`). Così la discovery
   include gli **arretrati** (mesi precedenti) che la select poi cattura: nessun fatturato
   arretrato perso.
5. Filtri perimetro BA/utility/emittente; corsia `fatturazione_immediata`.

La grana di raggruppamento è **`(emittente, tipo_doc_fiscale, utility)`** con
`competenza_mese = max(...)`: lo stesso emittente con lavoro su più utility (es. gas + ee)
produce **terne distinte**, una per utility, ciascuna destinata a un lotto separato.

---

### Regole principali

* Funzione **STABLE** (read-only, nessun effetto collaterale).
* `LIMIT` sulle **terne** (non sulle commesse).
* `utility_id` in output **mai NULL** (`commesse.utility_id` è NOT NULL a monte).
* `fn_list_commesse_emittibili` resta separata e **invariata** (approccio A3).

---

### Esempio d'uso

```sql
-- corsia immediata, competenza fino a luglio 2026, un emittente specifico
SELECT * FROM vendite.fn_list_emittibili_lane(
  p_competenza_mese => DATE '2026-07-01',
  p_emittente_soggetto_ruolo_id => 55,
  p_fatturazione_immediata => true
);
-- -> (emittente, tipo_doc, utility, competenza_mese=max, total_candidate) per ogni terna
```

---

{% include-markdown "signature-core.md" %}
