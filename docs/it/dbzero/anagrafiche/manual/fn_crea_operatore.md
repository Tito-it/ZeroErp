## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_operatore`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — la veste OPERATORE che nasce spenta
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane) — il rapporto di lavoro dell'operatore
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_auth_user](/dbzero/anagrafiche/funzioni/fn_crea_auth_user) — crea la credenziale quando l'email non ne ha una
> * [anagrafiche.fn_crea_soggetto_pf](/dbzero/anagrafiche/funzioni/fn_crea_soggetto_pf) — crea la persona fisica nel flusso A
> * [anagrafiche.fn_crea_risorsa_umana](/dbzero/anagrafiche/funzioni/fn_crea_risorsa_umana) — il rapporto, la veste e il legame SUPER_ADMIN
> * [anagrafiche.fn_crea_indirizzi_operatore](/dbzero/anagrafiche/funzioni/fn_crea_indirizzi_operatore) — residenza e domicilio fiscale, e il domicilio che manca
> * [anagrafiche.fn_crea_primo_amministratore](/dbzero/anagrafiche/funzioni/fn_crea_primo_amministratore) — il primo SUPER_ADMIN, che la compone
> * [script.fn_get_auth_user_id_for_email](/dbzero/script/funzioni/fn_get_auth_user_id_for_email) — quale credenziale ha questa email
> * [script.fn_get_credenziale_per_email](/dbzero/script/funzioni/fn_get_credenziale_per_email) — username e vesti della credenziale, per il dialog di conferma
> * [script.fn_check_operatore_invitabile](/dbzero/script/funzioni/fn_check_operatore_invitabile) — quando l'operatore appena creato si può invitare
> * [anagrafiche.trgfn_identita_digitali_sync_auth_user_active](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_sync_auth_user_active) — la credenziale segue le vesti
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — la persona, il rapporto, la veste e la credenziale
> * [Automazione DB](/guide/automazione-db) — perché il profilo nasce attivo su una veste spenta

---

### 🎯 Scopo Principale

`anagrafiche.fn_crea_operatore` crea un operatore: trova o crea la credenziale dell'email, trova o crea la
persona fisica, le dà il rapporto di lavoro e la veste OPERATORE spenta, con l'eventuale profilo SUPER_ADMIN e gli
indirizzi di residenza e domicilio fiscale. Restituisce la credenziale, il suo username effettivo e se è stata
riusata.

È la madre della creazione di un operatore umano: la chiama il backend dall'amministrazione degli utenti, e dentro
il database il verbo del primo amministratore (`anagrafiche.fn_crea_primo_amministratore`), il provisioning dei dati
di sviluppo e la fixture pgTAP `dbops.fn_pgtap_crea_operatore_umano`.

Il nome storico `anagrafiche.fn_crea_operatore_v2` è un involucro di questa funzione, con la stessa firma: lo
chiamano ancora il backend, il verbo del primo amministratore e la fixture, finché non passano al nome nuovo.

---

### Una persona, una credenziale

Se l'email ha già una credenziale (la persona è già cliente del portale o dello shop), la funzione la **riusa** e
non ne tocca password, username e nome. La cerca `script.fn_get_auth_user_id_for_email`, senza distinguere
maiuscole e minuscole; se ne trova più di una si ferma con `E_CREDENZIALE_EMAIL_AMBIGUA`. Solo se non c'è la crea
`anagrafiche.fn_crea_auth_user`, ed è allora che servono e si validano username e password.

Sulla credenziale trovata la funzione prende un lucchetto: due creazioni sulla stessa persona si mettono in fila,
e la seconda rilegge le vesti dopo che la prima ha finito.

Il ritorno dice lo username **effettivo**: su una credenziale riusata è il suo, non quello passato, e la password
passata è ignorata. Chi chiama deve dirlo a chi ha compilato il modulo.

---

### ⛔ Una credenziale che ha già una veste OPERATORE si rifiuta

Accesa o spenta, una veste OPERATORE sulla credenziale ferma la creazione con `E_CREDENZIALE_GIA_OPERATORE`: una
veste spenta è un invito pendente o un operatore disattivato, e il rimedio è il reinvito, non un secondo operatore
sulla stessa persona.

---

### ⭐ Il riuso non è mai silenzioso

