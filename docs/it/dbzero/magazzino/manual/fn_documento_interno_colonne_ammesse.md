## 📘 Documentazione Concettuale – Funzione `magazzino.fn_documento_interno_colonne_ammesse`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [magazzino.fn_documento_interno_famiglia](/dbzero/magazzino/funzioni/fn_documento_interno_famiglia) — il registro delle famiglie
> * [script.fn_guard_campi_ammessi](/dbzero/script/funzioni/fn_guard_campi_ammessi) — il controllo che usa la lista

---

### 🎯 Scopo Principale

Le colonne che i verbi dei documenti interni accettano, per **famiglia**, **parte** (testata o riga) e **gesto** (crea o modifica): la sede unica della lista, che leggono i verbi e il backend.

---

### Che cosa c'è nella lista

**Testata, alla nascita**: la data, la descrizione (inventario), il magazzino di arrivo (trasferimento) e la provenienza. **Testata, in modifica**: la data e la descrizione; la provenienza e l'arrivo non cambiano dopo la nascita.

**Riga**, alla nascita e in modifica: le colonne della riga, articolo compreso. La coerenza di articolo, lotto, seriale e ubicazione la dicono i controlli della tabella.

---

### ⛔ Che cosa non c'è mai

Lo stato (ha il suo verbo), il magazzino della testata e la testata della riga (sono l'identità della nascita), la quantità di sistema (la scrive la registrazione), le note strutturate e le colonne che scrive il sistema. Su una combinazione che non esiste la lista è vuota, e un verbo che la usa non ammette niente.

---

### Test

`db/pgtap/magazzino/test-verbi-documenti-interni-v1.sql`.

---

### Note di migrazione

* 2026-11-23 — nasce dalle liste di colonne che stavano nel backend (`brief-db-magazzino-tutte-le-scritture-dal-verbo`).

---

{% include-markdown "it/dbzero/magazzino/_documenti-interni.md" %}

---

{% include-markdown "signature-core.md" %}
