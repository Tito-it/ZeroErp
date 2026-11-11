## 📘 Documentazione Concettuale – Funzione `catalogo.fn_uom_conversione_capability`

> **Ultimo aggiornamento**: 11 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [catalogo.trgfn_uom_guard_storia](/dbzero/catalogo/funzioni/trgfn_uom_guard_storia) — il guard della storia, che la legge per le sue regole
>
> Approfondimento viste:
>
> * [catalogo.vw_articoli_uom_operativa_dettaglio](/dbzero/catalogo/views/vw_articoli_uom_operativa_dettaglio) — la pubblica per le mappature di un articolo
> * [catalogo.vw_unita_misura_conversioni_dettaglio](/dbzero/catalogo/views/vw_unita_misura_conversioni_dettaglio) — la pubblica per le conversioni generali

---

### 🎯 Scopo Principale

Dice che cosa si può fare oggi su una conversione versionata, la mappatura di un articolo o una
conversione generale, partendo dalle sue date: eliminarla, spegnerla o riaccenderla, chiuderla, e
da quale giorno.

---

### Le risposte

Una conversione è **in vigore** quando comincia prima di oggi, cioè ha giorni passati. Un inizio
vuoto vuol dire «da sempre».

* **Eliminare** e **spegnere o riaccendere**: solo una conversione senza giorni passati, quella
  inserita per errore. Altrimenti il motivo è `UOM_STORIA_IN_VIGORE`: si chiude.
* **Chiudere**: se la fine è vuota o non è ancora passata. Una fine già passata non si tocca più,
  e il motivo è `UOM_STORIA_CHIUSA`.
* **La prima fine ammessa** è la più tarda fra l'inizio e ieri: la fine non cambia i giorni già
  passati. **La fine proposta** è la più tarda fra l'inizio e oggi. Tutte e due sono vuote quando la
  conversione non si chiude.

Il giorno è quello operativo dell'azienda.

---

### Perché qui

È la regola del guard della storia, scritta una volta sola. Il guard la legge per decidere se
rifiutare, le due viste di dettaglio per dire all'interfaccia che cosa offrire: così l'interfaccia
non propone un'azione che il database poi respinge.

Non dice niente delle colonne che non si cambiano mai (unità, articolo, fattore, inizio): quelle le
blocca il lock di colonna, e il form le legge fra i campi non modificabili. Non tratta la riga
dell'unità base, che ha regole sue.

---

### Test

* `db/pgtap/catalogo/test-uom-conversione-capability-v1.sql` — le risposte sulle date costruite, le
  due viste, e il guard che riga per riga fa quello che la funzione dice.

---

### Note di migrazione

* 2026-11-11 — nasce (brief-db-revisione-catalogo, §15.11).

---

{% include-markdown "signature-core.md" %}
