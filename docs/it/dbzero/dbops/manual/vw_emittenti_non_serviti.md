## 📘 Documentazione Concettuale – Vista `dbops.vw_emittenti_non_serviti`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — i processi di dominio, con classe e canale
> * [dbops.processi_identita](/dbzero/dbops/tabelle/processi_identita) — l'utente tecnico di ogni processo
> * [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali) — l'emittente di quell'utente
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — le aziende da servire
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo che la iscrive
>
> Approfondimento funzioni:
>
> * [script.fn_crea_utente_tecnico](/dbzero/script/funzioni/fn_crea_utente_tecnico) — come si crea l'utente che manca
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come si legge un presidio che deve restare vuoto

---

### 🎯 Scopo Principale

Le coppie (processo di dominio, azienda emittente) per cui **non esiste un utente tecnico**.
Deve restare vuota: ogni riga è un'azienda che quel processo, di fatto, non lavorerà mai.

---

### ⭐⭐ Il guasto che copre non assomiglia a un errore

Manca l'utente tecnico per l'azienda X. Quando il lavoro notturno parte:

1. il lavoro **parte regolarmente**;
2. la row level security, non trovando un utente nel perimetro di X, mostra **zero righe**;
3. la corsa chiude con **«FATTO, 0 elaborate»**.

⛔ Nessun errore, nessun allarme, nessun log rosso. E l'azienda X **non viene mai fatturata**,
finché qualcuno non se ne accorge contando i soldi. «Non è successo niente» lo nota solo chi si
aspettava qualcosa: questa vista rende di nuovo visibile un silenzio.

---

### ⭐ La domanda: per la coppia (processo, azienda), esiste un utente?

Un utente tecnico ha **un solo** emittente. La domanda giusta non è quindi «a questo utente manca
l'azienda X?», che per costruzione avrebbe sempre una risposta per ogni azienda tranne una, ma
«fra gli utenti attivi di questo processo, ce n'è uno dell'azienda X?».

⇒ Un processo senza **nessun** utente compare una volta per ogni azienda attiva. Non è rumore, è
la risposta giusta: dice **quali** aziende sono scoperte, non solo che manca qualcosa.

---

### Chi entra e chi no

| Entra | Non entra |
| --- | --- |
| i processi di classe `DOMINIO` vivi: ritiro non raggiunto (`script.fn_e_obsoleto`) | i processi di manutenzione e di amministrazione, e quelli col ritiro raggiunto |
| i canali `PGAGENT` e `COMMAND`, e `CODA_AUTOMATICA`: i lavori di coda che nessuna persona accoda | il canale `CODA`: quei lavori girano con l'identità dell'operatore che li accoda |
| le aziende emittenti attive | le aziende disattivate: non vanno servite, e terrebbero la vista rossa per sempre |

⚠️ Un processo con una data di ritiro **nel futuro**, cioè un ritiro programmato, resta nella
vista fino a quel giorno: finché la data non arriva continua a girare, e un'azienda scoperta resta
scoperta.

⚠️ Conta solo l'identità attiva del processo (`processi_identita.attivo`), non lo stato
dell'utente nel backend: un utente tecnico disattivato dall'applicazione serve ancora l'azienda,
per questa vista.

---

### ⛔ La vista non concede niente

Elenca ciò che manca: non crea utenti e non assegna perimetri. Il perimetro di un processo
automatico lo decide una persona, creando l'utente tecnico con `script.fn_crea_utente_tecnico` per
l'azienda che ha scelto. Un sistema che si dà da solo i permessi che gli mancano non è un sistema
che si configura: è un sistema senza perimetro.

---

### Chi la può vedere

Gira coi privilegi del proprietario: il catalogo dei processi e le aziende non hanno un perimetro
per operatore. A catalogo è `ZERO`, `GIORNALIERA`, perimetro `LIBERO`.

---

### Test

* `db/pgtap/anagrafiche/test-identita-tecnica.sql`, test 8 — la vista nomina ogni emittente attivo
  rimasto scoperto.
* `db/pgtap/dbops/test-processi-coda-automatica.sql`, test 4 — un processo `CODA_AUTOMATICA`
  senza utente compare per ogni emittente attivo.

---

### Note di migrazione

* 2026-09-04 — la domanda cambia. La prima versione chiedeva quali aziende mancassero a un utente,
  sull'idea che un utente avesse una lista di aziende: non sarebbe mai arrivata a zero
  (`brief-db-processi-automatici-identita-e-perimetro` §4.5 e §8).
* 2026-09-05 — entrano i lavori `CODA_AUTOMATICA` (`brief-db-processi-automatici-residui-be`,
  sezione 1-quater).

---

{% include-markdown "signature-core.md" %}
