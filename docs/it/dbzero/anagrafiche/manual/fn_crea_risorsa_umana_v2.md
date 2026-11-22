## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_risorsa_umana_v2`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane) — il rapporto che la funzione crea
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — la veste OPERATORE che nasce insieme al rapporto
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_operatore_v2](/dbzero/anagrafiche/funzioni/fn_crea_operatore_v2) — l'unica madre che la chiama
> * [config.fn_profilo_super_admin_id](/dbzero/config/funzioni/fn_profilo_super_admin_id) — quale profilo è il SUPER_ADMIN
> * [config.fn_lega_profilo_identita](/dbzero/config/funzioni/fn_lega_profilo_identita) — scrive il legame fra la veste e il profilo
> * [script.fn_veste_utilizzabile](/dbzero/script/funzioni/fn_veste_utilizzabile) — quando una veste apre davvero la porta
> * [anagrafiche.trgfn_identita_digitali_sync_auth_user_active](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_sync_auth_user_active) — la credenziale segue le vesti
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — la persona, il rapporto, la veste e la credenziale

---

### 🎯 Scopo Principale

`anagrafiche.fn_crea_risorsa_umana_v2` crea il rapporto di lavoro di una persona (la risorsa umana) e, se le si
passa una credenziale, la sua veste OPERATORE, con l'eventuale legame al profilo SUPER_ADMIN, tutto nella stessa
istruzione.

È il building block che sta sotto la creazione di un operatore: dentro il database la chiama solo
`anagrafiche.fn_crea_operatore_v2`, che prima ha già trovato o creato la credenziale e il soggetto persona fisica.
Il suffisso `_v2` è un nome rimasto: oggi non esiste una funzione con lo stesso nome senza suffisso.

---

### Una persona è una risorsa umana sola

Il rapporto si appoggia al ruolo `RIS_UMANA` del soggetto, che la funzione trova o crea. Se quel ruolo ha già una
risorsa umana, accesa o spenta, la funzione si ferma con `E_RISORSA_UMANA_GIA_PRESENTE` prima di scrivere: il
vincolo unico sul ruolo non distingue le righe spente, e il rimedio è sulla risorsa che c'è (il reinvito, la
riattivazione), non una seconda. La frase dell'errore porta il nome della persona; il campo segnalato è il soggetto.

Il rapporto nasce sempre acceso. La qualifica è obbligatoria e dev'essere attiva; l'unità organizzativa è
facoltativa, ma se c'è dev'essere attiva.

---

### Le date valgono per il rapporto e per la veste

L'inizio e la fine passati alla funzione vanno sia sul rapporto sia sulla veste: un operatore nasce con la veste
valida esattamente quanto il suo rapporto. Se l'inizio non si passa, è il giorno operativo
(`script.fn_data_operativa`), non la data di sistema.

---

### La veste nasce solo con una credenziale

Senza credenziale la funzione crea il rapporto e basta: nessuna veste, nessun profilo. Con la credenziale (che
deve esistere in `django.auth_user`) crea la veste OPERATORE sullo stesso ruolo del rapporto, accesa o spenta
secondo il parametro `p_attivo`. La madre `fn_crea_operatore_v2` la chiede sempre spenta: la accende
l'attivazione dell'invito.

Che la credenziale si accenda o resti spenta non lo decide questa funzione: lo decidono i trigger della veste,
secondo la regola «accesa se almeno una veste è utilizzabile» (vedi la scheda del trigger di sincronizzazione).

---

### Il profilo SUPER_ADMIN si risolve prima di scrivere

Con `p_is_super_admin` vero e una credenziale, il profilo SUPER_ADMIN si cerca **prima** di ogni scrittura, con
`config.fn_profilo_super_admin_id`: per tipo, fra i profili attivi, esattamente uno. Se non è uno solo la funzione
si ferma con `E_CONFIG_MANCANTE` senza aver scritto niente. Il legame fra la veste e il profilo lo scrive
`config.fn_lega_profilo_identita`, e nasce attivo anche quando la veste nasce spenta: la porta e il profilo sono
due domande diverse. Chi difende l'ultimo SUPER_ADMIN è il guard della veste
([`trgfn_identita_digitali_guard_ultimo_super_admin`](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_ultimo_super_admin)).

---

### Tutto o niente

