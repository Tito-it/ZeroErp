## 📘 Documentazione Concettuale – Vista `dbops.vw_processi_dominio_senza_identita`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi_identita](/dbzero/dbops/tabelle/processi_identita) — il legame processo-utente tecnico
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — l'identità applicativa, col flag `tecnica`
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — classe e canale del processo
>
> Approfondimento viste:
>
> * [dbops.vw_emittenti_non_serviti](/dbzero/dbops/views/vw_emittenti_non_serviti) — quale azienda è rimasta senza utente tecnico
>
> Approfondimento funzioni:
>
> * [script.fn_crea_utente_tecnico](/dbzero/script/funzioni/fn_crea_utente_tecnico) — la fabbrica che svuota il presidio
>
> Guide:
>
> * [I lavori automatici: che natura hanno e per conto di chi girano](/guide/processi-automatici-classe-e-identita) — per conto di chi lavora un processo

---

### 🎯 Scopo Principale

Presidio: i processi di dominio che non possono dire **chi** agisce, guardati nei tre versi del
legame fra processi e utenti tecnici. Deve restare vuota.

---

### ⭐ Tre versi, e il terzo protegge dal residuo

| `motivo` | Che cosa è successo |
| --- | --- |
| processo DOMINIO headless senza utente tecnico | il processo esiste, nessun legame attivo: girerebbe senza identità |
| utente tecnico senza identità OPERATORE con flag tecnica | il legame c'è, ma l'utente non ha (più) un'identità attiva, tecnica, con ruolo `OPERATORE` |
| identità con flag tecnica non rivendicata da nessun processo | un'identità attiva marcata tecnica che nessun legame attivo rivendica |

⛔ **Il terzo verso è il motivo per cui la vista non guarda solo in avanti.** Il caso che resta
possibile è un processo ritirato male: il legame spento, l'utente lasciato in giro col suo flag e il
suo perimetro. L'altro abuso temuto, marcare tecnica l'identità di una persona per farla sparire dai
conteggi delle persone, lo rifiuta già a monte il guard di coerenza delle identità; il presidio
resta comunque.

Le righe del terzo verso non hanno processo né canale: sono identità senza padrone.

---

### ⭐ Quali processi vogliono un'identità

Il primo verso guarda i processi `DOMINIO` vivi (ritiro non raggiunto, `script.fn_e_obsoleto`: un
ritiro programmato conta fino al suo giorno), sui canali `PGAGENT`, `COMMAND` e
`CODA_AUTOMATICA`: quelli che nessuna persona lancia.

⚠️ `CODA_AUTOMATICA` c'è perché un lavoro di coda accodato da una **macchina** non ha un'identità
prestata da nessuno: ne vuole una propria. I processi `CODA` restano esclusi, ed è voluto: lì
l'identità la porta l'operatore che accoda, e dargliene una tecnica cancellerebbe il suo nome.

---

### Come si svuota

Con [fn_crea_utente_tecnico](/dbzero/script/funzioni/fn_crea_utente_tecnico), una chiamata per
ogni coppia processo-emittente: un utente ha un solo emittente, e un processo che serve tre aziende
vuole tre utenti. Un utente tecnico spento si riaccende con `script.fn_riattiva_utente_tecnico`.

---

### Chi la guarda

Nel catalogo dei presidi è un presidio che deve restare vuoto, guardato ogni giorno, che tocca allo
sviluppo. Non ha una colonna di stato, a differenza delle due sorelle sui bersagli: qui non c'è un
debito dichiarabile, e si conta la vista intera. La vista gira coi privilegi del proprietario.

---

### Test

* `db/pgtap/anagrafiche/test-identita-tecnica.sql` — un processo `DOMINIO` senza utente tecnico
  compare, un processo `CODA` no, un'identità tecnica non rivendicata compare.
* `db/pgtap/dbops/test-processi-coda-automatica.sql` — un processo `CODA_AUTOMATICA` senza utente
  tecnico compare.
* `db/pgtap/dbops/test-processo-vivo-v1.sql` — un processo a ritiro programmato compare, uno a
  ritiro raggiunto no.
* ⚠️ Il secondo verso (un legame verso un utente senza identità tecnica `OPERATORE`) non ha un caso
  costruito.

---

### Note di migrazione

* 2026-09-04 — nasce col registro dei processi automatici (`brief-db-processi-automatici-identita-e-perimetro`),
  sui canali `PGAGENT` e `COMMAND`.
* 2026-09-05 — il primo verso include `CODA_AUTOMATICA` (`brief-db-processi-automatici-residui-be`,
  §1-quater): prima la chiusura per scadenze, che usa un'identità tecnica, sarebbe risultata «non
  ne vuole».

---

{% include-markdown "signature-core.md" %}
