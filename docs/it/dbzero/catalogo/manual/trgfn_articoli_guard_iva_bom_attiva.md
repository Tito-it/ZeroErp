## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_articoli_guard_iva_bom_attiva`

> **Ultimo aggiornamento**: 9 novembre 2026
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

Fa valere, sull'articolo, la regola «il kit e i suoi componenti hanno la stessa IVA», sui legami
attivi da oggi in poi. Si giudica a fine transazione: l'IVA di un kit e dei suoi componenti (che
cambia per legge) si cambia in una transazione, in qualunque ordine.

La regola ha due lati. Sul legame la giudica il guard della distinta, quando il legame nasce o
si riaccende. Sull'articolo la giudica questo guard, quando cambia l'IVA.

---

### I due casi

Il guard è un **constraint trigger** `AFTER UPDATE OF iva_id`, `DEFERRABLE INITIALLY DEFERRED`,
quando l'IVA cambia davvero. Scatta alla fine della transazione e giudica lo stato di allora: l'IVA
di adesso dell'articolo e di quelli collegati, non il valore della singola istruzione.

* **L'articolo è un kit.** Si cerca un componente di un suo legame con un'IVA diversa.
* **L'articolo è un componente.** Si cerca il padre di un suo legame con un'IVA diversa.

Contano i legami attivi **da oggi in poi** (la validità arriva almeno al giorno aziendale): un
legame già finito non blocca.

Basta un articolo collegato con un'IVA diversa perché il cambio sia rifiutato
(`E_BOM_IVA_DISCORDANTE`). Il messaggio nomina il kit, il componente e le due aliquote in
percentuale, non l'id dell'IVA; un'IVA vuota si legge «—».

Il confronto tratta due IVA vuote come uguali: un articolo senza IVA in un kit senza IVA passa.
Un'IVA vuota contro una valorizzata è una differenza.

---

### ⚠️ Nei pgTAP

I pgTAP girano con `SET CONSTRAINTS ALL IMMEDIATE`: lì il guard scatta a fine istruzione. Per
provare il cambio in più istruzioni, il test differisce il solo vincolo
(`SET CONSTRAINTS catalogo.trg_articoli_a10_guard_iva_bom_attiva_upd DEFERRED`) e poi lo riporta
immediato.

La regola dell'IVA sul legame la giudica il guard della distinta, quando il legame nasce o si
riaccende.

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
* `db/pgtap/catalogo/test-iva-kit-a-fine-transazione-v1.sql` — il constraint trigger differito; kit e
  componente insieme, in un'istruzione o in due; il solo kit e il solo componente rifiutati; un
  legame finito che non blocca; l'IVA vuota letta «—».

---

### Note di migrazione

* 2026-05-13 — nasce.
* 2026-06-03 — il lato legame giudica anche la riaccensione di un legame: prima il percorso
  «spegni il legame, cambia l'IVA, riaccendi» restava scoperto.
* 2026-11-09 — diventa un constraint trigger differito sui legami da oggi in poi: l'IVA di un kit e
  dei suoi componenti si cambia in una transazione; un'IVA vuota si legge «—»; l'errore porta il
  campo e il `tx_id` (brief-db-revisione-catalogo, giro 3).

---

{% include-markdown "signature-core.md" %}
