## 📘 Documentazione Concettuale – Tabella `dbops.credenziali_di_prova`

### 🎯 Scopo
(18-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, R-4, 2b-3)

**L'etichetta degli utenti di prova.** Ogni credenziale creata dal
provisioning dei dati di sviluppo (gli utenti `dev.*`) ha qui una riga, con la
sua chiave: lo username con cui è nata.

* La scrive **solo** il provisioning; l'applicazione la legge.
* **Non si toglie e non cambia**: togliendola, l'utente sparirebbe al
  controllo che cerca i dati di prova nei database di produzione.
* In un database di **produzione non nasce**.
* La chiave serve anche a riconoscere l'utente alla corsa successiva del
  provisioning, anche se nel frattempo è stato rinominato.

La lista degli operatori la usa per nascondere gli utenti di prova (un filtro
attivo di default) e per mostrarli col badge «di prova».

### Test

`db/pgtap/dbops/test-etichette-di-prova-v1.sql`.

---

{% include-markdown "signature-core.md" %}
