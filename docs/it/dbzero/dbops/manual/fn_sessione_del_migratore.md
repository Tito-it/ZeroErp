## 📘 Documentazione Concettuale – Funzione `dbops.fn_sessione_del_migratore()`

> 👀 **Vedi anche**
>
> **Chi la usa:** [fn_sync_functions_owner](/dbzero/dbops/funzioni/fn_sync_functions_owner) · [fn_totp_disabilita_device](/dbzero/script/funzioni/fn_totp_disabilita_device)

---

### 🎯 Scopo Principale
(scritta il 29-09-2026)

Dice se la connessione è di **chi amministra il database** — il ruolo che
esegue le migrazioni, in qualunque ambiente, o un superuser — e non
dell'applicazione. Serve alle operazioni che solo lui può fare: allineare i
proprietari delle funzioni sensibili, e sbloccare il secondo fattore
dell'ultimo amministratore rimasto senza telefono.

---

### Regole

* Guarda il ruolo con cui la connessione è **entrata**: dentro una funzione che gira con i diritti del proprietario, il ruolo «corrente» sarebbe sempre il proprietario.
* ⚠️ Limite dichiarato: una connessione aperta dal migratore che cambia ruolo con `SET ROLE` resta del migratore. PostgreSQL non offre di meglio.
* Risponde sì o no, non solleva: rifiuta chi la chiama.

---

### Storia

* 2026-09-29 — estratta dal corpo di `fn_sync_functions_owner` (`20260929-08`, `-09`), alla seconda occorrenza. Brief: brief-db-secondo-fattore-totp.

{% include-markdown "signature-core.md" %}
