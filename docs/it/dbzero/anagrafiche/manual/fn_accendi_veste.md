## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_accendi_veste`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — la veste che la funzione accende
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_veste_portale](/dbzero/anagrafiche/funzioni/fn_crea_veste_portale) — crea la veste esterna, spesso spenta
> * [anagrafiche.fn_crea_operatore_v2](/dbzero/anagrafiche/funzioni/fn_crea_operatore_v2) — crea la veste OPERATORE, sempre spenta
> * [script.fn_veste_utilizzabile](/dbzero/script/funzioni/fn_veste_utilizzabile) — accesa non vuol dire ancora utilizzabile
> * [anagrafiche.trgfn_identita_digitali_sync_auth_user_active](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_sync_auth_user_active) — la credenziale segue le vesti
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — l'invito, la veste e la credenziale

---

### 🎯 Scopo Principale

`anagrafiche.fn_accendi_veste` accende una veste di una credenziale: quando la persona accetta l'invito, quando
attiva lo shop, o quando il provisioning dei dati di sviluppo prepara i suoi utenti. Risponde se la veste c'era.

È la sede unica dell'accensione: la chiamano il backend al consumo del token d'invito e, dentro il database, il
provisioning dei dati di sviluppo e la fixture pgTAP `dbops.fn_pgtap_crea_operatore_umano`.

---

### Si accende solo una veste di quella credenziale

La veste si indica col suo id **e** con la credenziale a cui deve appartenere; si può restringere anche ai tipi di
veste ammessi (vuoto vuol dire qualunque). Una veste che non c'è, che è di un'altra credenziale o che non è fra i
tipi ammessi non si accende, e la funzione risponde falso: così un token che porta l'id di una veste altrui non
accende niente, e chi chiama annulla.

Una veste già accesa resta com'è, senza scrittura, e la risposta è vero come per una veste appena accesa.

---

### Accesa non vuol dire utilizzabile

La funzione mette a vero lo stato della veste e basta: non tocca le date, il soggetto, né il rapporto di un
operatore. Se la veste è anche utilizzabile secondo `script.fn_veste_utilizzabile` (nelle sue date, sul soggetto
attivo, per un operatore umano col rapporto valido), i trigger della veste accendono anche la credenziale; se
non lo è, la credenziale resta com'era (vedi la scheda del trigger di sincronizzazione).

Accendere una veste può fallire per i controlli della tabella: per esempio una seconda veste accesa dello stesso
tipo sulla stessa credenziale o sullo stesso ruolo la ferma l'indice unico.

Il token dell'invito e il permesso di chi accende sono del backend.

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_SCRIPT_CHIAMATA_NON_VALIDA` | manca la veste o la credenziale |

Più quelli dei trigger e degli indici della tabella.

---

### Test

* Nessun test chiama la funzione direttamente. La esercitano `db/pgtap/anagrafiche/test-fn-provisiona-dati-di-sviluppo-v1.sql`
  (tutte le vesti dei dati di prova accese, anche alla seconda corsa) e ogni fixture che crea un operatore con
  `dbops.fn_pgtap_crea_operatore_umano`.
* Nessun test prova la risposta falsa (veste di un'altra credenziale, tipo non ammesso, veste inesistente), la
  veste già accesa senza scrittura, né gli argomenti mancanti.

---

### Note di migrazione

* 2026-10-18 — nasce come sede unica dell'accensione, che prima era scritta nel backend al consumo dell'invito e
  nella fixture pgTAP degli operatori.

---

{% include-markdown "signature-core.md" %}
