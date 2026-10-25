# Guida Tecnica – API Commesse (DB layer)

> **Ultimo aggiornamento**: 25 ottobre 2026
>
> Destinatari: sviluppatori backend e database di Zero ERP
>
> 👀 **Vedi anche**
>
> * [Guida fatturazione](/guide/fatturazione)
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) — **le regole comuni a tutti i documenti**: nascita, cambio di stato, permesso sul passaggio, emissione, annullo
> * [Gestione Listini e Pricing v5](/guide/gestione-listini) — modello pricing che alimenta lo snapshot commesse
> * [vendite.commesse](/dbzero/vendite/manual/commesse) — la tabella, con la testata leggibile
> * [vendite.stati_commessa](/dbzero/vendite/tabelle/stati_commessa)
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> * [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti)
> * [API stato commessa](/backend/vendite/manual/api_commessa_stato) — `GET/POST …/stato/`, `GET …/legami/` e `PATCH /commesse/<id>/`
> * [API lookup risorse umane](/backend/anagrafiche/manual/api_risorse_umane_lookup) — il picker del responsabile
> * [BoMComponentExpander (catalogo BB backend)](/dev/backend/catalogo-building-block-backend) — espansione compositi nella pipeline push

---

## Panoramica

Il modello commesse centralizza tutte le attività fatturabili prima della
pipeline di fatturazione. Ogni sorgente (preventivo, ordine, contratto, DDT,
consumi) transita per la commessa — nessun bypass diretto verso
`attivita_fatturabili`.

```
SORGENTI (preventivi / ordini / consumi / ...)
        |
        v
    COMMESSA  <--- fn_get_or_create_commessa
        |
        | fn_upsert_commessa_attivita (righe)
        v
  COMMESSE_ATTIVITA
        |
        | fn_list_commesse_emittibili (discovery)
        | fn_emit_attivita_fatturabili_da_commessa (pull)
        v
  ATTIVITA_FATTURABILI  --->  PIPELINE FATTURAZIONE
```

---

## Ciclo di vita della commessa

⭐ Le regole comuni a tutti i documenti — in che stato si nasce, chi cambia lo stato, quale permesso chiede un passaggio, l'emissione, l'annullo — stanno nel [modello del documento di vendita](/guide/modello-documento-di-vendita), che al §10 dice anche a che punto è la commessa rispetto al modello. Qui ci sono gli stati e i passaggi che sono suoi.

### Stati

| ID  | Codice              | chiude | emittibile | modificabile |
| --- | ------------------- | ------ | ---------- | ------------ |
| 1   | BOZZA               | false  | false      | true         |
| 2   | APERTA              | false  | false      | true         |
| 3   | IN_ESECUZIONE       | false  | false      | true         |
| 4   | PRONTA_FATTURAZIONE | false  | true       | true         |
| 5   | CHIUSA              | true   | false      | false        |
| 6   | ANNULLATA           | true   | false      | false        |

I flag governano le operazioni:

* **modificabile**: consente upsert righe (`fn_upsert_commessa_attivita`)
* **emittibile**: consente il pull verso AF (`fn_list_commesse_emittibili`)
* **chiude_commessa**: impedisce riuso da `fn_get_or_create_commessa`

### Macchina di transizioni (data-driven)

Lo stato della testata vive **solo** nella FK `stato_commessa_id` (nessuna colonna
`stato` testuale — rimossa). Ogni cambio stato è validato contro una matrice:

* matrice [`vendite.transizioni_stati_commessa`](/dbzero/vendite/tabelle/transizioni_stati_commessa)
  (coppie `(stato_da, stato_a)` ammesse + `meta.manuale`);
* trigger `trgfn_commesse_guard_transizione` (BEFORE UPDATE OF `stato_commessa_id`):
  se `(OLD, NEW)` non è in matrice → `E_COMMESSA_STATO_TRANSIZIONE_INVALIDA` (472); per
  `→ PRONTA_FATTURAZIONE` richiede ≥1 riga APPROVATA+NON_EMESSA, altrimenti
  `E_COMMESSA_NESSUNA_RIGA_APPROVATA` (473);
* entrypoint sottile `fn_cambia_stato_commessa(p_commessa_id, p_nuovo_stato, p_user)`:
  risolve codice→id e fa l'UPDATE, delegando la validazione al trigger.

