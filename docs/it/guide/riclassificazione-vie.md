# Guida Operativa – Riclassificazione Vie e Toponomastica

> **Ultimo aggiornamento**: 4 novembre 2026
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

⚠️ Il passo 2 della policy — puntare un indirizzo a un'altra via — ha una funzione, [`dbops.fn_admin_merge_stradario`](/dbzero/dbops/funzioni/fn_admin_merge_stradario): fonde due vie, registra la fusione in `storico.stradario_trasformazioni` e ripunta sulla destinazione gli indirizzi della via d'origine. Oggi però **fallisce appena la via d'origine ha un indirizzo**: non apre il flag di manutenzione, il guard respinge il cambio di `stradario_id` (`E_COLONNA_NON_MODIFICABILE`) e la fusione intera si annulla. Passa solo la fusione di una via senza indirizzi. Le due procedure di manutenzione qui sotto non cambiano `stradario_id`: **rinormalizzano** i dati esistenti, non spostano gli indirizzi.

---

## Procedure di manutenzione

I flag di manutenzione valgono per la **transazione** in cui sono accesi, non per la sessione: per questo una procedura che ne accende uno lo spegne prima di proseguire, anche in caso di errore.

### Rinormalizzazione degli indirizzi di una via

La procedura [`maintenance.proc_bump_indirizzi_dettaglio`](/dbzero/maintenance/funzioni/proc_bump_indirizzi_dettaglio):

* riscrive senza cambiarle le righe di `indirizzi_dettaglio` di un dato `stradario_id`, così i trigger di normalizzazione ricalcolano `via_norm` e `indirizzo_normalizzato`;
* non accende il flag `zeroerp.maintenance_indirizzi_dettaglio`: lo `stradario_id` non cambia, e il guard non scatta. Il flag resta la porta del verbo che sposterà gli indirizzi su un'altra via, quando nascerà;
* lascia la storicizzazione ai trigger standard, che storicizzano solo le righe con `storicizza` attivo.

### Correzione della descrizione di un toponimo

La procedura [`maintenance.proc_bump_toponomastica`](/dbzero/maintenance/funzioni/proc_bump_toponomastica):

* accende il flag `zeroerp.maintenance_toponomastica`, con cui il guard lascia cambiare la descrizione di un toponimo già in uso, e lo spegne subito dopo la scrittura, anche in caso di errore;
* scrive la nuova descrizione su `config.toponomastica`;
* fa rinormalizzare dai trigger le righe di `config.stradario_generale` che usano quel toponimo;
* chiama `proc_bump_indirizzi_dettaglio` per ogni via che usa il toponimo, nella stessa transazione: anche gli indirizzi di dettaglio prendono la descrizione nuova.

Si può chiamare anche dentro un'unità di lavoro più grande: il flag non resta acceso dopo la procedura.

In alternativa alla correzione sul posto, si può creare una **nuova** voce in `config.toponomastica` e riallineare i record di `config.stradario_generale` interessati.

---

## Esempi applicativi

* **Rinomina totale via**: nuova via + riallineamento di tutti i civici collegati al vecchio `stradario_id`
* **Rinomina parziale via**: nuova via + riallineamento solo dei civici del tratto interessato
* **Fusione vie**: riallineamento dei civici su un unico `stradario_id`

---

{% include-markdown "signature-core.md" %}
