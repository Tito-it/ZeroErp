## 📘 Documentazione Concettuale – Funzione `script.fn_blocca_credenziale()`

> 👀 **Vedi anche**
>
> **Il modello:** [config.credenziali](/dbzero/config/tabelle/credenziali)
>
> **Il contrario:** [fn_sblocca_credenziale](/dbzero/script/funzioni/fn_sblocca_credenziale)
>
> **Chi può farlo:** [fn_guard_super_admin](/dbzero/script/funzioni/fn_guard_super_admin)

---

### 🎯 Scopo Principale
(scritta il 25-09-2026)

**Blocca una credenziale** per decisione di un amministratore: da quel momento
la persona non entra più da nessuna porta — gestionale, portale, shop — e da
nessuna macchina.

Le password sbagliate non bloccano mai davvero: frenano chi le prova. Chiudere
una credenziale è un **gesto esplicito**, e porta con sé chi l'ha fatto, quando e
perché.

---

### Regole

* Solo un **SUPER_ADMIN** (prima riga: `fn_guard_super_admin`).
* Il **motivo è obbligatorio** (`E_CREDENZIALE_MOTIVO_OBBLIGATORIO`).
* Il blocco **non scade** e il **reset della password non lo toglie**: lo toglie
  solo [fn_sblocca_credenziale](/dbzero/script/funzioni/fn_sblocca_credenziale).
* Bloccare di nuovo una credenziale già bloccata riscrive chi, quando e perché.
* ⛔ **Non si può bloccare l'ultimo SUPER_ADMIN raggiungibile**, nemmeno se
  stessi: lo impedisce il guard sulla tabella
  ([trgfn_credenziali_guard_ultimo_super_admin](/dbzero/config/funzioni/trgfn_credenziali_guard_ultimo_super_admin)),
  che risponde `E_PROFILO_ULTIMO_SUPER_ADMIN`.
* Le sessioni già aperte le chiude il backend.

---

### Storia

* 2026-09-25 — nasce (`20260925-14`). Brief: brief-db-blocco-login-per-credenziale.

{% include-markdown "signature-core.md" %}
