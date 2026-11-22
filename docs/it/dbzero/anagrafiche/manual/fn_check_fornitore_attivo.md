## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_check_fornitore_attivo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.fornitori](/dbzero/anagrafiche/tabelle/fornitori) — il flag `attivo` e lo stato del fornitore
> * [config.stati_fornitore](/dbzero/config/tabelle/stati_fornitore) — il flag `blocca_ordini` dello stato
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_fornitore_attivo](/dbzero/anagrafiche/funzioni/fn_guard_fornitore_attivo) — la stessa domanda, con il rifiuto

---

### 🎯 Scopo Principale

`anagrafiche.fn_check_fornitore_attivo` dice se un fornitore si può usare: vero quando esiste, è attivo e il suo
stato non blocca gli ordini; falso in ogni altro caso. Non solleva niente e non scrive niente.

---

### Il check e il guard

È la metà «domanda» di una coppia: `anagrafiche.fn_guard_fornitore_attivo` fa la stessa verifica e rifiuta, con un
codice per ogni motivo. Il check serve dove l'esito è un dato (un filtro, un avviso prima di salvare), il guard
dove deve fermare l'operazione.

Il check è chiuso per difetto: un id assente, un fornitore che non esiste, spento o in uno stato che blocca gli
ordini rispondono tutti falso, senza dire quale dei motivi.

---

### Chi la usa

Nessun oggetto del database la chiama: è a disposizione di chi scrive i flussi del ciclo passivo. Gira coi
permessi di chi la chiama; i fornitori non hanno visibilità per azienda.

---

### ⚠️ Che cosa oggi non copre

* **La regola sta in due corpi.** Il check e il guard scrivono ciascuno la propria lettura di «attivo e non
  bloccato»: una condizione aggiunta a uno dei due non arriva all'altro.

---

### Test

Nessun pgTAP la prova.

---

{% include-markdown "signature-core.md" %}
