## 📘 Documentazione Concettuale – Tabella `dbops.processi_identita`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo servito dall'utente tecnico
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — l'identità applicativa dell'utente tecnico, col flag `tecnica`
> * [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali) — l'emittente dell'utente, che qui non si ripete
>
> Approfondimento viste:
>
> * [dbops.vw_processi_dominio_senza_identita](/dbzero/dbops/views/vw_processi_dominio_senza_identita) — il presidio dei legami rimasti a metà
> * [dbops.vw_emittenti_non_serviti](/dbzero/dbops/views/vw_emittenti_non_serviti) — quale azienda è rimasta senza utente tecnico
> * [dbops.vw_processi_roster](/dbzero/dbops/views/vw_processi_roster) — con quale identità un processo lavora ciascuna azienda
>
> Approfondimento funzioni:
>
> * [script.fn_crea_utente_tecnico](/dbzero/script/funzioni/fn_crea_utente_tecnico) — la fabbrica degli utenti tecnici
> * [script.fn_riattiva_utente_tecnico](/dbzero/script/funzioni/fn_riattiva_utente_tecnico) — riaccende insieme tutti gli anelli di un utente tecnico
>
> Guide:
>
> * [I lavori automatici: che natura hanno e per conto di chi girano](/guide/processi-automatici-classe-e-identita) — per conto di chi gira un lavoro automatico

---

### 🎯 Scopo Principale

Il legame fra un processo automatico e l'utente tecnico con cui gira (`auth_user_id`, l'utente
Django). Un lavoro che emette fatture deve saper rispondere «per conto di chi stai scrivendo?»
esattamente come una persona che usa l'applicazione.

---

### ⭐ Un utente tecnico per emittente, non uno per processo

In questo modello un utente ha **un solo** emittente (`config.user_emittenti_fiscali` è uno a uno
sull'utente); multi-emittente è solo il super admin.

⇒ Un processo che serve tre aziende non ha un utente con tre permessi: ha **tre utenti tecnici**,
uno per azienda. La chiave unica è perciò su `auth_user_id` (un utente serve un processo solo), e
un processo può averne quanti ne servono.

⛔ L'emittente **non** si ripete qui: sta in `config.user_emittenti_fiscali`, e duplicarlo farebbe
una seconda sorgente di verità.

---

### Chi ha bisogno di una riga qui, e chi no

| Canale del processo di dominio | Serve un utente tecnico? |
| --- | --- |
| `PGAGENT`, `COMMAND`, `CODA_AUTOMATICA` | ⛔ sì: nessuna persona lo lancia, l'identità va data |
| `CODA` | no: porta l'identità dell'operatore che l'ha accodato |

⭐ Dare un utente tecnico a un lavoro accodato da una persona sarebbe un danno, non una svista:
cancellerebbe il nome di chi l'ha chiesto, e con esso la possibilità di sapere chi ha fatto cosa.

Il lavoro di coda gira poi **come operatore**: un `CODA_AUTOMATICA` lo esegue il drenatore con
l'identità tecnica che il roster gli assegna, un `CODA` con quella di chi l'ha accodato.

---

### Il legame si spegne, non si cancella

`attivo` spegne il legame. ⚠️ Spegnerlo lascia in giro l'utente col suo flag `tecnica` e il suo
perimetro: è un residuo, e il presidio
[vw_processi_dominio_senza_identita](/dbzero/dbops/views/vw_processi_dominio_senza_identita) lo
vede come identità tecnica che nessun processo rivendica. `note` dice a quale emittente serve
l'utente, quando non si legge dal nome.

---

### ⚠️ È dato di macchina, non catalogo

I processi sono catalogo, uguali su ogni installazione. Gli utenti tecnici **no**: dipendono da
quali aziende esistono su quella installazione, e le righe puntano a `django.auth_user` e ad
anagrafiche locali.

⇒ Il seed che li crea gira solo nel contesto dei dati di macchina, che la CI non esegue. Un
ambiente nuovo nasce senza utenti tecnici, e i presidi lo dicono subito invece di lasciarlo
scoprire alla prima fatturazione muta.

---

### Test

* `db/pgtap/anagrafiche/test-identita-tecnica.sql` — il flag `tecnica` e i due presidi su casi
  costruiti: processo senza utente, identità tecnica non rivendicata, emittente non servito.
* `db/pgtap/dbops/test-vw-processi-roster.sql` — spento il legame, la coppia processo-azienda
  sparisce dal roster.
* `db/pgtap/script/test-fn-riattiva-utente-tecnico.sql` — la riattivazione riaccende anche il
  legame.

---

### Note di migrazione

* 2026-09-04 — nasce col registro dei processi automatici (`brief-db-processi-automatici-identita-e-perimetro`).
  Lo stesso giorno la chiave unica passa da «un utente per processo» a «un processo per utente»:
  l'idea di partenza, una lista di emittenti per utente, contraddiceva il modello.

---

{% include-markdown "signature-core.md" %}
