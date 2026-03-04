# Guida Operativa – Riclassificazione Vie e Toponomastica

> (latest review 02-03-26)
>
> Destinatari: amministratori database, operatori manutenzione dati
>
> Vedi anche
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — guida architetturale completa
> * [maintenance.proc_bump_indirizzi_dettaglio](/dbzero/maintenance/funzioni/proc_bump_indirizzi_dettaglio)
> * [maintenance.proc_bump_toponomastica](/dbzero/maintenance/funzioni/proc_bump_toponomastica)

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

Il campo `stradario_id` su `anagrafiche.indirizzi_dettaglio` e protetto dal guard `trgfn_indirizzi_dettaglio_protect_update`: la modifica manuale e bloccata. Per eseguire la riclassificazione serve abilitare la modalita manutenzione tramite la procedura dedicata.

---

## Procedure di manutenzione

### Riclassificazione indirizzi

La procedura [`maintenance.proc_bump_indirizzi_dettaglio`](/dbzero/maintenance/funzioni/proc_bump_indirizzi_dettaglio):

* Abilita la modalita manutenzione per la sessione (`zeroerp.maintenance_indirizzi_dettaglio = 'on'`)
* Aggiorna le righe di `indirizzi_dettaglio` per un dato `stradario_id`
* Forza la rinormalizzazione dei campi calcolati
* La storicizzazione avviene automaticamente tramite i trigger standard

### Correzione toponomastica

La procedura [`maintenance.proc_bump_toponomastica`](/dbzero/maintenance/funzioni/proc_bump_toponomastica):

* Abilita la modalita manutenzione per la sessione (`zeroerp.maintenance_toponomastica = 'on'`)
* Aggiorna la riga di `config.toponomastica` con la nuova descrizione
* La propagazione ai record di `config.stradario_generale` e automatica

**Nota:** la correzione di un toponimo non avviene modificando la riga in uso. Si crea una **nuova** voce in `config.toponomastica`, si riallineano i record di `config.stradario_generale` interessati e si lascia che la normalizzazione aggiorni `indirizzo_normalizzato`.

---

## Esempi applicativi

* **Rinomina totale via**: nuova via + riallineamento di tutti i civici collegati al vecchio `stradario_id`
* **Rinomina parziale via**: nuova via + riallineamento solo dei civici del tratto interessato
* **Fusione vie**: riallineamento dei civici su un unico `stradario_id`

---

{% include-markdown "signature-core.md" %}
