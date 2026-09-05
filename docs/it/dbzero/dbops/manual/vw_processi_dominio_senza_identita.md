## 📘 Documentazione Concettuale – View `dbops.vw_processi_dominio_senza_identita`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[dbops.processi_identita](/dbzero/dbops/manual/processi_identita)
>
[anagrafiche.identita_digitali](/dbzero/anagrafiche/manual/identita_digitali)
>
Approfondimenti funzioni:
>
[script.fn_crea_utente_tecnico](/dbzero/script/manual/fn_crea_utente_tecnico)

---
### 🎯 Scopo Principale
(latest review 04-09-2026)

Elenca tutto ciò che, nel legame fra **processi** e **utenti tecnici**, è
rimasto a metà.

> ⚠️ **Deve restare vuota.**

---

### ⭐ Guarda in TRE versi, e il terzo è quello che protegge dal caso peggiore

| motivo | Che cosa è successo |
| --- | --- |
| processo DOMINIO headless senza utente tecnico | il processo esiste, l'utente no: girerebbe senza identità |
| utente tecnico senza identità OPERATORE col flag | il legame c'è, ma l'utente non è (più) un'identità tecnica valida |
| **identità col flag tecnica non rivendicata** | esiste un utente marcato «processo» che **nessun processo rivendica** |

⛔ **Il terzo verso è il motivo per cui la vista non guarda solo in avanti.**
Senza di esso, il flag `tecnica` diventerebbe un modo per far **sparire una
persona dai conteggi**: si marca l'identità di un operatore come tecnica, e
quell'utente esce da tutti i controlli che riguardano le persone.

⚠️ Oggi quel gesto è impedito anche a monte — il guard di coerenza rifiuta di
marcare tecnica l'identità di una persona, perché un'identità tecnica pretende
un soggetto-ruolo di tipo processo. ⭐ Ma il presidio resta, e serve per il caso
che **è** ancora possibile: un processo ritirato male, con l'utente lasciato in
giro col suo flag e il suo perimetro.

---

### ⭐ I processi di CODA sono esclusi, ed è una correzione, non una dimenticanza

Un lavoro accodato porta con sé **l'identità dell'operatore che l'ha chiesto**.
Non gli serve un utente tecnico, e dargliene uno cancellerebbe il nome di quella
persona.

⇒ La vista guarda solo i canali `PGAGENT` e `COMMAND`, cioè i processi che
partono senza nessuno dietro.

---

### Come si svuota

Con [fn_crea_utente_tecnico](/dbzero/script/manual/fn_crea_utente_tecnico),
**una chiamata per ogni coppia processo × emittente**. ⚠️ Un utente ha un solo
emittente: un processo che serve tre aziende vuole tre utenti.

---

### Esempio d'uso

```sql
SELECT processo_codice, canale, auth_user_id, motivo
FROM dbops.vw_processi_dominio_senza_identita
ORDER BY motivo, processo_codice;
```

Origine: `docs/it/dev/work-done/brief-db-processi-automatici-identita-e-perimetro.md` §4 e §8.

---

{% include-markdown "signature-core.md" %}
