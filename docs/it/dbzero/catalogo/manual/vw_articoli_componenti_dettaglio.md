## 📘 Documentazione Concettuale – Vista `catalogo.vw_articoli_componenti_dettaglio`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:   
>
[catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti)      
> [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)     

---
### 🎯 Scopo Principale
(latest review 14-01-26)
La vista **`catalogo.vw_articoli_componenti_dettaglio`** espone i legami
prodotto–componente e arricchisce la riga con codice/descrizione di prodotto
e componente.

Restituisce **una riga per legame componente**.

---

### Struttura logica della vista

La vista parte da `catalogo.articoli_componenti` e aggiunge:

* join a `catalogo.articoli` per il **prodotto**;
* join a `catalogo.articoli` per il **componente**.

---

### 📑 Campi esposti (principali)

| Colonna                                       | Descrizione                |
| --------------------------------------------- | -------------------------- |
| `id`, `prodotto_id`, `componente_id`          | Identificativi del legame. |
| `prodotto_codice`, `prodotto_descrizione`     | Dati articolo prodotto.    |
| `componente_codice`, `componente_descrizione` | Dati articolo componente.  |
| `coeff_qta`, `obbligatorio`                   | Parametri del legame. (`partecipa_qta` e `determina_qta_padre` ritirate il 2026-10-02, `20261002-62`.) |
| `valid_from`, `valid_to`                      | Validita temporale.        |
| `attivo`, `storicizza`, `tx_id`               | Stato e tracciamento.      |

(Sono esposti anche i campi di audit e note di `catalogo.articoli_componenti`.)

---

### Modalita' d'uso tipiche

```sql
SELECT *
FROM catalogo.vw_articoli_componenti_dettaglio
WHERE prodotto_id = :articolo_id
ORDER BY valid_from;
```

---

### Best practice e raccomandazioni

* Usare la vista per consultazione e composizione distinta base.
* Per modifiche, aggiornare sempre `catalogo.articoli_componenti`.

---
<!-- rev-2026-09-28-liste-righe -->
### 🔄 rev 2026-09-28 — brief-db-liste-righe-documento

**Diventa la sorgente unica delle righe della distinta base** (`20260928-27`, D-8.5): la lista configurabile `catalogo.articolo_componenti` e il repository la leggono. In coda `determina_qta_padre` ed `esposto_in_fattura` (dal 2026-10-01 `esposizione_in_fattura`, vedi sotto), che solo la copia Python aveva. La capability di chiusura resta qui, sede unica (il backend ritira la sua copia).

<!-- rev-2026-10-01-esposizione -->
### 🔄 rev 2026-10-01 — brief-db-esposizione-componenti-kit-in-fattura

**L'esposizione in fattura passa da due a tre modi** (`20261001-44`; la vista è stata tolta da `20261001-42` per convertire la colonna e ricreata identica nel resto):

| Colonna | Cosa porta |
| --- | --- |
| `esposizione_in_fattura` | al posto di `esposto_in_fattura`, nello stesso posto: il codice interno `NASCOSTO` \| `DESCRITTIVO` \| `VALORIZZATO`. È il valore su cui ragiona la logica |
| `esposizione_in_fattura_codice` | in coda: il `codice` di `config.esposizioni_componente`, quello che la lista a video mostra |
| `esposizione_in_fattura_etichetta_key` | in coda: la chiave i18n dell'etichetta, per il frontend |

La decodifica è in `LEFT JOIN`: una riga che non aggancia il vocabolario resta visibile nella distinta. Il significato dei tre modi è in [`catalogo.articoli_componenti`](/dbzero/catalogo/tabelle/articoli_componenti); fino al 2026-10-01 la colonna era il booleano `esposto_in_fattura` (`false` → `NASCOSTO`, `true` → `DESCRITTIVO`).

<!-- rev-2026-10-02-flag-qta -->
### 🔄 rev 2026-10-02 — brief-db-bom-flag-quantita-e-kit-in-fattura

**Senza `partecipa_qta` e `determina_qta_padre`** (`20261002-62`; la vista è stata tolta da `20261002-60` per ritirare le due colonne dalla tabella, e ricreata identica nel resto). Nessuna logica le leggeva: la quantità del componente è sempre `quantità padre × coeff_qta`. La lista configurabile non le mostrava.

---
{% include-markdown "signature-core.md" %}
