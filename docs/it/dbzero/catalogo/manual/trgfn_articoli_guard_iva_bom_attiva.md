## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_articoli_guard_iva_bom_attiva`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — la tabella su cui il guard è montato
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — i legami di distinta che il guard interroga
> * [config.iva](/dbzero/config/tabelle/iva) — l'aliquota che compare nel messaggio
>
> Approfondimento funzioni:
>
> * [catalogo.trgfn_articoli_componenti_guard_componente](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_guard_componente) — il lato legame della stessa regola
> * [script.fn_check_articolo_riga](/dbzero/script/funzioni/fn_check_articolo_riga) — la check del legame, col motivo `E_BOM_IVA_DISCORDANTE`
>
> Guide:
>
> * [Modello componenti BoM](/dev/manual/modello-componenti-bom) — perché un kit ha un'IVA sola

---

### 🎯 Scopo Principale

Impedisce di cambiare `iva_id` su un articolo che sta in una distinta attiva, se il cambio
rompe la regola «il kit e i suoi componenti hanno la stessa IVA».

La regola ha due lati. Sul legame la giudica il guard della distinta, quando il legame nasce o
si riaccende. Sull'articolo la giudica questo guard, quando cambia l'IVA.

---

### I due casi

Il guard è `BEFORE UPDATE OF iva_id`, riga per riga.

* **L'articolo è un kit.** Se l'articolo è composito, si cerca un componente di un suo legame
  attivo con un'IVA diversa dalla nuova.
* **L'articolo è un componente.** Sempre, anche se l'articolo non è composito, si cerca il padre
  di un suo legame attivo con un'IVA diversa dalla nuova.

Basta un articolo collegato con un'IVA diversa perché il cambio sia rifiutato
(`E_BOM_IVA_DISCORDANTE`). Il messaggio nomina il kit, il componente e le due aliquote in
percentuale, non l'id dell'IVA.

Il confronto tratta due IVA vuote come uguali: un articolo senza IVA in un kit senza IVA passa.
Un'IVA vuota contro una valorizzata è una differenza.

---

### ⚠️ Che cosa oggi non copre

* **L'IVA di un kit con legami attivi non si cambia più.** Il guard confronta la nuova IVA con
  quella **attuale** degli articoli collegati, e non aspetta la fine della transazione. Se si
  cambia prima il kit, i componenti hanno ancora la vecchia; se si cambia prima un componente,
  il kit ha ancora la vecchia. Nemmeno un UPDATE unico passa: la prima riga elaborata vede le
  altre col valore vecchio.
* **Contano anche i legami chiusi.** Il guard filtra solo i legami attivi, senza guardare la
  validità. Un legame scaduto resta attivo, e non si può spegnere appena una riga di documento
  lo cita: blocca il cambio d'IVA anche quando quella distinta non è più in vigore.
* **Con `iva_id` vuota il messaggio esce incompleto.** Se la nuova IVA è vuota, l'aliquota nuova
  nel messaggio resta vuota invece di mostrare un segnaposto.
* **L'errore non porta il `tx_id` della riga.**

La regola dell'IVA sul legame, invece, regge: un legame che si riaccende in uno stato incoerente
è rifiutato dal guard della distinta.

---

### Codici errore

* `E_BOM_IVA_DISCORDANTE` — la nuova IVA dell'articolo è diversa da quella di un componente (se
  l'articolo è un kit) o di un padre (se è un componente) di un legame attivo.

---

### Test

* `db/pgtap/catalogo/test-guard-iva-reactivation-v1.sql` — con il legame spento l'IVA del padre
  cambia, perché il guard ignora i legami spenti; la riaccensione del legame in uno stato
  incoerente è rifiutata dal lato legame.
* `db/pgtap/catalogo/test-distinta-un-livello-e-onere-natura-v1.sql` — su un legame con un
  componente composito e un'IVA diversa parla prima il livello della distinta, poi l'IVA.

---

### Note di migrazione

* 2026-05-13 — nasce.
* 2026-06-03 — il lato legame giudica anche la riaccensione di un legame: prima il percorso
  «spegni il legame, cambia l'IVA, riaccendi» restava scoperto.

---

{% include-markdown "signature-core.md" %}