Un'email sbagliata non deve poter collegare la veste all'accesso di un'altra persona.

* **Dove il modello sa dire chi è la persona** — la credenziale ha una veste su un soggetto persona fisica — quel
  soggetto dev'essere l'operatore: nel flusso B lo stesso soggetto, nel flusso A lo stesso codice fiscale.
  Altrimenti `E_CREDENZIALE_ALTRA_PERSONA`. Con lo stesso codice fiscale nel flusso A parla `fn_crea_soggetto_pf`
  (`E_ADMIN_CF_DUPLICATO`): la persona esiste già, e si sceglie il soggetto esistente.
* **Negli altri casi** (vesti su un'azienda, o nessuna veste) decide l'amministratore, con una dichiarazione:
  `p_riusa_auth_user_id` dev'essere la credenziale trovata, oppure vuoto se l'email è nuova. Una dichiarazione
  assente o diversa ferma con `E_CREDENZIALE_DA_CONFERMARE`: un id e non un sì, perché dice *a che cosa* si è detto
  sì, e una credenziale cambiata fra il dialog e l'invio ferma di nuovo.

Il dialog di conferma del backend legge username e vesti da `script.fn_get_credenziale_per_email`, e il rifiuto li
prende dalla stessa funzione: dialog e rifiuto non possono divergere. Nel contesto dell'errore restano per il log;
al client non arrivano.

Il controllo del consenso sta **dopo** il soggetto: i rifiuti definitivi (dati della persona incompleti, codice
fiscale già presente, soggetto che non è una persona fisica) parlano prima, e l'amministratore non conferma una
creazione che sarebbe rifiutata comunque.

---

### Il soggetto: nuovo (flusso A) o esistente (flusso B)

* **Flusso A**, senza `p_soggetto_id`: cognome, nome e codice fiscale sono obbligatori, e la persona nasce come
  privato (dettaglio `PR`, una persona fisica senza partita IVA) da `fn_crea_soggetto_pf`, con l'email come
  contatto. Per un privato il sesso è obbligatorio: senza, lo rifiuta il guard dei soggetti
  (`E_SESSO_OBBLIGATORIO`). La funzione non ha un sesso di default.
* **Flusso B**, con `p_soggetto_id`: il soggetto deve esistere ed essere una persona fisica. Cognome, nome, codice
  fiscale, sesso, data e comune di nascita non si leggono.

In tutti e due i flussi un soggetto che ha già una risorsa umana si ferma con `E_RISORSA_UMANA_GIA_PRESENTE`, dal
building block del rapporto.

---

### ⭐ La veste OPERATORE nasce spenta, sempre

Il rapporto nasce acceso; la veste nasce spenta e la accende l'attivazione dell'invito, la stessa regola per ogni
veste. Finché non è accesa, una credenziale nuova resta spenta: i trigger della veste accendono la credenziale solo
se almeno una sua veste è utilizzabile. Una credenziale riusata che ha un'altra veste utilizzabile (lo shop, il
portale) resta accesa. L'operatore appena creato è **invitabile**.

Le date `p_valido_dal` e `p_valido_al` valgono per il rapporto e per la veste; l'inizio, se non si passa, è il giorno
operativo.

Il legame al profilo SUPER_ADMIN, se chiesto, nasce invece attivo: la porta e i profili sono due domande diverse, e
i lettori dei permessi le chiedono entrambe.

---

### Gli indirizzi seguono la residenza

Se si passa l'indirizzo di residenza, la funzione scrive sul soggetto la residenza e il domicilio fiscale; il
domicilio, se non si passa, è la residenza. Senza residenza non scrive nessun indirizzo, e la completezza del
soggetto la verificano i suoi guard alla chiusura della transazione.

La regola dei due indirizzi sta in `anagrafiche.fn_crea_indirizzi_operatore`, che la usa anche il verbo del primo
amministratore: qui gli indirizzi sono dettagli già risolti.

---

### Tutto o niente

