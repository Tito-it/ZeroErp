## 📘 Documentazione Concettuale – Funzione `script.fn_totp_ricifra_segreto()`

> 👀 **Vedi anche**
>
> **La tabella:** [config.auth_totp_device](/dbzero/config/tabelle/auth_totp_device)

---

### 🎯 Scopo Principale
(scritta il 01-10-2026)

**Il segreto del telefono resta leggibile quando si cambiano le chiavi.** Il
segreto da cui il telefono calcola i codici lo cifra il backend, con le chiavi
dei dati cifrati. Quando quelle chiavi si cambiano, un comando del backend
riapre ogni segreto con la chiave vecchia e lo richiude con quella nuova. Questa
funzione è il modo in cui quel comando **riscrive** il segreto, perché
l'applicazione non può scrivere la tabella direttamente.

Senza, il giorno in cui la chiave vecchia viene tolta ogni persona col secondo
fattore dovrebbe riconfigurare il telefono.

---

### Regole

* **Sostituisce solo se il segreto è ancora quello letto.** Il comando dice
  quale segreto ha letto e quale vuole scrivere: se nel frattempo la persona ha
  riconfigurato o disattivato il dispositivo, la funzione non scrive niente e
  risponde «no». Non è un errore: il comando lo conta e lo dice.
* Vale per un dispositivo in **qualunque** stato, anche **da confermare**: anche
  quel segreto deve passare alla chiave nuova.
* **Non tocca altro**: lo stato, l'ultimo codice usato, i codici di recupero e
  la data dell'ultimo uso restano come sono.
* **Nessuno agisce**: la chiama un comando di manutenzione, senza un utente.
* Una chiamata senza credenziale, con un segreto vuoto, o con il segreto nuovo
  uguale al vecchio è un difetto di chi chiama (`E_AUTH_CHIAMATA_NON_VALIDA`).
  I segreti non finiscono mai nel registro degli errori, nemmeno cifrati.

---

### ⚠️ Il limite

La funzione lascia al backend sostituire un segreto **senza dire chi è**. Non
gli dà un potere nuovo: il segreto lo può aprire solo il backend, che ha le
chiavi, e un backend capace di abusarne decide già chi entra. È lo stesso limite
di tutti i verbi del database: il modello protegge da un backend che
**sbaglia**, non da uno **manomesso**.

Il confronto col segreto letto protegge dall'errore vero: sovrascrivere un
segreto che è cambiato fra la lettura e la scrittura.

---

### Storia

* 2026-10-01 — nasce (`20261001-35`). Brief: brief-db-totp-ricifra-segreto.

{% include-markdown "signature-core.md" %}
