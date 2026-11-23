## 📘 Documentazione Concettuale – Funzione `magazzino.fn_documento_interno_famiglia`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.inventari](/dbzero/magazzino/tabelle/inventari) — la testata dell'inventario
> * [magazzino.rettifiche](/dbzero/magazzino/tabelle/rettifiche) — la testata della rettifica
> * [magazzino.trasferimenti](/dbzero/magazzino/tabelle/trasferimenti) — la testata del trasferimento
>
> Approfondimento funzioni:
>
> * [magazzino.fn_documento_interno_blocca](/dbzero/magazzino/funzioni/fn_documento_interno_blocca) — lo legge per prendere la testata
> * [script.fn_check_documento_interno_registrabile](/dbzero/script/funzioni/fn_check_documento_interno_registrabile) — lo legge per dire se un documento si registra

---

### 🎯 Scopo Principale

Il **registro delle tre famiglie** dei documenti interni: per inventario, rettifica e trasferimento dice le tabelle, le colonne che li legano, lo stato, il magazzino che fa da perimetro e la variabile della registrazione.

---

### ⭐ Una funzione e non una tabella

Una famiglia nuova vuole tabelle, controlli e vincoli suoi: non si aggiunge configurando una riga. Il registro sta nel codice, accanto alle tabelle che descrive, e chi chiede una famiglia che non esiste riceve nessuna riga: il codice d'errore lo sceglie chi chiama.

---

### La tabella della testata è anche l'oggetto del permesso

Il livello dell'operatore si controlla sul documento: per la testata e per le righe, l'oggetto è la tabella della testata che il registro indica.

---

### Test

`db/pgtap/magazzino/test-verbi-documenti-interni-v1.sql` (le tre famiglie, nessuna riga per una che non esiste).

---

### Note di migrazione

* 2026-11-23 — nasce dalla stessa mappa che stava in tre posti: nel registro del backend, nella funzione che dice se un documento si registra e nei verbi (`brief-db-magazzino-tutte-le-scritture-dal-verbo`).

---

{% include-markdown "it/dbzero/magazzino/_documenti-interni.md" %}

---

{% include-markdown "signature-core.md" %}
