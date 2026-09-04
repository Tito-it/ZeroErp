## 📘 Documentazione Concettuale – Tabella `dbops.processi_identita`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [dbops.processi](/dbzero/dbops/manual/processi)
> • [anagrafiche.identita_digitali](/dbzero/anagrafiche/manual/identita_digitali)
>
**Approfondimento funzioni:**
>
• [script.fn_crea_utente_tecnico](/dbzero/script/manual/fn_crea_utente_tecnico)
>

### 🎯 Scopo Principale
(latest review 04-09-2026)

Dice **con quale utente gira** un processo automatico di dominio.

Un lavoro che emette fatture deve poter rispondere a *«per conto di chi stai
scrivendo?»* esattamente come risponde una persona che usa l'applicazione. Fino
a questo cantiere non rispondeva: girava senza nessuno, e il database lo
lasciava passare.

---

### ⭐ UNA riga per utente, non per processo — ed è il modello, non un limite

È la cosa che sorprende leggendo la tabella, e va spiegata subito.

> **In questo sistema un utente ha UN SOLO emittente.**
> `config.user_emittenti_fiscali` è uno-a-uno; multi-emittente è **solo** il
> super admin.

⇒ Un processo che serve tre aziende non ha *un* utente tecnico con tre
permessi: ha **tre utenti tecnici**, uno per azienda. Il vincolo UNIQUE è
perciò su `auth_user_id` — un utente appartiene a un processo solo — e non su
`processo_id`.

⚠️ **Questa non era l'idea di partenza**, ed è stata corretta applicando: la
parola «whitelist» faceva pensare a una lista di emittenti per utente. Il
modello dice il contrario, e la tabella lo rispecchia.

---

### Chi ha bisogno di una riga qui, e chi no

| Canale del processo | Serve un utente tecnico? |
| --- | --- |
| `PGAGENT`, `COMMAND` | ⛔ **sì** — non c'è nessuno che lo lancia, l'identità va data |
| `CODA` | ✅ **no** — porta l'identità dell'operatore che l'ha accodato |

⭐ Dare un utente tecnico a un lavoro di coda sarebbe un danno, non una svista:
**cancellerebbe il nome della persona** che ha chiesto quel lavoro, e con esso
la possibilità di sapere chi ha fatto cosa.

---

### Campi chiave

* `processo_id`: hard FK verso [processi](/dbzero/dbops/manual/processi).
* `auth_user_id`: l'utente tecnico. **UNIQUE**: un utente serve un processo
  solo.
* `attivo`: spegnere il legame lascia in giro l'utente col suo flag e col suo
  perimetro. ⚠️ È un residuo, e il presidio lo vede — vedi sotto.
* `note`: a quale emittente serve quell'utente, quando non si legge dal nome.

---

### ⚠️ Questa tabella è DATO DI MACCHINA, non catalogo

I processi sono catalogo — uguali in ogni installazione. Gli utenti tecnici
**no**: dipendono da quali aziende esistono su *quella* installazione, e le
righe puntano a `django.auth_user` e ad anagrafiche locali.

⇒ Il seed che le crea gira nel contesto `dati_macchina`, che la CI **non**
esegue. Un ambiente nuovo nasce senza utenti tecnici, e i presidi lo dicono
subito invece di lasciarlo scoprire alla prima fatturazione muta.

---

### I due presidi che la guardano

* [vw_processi_dominio_senza_identita](/dbzero/dbops/manual/vw_processi_dominio_senza_identita)
  — guarda nei **due versi**: processi senza utente, e utenti col flag tecnico
  che **nessun processo rivendica più** (il residuo di un processo ritirato
  male).
* [vw_emittenti_non_serviti](/dbzero/dbops/manual/vw_emittenti_non_serviti)
  — dice **quale azienda** è rimasta scoperta.

Origine: `docs/it/dev/work-in-progress/brief-db-processi-automatici-identita-e-perimetro.md` §2.4 e §4.

---

{% include-markdown "signature-core.md" %}
