## 📘 Documentazione Concettuale – Tabella `anagrafiche.risorse_umane`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo `RIS_UMANA` di cui il rapporto è la specializzazione
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la persona
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — la veste operatore appesa allo stesso ruolo
> * [config.qualifiche](/dbzero/config/tabelle/qualifiche) — la qualifica del rapporto
> * [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative) — il reparto in cui la persona lavora
>
> Approfondimento viste:
>
> * [anagrafiche.vw_risorse_umane_dettaglio](/dbzero/anagrafiche/views/vw_risorse_umane_dettaglio) — il rapporto col nome della persona, la qualifica e il reparto
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_risorsa_umana](/dbzero/anagrafiche/funzioni/fn_crea_risorsa_umana) — la porta che crea il rapporto
> * [anagrafiche.fn_crea_operatore](/dbzero/anagrafiche/funzioni/fn_crea_operatore) — crea insieme la persona, il rapporto, la credenziale e la veste operatore
> * [script.fn_veste_utilizzabile](/dbzero/script/funzioni/fn_veste_utilizzabile) — dove il rapporto decide se l'operatore entra
> * [anagrafiche.trgfn_risorse_umane_sync_auth_user_active](/dbzero/anagrafiche/funzioni/trgfn_risorse_umane_sync_auth_user_active) — la sincronizzazione della credenziale al cambio del rapporto
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — il rapporto di lavoro, la veste e la credenziale
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il soggetto, i ruoli e le loro specializzazioni

---

### 🎯 Scopo Principale

`anagrafiche.risorse_umane` registra il rapporto di lavoro di una persona con l'azienda (dipendente, consulente,
collaboratore): la sua qualifica, il suo reparto e le date in cui vale. È la specializzazione del ruolo `RIS_UMANA`
di un soggetto.

---

### Un rapporto per ruolo

Ogni riga nomina con `soggetto_ruolo_id` un ruolo `RIS_UMANA`, e ne è l'unica: il vincolo unico sul ruolo non è
parziale, e vale anche quando il rapporto che c'è è spento. La porta di creazione rifiuta una seconda risorsa umana
sulla stessa persona con un codice suo, invece di lasciarla arrivare al vincolo.

La riga porta anche `soggetto_id`, una copia del soggetto del ruolo, che i lettori usano senza passare dal ruolo. Il
guard di ruolo verifica, a ogni scrittura, che il ruolo sia una risorsa umana e che la copia coincida col soggetto
del ruolo.

La qualifica è obbligatoria; il reparto no. Il reparto conta per i permessi: un profilo di accesso dato a un reparto
vale per chi ci lavora.

---

### Il rapporto e l'accesso

Il rapporto non è collegato alla credenziale da una chiave esterna: la veste operatore della persona
(`anagrafiche.identita_digitali`) sta sullo stesso `soggetto_ruolo_id`, ed è da lì che si risale dall'uno all'altra.

Per una persona il rapporto fa parte dell'accesso. Una veste operatore è utilizzabile solo se, oltre a essere accesa
e dentro le sue date, ha il rapporto acceso e dentro le sue date: la regola sta in `script.fn_veste_utilizzabile`, e
«oggi» è il giorno operativo. La credenziale è accesa quando almeno una delle vesti è utilizzabile. Così la fine del
rapporto chiude l'accesso dell'operatore senza toccare la veste; non tocca invece le vesti di altro tipo della stessa
credenziale (il portale, lo shop), che non dipendono dal rapporto.

Le vesti tecniche dei processi automatici non hanno un rapporto, e non ne dipendono.

---

### Le regole che i trigger reggono

I trigger della tabella, elencati nella scheda, reggono questi temi:

* **il ruolo giusto**: il guard di ruolo, descritto sopra;
* **le date**: la fine non viene prima dell'inizio, con un vincolo e col guard comune delle date di validità;
  `validita` è l'intervallo calcolato dalle due date;