La funzione è una sola istruzione: se un passo fallisce, non resta né il ruolo, né il rapporto, né la veste, né il
legame. I controlli che non sono suoi (la coerenza fra veste e ruolo, la natura della credenziale, l'unicità
della veste accesa, i guard del rapporto) li fanno i trigger delle due tabelle.

---

### ⚠️ Che cosa oggi non copre

* **`p_attivo` ha come default «accesa».** La regola è che la veste OPERATORE nasce spenta, e la madre la passa
  spenta; ma la funzione è eseguibile da `zeroerp_app`, e un chiamante diretto che non dice niente ottiene una
  veste accesa. La funzione gemella dei portali, `fn_crea_veste_portale`, non ha un default proprio per questo.
* **Un SUPER_ADMIN senza credenziale è ignorato in silenzio.** Con `p_is_super_admin` vero e nessuna credenziale
  non nasce né la veste né il legame, e la funzione non lo dice.
* **La credenziale non si controlla qui.** Che la credenziale abbia già una veste OPERATORE lo rifiuta la madre
  (`E_CREDENZIALE_GIA_OPERATORE`); chiamata direttamente, la funzione si affida agli indici unici, che valgono
  solo per le vesti accese: una seconda veste OPERATORE spenta sulla stessa credenziale passa.
* **Un inizio passato esplicitamente vuoto** non diventa il giorno operativo: il rapporto vuole la data, e l'errore
  arriva dal vincolo della colonna, senza un codice del catalogo. Il ripiego sul giorno operativo scritto per la
  veste non si raggiunge mai.

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_ADMIN_VALIDAZIONE` | manca il soggetto o la qualifica; la qualifica non esiste o è spenta; la credenziale passata non esiste |
| `E_ADMIN_UO_NON_TROVATA` | l'unità organizzativa passata non esiste o è spenta |
| `E_CONFIG_MANCANTE` | è chiesto un SUPER_ADMIN e i profili attivi di quel tipo non sono esattamente uno (da `config.fn_profilo_super_admin_id`) |
| `E_RISORSA_UMANA_GIA_PRESENTE` | il soggetto ha già una risorsa umana, accesa o spenta |

Più quelli dei trigger delle tabelle scritte.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-risorsa-umana.sql` — il rapporto senza credenziale (nessuna veste), il
  rapporto con la credenziale (la veste OPERATORE, chiesta accesa), il soggetto mancante, l'unità organizzativa
  inesistente. Il file lavora coi vincoli differiti: i guard di completezza del soggetto non scattano.
* `db/pgtap/anagrafiche/test-fn-crea-risorsa-umana-gia-presente-v1.sql` — il secondo rapporto sullo stesso
  soggetto, con la risorsa accesa e spenta, dalla madre e chiamando la funzione direttamente: il codice, il campo,
  la frase col nome, e che non resti niente scritto.
* Il legame SUPER_ADMIN lo esercitano le fixture che creano un super admin con
  `dbops.fn_pgtap_crea_operatore_umano`; `db/pgtap/config/test-fn-profilo-super-admin-id-v1.sql` prova, chiamando
  questa funzione, che con due profili SUPER_ADMIN attivi si ferma con `E_CONFIG_MANCANTE`.
* Nessun test prova il default di `p_attivo`, la qualifica spenta, la credenziale inesistente, il SUPER_ADMIN
  chiesto senza credenziale, né che le date finiscano anche sulla veste.

---

### Note di migrazione

* 2026-04-29 — nasce col suffisso `_v2` e prende il posto di `fn_crea_risorsa_umana`, che chiedeva il ruolo con
  l'enum `config.ruolo_sistema`; funzione ed enum sono stati ritirati. Il commento del corpo e quello della
  funzione descrivono ancora la differenza da quella versione.
* 2026-09-12 — ritirata la tabella ponte `risorse_umane_auth_user`: il legame fra rapporto e credenziale è la veste
  OPERATORE sullo stesso ruolo.
* 2026-09-23 — il profilo SUPER_ADMIN si risolve per tipo; prima era un id del seed scritto nel corpo.
* 2026-10-02 — il rifiuto `E_RISORSA_UMANA_GIA_PRESENTE`: prima il secondo rapporto arrivava al client come errore
  generico del vincolo unico.
* 2026-10-18 — il legame lo scrive `config.fn_lega_profilo_identita` e il profilo lo trova
  `config.fn_profilo_super_admin_id`, sedi uniche delle due regole.

---

{% include-markdown "signature-core.md" %}
