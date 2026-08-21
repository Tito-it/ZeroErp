## 📘 Documentazione Concettuale – Tabella `dbops.messaggi_errore_codici_legacy`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [config.codici_errore](/dbzero/config/tabelle/codici_errore)
> • [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
> • [dbops.codici_errore_senza_policy](/dbzero/dbops/tabelle/codici_errore_senza_policy)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Registro del debito ereditato sulla convenzione dei nomi** dei codici errore
(`E_{MODULO}_{TIPO}`, famiglia `W_` per i warning — `docs/it/dev/api.md`).

Ci va un codice che **arriva da fuori già fuori convenzione** e che non conviene rinominare.
Il `CHECK chk_..._non_conforme` impedisce di registrarci un codice conforme: nel registro del
debito non si mette ciò che debito non è.

---

### ⭐ È a **zero righe** dal 2026-08-07 — e non va droppata

Le 57 voci del 2026-08-05 sono state tutte smaltite, l'ultima col rename
`MESSAGGIO_NON_DEFINITO` → `E_MESSAGGIO_NON_DEFINITO`.

⛔ **Non droppare** (decisione di Tid, 2026-08-08). A zero righe il `DROP` sarebbe neutro nel
comportamento, ma:

* costringerebbe a mettere mano al controllo (B) di
  `scripts/sql/guardrail_codice_errore_strutturato.sql` — l'unica cosa che tiene la
  convenzione — **in un presidio che è verde**, che è il momento peggiore per toccarlo;
* toglierebbe il meccanismo già pronto per la prossima eredità di codici.

**Un registro vuoto non è un registro inutile: è un registro in pari.** È anche l'unico modo
per distinguere «nessun debito» da «nessuno lo sta più misurando».

---

### ⚠️ Non è una whitelist di eccezioni

La distinzione decide come si risolvono i casi nuovi.

Una **famiglia nuova con una semantica sua** — com'è stato per i `W_` (changeSet
`20260805-28`) — si risolve **allargando la convenzione**, non registrandola qui. I `W_` non
sono codici sbagliati: sono warning, una categoria diversa, e la convenzione è stata estesa
per accoglierli.

Ecco perché **non c'è una colonna `motivo`**: un'eccezione avrebbe bisogno di essere
giustificata, un debito no — deve solo essere smaltito. L'orologio è `data_registrazione`.

---

### ⚠️ Da non confondere con l'altro registro

`dbops.codici_errore_senza_policy` misura un debito **diverso**: codici privi di policy nel
backend, quindi con lo stato HTTP appiattito su 400. Questo registro riguarda il **nome** del
codice, quello il suo **trasporto**.

---

### Riferimenti

`docs/it/dev/work-done/piano-db-classe-codici-errore.md` §5.5.

---

{% include-markdown "signature-core.md" %}
