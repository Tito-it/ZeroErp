## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_calcoli_tempo_guard_immutabili`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.calcoli_tempo](/dbzero/pratiche/tabelle/calcoli_tempo) — la tabella che protegge
>
> Approfondimento funzioni:
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva l'errore

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_calcoli_tempo_guard_immutabili` rende immutabili i riferimenti
di un calcolo di tempo: una volta nato, il calcolo non cambia pratica, flussi, formula né punto di
partenza.

---

### I campi protetti

`pratica_id`, `flusso_da_id`, `flusso_a_id`, `formula_tempo_id`, `giorni_formula` e
`data_inizio_calcolo` sono la definizione del calcolo: cambiarne uno vorrebbe dire un altro calcolo,
che si crea come riga nuova. Restano modificabili le colonne che il calcolo produce mentre avanza.

Il guard scatta `BEFORE UPDATE`, riga per riga, e solo quando l'aggiornamento nomina una di quelle
colonne; per ognuna confronta il valore vecchio col nuovo, e un valore riscritto uguale passa.

---

### Codici errore

* `E_COLONNA_NON_MODIFICABILE` — uno dei campi protetti cambia valore; il contesto dell'errore porta il
  nome della colonna e l'id del calcolo.

---

{% include-markdown "signature-core.md" %}
