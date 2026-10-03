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
* ⭐ **Perché non si può bloccare** lo dice
  [fn_check_credenziale_bloccabile](/dbzero/script/funzioni/fn_check_credenziale_bloccabile),
  la stessa regola che spegne il pulsante «Blocca accesso». Il verbo la chiama
  e solleva il primo motivo:
    * ⛔ una **credenziale di sistema** (l'utente di un processo automatico o
      un sistema esterno) non si blocca dall'applicazione
      (`E_CREDENZIALE_DI_SISTEMA`): fermerebbe il suo lavoro senza che il
      suo pannello lo sappia;
    * ⛔ **non si può bloccare l'ultimo SUPER_ADMIN raggiungibile**, nemmeno
      se stessi (`E_PROFILO_ULTIMO_SUPER_ADMIN`). Resta anche il guard sulla
      tabella
      ([trgfn_credenziali_guard_ultimo_super_admin](/dbzero/config/funzioni/trgfn_credenziali_guard_ultimo_super_admin)),
      che copre due blocchi fatti nello stesso momento.
* 🚨 **L'emergenza**: una credenziale di sistema compromessa (per esempio la
  chiave rubata di un sistema esterno) si blocca **dal server**, dalla
  sessione di chi amministra il database. Anche lì serve un SUPER_ADMIN
  dichiarato come autore: il blocco porta sempre chi l'ha deciso.
* Lo sblocco di una credenziale di sistema resta sempre possibile.
* Le sessioni già aperte le chiude il backend.

---

### Storia

* 2026-09-25 — nasce (`20260925-14`). Brief: brief-db-blocco-login-per-credenziale.
* 2026-10-03 — chiama la check dei motivi; le credenziali di sistema si bloccano solo dal server (`20261003-02`). Brief: brief-db-credenziale-verbi-amministratore.

{% include-markdown "signature-core.md" %}