* **l'identità attiva**: il rapporto non si spegne finché la veste operatore sullo stesso ruolo è accesa;
* **l'ultimo SUPER_ADMIN**: il rapporto dell'ultimo amministratore senza scadenza non si spegne, non riceve una
  data di fine, non sposta l'inizio in avanti e non cambia ruolo;
* **la sincronizzazione**: un cambio dello stato o delle date del rapporto riallinea la credenziale; il come sta
  nella scheda della trigger function di sincronizzazione;
* **la notifica del reparto**: un cambio di reparto avvisa il backend, che ricalcola i permessi della persona;
* **i figli**: il rapporto non si spegne finché è il responsabile di una commessa accesa o ha pratiche, flussi o
  competenze sui flussi accesi;
* **i padri**: il soggetto, la qualifica e il reparto devono essere accesi, controllati alla conferma della
  transazione;
* **la cancellazione**: un rapporto non si cancella, si spegne; la cancellazione passa solo dalla porta di
  manutenzione;
* **la storia**: quando `storicizza` è acceso, ogni modifica e cancellazione lascia la riga di prima nello
  storico.

---

### ⚠️ Che cosa oggi non copre

* **Il rapporto che cambia ruolo.** La sincronizzazione scatta sullo stato e sulle date, non su
  `soggetto_ruolo_id`: spostare il rapporto su un altro ruolo lascia la credenziale com'era, finché non passa il
  riallineamento orario. Lo spegnimento del soggetto, che pure cambia l'utilizzabilità della veste, è fermato prima
  dal rapporto acceso.
* **Il commento.** La tabella non ha un commento nel database, e quasi nessuna colonna ne ha uno.

---

### Codici errore

* `E_RISORSA_UMANA_IDENTITA_ATTIVA` — si spegne il rapporto con la veste operatore ancora accesa.
* `E_PROFILO_ULTIMO_SUPER_ADMIN` — la scrittura toglierebbe l'ultimo SUPER_ADMIN senza scadenza.
* `E_RISORSA_UMANA_SOGGETTO_MISMATCH`, `E_SOGGETTI_RUOLI` — il ruolo non è una risorsa umana, o non è del soggetto
  scritto sulla riga.
* `E_DATA_AL_MINORE_DAL` — la fine viene prima dell'inizio.
* `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` — si spegne il rapporto con commesse, pratiche, flussi o competenze accesi.
* `E_ATTIVO_PADRE_NON_ATTIVO` — il soggetto, la qualifica o il reparto sono spenti.
* `E_DELETE_NOT_ALLOWED` — si cancella il rapporto fuori dalla porta di manutenzione.
* `E_RISORSA_UMANA_GIA_PRESENTE` — lo solleva la porta di creazione, per una persona che ha già un rapporto.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-risorsa-umana-gia-presente-v1.sql` — una persona ha un rapporto solo, anche
  quando quello che c'è è spento.
* `db/pgtap/anagrafiche/test-risorse-umane-guard-identita-attiva-v1.sql` — il rapporto non si spegne con la veste
  accesa; spenta la veste, si spegne e la credenziale lo segue.
* `db/pgtap/anagrafiche/test-super-admin-senza-scadenza-v1.sql` — la data di fine e l'inizio in avanti sul rapporto
  dell'ultimo amministratore sono rifiutati.
* `db/pgtap/anagrafiche/test-notify-cambio-reparto.sql` — il cambio di reparto attraversa il trigger senza errori.

Nessun test esegue i rifiuti del guard di ruolo, né lo spostamento del rapporto su un altro ruolo.

---

### Note di migrazione

* 2026-09-12 — la tabella ponte `risorse_umane_auth_user`, che legava il rapporto alla credenziale, era già
  diventata una vista sulle vesti, ed è ritirata: il legame passa dalla veste operatore sullo stesso ruolo.
* 2026-10-07 — il rapporto entra nella regola dell'accesso: la sua fine chiude l'accesso dell'operatore.

---

{% include-markdown "signature-core.md" %}