La funzione è una sola istruzione: se un passo fallisce non resta niente, neppure sulla credenziale riusata. Il
ritorno è una tabella di una riga, e si legge con una selezione dalla funzione: chiamata come valore singolo
consegnerebbe la riga intera in un campo solo.

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_ADMIN_VALIDAZIONE` | email o qualifica mancanti; nel flusso A cognome, nome o codice fiscale mancanti; nel flusso B soggetto inesistente o non persona fisica |
| `E_CREDENZIALE_EMAIL_AMBIGUA` | più credenziali con la stessa email a meno delle maiuscole (da `script.fn_get_auth_user_id_for_email`) |
| `E_CREDENZIALE_GIA_OPERATORE` | la credenziale dell'email ha già una veste OPERATORE, accesa o spenta |
| `E_CREDENZIALE_ALTRA_PERSONA` | la credenziale ha una veste su una persona fisica che non è l'operatore |
| `E_CREDENZIALE_DA_CONFERMARE` | la credenziale esiste e `p_riusa_auth_user_id` non la dichiara, o dichiara una credenziale che non c'è |
| `E_CODICE` | il dettaglio `PR` non è in `config.tipi_soggetto_dettaglio` |

Più quelli propagati da `fn_crea_auth_user` (username o email già presi, dati della credenziale mancanti),
`fn_crea_soggetto_pf` (fra gli altri `E_ADMIN_CF_DUPLICATO`), dal guard del sesso, da
`fn_crea_risorsa_umana` (`E_RISORSA_UMANA_GIA_PRESENTE`, `E_ADMIN_UO_NON_TROVATA`, `E_CONFIG_MANCANTE`) e da
`fn_crea_indirizzo_soggetto`.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-operatore.sql` — la creazione riuscita, la catena fino alla veste OPERATORE
  spenta, il soggetto privato, il contatto con l'email; username duplicato, email già di un operatore anche in
  maiuscolo, codice fiscale duplicato, unità organizzativa inesistente, cognome vuoto. Lavora coi vincoli
  differiti.
* `db/pgtap/anagrafiche/test-crea-operatore-riusa-credenziale-v1.sql` — il riuso (stessa credenziale, username
  suo, password e nome intatti, veste spenta, operatore invitabile), il rifiuto «già operatore» con la veste spenta e
  accesa, la credenziale nuova spenta, l'atomicità di un riuso che fallisce a metà, il consenso mancante o sbagliato,
  l'altra persona nei due flussi, la stessa persona.
* `db/pgtap/anagrafiche/test-fn-crea-risorsa-umana-gia-presente-v1.sql` — il secondo operatore sullo stesso
  soggetto.
* `db/pgtap/script/test-fn-get-credenziale-per-email-v1.sql` — la lettura che il rifiuto condivide col dialog.
* `db/pgtap/anagrafiche/test-soggetti-sesso-policy-v1.sql` — il sesso obbligatorio del privato.
* `db/pgtap/anagrafiche/test-crea-primo-amministratore-v1.sql` — il ripiego del domicilio sulla residenza, dal
  building block che questa funzione condivide col verbo del primo amministratore.
* Nessun test prova le date passate al rapporto e alla veste.

---

### Note di migrazione

* 2026-04-29 — nasce col suffisso `_v2`, col SUPER_ADMIN chiesto come sì o no; la funzione di prima, che chiedeva
  il ruolo con l'enum `config.ruolo_sistema`, è ritirata.
* 2026-11-26 — torna al nome senza suffisso; `fn_crea_operatore_v2` resta come involucro finché i chiamanti non
  passano al nome nuovo.
* 2026-09-25 — una persona, una credenziale: il riuso, la veste che nasce spenta (il parametro dello stato è uscito
  dalla firma), il ritorno a tabella; poi il riuso non silenzioso (l'altra persona, il consenso dichiarato).
* 2026-09-27 — nel rifiuto del consenso username e vesti vengono dalla stessa funzione del dialog.
* 2026-10-02 — un operatore disattivato è una veste OPERATORE spenta: `DISABILITATO` non è più un tipo di veste.
* 2026-10-09 — il sesso senza default (era maschile) e il soggetto del flusso A chiesto come privato.
* 2026-10-18 — gli indirizzi passano a `fn_crea_indirizzo_soggetto` nel contratto nuovo della madre.
* 2026-11-25 — la regola dei due indirizzi passa a `fn_crea_indirizzi_operatore`, condivisa col verbo del primo
  amministratore; comportamento invariato.

---

{% include-markdown "signature-core.md" %}
