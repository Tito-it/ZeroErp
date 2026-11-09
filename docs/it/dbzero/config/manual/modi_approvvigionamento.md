## 📘 Documentazione Concettuale – Tabella `config.modi_approvvigionamento`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
> • [config.nature_vendita](/dbzero/config/tabelle/nature_vendita)
>
Approfondimento viste:
> • [catalogo.vw_articoli_dettaglio](/dbzero/catalogo/views/vw_articoli_dettaglio)

---
### 🎯 Scopo Principale

(rev 2026-09-13 — nata con `20260913-04`, seminata da `20260913-09`)

**Da dove arriva la merce di un articolo.** Quattro voci, e ognuna risponde a
una domanda che prima nessuna colonna sapeva porre:

| `codice_interno` | Che cosa dice |
|---|---|
| `ACQUISTO` | la compro — è il **default** di ogni articolo nuovo |
| `PRODUZIONE` | la faccio: questa riga richiede produzione |
| `STOCK` | c'è a magazzino |
| `NON_APPLICABILE` | è una prestazione: non c'è merce |

È il perno di due cantieri indipendenti: la **produzione** («questa riga
richiede produzione?») e l'**acquisto** («questo articolo si compra?»). Un
vocabolario che serve a due cantieri non dipende dalla forma di nessuno dei due.

---

### ⭐ È ortogonale alla natura di vendita, non un suo doppione

`config.nature_vendita` dice **dove va** la riga venduta (ordine, commessa,
contratto); questa tabella dice **da dove arriva** ciò che si promette. Un
assemblato può essere comprato finito, un articolo semplice può essere
prodotto: le due domande hanno risposte indipendenti, e per questo sono due
colonne su `catalogo.articoli` e non una.

⛔ Non si deriva nemmeno da `articoli.is_composito` (che parla di fatturazione
dei componenti) né da `nature_vendita.e_cessione_beni` (che è fiscale).

---

### Regole principali

* Forma di tutti i vocabolari di `config`: `codice_interno` **immutabile** (il
  lock lo monta da solo il framework delle automazioni, per la sola presenza
  della colonna), `codice` e `descrizione` modificabili dall'operatore,
  `attivo`, `ordine`, `meta`.
* La logica confronta **solo** `codice_interno`; a video si mostra la
  `descrizione` (è ciò che la lista articoli espone come
  `modo_approvvigionamento_descrizione`). Regola generale:
  [linee guida SQL §6c](/linee-guida-sql).
* Una voce **spenta** non si può assegnare a un articolo, e una voce usata da
  articoli attivi non si può spegnere: i due trigger nascono dal framework
  ATTIVO a `ci_apply`, non da un changeSet — guida
  [automazione DB](/guide/automazione-db).
* L'indice sulla chiave esterna da `catalogo.articoli` è deciso **`SENZA_INDICE`**
  nel CSV di `dbops.fk_index_policy`: nessuna interrogazione entra da quella colonna.

---

### Come si aggiunge una voce

Nel CSV `80_data/sql/config/modi_approvvigionamento.csv`, mai con un `INSERT`
a parte: il mirror `runOnChange` rilegge il file. Il giorno in cui la
produzione avrà bisogno di attributi («richiede un ordine di lavoro?»), qui c'è
posto: è la ragione per cui è una tabella e non un `CHECK` su una stringa.

Brief: `brief-db-modifiche-certe-ciclo-vendita-e-articolo`, sezione 3.2.

---
{% include-markdown "signature-core.md" %}
