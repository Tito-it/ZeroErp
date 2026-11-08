## 📘 Documentazione Concettuale – Vista `dbops.vw_processi_che_bypassano`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il registro dei processi automatici, di cui questa vista guarda i ruoli
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo in cui la vista è un presidio
>
> Approfondimento viste:
>
> * [dbops.vw_processi_dominio_senza_difesa](/dbzero/dbops/views/vw_processi_dominio_senza_difesa) — l'altro lato: le tabelle senza policy o guard
>
> Guide:
>
> * [I lavori automatici: che natura hanno e per conto di chi girano](/guide/processi-automatici-classe-e-identita) — perché un processo non deve saltare la row level security
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come si legge un presidio e il suo registro del debito

---

### 🎯 Scopo Principale

Presidio: i ruoli applicativi che saltano la row level security, cioè i ruoli che possono
collegarsi, non sono superuser e hanno `BYPASSRLS`. La vista ha una sola colonna, `ruolo`, e
**deve restare vuota**: ogni riga è un allarme.

---

### ⚠️ Non dice «nessuno salta la row level security»

Lo scheduler bypassa perché è superuser, il proprietario delle tabelle per proprietà, e devono
farlo: eseguono DDL. La vista li esclude per costruzione e guarda solo ciò che resta: un ruolo che
si collega come un'applicazione e vede tutto senza che nessuna policy lo filtri.

⇒ Un ruolo così è una porta che scavalca la separazione dei dati fra aziende emittenti. Toglierla è
un lavoro che vive fuori dal database (il ruolo va ritirato dal provisioning, il backend deve
smettere di collegarsi con quello): finché non è fatto, la vista la tiene **contata**, invece di
lasciarla alla memoria.

---

### ⭐ Perché deve restare vuota

Oggi nessun ruolo applicativo ha bisogno di `BYPASSRLS`: i lavori automatici girano come
l'applicazione, con l'utente tecnico dell'azienda che servono, e la row level security li filtra.
Non c'è quindi nessuna riga da tollerare, e il presidio nel catalogo
[dbops.presidi](/dbzero/dbops/tabelle/presidi) conta **tutte** le righe, con soglia zero e nessun
filtro di stato.

⛔ **Niente eccezioni scritte per nome.** Un nome di ruolo scritto nella definizione della vista
diventa un'eccezione che sopravvive al ruolo: se un giorno tornasse un ruolo con quel nome, passerebbe
muto. È successo davvero (vedi le note di migrazione), ed è il motivo per cui la vista non ha più né
una colonna di stato né una nota.

**Se servisse un debito nuovo** — un ruolo con `BYPASSRLS` che si decide consapevolmente di tenere
per un periodo — non si aggiunge un nome a un elenco: si scrive un changeSet che cambia **insieme**
la vista e la sua riga nel catalogo dei presidi, dichiarando che cosa si tollera, perché e quando si
chiude. Chiuso il debito, un changeSet nuovo riporta la vista e il presidio a questa forma.

---

### ⚠️ Perché si legge il catalogo dei ruoli

`information_schema.role_table_grants` mostra solo i privilegi che la sessione corrente può vedere:
una vista costruita lì sarebbe vuota per ragioni che non hanno niente a che fare con la sicurezza.
La vista legge il catalogo dei ruoli (`pg_roles`), che è il dato vero.

---

### Chi la guarda

Nel catalogo dei presidi è un presidio a soglia zero, guardato ogni settimana; chi agisce è chi
gestisce il server. La vista è `security_invoker`: legge solo `pg_roles`, che vedono tutti, e
risponde uguale a chiunque la interroghi.

---

### Test

* `db/pgtap/dbops/test-processi-registro.sql`:
  * test 13 — la vista è vuota: nessun ruolo applicativo bypassa la row level security;
  * test 13-bis — la definizione della vista non contiene letterali (nessun nome di ruolo scritto
    lì) e la riga del presidio non ha filtro di stato. È un controllo sul testo, dichiarato tale: un
    ruolo con `BYPASSRLS` non si può creare in un test, serve un superuser, e senza il 13-bis il 13
    sarebbe verde anche con la vista di prima.

---

### Note di migrazione

* 2026-09-04 — nasce col registro dei processi automatici (`brief-db-processi-automatici-identita-e-perimetro`):
  l'unico ruolo applicativo con `BYPASSRLS` era quello della fatturazione batch, dichiarato come
  debito per nome nella vista; il presidio contava solo le righe non dichiarate.
* 2026-10-15 — il ruolo della fatturazione batch è ritirato; il suo nome resta nell'elenco della
  vista.
* 2026-11-04 — D43 di `brief-db-revisione-dbops`: tolti il debito dichiarato per nome
  (`zeroerp_batch_fatturazione`) e le colonne `stato` e `nota`; resta `ruolo`. La vista deve restare
  vuota e il presidio conta tutte le righe: prima un ruolo tornato con quel nome sarebbe passato
  muto. La vista diventa `security_invoker`.

---

{% include-markdown "signature-core.md" %}