Transizioni attualmente in matrice: `BOZZA→{APERTA,PRONTA,ANNULLATA}`,
`APERTA→{IN_ESECUZIONE,PRONTA,ANNULLATA}`, `IN_ESECUZIONE→{PRONTA,ANNULLATA}`,
`PRONTA→{IN_ESECUZIONE,CHIUSA,ANNULLATA}`. Il flag `meta.manuale` distingue le
transizioni *automatiche* (push/ponte emittibilità) da quelle *utente*; il guard non lo
filtra (valida solo l'ammissibilità della coppia).

Le **azioni di stato utente** (chiudi / riapri / annulla) sono **esposte**: le
calcola
[script.fn_available_actions_commessa](/dbzero/script/manual/fn_available_actions_commessa)
— mirror del pattern di ordini, offerte, contratti e preventivi, **senza azioni
applicative** (il push è *verso* la commessa, non un'azione della commessa) — e le
serve l'endpoint [`GET/POST .../commesse/<id>/stato/`](/backend/vendite/manual/api_commessa_stato):
il `GET` porta stato, contatori e capability, il `POST` applica l'azione.

⭐ **Le azioni sono data-driven, non un elenco nel codice**: escono da
`vendite.transizioni_stati_commessa` filtrando le transizioni **manuali**
(`meta.manuale = true`) con `action_key` e `label_key` valorizzate. Le transizioni
automatiche non compaiono fra le azioni utente. Sugli stati terminali (`CHIUSA`,
`ANNULLATA`) l'elenco è vuoto e `can_change_state` è `false`.

⚠️ **La capability propone, il guard ammette**: l'enforcement resta su
`vendite.trgfn_commesse_guard_transizione` (via `fn_cambia_stato_commessa`). La
funzione delle azioni è di **sola lettura** e non esegue niente — un client che
non la legge prende il rifiuto del guard, e ha ragione lui.

> Le righe (`commesse_attivita`) hanno due assi indipendenti: `stato_approvazione`
> (BOZZA→APPROVATA) e `stato_emissione` (NON_EMESSA→EMESSA).

### Annullare una commessa

Fra due documenti collegati c'è un verso **in avanti** (a monte → a valle) e un verso
**all'indietro**. La commessa sta a valle di tutto ciò che la riempie: preventivi,
ordini, contratti, bolle, consumi, le rettifiche dei resi, gli oneri.

* **In avanti è bloccato.** Una commessa con righe già **emesse** (in volo verso una
  fattura) non si annulla: `E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE`
  ([script.fn_check_commessa_annullabile](/dbzero/script/funzioni/fn_check_commessa_annullabile)),
  e l'azione «Annulla commessa» è spenta col motivo. Si sistema prima il documento a
  valle.
* **All'indietro riapre, con la segnalazione.** Una commessa con righe **non ancora
  emesse** si annulla con la **conferma**: chi annulla vede che cosa si riapre e dove,
  e conferma.

Che cosa succede a ogni riga non emessa (un **legame** per riga, letto da
[vendite.fn_documento_legami](/dbzero/vendite/funzioni/fn_documento_legami)`('COMMESSA', id)`):

| La riga viene da | Annullando la commessa |
| --- | --- |
| un preventivo, un ordine, un contratto, una bolla | la riga esce dalla commessa (`ANNULLATA`, col registro) e il documento torna **da mandare in commessa**. Il preventivo `EVASO` torna `ACCETTATO` |
| un consumo | il consumo torna da mandare in commessa |
| la rettifica di un reso | l'accredito si annulla: il reso torna **da accreditare**. ⚠️ Oggi il caso non si presenta: la rettifica sta nella commessa della riga fatturata che corregge, quella riga resta emessa finché l'accredito c'è (una fattura con un accredito non si disfa), e una commessa con righe emesse non si annulla. Prima si annulla l'accredito |
| un onere | non c'è niente a monte: l'onere **si annulla** con la commessa |

⚠️ **L'ordine non cambia stato.** `EVASO` vuol dire «la merce è partita», e lo dicono
solo le bolle: né l'invio in commessa né il suo annullo lo toccano. Le righe dell'ordine
tornano semplicemente da mandare.

⭐ **Si torna indietro di un passo alla volta.** Nella catena preventivo → ordine →
commessa, annullare la commessa riapre solo l'ordine: il preventivo non si muove, le
sue righe le usa ancora l'ordine.

La strada è una sola, il verbo
[vendite.fn_annulla_commessa](/dbzero/vendite/funzioni/fn_annulla_commessa)`(id, legami_confermati)`:
prima ciò che vieta (righe emesse), poi la conferma — chi conferma **dichiara quanti
legami ha visto**; se nel frattempo sono cambiati, il DB chiede di nuovo — poi il
ritiro e lo stato `ANNULLATA`, in una transazione. Ogni altra strada che porta la
commessa ad `ANNULLATA` con righe non emesse è rifiutata dall'avviso
`E_DOC_ANNULLO_CON_LEGAMI` (guard `trg_commesse_m10_guard_annullo_con_legami_upd`): è
lo stesso meccanismo di bolla, ordine, preventivo e contratto, e a video la stessa
finestra di conferma. Per questo una commessa annullata non ha mai righe `NON_EMESSA`.

⭐ **Una riga ritirata non occupa il documento.** Una riga di commessa `ANNULLATA` non
conta come «già mandata» ([script.fn_get_stato_push_segment](/dbzero/script/funzioni/fn_get_stato_push_segment),
la sede unica letta dai lister e dal pannello di smistamento): è ciò che fa tornare il
documento da mandare.

⭐ **Il documento si rimanda in un'altra commessa.** Il legame documento → commessa
([vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti)) **resta come
storia** anche dopo l'annullo o la chiusura: il lineage del documento mostra tutte le sue
commesse. La regola è che un documento sta in **una sola commessa aperta alla volta**
(`E_COMMESSA_SORGENTE_ALTRA_COMMESSA`); quale sia la dice
[vendite.fn_commessa_viva_di_sorgente](/dbzero/vendite/funzioni/fn_commessa_viva_di_sorgente).
Il legame nasce insieme alla riga, dentro
[vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita):
nessun invio può dimenticarlo.

#### L'eccezione: il documento con righe in una commessa viva

L'inverso — annullare un **preventivo, un ordine o una bolla** che hanno righe in una
commessa viva, non ancora emesse — **non è bloccato**: si annulla con la conferma, e le
sue righe escono dalla commessa; le righe degli altri documenti restano. È voluto: la
commessa raccoglie righe di più documenti dello stesso cliente, e il blocco
costringerebbe ad annullare l'intera commessa o a togliere le righe una a una, che il
modello vieta (`vendite.fn_annulla_commessa_attivita` rifiuta le righe con sorgente).
Il blocco resta dove la riga è già emessa.

---

## Di chi è una commessa

### L'emittente non è un attributo: è la chiave di perimetro

`vendite.commesse.emittente_soggetto_ruolo_id` decide **chi può vedere quella
commessa**. Ci si appoggiano la row security della tabella, il filtro di scope
del cruscotto competenza e il giornale degli eventi.

⛔ Con quella colonna vuota la commessa non compariva sbagliata: **spariva**. Il
lavoro restava nel database, non lo vedeva nessuno e non veniva mai fatturato —
e una lista che non mostra una riga ha lo stesso aspetto di una lista in cui
quella riga non c'è. Da qui il `NOT NULL`.

### Da dove viene il valore

**Dal billing account, sempre.** La commessa non la compila una persona in un
form: nasce dal push, e l'emittente si ricava dal cliente del documento
sorgente. Tre pezzi, tutti in `20_code`:

| Oggetto                                                                                                     | Cosa fa                                          |
| ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| [`trgfn_commesse_default_emittente`](/dbzero/vendite/manual/trgfn_commesse_default_emittente)               | riempie la colonna quando arriva `NULL`          |
| [`script.trgfn_doc_guard_emittente_ba`](/dbzero/script/manual/trgfn_doc_guard_emittente_ba)             | rifiuta un valore diverso da quello derivato     |
| [`trgfn_commesse_sorgenti_guard_emittente`](/dbzero/vendite/manual/trgfn_commesse_sorgenti_guard_emittente) | vieta di collegare sorgenti di emittenti diversi |

⇒ **Chi crea una commessa non deve sapere niente di emittenti.** Se lo passa e
coincide, è ridondante; se non coincide, viene respinto. Per questo il parametro
è stato tolto dalla firma: *un parametro il cui unico valore ammesso è quello
che la funzione calcola da sé non è un'opzione, è una trappola per il prossimo
chiamante.*

### Una commessa non aggrega due emittenti

Tutto il lavoro raccolto in una commessa deve uscire da **un solo** emittente: è
l'emittente a decidere su quale registro la fattura verrà numerata, e con due
emittenti nella stessa commessa quella scelta non sarebbe più vera per una parte
delle righe.

⚠️ Il criterio è l'**emittente**, non il cliente: più clienti possono stare sotto
lo stesso emittente — è a questo che serve l'albero dei billing account — e
vietare che il documento di un cliente «figlio» contribuisca alla commessa del
«padre» sarebbe una regola più severa, che nessuno ha deciso.

### ⚠️ E il cliente non cambia emittente a piacere

L'altra metà dell'invariante sta in anagrafica: un cliente che ha già fatture o
commesse **non si sposta** su un altro emittente, perché i documenti già emessi
resterebbero orfani. Vedi
[`anagrafiche.fn_guard_ba_cambio_emittente`](/dbzero/anagrafiche/manual/fn_guard_ba_cambio_emittente).

---

## La testata leggibile

`vendite.commesse` porta, oltre al codice, tre colonne che dicono **che cosa è**
una commessa a chi la legge in una lista o in un drawer:

| Colonna                         | Che cosa dice                                                                                                                                |  Null  | Chi la scrive                                      |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | :----: | -------------------------------------------------- |
| `descrizione`                   | l'oggetto della commessa, in parole (max 255)                                                                                                |   sì   | l'operatore, dal drawer                            |
| `data_apertura`                 | quando è stata aperta — per le commesse nuove è **oggi nel fuso dell'azienda** (`script.fn_data_operativa()`), mai l'orologio della sessione | **no** | il default alla nascita; **sola lettura** dall'API |
| `responsabile_risorsa_umana_id` | chi la governa: una **risorsa umana** (`anagrafiche.risorse_umane`), come in `pratiche` — non un ruolo qualsiasi                             |   sì   | l'operatore, dal drawer                            |

⚠️ **`data_apertura` non è la competenza**: `competenza_dal`/`competenza_al`
restano la finestra fiscale del lavoro, e riusarle per «quando è nata» avrebbe
fatto rispondere una colonna a due domande.

### Come si leggono e si scrivono

* **Lettura**: nello stesso payload di `GET …/commesse/<id>/stato/` (`descrizione`,
  `data_apertura` ISO, `responsabile_risorsa_umana_id`, `responsabile_display` —
  il nome della persona dalla vista modello `anagrafiche.vw_risorse_umane_dettaglio`,
  la stessa che serve il picker). ⚠️ Non escono da `fn_get_commessa_stato`: il
  backend le fonde (§3 sotto).
* **Scrittura**: `PATCH /commesse/<id>/` — parziale, `null` esplicito **azzera**
  (togliere il responsabile è un gesto legittimo); `data_apertura` non si scrive
  e una chiave estranea è un `400` (whitelist chiusa). Nessun guard di **stato**:
  il database non ne mette, di proposito — la descrizione di una commessa chiusa
  si può correggere.
* **Il picker del responsabile** è `GET /anagrafiche/risorse-umane/lookup/`
  (cross-dominio: `risorse_umane` non ha codice/descrizione, il lookup generico
  non la può servire). Elenca le **attive**; una persona disattivata che è già
  responsabile compare come voce non selezionabile, col nome che arriva dal
  dettaglio.

### Il responsabile deve essere una persona attiva — nei due versi

* **Figlio → padre**: una commessa non punta a una risorsa umana spenta. Lo
  impone a DB il require generato dal framework ATTIVO
  (`trg_commesse_a10_risorse_umane_require_attivo_ins_upd`), che però risponde
  con `E_ATTIVO_REQUIRE` — classe **TECNICO**, la stessa del trigger montato
  male. Per l'operatore è un dato sbagliato, non un guasto: il backend verifica
  «persona attiva» **prima** dell'`UPDATE` e risponde `400` col campo; il guard
  DB resta l'autorità.
* **Padre → figli**: una persona responsabile di una commessa — **anche
  chiusa**, perché `commesse` non ha `attivo` e il block conta tutti i figli —
  **non si disattiva** (`trg_risorse_umane_a10_commesse_block_deact_upd`). È il
  quarto block della sua specie su `risorse_umane`, accanto a `pratiche`,
  `flussi` e `competenze_flussi`: per liberare una persona si cambia il
  responsabile, non si spegne la persona.

⚠️ **Non esiste una lista configurata `vendite.commesse`**: in
`ui.lista_definizione` ci sono `vendite.commesse_attivita` e il drill-down di
dashboard, non la commessa. Le tre colonne hanno quindi come sola superficie il
drawer e l'API, finché una lista non verrà configurata — e configurarla è dato,
non un cantiere.

---

## API — Funzioni DB

### 1. `fn_get_or_create_commessa`

> [Doc autogenerata](/dbzero/vendite/funzioni/fn_get_or_create_commessa) |
> [Doc concettuale](/dbzero/vendite/manual/fn_get_or_create_commessa)

**Scopo**: recupera una commessa riusabile o ne crea una nuova.

**Parametri principali**:

| Parametro                  | Obbligatorio | Note                                   |
| -------------------------- | :----------: | -------------------------------------- |
| `p_billing_account_id`     |      si      | FK anagrafiche.billing_account         |
| `p_utility_id`             |      si      | Deve coincidere con utility del BA     |
| `p_tipo_commessa`          |      no      | Default `AUTO`                         |
| `p_policy_fatturazione`    |      no      | Default `DA_DOCUMENTO`                 |
| `p_competenza_dal` / `_al` |      no      | Range competenza testata               |
| `p_force_new`              |      no      | Default `false` — forza nuova commessa |

⛔ **Non esiste un parametro per l'emittente.** L'emittente non si passa: **si
deriva dal billing account**, sempre. Vedi
[§ Di chi è una commessa](#di-chi-e-una-commessa).

**Ritorna**: `commessa_id` (nuova o riusata).

**Regole chiave**:

* Riuso solo su commesse con `chiude_commessa = false`
* Advisory lock transazionale per evitare doppie create concorrenti
* Emittente **derivato** dal billing account (non è un parametro)

```sql
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => 1001,
  p_utility_id => 2,
  p_force_new => false
);
```

---

### 2. `fn_upsert_commessa_attivita`

> [Doc autogenerata](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita) |
> [Doc concettuale](/dbzero/vendite/manual/fn_upsert_commessa_attivita)

**Scopo**: inserisce o aggiorna una riga attività nella commessa.

**Parametri principali**:

| Parametro              | Obbligatorio | Note                                                |
| ---------------------- | :----------: | --------------------------------------------------- |
| `p_commessa_id`        |      si      |                                                     |
| `p_segment_key`        |      si      | Chiave idempotenza (unique con commessa_id)         |
| `p_articolo_id`        |      si      | UUID catalogo.articoli                              |
| `p_istanza_utility_id` |      si      |                                                     |
| `p_uom_id`             |      si      |                                                     |
| `p_quantita`           |      si      | Diversa da 0, negativi ammessi                      |
| `p_prezzo_snapshot`    |      si      | Negativi ammessi                                    |
| `p_competenza_mese`    |      no      | Normalizzato al primo del mese                      |
| `p_stato_approvazione` |      no      | Default `BOZZA`                                     |
| `p_stato_emissione`    |      no      | Default `NON_EMESSA`                                |
| `p_tipo_movimento`     |      no      | `NORMALE`, `RETTIFICA` o `ONERE` (colonna)          |

**Ritorna**: `commessa_attivita_id`.

**Guard**: la commessa deve avere `stati_commessa.modificabile = true`.

```sql
SELECT vendite.fn_upsert_commessa_attivita(
  p_commessa_id => 12345,
  p_segment_key => 'ORD-1001-RIGA-1',
  p_articolo_id => '8c5ce3a9-...',
  p_istanza_utility_id => 10,
  p_data_attivita => DATE '2026-02-01',
  p_uom_id => 1,
  p_quantita => 1,
  p_competenza_mese => DATE '2026-02-01',
  p_competenza_dal => DATE '2026-02-01',
  p_competenza_al => DATE '2026-02-28',
  p_prezzo_snapshot => 100
);
```

---

### 3. `fn_get_commessa_stato`

> [Doc autogenerata](/dbzero/vendite/funzioni/fn_get_commessa_stato) |
> [Doc concettuale](/dbzero/vendite/manual/fn_get_commessa_stato)

**Scopo**: restituisce stato operativo + contatori aggregati in una singola query.

**Parametri**:

| Parametro       | Obbligatorio | Note                 |
| --------------- | :----------: | -------------------- |
| `p_commessa_id` |      si      | Errore se non esiste |

**Ritorna** (singola riga):

| Campo                                                                   | Descrizione                       |
| ----------------------------------------------------------------------- | --------------------------------- |
| `stato_commessa_id`                                                     | FK stati_commessa                 |
| `stato_commessa`                                                        | Codice testuale (backward compat) |
| `chiude_commessa` / `emittibile` / `modificabile`                       | Flag operativi                    |
| `policy_fatturazione` / `fatturazione_immediata` / `priorita_operativa` | Config testata                    |
| `billing_account_id` / `utility_id` / `emittente_soggetto_ruolo_id`     | Perimetro                         |
| `total_attivita`                                                        | Totale righe                      |
| `total_approvate` / `total_non_approvate`                               | Per stato approvazione            |
| `total_emesse` / `total_non_emesse`                                     | Per stato emissione               |
| `total_prezzo_da_riallineare`                                           | Righe con prezzo da aggiornare    |
| `last_update`                                                           | Max tra testata e ultima riga     |

```sql
SELECT * FROM vendite.fn_get_commessa_stato(12345);
```

⚠️ **La testata leggibile non esce da qui**: `descrizione`, `data_apertura` e
responsabile (§ *La testata leggibile*) li legge il backend da `vendite.commesse`
e li fonde nello stesso payload del `GET …/stato/` — un secondo endpoint sarebbe
una seconda chiamata per tre colonne della stessa riga.

---

### 4. `fn_list_commessa_attivita`

> [Doc autogenerata](/dbzero/vendite/funzioni/fn_list_commessa_attivita) |
> [Doc concettuale](/dbzero/vendite/manual/fn_list_commessa_attivita)

**Scopo**: elenca le righe `commesse_attivita` con filtri e paginazione (read-only).

**Parametri**:

| Parametro              | Obbligatorio | Note                           |
| ---------------------- | :----------: | ------------------------------ |
| `p_commessa_id`        |      si      | Errore se non esiste           |
| `p_stato_emissione`    |      no      | Es. `NON_EMESSA`               |
| `p_stato_approvazione` |      no      | Es. `APPROVATA`                |
| `p_competenza_mese`    |      no      | Normalizzato al primo del mese |
| `p_limit`              |      no      | Default 1000, max 10000        |
| `p_offset`             |      no      | Default 0                      |

**Ritorna**: elenco righe con JOIN `sorgente_codice` da `config.sorgenti`.

**Indice utilizzato**: `ix_commesse_attivita_commessa_stati (commessa_id, stato_approvazione, stato_emissione)`.

```sql
SELECT *
FROM vendite.fn_list_commessa_attivita(
  p_commessa_id => 12345,
  p_stato_emissione => 'NON_EMESSA',
  p_competenza_mese => DATE '2026-02-01',
  p_limit => 200
);
```

---

### 5. `fn_list_commesse_emittibili`

> [Doc autogenerata](/dbzero/vendite/funzioni/fn_list_commesse_emittibili) |
> [Doc concettuale](/dbzero/vendite/manual/fn_list_commesse_emittibili)

**Scopo**: discovery delle commesse pronte per il pull verso AF (read-only).

**Parametri**:

| Parametro                       |       Obbligatorio        | Note                                                                                                                                                                                                                                                |
| ------------------------------- | :-----------------------: | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `p_competenza_mese`             |            no             | Normalizzato al primo del mese                                                                                                                                                                                                                      |
| `p_billing_account_id`          |            no             | Filtro perimetro                                                                                                                                                                                                                                    |
| `p_utility_id`                  |            no             | Filtro perimetro                                                                                                                                                                                                                                    |
| `p_emittente_soggetto_ruolo_id` |            no             | Filtro emittente                                                                                                                                                                                                                                    |
| `p_limit`                       |            no             | Default 1000, max 10000                                                                                                                                                                                                                             |
| `p_gruppi`                      |            no             | Emissione mirata: solo le commesse con almeno una riga dei gruppi richiesti                                                                                                                                                                         |
| `p_emit_batch_id`               | no (⛔ **sì** per il pull) | L'identità del giro (`fatturazione_lotti.lock_batch_id`), la stessa dell'emit. Con essa le righe trattenute **dal lotto stesso** contano come pronte: al rilancio di un pull fallito la commessa viene rivisitata. `NULL` = nessuna auto-esclusione |

**Criteri di inclusione**:

1. `stati_commessa.emittibile = true`
2. Almeno una riga `commesse_attivita` con classe `PRONTA`, `RIFIUTATA` o
   `NON_APPROVATA` in `vw_commesse_attivita_emittibilita` — **vista dal giro**:
   una riga `TRATTENUTA` soltanto dal lotto di `p_emit_batch_id` è `PRONTA`;
   trattenuta da un **altro** lotto in gioco non conta
3. Se `p_competenza_mese` fornito, filtra su `commesse_attivita.competenza_mese`

**Ritorna**: lista commesse con `total_non_emesse` per ciascuna.

```sql
SELECT *
FROM vendite.fn_list_commesse_emittibili(
  p_competenza_mese => DATE '2026-02-01',
  p_limit => 500
);
```

---

### 6. `fn_emit_attivita_fatturabili_da_commessa`

> [Doc autogenerata](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa) |
> [Doc concettuale](/dbzero/vendite/manual/fn_emit_attivita_fatturabili_da_commessa)

**Scopo**: esegue il pull da `commesse_attivita` verso `attivita_fatturabili` (mutante).

**Parametri**:

| Parametro         | Obbligatorio | Note                                    |
| ----------------- | :----------: | --------------------------------------- |
| `p_commessa_id`   |      si      |                                         |
| `p_only_approved` |      no      | Default `true` — solo righe APPROVATA   |
| `p_dry_run`       |      no      | Default `false` — simula senza scrivere |

**Ritorna**: contatori (`total_candidate`, `inserted_rows`, `updated_rows`, `skipped_rows`).

**Regole chiave**:

* ROOT source obbligatoria sulla commessa
* Sorgente AF = `COMMESSA` + hash deterministico `segment_key` -> UUID
* Idempotenza su chiave `(sorgente_tipo_id, sorgente_uid)`
* Blocco se riga AF già fatturata
* Aggiorna `stato_emissione = EMESSA` sulle righe processate
* Propaga `sorgente_origine_tipo_id` (sorgente business originale)

```sql
SELECT *
FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  p_commessa_id => 12345,
  p_only_approved => true,
  p_dry_run => false
);
```

---

### 7. Funzioni di supporto

| Funzione                                                                            | Scopo                                                                                 |
| ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| [`fn_link_commessa_sorgente`](/dbzero/vendite/funzioni/fn_link_commessa_sorgente)   | Collega una sorgente alla commessa. **Ruolo auto-deciso a DB** `ROOT`/`COLLEGATO`. La chiama la madre delle righe, non chi invia |
| [`fn_commessa_viva_di_sorgente`](/dbzero/vendite/funzioni/fn_commessa_viva_di_sorgente) | La commessa **aperta** di un documento, o `NULL` (i legami verso commesse chiuse o annullate restano come storia) |
| [`fn_start_commessa_push_run`](/dbzero/vendite/funzioni/fn_start_commessa_push_run) | **Apre** il giro di push: la riga nasce in testa alla corsa, in stato `IN_ESECUZIONE` |
| [`fn_close_commessa_push_run`](/dbzero/vendite/funzioni/fn_close_commessa_push_run) | **Chiude** lo stesso giro con il suo esito, il risultato per handler e la durata      |

> ⭐ **Il giro di push si apre e si chiude, non si registra a cose fatte.** Con
> la riga creata all'inizio, quella rimasta a `IN_ESECUZIONE` è la prova che
> qualcosa è partito e non è tornato: un push interrotto lascia traccia.
>
> ⚠️ Il guadagno vale sul **batch**, che gira in autocommit. Il push singolo dal
> drawer avvolge tutta la corsa in una transazione unica: lì anche la riga
> d'apertura viene annullata insieme al resto.

---

## Flusso tipo — Backend step `pull_attivita_da_commessa`

Lo step pipeline `pull_attivita_da_commessa` (handler in
[`pipeline_step_executor.py`](/dev/backend/catalogo-building-block-backend)) esegue il
ponte commessa → `attivita_fatturabili`. Il perimetro (competenza/emittente/utility,
e `fatturazione_immediata`) arriva dal contesto del lotto (`LottoContext`), non
cablato nell'handler:

```python
# 1. Discovery commesse emittibili (filtrate per la corsia del lotto)
rows = db.call_fn("vendite.fn_list_commesse_emittibili",
    p_competenza_mese=competenza_mese,
    p_emittente_soggetto_ruolo_id=emittente_id,
    p_fatturazione_immediata=fatturazione_immediata,  # True (immediata) / False (differita) / None
)

# 2. Per ogni commessa, pull verso AF (idempotente, solo righe APPROVATE)
for row in rows:
    result = db.call_fn("vendite.fn_emit_attivita_fatturabili_da_commessa",
        p_commessa_id=row.commessa_id,
        p_only_approved=True,
        p_dry_run=False,
    )
    log.info(f"Commessa {row.commessa_id}: {result.inserted_rows} ins, "
             f"{result.updated_rows} upd")
```

> **Nota**: la firma di `fn_emit_attivita_fatturabili_da_commessa` è
> `(p_commessa_id, p_only_approved, p_dry_run)`; la funzione propaga anche le 8
> colonne snapshot audit pricing v5 da `commesse_attivita` ad
> `attivita_fatturabili`.

**Catena pipeline** (ordine dato dal seed `fn_list_fatturazione_pipeline_steps`,
orchestrata in Python da `LottoPipelineRunner`):

```
pull_attivita_da_commessa --> select_attivita --> generate_fatture_righe
  --> ricalcola_iva_lotto --> genera_fondi/applica_fondi
  --> prepare_sdi_payload_lotto --> numera_fatture --> close_lotto
```

---

## Flusso tipo — Push sorgente -> commessa

```python
# 1. Ottieni/crea commessa
commessa_id = db.call_fn("vendite.fn_get_or_create_commessa",
    p_billing_account_id=ba_id,
    p_utility_id=utility_id,
    p_competenza_dal=dal,
    p_competenza_al=al
)

# 2. Upsert righe: per una riga con sorgente documento la madre scrive anche
#    il legame documento -> commessa (fn_link_commessa_sorgente), e rifiuta se
#    il documento sta gia' in un'altra commessa aperta
for riga in righe_documento:
    db.call_fn("vendite.fn_upsert_commessa_attivita",
        p_commessa_id=commessa_id,
        p_segment_key=riga.segment_key,
        p_articolo_id=riga.articolo_id,
        ...
    )

# 3. Chiusura del giro (aperto PRIMA del punto 1 con fn_start_commessa_push_run)
db.call_fn("vendite.fn_close_commessa_push_run",
    p_id=push_log_id,          # l'id restituito dall'apertura
    p_stato="COMPLETATO",      # oppure PARZIALE / ERRORE
    p_risultato=esiti_per_handler,
    p_durata_ms=durata,
)

# 4. Giro COMPLETATO: per ogni commessa toccata, le righe di QUESTO invio
#    approvate e la testata a PRONTA_FATTURAZIONE (gia' pronta: non si ritenta)
db.call_fn("vendite.fn_rendi_commessa_emittibile",
    p_commessa_id=commessa_id,
    p_righe_ids=righe_di_questo_invio,   # mai le righe di terzi in attesa
    p_user=utente,
)
```

> ⭐ **Il verso in avanti verso la commessa sta nel DB, come il ritorno.** Il passo 4 è
> una madre DB: «le righe di questo invio» le conosce solo chi orchestra, quindi la
> chiama il backend. Il preventivo passa da `ACCETTATO` a `EVASO` da solo: il trigger
> delle righe di commessa lo riproietta dal residuo sulle due strade (merce da ordinare,
> servizi da mandare: `vendite.fn_preventivo_proietta_stato_smistamento`), lo stesso che
> lo riporta ad `ACCETTATO` quando una riga esce. L'ordine non cambia stato.

> ⚠️ **Il giro si apre prima, non si registra dopo.** L'esempio sopra mostra solo
> la chiusura: l'apertura (`fn_start_commessa_push_run`) è la prima cosa che fa
> l'orchestratore, prima ancora della discovery, ed è ciò che dà un
> identificativo vero all'evento d'avvio. Se la corsa muore nel mezzo, quella
> riga resta a `IN_ESECUZIONE` — ed è tutto ciò che si ha per sapere che era
> partita.

---

## Lifecycle prezzo: dal preventivo alla fattura

Questa sezione documenta il flusso completo del prezzo dall'origine (preventivo o ordine) fino alla fattura, passando per la commessa.

### Flusso standard

```text
1. Creazione preventivo (modello pricing v5)
   L'operatore inserisce righe con prezzo. Il prezzo puo venire da:
   - Resolver pricing v5 (fn_resolve_prezzo_listino_v2) - 3 stadi:
       STADIO 0: PROMO overlay
       STADIO 1: CONTRATTO (modalita A/B/C)
       STADIO 2: CATEGORIA cliente via matrice
   - Override manuale L1 (azione processo prezzo_override_manuale)
   - Workflow L3 approvazione:
       Se override viola L2 (limiti VENDITE_MAX_SCONTO/MAGGIORAZIONE_PCT)
       e l'operatore richiede approvazione (richiesta_approvazione=true),
       la riga e' salvata con stato_approvazione_prezzo='PENDING'.
       Il preventivo NON puo' transitare a ACCETTATO finche' tutte le
       righe PENDING sono APPROVED o REJECTED (trigger DB).
       Solo i preventivi ACCETTATI transitano in commessa: quindi una
       riga PENDING non arriva mai alla pipeline push commesse.

2. Push in commessa
   Il push (handler PREVENTIVO/ORDINE/CONTRATTO/DDT/CONSUMI) crea
   commesse_attivita con:
   - prezzo_snapshot = prezzo risolto o manuale
   - listino_versione_id = versione usata dal resolver (NULL se manuale)
   - listino_riga_id = riga usata dal resolver (NULL se manuale)
   - prezzo_bloccato = TRUE se override manuale, FALSE se da resolver
   - pricing_mode = 'FIXED' (v1)
   - 8 colonne snapshot audit pricing v5 (vedi sezione dedicata sotto)

3. Modifica preventivo post-push
   Se il preventivo viene modificato dopo il push:
   - commesse_attivita.prezzo_da_riallineare = TRUE (segnalazione, no update automatico)
   - Il prezzo NON viene aggiornato silenziosamente
   - L'operatore deve decidere se riallineare (N5) o ignorare

4. Riallineamento su conferma esplicita (N5)
   POST .../riallinea-prezzo/ ricalcola dal resolver alla data originale
   - Se la versione listino e cambiata: richiede conferma esplicita
   - Aggiorna prezzo_snapshot + prezzo_unitario su attivita_fatturabili,
     e con il prezzo la sua provenienza (versione listino, origine, base)
   - Azzera prezzo_da_riallineare
   - prezzo_bloccato resta FALSE

5. Variazione eccezionale (N7) — alternativa a N5
   POST .../variazione-prezzo-eccezionale/ con prezzo manuale + motivo
   - Imposta prezzo_bloccato = TRUE (il resolver non ricalcolera piu)
   - Il prezzo manuale prevale su qualsiasi listino
   - origine_prezzo = MANUALE, provenienza da listino azzerata

6. Sblocco (N7-sblocco) — reversibilita di N7
   POST .../sblocca-prezzo/ ricalcola dal resolver e sblocca
   - Imposta prezzo_bloccato = FALSE e riscrive la provenienza dal resolver

7. Conversione in ordine
   Se il preventivo non e stato riallineato (prezzo_da_riallineare = TRUE),
   il flag persiste sulla commessa. L'ordine non lo azzera automaticamente.
   L'operatore puo riallineare in qualsiasi momento prima della fatturazione.

8. Emissione fattura
   La pipeline fatturazione legge SOLO da attivita_fatturabili:
   - prezzo_unitario (snapshot gia propagato)
   - prezzo_bloccato (informativo)
   - NON rilegge mai il listino
```

### Snapshot pricing v5 — 8 colonne audit

Ogni riga `commesse_attivita` registra l'audit completo del calcolo prezzo
all'epoca del push. Queste colonne sono **immutabili dopo emissione fattura**
e permettono ricostruzione storica del processo pricing senza dipendere da
modifiche successive a listini/contratti/promo.

| Colonna                         | Valore                                                                         |
| ------------------------------- | ------------------------------------------------------------------------------ |
| `prezzo_base_snapshot`          | Prezzo riga listino prima di qualunque variazione                              |
| `origine_prezzo`                | `PROMO` / `CONTRATTO_OVERRIDE` / `CONTRATTO_LISTINO` / `CATEGORIA` / `MANUALE` |
| `tipo_variazione_applicata`     | `PERCENTUALE` / `VALORE_FISSO` / `PREZZO_FISSO` / `NESSUNA`                    |
| `valore_variazione_applicata`   | Valore firmato (negativo=sconto, positivo=maggiorazione)                       |
| `promo_id`                      | FK promo se origine=PROMO                                                      |
| `contratto_id`                  | FK contratto se origine CONTRATTO_*                                            |
| `categoria_cliente_id_snapshot` | FK categoria cliente al momento dello snapshot (anche se categoria poi cambia) |
| `classe_utenza_id_snapshot`     | FK classe utenza derivata da contratto/istanza                                 |

Popolazione: `fn_upsert_commessa_attivita` riceve gli 8 campi dal
chiamante Python (`CommessaAttivitaInput`). Al **push** li valorizza
`BaseSourceHandler._resolve_pricing_audit` via `PricingService.resolve_prezzo`
(`fn_resolve_prezzo_listino_v2`), **senza sovrascrivere `prezzo_snapshot`** (negoziato,
autoritativo): l'audit è diagnostico. Best-effort (errore resolver → audit NULL, push non
si blocca), `origine_prezzo` filtrato contro il CHECK (valore fuori set → NULL). Per i
componenti BoM l'`origine_prezzo` negoziato (in `meta`) prevale. La pull
`fn_emit_attivita_fatturabili_da_commessa` propaga gli 8 campi anche su
`attivita_fatturabili` (audit completo fino all'emissione).

### Espansione compositi BoM v5 (modello snapshot)

Quando una sorgente contiene un articolo composito
(`catalogo.articoli.is_composito = true`), la pipeline push **espande sempre** la riga
padre in N righe `commesse_attivita`, una per ogni componente **attivo** della BoM —
l'**esposizione in fattura** del componente (`esposizione_in_fattura`: `NASCOSTO` |
`DESCRITTIVO` | `VALORIZZATO`) **non è gate di espansione**: è solo una regola di
**presentazione** in fattura (vedi sotto). Vale per **tutte le sorgenti
documento** (preventivi, ordini, contratti, DDT) tramite lo stesso modello.

Logica orchestrata da `BoMComponentExpander` + `_componenti_repo_factory` in
`apps/vendite/services/commesse_source_handlers.py`:

* 1 riga sorgente composito → N righe `commesse_attivita`
* i componenti sono letti **dallo snapshot negoziato** della riga sorgente
  (`<sorgente>_righe_componenti` via `ComponentiRepositoryMixin.list_componenti_riga`),
  mai risolti di nuovo dal catalogo
* `articolo_id` = `componente_id`
* `quantita` = `quantita_padre × coeff_qta` (no rounding sotto-componenti)
* `prezzo_snapshot` = `prezzo_unitario` negoziato del componente (dallo snapshot)
* `segment_key` = `{padre_segment_key}#CMP:{componente_id}` (idempotente per re-run)
* `meta` arricchito con `componente_di`, l'esposizione del componente, `coeff_qta`, `origine_prezzo`.
  ⚠️ La chiave dell'esposizione diventa `esposizione` (il codice del modo); fino al
  2026-10-01 era `esposto_in_fattura` (booleano). Il passaggio lo fa il backend
  (`BoMComponentExpander` che la scrive, `FattureRigheService` che la legge): richiesta
  aperta nel brief `brief-db-esposizione-componenti-kit-in-fattura` §5
* Tutti gli altri campi (BA, utility, competenza, sorgente_uid, tipo_doc_fiscale) ereditati dal padre

**Qualunque sia il modo, ogni componente è tracciato in `commesse_attivita` col suo
prezzo**: l'esposizione decide solo la **presentazione** a valle, e la applica la vista
di rappresentazione della fattura
([vendite.vw_fattura_righe_esposte](/dbzero/vendite/views/vw_fattura_righe_esposte)):
nascosto = dentro il prezzo del kit, descrittivo = riga senza importo sotto il kit,
valorizzato = riga con prezzo e importo suoi sotto il kit, fuori dal suo prezzo. Le
regole sono nella [guida fatturazione § Come si espone un kit](/guide/fatturazione).

**Caso semplice (non composito, o senza loader/snapshot)**: pass-through,
1 riga sorgente → 1 riga `commesse_attivita`.

**Consumi utility (gas/energia/acqua/…)**: la decomposizione tariffaria è **rimandata**;
un consumo entra in commessa come **riga singola** (nessun fan-out).

**BoM immutabile**: la struttura BoM non puo' essere modificata in place
dopo essere stata pushata. Pattern admin: chiudi riga + duplica nuova
versione (vedi [gestione-listini §5.3](/guide/gestione-listini#53-immutabilita-della-bom-pattern-chiudi-nuova-versione)).
Garantisce che lo snapshot resti sempre ancorato alla struttura del momento.

### Gerarchia prezzo (riassunto)

| Priorita | Fonte                                      | prezzo_bloccato dopo |
| -------- | ------------------------------------------ | -------------------- |
| 1        | Override manuale su documento (N7)         | TRUE                 |
| 2        | Prezzo da resolver listino (standard o N5) | FALSE                |

### Casi limite

| Caso                                                            | Comportamento                                                                                                           |
| --------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Preventivo modificato, commessa non riallineata, fattura emessa | La fattura usa il prezzo dello snapshot originale. Il flag `prezzo_da_riallineare` resta TRUE come segnalazione storica |
| Versione listino cambiata dopo lo snapshot                      | N5 detecta il cambio e richiede conferma. Senza conferma, non aggiorna                                                  |
| Riga commessa gia fatturata                                     | N5/N7/N7-sblocco rifiutano con 409. Per correggere serve NDC/NDD (DB-L4)                                                |

---

## Error handling

Tutte le funzioni usano `script.fn_log_and_raise_error` con:

* Ambito `COMMESSE`
* Severity `C` (critico) per guard violations
* Context JSONB strutturato per diagnostica

Errori comuni:

| Errore                       | Funzione                       | Causa                                                                                                                                            |
| ---------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| commessa_id obbligatorio     | Tutte                          | Parametro NULL o <= 0                                                                                                                            |
| commessa non trovata         | get_stato, list_attivita, emit | ID inesistente                                                                                                                                   |
| commessa non modificabile    | upsert_attivita                | Stato CHIUSA/ANNULLATA                                                                                                                           |
| riga AF già fatturata        | emit_da_commessa               | Tentativo update su riga fatturato=true                                                                                                          |
| ROOT source mancante         | emit_da_commessa               | Nessun link ROOT in commesse_sorgenti                                                                                                            |
| sorgente COMMESSA non attiva | emit_da_commessa               | config.sorgenti COMMESSA disabilitata                                                                                                            |
| responsabile non attivo      | `PATCH /commesse/<id>/`        | il backend risponde `400` col campo (`E_COMMESSA_VALIDATION`) **prima** del require DB, che rifiuterebbe con `E_ATTIVO_REQUIRE` (classe TECNICO) |

---

## Test pgTAP

| File test                               | Copertura                                                                                               |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `test-commesse-stati-commessa-v1.sql`   | DDL stati_commessa, flag, fn_get_commessa_stato, fn_upsert guard, fn_list_commesse_emittibili (20 test) |
| `test-fn-list-commessa-attivita-v1.sql` | fn_list_commessa_attivita: filtri, paginazione, guard (14 test)                                         |


---
{% include-markdown "signature-core.md" %}
