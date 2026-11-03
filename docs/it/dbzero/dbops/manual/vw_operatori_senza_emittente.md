## 📘 Documentazione Concettuale – Vista `dbops.vw_operatori_senza_emittente`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — l'identità dell'operatore e il suo ruolo applicativo
> * [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali) — l'emittente assegnato all'utente
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo che la iscrive
>
> Approfondimento funzioni:
>
> * [script.fn_change_user_emittenti_scope](/dbzero/script/funzioni/fn_change_user_emittenti_scope) — la sede unica che assegna l'emittente
> * [script.fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin) — chi è escluso, e perché
>
> Guide:
>
> * [Architettura di permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — il perimetro dell'emittente
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come si legge un presidio che deve restare vuoto

---

### 🎯 Scopo Principale

Gli operatori **configurati a metà**: hanno un'identità attiva con ruolo `OPERATORE`, non sono
super admin, e non hanno l'emittente fiscale assegnato. Deve restare vuota: una riga è una
persona che apre l'applicazione e non trova niente.

---

### Perché esiste: un perimetro vuoto non si annuncia

L'assegnazione dell'emittente è obbligatoria, e chi non ce l'ha **non vede nulla**. È il
comportamento corretto: senza, vedrebbe gli emittenti di chiunque, indistinguibile da un
amministratore. Ma ha una proprietà sgradevole: **non si annuncia**.

Non c'è un errore, non c'è un messaggio: c'è una schermata vuota. A differenza di un controllo
che blocca e spiega, questo difetto è silenzioso per costruzione: lo scopre l'interessato, e lo
segnala come un guasto. Questa vista lo trasforma in una cosa che **si guarda** invece che in una
cosa che si subisce.

---

### Chi è escluso, e perché

Il **super admin** è legittimamente senza assegnazione: il suo perimetro passa da
`script.fn_is_super_admin`, non dall'emittente. Comparirebbe come falso allarme, e un cruscotto
con dentro un falso allarme fisso è un cruscotto che si smette di guardare.

Le identità spente non entrano: chi non può entrare non può nemmeno trovare la schermata vuota.

---

### Come si sistema una riga

Con `script.fn_change_user_emittenti_scope`, la funzione di dominio che assegna l'emittente a un
utente, **non** con una scrittura diretta: è lì che stanno i controlli del modello «un operatore,
un emittente».

---

### Chi la può vedere

Gira coi privilegi del proprietario. A catalogo è `ZERO`, `GIORNALIERA`, perimetro `LIBERO`, e
chi deve agire è l'amministratore.

---

### Test

Nessun pgTAP la interroga; la sua riga a catalogo la controlla
`db/pgtap/dbops/test-catalogo-presidi-v1.sql`.

---

### Note di migrazione

* 2026-08-18 — nasce col fail-closed del perimetro dell'emittente, come diagnostica P-2a
  (`brief perimetro-emittente`).

---

{% include-markdown "signature-core.md" %}
