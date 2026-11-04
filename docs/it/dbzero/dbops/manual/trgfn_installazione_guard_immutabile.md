## 📘 Documentazione Concettuale – Trigger function `dbops.trgfn_installazione_guard_immutabile`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.installazione](/dbzero/dbops/tabelle/installazione) — la tabella che il guard protegge
>
> Approfondimento viste:
>
> * [dbops.vw_ambiente_non_dichiarato](/dbzero/dbops/views/vw_ambiente_non_dichiarato) — il presidio dell'ambiente che manca

---

### 🎯 Scopo Principale

Il guard dell'immutabilità dell'ambiente: rifiuta ogni modifica, cancellazione e svuotamento di
`dbops.installazione`. L'ambiente si scrive una volta, alla nascita, dalla fase `post` del
provisioning, e non cambia in nessuno dei due versi.

---

### ⛔ Non cambia, nemmeno allo stesso valore

Il guard non guarda che cosa si scrive: rifiuta l'operazione. Anche una modifica che riscrive lo
stesso ambiente è rifiutata, perché la riga non si riscrive.

Un database di sviluppo non si certifica pulito, e una copia della produzione resta produzione: le
ragioni stanno nella pagina di [dbops.installazione](/dbzero/dbops/tabelle/installazione).

---

### Due trigger, una funzione

| Trigger | Che cosa prende |
| --- | --- |
| di riga, prima di modifica e cancellazione | la riga che si toccherebbe |
| di istruzione, prima dello svuotamento | lo svuotamento, che i trigger di riga non vedono |

Nel trigger di istruzione la riga vecchia non c'è: l'ambiente che l'errore riporta si legge dalla
tabella. L'inserimento non passa da qui: una seconda riga la ferma la chiave sull'id unico.

⚠️ Il proprietario può disattivare il trigger: la difesa contro un amministratore del database
malintenzionato sono i ruoli, non un guard. È la stessa strada che i test usano, dentro una
transazione annullata, per costruire un'installazione di produzione o senza ambiente.

---

### Codici errore

* `E_AMBIENTE_IMMUTABILE` — su ogni modifica, cancellazione o svuotamento; porta l'ambiente scritto.

---

### Test

* `db/pgtap/dbops/test-installazione-ambiente-v1.sql` — i due trigger montati; modifica (anche allo
  stesso valore), cancellazione e svuotamento rifiutati.

---

### Note di migrazione

* 2026-10-16 — nasce con la tabella dell'ambiente (`brief-db-processi-accensione-per-ambiente`), da
  una decisione di Tid dello stesso giorno.

---

{% include-markdown "signature-core.md" %}
