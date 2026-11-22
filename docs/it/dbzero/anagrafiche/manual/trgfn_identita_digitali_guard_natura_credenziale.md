## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_identita_digitali_guard_natura_credenziale`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — le vesti di cui si confronta la natura
> * [config.credenziali](/dbzero/config/tabelle/credenziali) — lo stato della password, comune a tutte le vesti
>
> Approfondimento viste:
>
> * [dbops.vw_credenziali_da_sanare](/dbzero/dbops/views/vw_credenziali_da_sanare) — il presidio delle credenziali miste che il guard non vede
>
> Approfondimento funzioni:
>
> * [script.fn_veste_di_sistema](/dbzero/script/funzioni/fn_veste_di_sistema) — la natura di una veste
> * [script.fn_categoria_accesso](/dbzero/script/funzioni/fn_categoria_accesso) — la categoria di una credenziale, che poggia su questa regola
> * [anagrafiche.trgfn_identita_digitali_guard_coerenza](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_coerenza) — il guard che scatta prima, sul tipo di veste
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — vesti, credenziali e l'area «Accessi»

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_identita_digitali_guard_natura_credenziale` impedisce che una credenziale abbia insieme vesti di
una persona e vesti di una macchina.

---

### Una credenziale è di una persona o di una macchina

Una veste è **di macchina** quando è del sistema esterno (`API_CLIENT`) o è tecnica (`tecnica = true`); altrimenti è
**di persona**. Lo dice `script.fn_veste_di_sistema`. Tutte le vesti di una credenziale, anche le spente, devono
avere la stessa natura.

Il modello non ammette la credenziale mista per due motivi:

* una credenziale è **una password per tutte le porte**: chi conosce quella di un processo sarebbe anche la persona,
  e viceversa;
* le azioni della credenziale, il blocco e il secondo fattore, valgono per tutte le sue vesti: bloccare la persona
  fermerebbe il processo all'insaputa di chi lo guarda.

Contano anche le vesti spente, perché una veste spenta è ancora della sua credenziale, e riaccenderla non deve
poter mescolare. Su questa regola poggia la categoria di una credenziale (`script.fn_categoria_accesso`), cioè il
tab dell'area «Accessi» in cui sta.

Il caso che si incontra è un'email di un utente tecnico usata per invitare una persona: rimedia chi compila, con
un'altra email.

---

### Quando scatta

Prima dell'inserimento di una veste e di ogni modifica che nomina `auth_user_id`, `ruolo_applicativo` o `tecnica`:
le tre colonne che cambiano la natura della veste o la credenziale a cui appartiene. Scatta dopo il guard di
coerenza: un tipo ritirato si rifiuta prima di chiedersene la natura.

---

### ⚠️ Che cosa oggi non copre

* **Le righe già scritte.** Il guard giudica la riga che passa, non le credenziali miste nate prima della regola.
* **Due scritture concorrenti.** Due transazioni che scrivono insieme le due nature sulla stessa credenziale non si
  vedono a vicenda, e passano tutte e due.

Le une e le altre le segnala il presidio `dbops.vw_credenziali_da_sanare`, col motivo `PERSONA_E_SISTEMA`.

---

### Codici errore

* `E_CREDENZIALE_PERSONA_E_SISTEMA` — la veste ha una natura diversa da un'altra veste della stessa credenziale.
  La frase nomina lo username.

---

### Test

* `db/pgtap/anagrafiche/test-area-accessi-v1.sql` (casi 4-6 e 15) — il sistema esterno su una credenziale di persona
  e lo shop su un utente tecnico rifiutati, il sistema esterno su un utente tecnico ammesso; e il presidio, su una
  credenziale mista costruita spegnendo il guard.

---

### Note di migrazione

* 2026-10-02 — nasce con l'area «Accessi», insieme alla categoria di una credenziale e al presidio.

---

{% include-markdown "signature-core.md" %}
