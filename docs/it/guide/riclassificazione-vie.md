# Guida Operativa – Riclassificazione Vie e Toponomastica

> **Ultimo aggiornamento**: 3 novembre 2026
>
> **Destinatari**: amministratori database, operatori manutenzione dati
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [maintenance.proc_bump_indirizzi_dettaglio](/dbzero/maintenance/funzioni/proc_bump_indirizzi_dettaglio) — rinormalizza gli indirizzi di una via
> * [maintenance.proc_bump_toponomastica](/dbzero/maintenance/funzioni/proc_bump_toponomastica) — corregge la descrizione di un toponimo in uso
> * [anagrafiche.trgfn_indirizzi_dettaglio_protect_update](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_dettaglio_protect_update) — il guard su `stradario_id`
>
> **Vedi anche** — guide correlate:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — guida architetturale completa

---

## Quando serve

La riclassificazione si rende necessaria quando cambia la toponomastica ufficiale:

* Una via viene rinominata (totalmente o parzialmente)
* Due vie vengono fuse in una sola
* Cambia il tipo di toponimo (es. da "Strada" a "Via")
* Un comune viene accorpato o rinominato

Queste variazioni non sono frequenti, ma quando avvengono devono propagarsi correttamente a tutti gli indirizzi coinvolti senza perdere lo storico.

---

## Policy operativa unica

Per tutte le casistiche si adotta la stessa logica in quattro passi:

1. **Creare il nuovo riferimento in configurazione**
   * Vie: nuova riga in `config.stradario_generale` e relativo record in `config.stradario`
   * Comuni: nuovo riferimento in `config.comuni` (o aggiornamento coerente con le regole di dominio)

2. **Allineare gli indirizzi coinvolti**
   * Aggiornare **solo** le righe di `anagrafiche.indirizzi_dettaglio` interessate, puntandole al nuovo riferimento

3. **Rinormalizzare**
   * I trigger di normalizzazione aggiornano `via_norm` e `indirizzo_normalizzato`

4. **Storico garantito**
   * Le modifiche sono tracciate in `storico.stradario` e in `storico.indirizzi_dettaglio`

---

## Protezione stradario_id

Il campo `stradario_id` su `anagrafiche.indirizzi_dettaglio` è protetto dal guard `trgfn_indirizzi_dettaglio_protect_update`: cambiarlo è bloccato, a meno che nella transazione sia acceso il flag di manutenzione `zeroerp.maintenance_indirizzi_dettaglio`.

⚠️ Il passo 2 della policy — puntare un indirizzo a un'altra via — oggi non ha una procedura: nessuna delle due procedure di manutenzione cambia `stradario_id`. Le procedure qui sotto **rinormalizzano** i dati esistenti, non spostano gli indirizzi.

---

## Procedure di manutenzione

Tutte e due accendono un flag che vale per la **transazione** in cui sono chiamate, non per la sessione.

### Rinormalizzazione degli indirizzi di una via

La procedura [`maintenance.proc_bump_indirizzi_dettaglio`](/dbzero/maintenance/funzioni/proc_bump_indirizzi_dettaglio):

* accende il flag `zeroerp.maintenance_indirizzi_dettaglio` e lo rispegne prima di uscire, anche in caso di errore;
* riscrive senza cambiarle le righe di `indirizzi_dettaglio` di un dato `stradario_id`, così i trigger di normalizzazione ricalcolano `via_norm` e `indirizzo_normalizzato`;
* lascia la storicizzazione ai trigger standard, che storicizzano solo le righe con `storicizza` attivo.

### Correzione della descrizione di un toponimo

La procedura [`maintenance.proc_bump_toponomastica`](/dbzero/maintenance/funzioni/proc_bump_toponomastica):

* accende il flag `zeroerp.maintenance_toponomastica`, con cui il guard lascia cambiare la descrizione di un toponimo già in uso;
* scrive la nuova descrizione su `config.toponomastica`;
* fa rinormalizzare dai trigger le righe di `config.stradario_generale` che usano quel toponimo.

⚠️ Due limiti di oggi:

* la rinormalizzazione si ferma allo stradario generale: gli indirizzi di dettaglio su quelle vie tengono la via normalizzata vecchia finché non si lancia `proc_bump_indirizzi_dettaglio` via per via;
* il flag resta acceso fino alla fine della transazione chiamante: la procedura va chiamata da sola, non dentro un'unità di lavoro più grande.

In alternativa alla correzione sul posto, si può creare una **nuova** voce in `config.toponomastica` e riallineare i record di `config.stradario_generale` interessati.

---

## Esempi applicativi

* **Rinomina totale via**: nuova via + riallineamento di tutti i civici collegati al vecchio `stradario_id`
* **Rinomina parziale via**: nuova via + riallineamento solo dei civici del tratto interessato
* **Fusione vie**: riallineamento dei civici su un unico `stradario_id`

---

{% include-markdown "signature-core.md" %}
