## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_attivita_fatturabili_guard_commessa`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — la tabella su cui è montato
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — la riga di commessa da cui l'attività nasce
> * [vendite.commesse](/dbzero/vendite/tabelle/commesse) — la commessa dichiarata
>
> Guide:
>
> * [Fatturazione](/guide/fatturazione) — dalla riga di commessa all'attività fatturabile

---

### 🎯 Scopo Principale

Il guard che tiene coerente un'attività fatturabile con la sua commessa: la riga di commessa da cui
l'attività nasce esiste e appartiene alla commessa che l'attività dichiara.

---

### Che cosa controlla, e che cosa lascia al vincolo

Un'attività fatturabile nasce sempre da una riga di commessa: `commessa_id` e
`commessa_attivita_id` sono obbligatorie. Il guard non ripete questa regola: se una delle due
colonne è vuota, lascia la parola al vincolo NOT NULL, che rifiuta la riga nominando la colonna.

Controlla invece ciò che il vincolo non sa dire:

* che la riga di commessa indicata esista;
* che appartenga alla commessa indicata.

Il controllo scatta all'inserimento e quando cambia una delle due colonne, e vale **sempre**: non
dipende da un parametro.

---

### ⚠️ Il bypass di manutenzione

Un superuser che accende la GUC `zeroerp.maintenance_allow_attivita_bypass` salta il controllo. È
una porta per la manutenzione del dato, non per l'applicazione: l'applicazione non è superuser.

---

### Codici errore

* `E_COMMESSA_ATTIVITA_NON_COERENTE` — la riga di commessa non esiste, oppure appartiene a un'altra
  commessa.

---

### Test

* `vendite/test-attivita-guardrail-commessa-v1` — la coppia coerente passa, la riga di un'altra
  commessa è rifiutata, le colonne vuote le rifiuta il NOT NULL, l'emissione dalla commessa resta
  operativa.

---

### Note di migrazione

* 2026-02-24 — nasce col modello in cui l'attività fatturabile si lega sempre a una riga di
  commessa, acceso da un parametro.
* 2026-11-08 — il parametro `attivita_fatturabili_require_commessa` è ritirato: il guard controlla
  sempre, e i due controlli che ripetevano il NOT NULL sono tolti.

---

{% include-markdown "signature-core.md" %}
