## 📘 Documentazione Concettuale – Funzione `script.fn_get_totp_device()`

> 👀 **Vedi anche**
>
> **La tabella:** [config.auth_totp_device](/dbzero/config/tabelle/auth_totp_device)

---

### 🎯 Scopo Principale
(scritta il 29-09-2026)

Lo stato del dispositivo di una persona, **sempre in una riga**, anche quando il
dispositivo non c'è:

| Stato | Significa |
| --- | --- |
| `ASSENTE` | mai configurato, o disattivato |
| `DA_CONFERMARE` | configurazione iniziata, primo codice non ancora inserito |
| `ATTIVO` | in uso |

Porta anche il segreto cifrato (lo decifra il backend per verificare i codici),
l'ultimo intervallo usato e quanti codici di recupero restano.

---

### Regole

* È la sola sede del significato della riga assente.
* Si può chiamare anche prima del login.

---

### Storia

* 2026-09-29 — nasce (`20260929-15`). Brief: brief-db-secondo-fattore-totp.

{% include-markdown "signature-core.md" %}
