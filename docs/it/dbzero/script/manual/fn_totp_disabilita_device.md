## 📘 Documentazione Concettuale – Funzione `script.fn_totp_disabilita_device()`

> 👀 **Vedi anche**
>
> **La tabella:** [config.auth_totp_device](/dbzero/config/tabelle/auth_totp_device)
>
> **Chi amministra il database:** [fn_sessione_del_migratore](/dbzero/dbops/funzioni/fn_sessione_del_migratore)
>
> **Il SUPER_ADMIN:** [fn_guard_super_admin](/dbzero/script/funzioni/fn_guard_super_admin)

---

### 🎯 Scopo Principale
(scritta il 29-09-2026)

**Disattiva il secondo fattore** di una persona cancellando il dispositivo:
segreto e codici di recupero spariscono. Se la persona ha l'obbligo, al prossimo
accesso viene riportata alla configurazione.

---

### Regole

* Può farlo la **persona stessa**, senza motivo.
* Può farlo un **SUPER_ADMIN**, con un **motivo** (`E_TOTP_MOTIVO_OBBLIGATORIO`).
* ⭐ **Il caso senza via d'uscita**: se l'unico amministratore perde telefono e codici, nessuno potrebbe aiutarlo. Allora può farlo **chi amministra il database**, collegato al server, sempre con un motivo (decisione di Tid del 29-09-2026). L'applicazione non arriva a questa strada.
* **La traccia** (chi, quando, perché): dall'applicazione la registra il backend nell'audit degli accessi (`dbops.sessioni_utente`); **dal server** la scrive la funzione stessa, nella stessa tabella, come evento `TOTP_DISABILITATO` con il motivo e il ruolo che si è collegato (decisione di Tid del 29-09-2026). Se la traccia non si scrive, la disattivazione non avviene.
* Senza dispositivo: `E_TOTP_DEVICE_ASSENTE`.

---

### Storia

* 2026-09-29 — nasce (`20260929-22`); la sera stessa scrive la traccia dello sblocco dal server (`-26`, D-T5). Brief: brief-db-secondo-fattore-totp.

{% include-markdown "signature-core.md" %}
