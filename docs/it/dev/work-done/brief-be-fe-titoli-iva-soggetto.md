# Piano BE/FE — `I7`: i titoli IVA del soggetto hanno una sede e nessuno la riempie

> ## ✅ CHIUSO — 2026-08-31: la sede si riempie
>
> `T1`, `T2`, `T3-a` e `T4` erano verdi dal 2026-08-29; **`T3-b`** — l'annullo
> della forzatura — si è chiusa il 2026-08-31, ad apply avvenuto della colonna
> `annulla_movimento_id` (merge `#1438`). Consuntivo nel §8.
>
> 📌 **Resta una promessa, e non è di questo piano**: nessuna fattura consuma
> ancora il plafond. Il registro si popola solo con le **forzature** manuali
> finché non arriva il task di pipeline `consuma_plafond_lotto` — voce 1 di
> [brief-db-richieste-aperte-dal-backend-2.md](../work-in-progress/brief-db-richieste-aperte-dal-backend-2.md),
> e il consumatore è `F3-b2` del
> [piano di Fase 3](brief-be-fe-iva-fase-3-consumatori-risolutore.md).

> **Destinatario:** backend (`dev/backend-tid`) e frontend. ⭐ **Nessuna azione DB
> in questo piano**, e non è un caso: la Fase 2 ha costruito tutto il lato DB.
>
> **Base.** [brief-db-be-iva-risolutore-e-regime-cliente.md](brief-db-be-iva-risolutore-e-regime-cliente.md)
> — `I7` nel suo §5, le decisioni in `D5`, `D10`, `D10-bis`, `D12`, `D13`,
> `D15-bis`, l'applicato nel suo **§8-ter**. Questo documento non ri-discute
> niente di tutto ciò: costruisce la metà che il §5 chiama «BE».
>
> **Origine.** Domanda di Tid del 2026-08-29, dopo il push della Fase 2:
> *«si è sbloccato altro, ci sono attività che puoi fare?»*.
>
> **Stato.** 2026-08-31 — ✅ **tutte e cinque le slice fatte e verdi**.
> Avanzamento nel §8.
>
> **Correlati:**
> [soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) ·
> [soggetti_titoli_iva_ambiti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_ambiti) ·
> [soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti) ·
> [tipi_titolo_iva](/dbzero/config/tabelle/tipi_titolo_iva) ·
> [fn_consuma_plafond_titolo_iva](/dbzero/anagrafiche/funzioni/fn_consuma_plafond_titolo_iva)

---

## 0. ⛔ Perché questa voce non può aspettare la Fase 3

La Fase 2 ha costruito **tre tabelle, cinque guard, la RLS, i grant, la primitiva
di consumo e ventotto asserzioni pgTAP**. E oggi non esiste **nessun modo** di
registrare un titolo: nessun endpoint, nessuna schermata.

⛔ **È la voce 2 del brief madre, in miniatura e al contrario.** Là il difetto era
*«un campo che l'operatore compila e nessuno legge»*; qui sarebbe *«una sede che
il modello legge e nessuno compila»*. La forma è la stessa — una promessa
strutturale senza il suo anello — e la cura è la stessa: costruire l'anello
mancante prima che qualcuno si abitui alla sua assenza.

⚠️ **E c'è una conseguenza diretta sulla Fase 3**, che è la ragione per cui questa
voce viene *adesso* e non dopo. `I2` è lo **stadio B**: legge i titoli. Un
risolutore scritto sopra tabelle che nessuno può riempire si può provare **solo**
in pgTAP, che le sue righe se le costruisce da sé. In applicazione non sarebbe
collaudabile da nessuno — e il §6 del brief madre chiede proprio un collaudo che
attraversa i due lati: *«soggetto con un titolo valido diverso dall'aliquota
dell'articolo → il risolutore ritorna quello del titolo»*.

⭐ **Detto in una riga:** senza questa voce, `I2` nasce verde e non provato.

---

## 1. Cosa c'è già, e cosa manca

### Il lato DB — tutto pronto

| Oggetto | Cosa dà |
| --- | --- |
| `config.tipi_titolo_iva` | vocabolario a seed: `INTENTO` (⭐ **l'unico** con `ha_plafond = true`), `USO_INDUSTRIALE`, `AGEVOLATA_104`, `COOPERATIVA` |
| `anagrafiche.soggetti_titoli_iva` | la sede: **soggetto proprietario + emittente destinatario** (`D10-bis`), tipo, `iva_id` sostitutivo, `ambito` (`TUTTO`/`RISTRETTO`), `validita` `daterange`, estremi documentali, `plafond`, `imponibile_utilizzato` |
| `…_ambiti` | l'ambito su tre livelli: `ARTICOLO`, `GRUPPO_VOCE`, `TIPO_VOCE`. `ON DELETE CASCADE` dal titolo |
| `…_movimenti` | il registro di `D5`: `FATTURA` (+), `NOTA_CREDITO` (−), `FORZATURA` (±, **motivo obbligatorio**). ⛔ **Nessun** `ON DELETE CASCADE` dal titolo |
| guard + `EXCLUDE` | coerenza plafond↔tipo, «TUTTO non ha righe», anti-sovrapposizione |
| RLS | le tre tabelle filtrate su `fn_scope_ef_whitelist(user, emittente_fiscale_id)` |
| `config.iva` | il codice **`NI35`** (id 18, `natura_iva_id = 8`): da oggi la natura N3.5 non è più orfana |

⭐ **Due lookup che servono all'ambito sono già nella whitelist**:
`vendite.articoli_gruppi` e `vendite.articoli_tipologie`. Si usano con
`<LookupSelect rel="…">` senza scrivere niente.

### Il lato BE/FE — tutto da fare

Nessun repository, nessun service, nessuna rotta, nessun componente. E
`config.tipi_titolo_iva` **non è nella whitelist dei lookup**: va aggiunta lì e
non esposta con un endpoint dedicato (`feedback_lookup_whitelist_first`).

---

## 2. Le decisioni da prendere prima di scrivere

> Sei, e nessuna era già decisa nel brief madre.
>
> ✅ **Tutte approvate da Tid il 2026-08-29** nella forma proposta, con una
> precisazione su `Q4` e **una richiesta nuova** che diventa `Q7`.

### Q1 · Dove vive il CRUD dei titoli?

Il titolo è **del soggetto** (`D10-bis`: *«è una tabella legata al soggetto e
basta, quella partita IVA ha una dichiarazione d'intento»*).

⭐ **Proposta: sub-drawer dal `SoggettoDrawer`**, esattamente come conti bancari,
indirizzi e contatti — sezione con riepilogo e pulsante «Gestisci». È lì che
l'operatore si trova quando arriva la dichiarazione, ed è la sede che il modello
dichiara.

⚠️ **Ma il drawer del singolo titolo nasce autonomo fin da subito**
(`feedback_drawer_autonomi`): richiamabile dal drawer padre **e** da una lista.
Costa uguale adesso e non si rifà per `Q4`.

📌 Rotte, con la grammatica di `api.md` (verbi nel metodo, mai nel path), sul
modello di `soggetti/<id>/conti-bancari/`:

```text
GET  POST    /anagrafiche/soggetti/<uuid>/titoli-iva/
GET  PATCH DELETE  /anagrafiche/soggetti/<uuid>/titoli-iva/<id>/
GET  POST    /anagrafiche/soggetti/<uuid>/titoli-iva/<id>/ambiti/
DELETE       /anagrafiche/soggetti/<uuid>/titoli-iva/<id>/ambiti/<id>/
GET  POST    /anagrafiche/soggetti/<uuid>/titoli-iva/<id>/movimenti/
```

⭐ Il terzo livello di annidamento **ha già un precedente** in questo progetto:
`contratti/<id>/righe/<id>/componenti/`.

### Q2 · L'ambito ristretto senza righe: si blocca o si avvisa?

Il DB lo **ammette apposta**, e lo dice: *«un titolo RISTRETTO senza righe figlie
non copre niente, ed è voluto: il caso si costruisce in due istruzioni, quindi un
vincolo lo rifiuterebbe a metà strada»*.

⭐ **Proposta: si avvisa, non si blocca.** Il drawer salva, e finché il titolo è
`RISTRETTO` con zero righe mostra un avviso che dice **l'effetto**, non lo stato:
«questo titolo non si applica a nessuna merce». ⛔ Bloccare il salvataggio
significherebbe impedire di costruire il caso in due passi, che è esattamente
quello che il DB ha deciso di permettere; tacere significherebbe lasciare in giro
un titolo che sembra attivo e non fa niente.

⚠️ **E l'avviso non è cosmetico**: è l'unica cosa che distingue «non ho ancora
finito» da «ho sbagliato», e nessuna delle due la può dire un vincolo.

### Q3 · Chi scrive nel registro dei movimenti?

Tre tipi: `FATTURA`, `NOTA_CREDITO`, `FORZATURA`.

⭐ **Proposta: dall'API si scrive SOLO `FORZATURA`.** Le prime due le produrrà la
pipeline con `I4`, dentro la transizione a DEFINITIVA (`D15-bis`), passando dalla
primitiva `fn_consuma_plafond_titolo_iva` che tiene il lock.

⛔ **Il guard non è formale, ed è il punto della voce.** Un `POST` che accettasse
`FATTURA` consumerebbe plafond **senza una fattura**: il `CHECK` del DB pretende
`fattura_id NOT NULL` sui tipi non-forzatura, quindi un chiamante dovrebbe
inventarsi l'id di una fattura vera — e a quel punto `uq_stiva_movimenti_documento`
non protegge più niente, perché la riga *è* formalmente valida. Il numero che ne
esce è precisamente quello che l'Agenzia delle Entrate verifica.

📌 `motivo` obbligatorio sulla forzatura lo impone già un `CHECK`; il service lo
chiede **prima**, per dare un errore che nomina il campo invece di uno SQLSTATE.

### Q4 · La lista dei «titoli sfondati»: configurabile o semplice?

È il residuo dichiarato al punto 4 del §8-ter: il DB ha deciso di **non bloccare**
il superamento sulle forzature — *«una forzatura esiste per registrare
fatturazioni fuori dal sistema, e impedire di scriverla impedirebbe di
accorgersene»* — e dice che il presidio giusto è **una lista che qualcuno guarda**.

⚠️ Una lista **configurabile** (`<ListaConfigurabile>`) si registra con righe di
seed in `ui.lista_definizione` e `ui.lista_colonna`, che sono **CSV di
`80_data`** — cioè una dipendenza dal team DB.

⭐ **Proposta: lista semplice adesso, senza dipendenze.** È una lista di
**presidio**, non di lavoro quotidiano: si guarda, non si esporta e non si
personalizza. E la forma non pregiudica niente — il giorno che servisse
configurabile, il seed è una cella di CSV e la query BE è già scritta.

⚠️ **La query ritorna il residuo, non un booleano** (`feedback_concentrico_no_yagni`).
Oggi la lista filtra `residuo < 0`; una soglia «in esaurimento» si aggiungerà
senza cambiare forma. ⛔ Non ne invento una adesso: non c'è nessuna decisione che
la fissi.

⭐ **La formula, precisata da Tid il 2026-08-29** — *«la somma degli imponibili
applicati; il residuo quindi sarà tetto intento − imponibile già applicato»*:

```text
residuo = plafond − imponibile_utilizzato
```

⚠️ **E il secondo termine non è un contatore che qualcuno incrementa**: è
`imponibile_utilizzato`, che il trigger `…_movimenti_accumulatore` **ricalcola
come `SUM` del registro** dopo ogni scrittura — è precisamente ciò che rende vera
la promessa di `D5`. Il BE quindi **legge la colonna** e non ri-somma le righe:
sommare a valle creerebbe una seconda verità sullo stesso numero, che è il
difetto che `D5` esisteva per evitare.

📌 Perimetro: **solo i tipi con `ha_plafond`** — sugli altri il residuo non
significa niente.

### Q5 · L'emittente destinatario: chi lo sceglie, e si può cambiare?

`emittente_fiscale_id` è `NOT NULL` ed è **in chiave** per `D10-bis`: senza, i
plafond di due emittenti si consumerebbero da un contatore solo.

⭐ **Proposta: `<EmittenteFiscaleField>`**, il building block che esiste già e che
fa esattamente i tre rami che servono — in edit testo read-only, in create Select
per l'admin globale, in create testo dal profilo per l'operatore.

⛔ **E in EDIT non si cambia mai.** Spostare l'emittente di un titolo sposterebbe
anche il plafond già consumato sotto un altro fornitore: i movimenti restano
attaccati al titolo, non all'emittente. Chi ha sbagliato destinatario disattiva e
ne registra un altro — che è anche la traccia giusta.

### Q6 · Cancellare un titolo, o disattivarlo?

Il titolo ha `attivo`, e l'`EXCLUDE` anti-sovrapposizione guarda `attivo IS TRUE`
— quindi **disattivare libera la finestra**, ed è la via prevista dal modello.

⭐ **Proposta: `DELETE` ammesso solo su un titolo senza movimenti; con movimenti
si disattiva.** Le righe di ambito seguono da sé (`ON DELETE CASCADE`); i
movimenti **no**, e non è una dimenticanza — un registro è la traccia di ciò che è
stato consumato, e un `DELETE` che se lo porta via cancella la prova.

⚠️ **Il DB la regge già**, ma male: senza movimenti-cascade il `DELETE` fallisce
con un `23503` che nomina un vincolo. Il service deve dire prima **la cosa vera**:
«questo titolo ha già consumato plafond: si disattiva, non si elimina».

### Q7 · ✅ **RICHIESTA DI TID (2026-08-29)** — una forzatura si **annulla**, non si cancella

> *«dovrebbe essere permesso l'annullamento di una riga forzata/manuale; solo
> annullamento, deve rimanere traccia ma no delete»*.

⭐ **Il meccanismo giusto è un CONTRO-MOVIMENTO, non un flag.** Una forzatura
sbagliata si annulla registrando una seconda riga `FORZATURA` di segno opposto,
che punta a quella annullata. Le ragioni, in ordine di peso:

1. ⭐ **il registro resta append-only, che è il punto di `D5`**: *«una forzatura
   che sovrascrive non lascia traccia del perché; una forzatura che è una riga
   **è** la traccia»*. Un flag `annullato` sarebbe di nuovo un valore
   sovrascritto sopra a un altro;
2. **l'accumulatore non si tocca**: `trgfn_…_movimenti_accumulatore` fa
   `SUM(imponibile)` su **tutto** il registro, senza filtri — un contro-movimento
   riporta `imponibile_utilizzato` al valore giusto da solo. Un flag imporrebbe
   invece di modificare il trigger perché escluda le righe annullate, cioè una
   modifica **al cuore** di `I7` per un caso di correzione;
3. ⭐ **la data dell'annullo è essa stessa un'informazione** — *quando* qualcuno
   si è accorto dell'errore. Un flag la perde; una riga la porta in
   `data_movimento`;
4. **la traccia che Tid chiede è più forte, non più debole**: si vedono
   **entrambe** le righe, l'errore e la correzione, ognuna con il suo motivo.

⛔ **Si annullano SOLO le forzature.** Un movimento `FATTURA` si corregge dal
documento — con una nota di credito, che è già un tipo del registro — e quella
strada è di `I4`. Coerente con `Q3`: dall'API si scrive solo `FORZATURA`.

⚠️ **E il conto sotto zero resta presidiato**: annullare una forzatura positiva
quando la somma scenderebbe sotto zero lo rifiuta già
`E_TITOLO_IVA_UTILIZZATO_NEGATIVO`, con una frase che nomina il titolo.

#### ⛔ Ma il collegamento vuole una colonna, e non ce l'ha

Il contro-movimento deve **dire quale riga annulla**, o il FE non può né marcare
la riga annullata né impedire di annullarla due volte.

⛔ **Non in `meta`.** Un riferimento strutturale in un jsonb non è interrogabile,
non ha FK e non ha vincolo di unicità: sarebbe una relazione dichiarata a parole
dentro un campo libero. Serve **una colonna vera**, ed è una richiesta di una
riga al team DB:
[brief-db-titoli-iva-movimenti-annullo.md](brief-db-titoli-iva-movimenti-annullo.md).

⚠️ **Come si procede intanto** (`feedback_be_fe_attende_prerequisiti_db`): `T3` si
spezza. Il **registro in lettura** e la **creazione della forzatura** non
dipendono da quella colonna e si fanno subito (`T3-a`); l'**annullo** aspetta
(`T3-b`). `T1`, `T2` e `T4` non sono toccate.

---

## 3. Le slice

### `T1` — BE: repository + service + rotte

* `SoggettiTitoliIvaRepository` — le tre tabelle, con i display field via JOIN
  (`feedback_display_fields_backend`): descrizione del tipo, codice/descrizione
  IVA, ragione sociale dell'emittente, nome dell'articolo o della categoria
  sull'ambito. ⚠️ **Nessun lookup lato client.**
* `SoggettiTitoliIvaService` — validazioni di merito: coerenza plafond↔tipo
  *prima* del trigger, `FORZATURA` unico tipo accettato dall'API, `DELETE` con
  movimenti rifiutato, ambito coerente col livello.
* rotte di `Q1`, su `DomainAPIView`, `area_funzionale = "anagrafiche"`.
* ⭐ `config.tipi_titolo_iva` **nella whitelist dei lookup**, non un endpoint suo.

⚠️ **La RLS fa già il perimetro emittente**: il repository **non** deve
ri-filtrare per emittente in Python. Ma i test che contano le righe vanno scritti
sapendolo (`feedback_rls_conteggio_zero_non_e_un_dato`).

### `T2` — FE: il drawer del titolo + la sezione sul soggetto

* `TitoloIvaDrawer.vue` — autonomo (`Q1`), con `readonly` + `useInjectReadonly`;
  `<EmittenteFiscaleField>`; tipo, IVA sostitutiva, validità, estremi documentali,
  plafond (**visibile solo se il tipo ha un tetto**), ambito;
* l'ambito RISTRETTO come **master-detail inline** (`RigheMasterDetailTable`),
  con il livello che decide quale lookup si apre — articolo, gruppo voce o
  tipologia voce;
* `TitoliIvaSoggettoDrawer.vue` — la lista dei titoli di un soggetto, aperta
  dalla sezione «Titoli IVA» del `SoggettoDrawer`, sul modello di
  `ContiBancariDrawer`;
* i18n `it` + `en`, chiavi sotto `anagrafiche.titoli_iva.*`.

### `T3-a` — FE + BE: il registro dei movimenti, lettura + forzatura

Lista in sola lettura dentro il drawer del titolo (data, tipo, imponibile,
documento, motivo) + il verbo **«Forza rettifica»** con motivo obbligatorio, in
un `AppDialog`. ⭐ Il totale mostrato è `imponibile_utilizzato`, che il trigger
tiene allineato: il FE **non lo ricalcola** sommando le righe — sarebbe una
seconda verità.

### `T3-b` — ✅ L'annullo della forzatura

Il contro-movimento di `Q7`, con il verbo «Annulla» sulla sola riga `FORZATURA`
non ancora annullata. ⛔ Aspettava la colonna di collegamento: senza, l'annullo
si sarebbe potuto scrivere ma non **mostrare**, ed è metà del valore.
✅ Applicata il 2026-08-31; consuntivo nel §8.

### `T4` — La lista dei titoli sfondati

Schermata di presidio (`Q4`), con la riga che apre il `TitoloIvaDrawer` di `T2`.

---

## 4. L'ordine

```text
T1  BE: repository + service + rotte      ⭐ per prima: senza, il FE non ha nulla
T2  FE: drawer titolo + sezione soggetto  il grosso
T3  registro movimenti + forzatura        dopo T2 (vive dentro quel drawer)
T4  lista titoli sfondati                 per ultima: riusa il drawer di T2
```

⚠️ **`T4` per ultima e non per priorità**: apre il drawer di `T2`, e costruirla
prima vorrebbe dire scrivere due volte la stessa apertura.

---

## 5. Presidi attesi

* ⭐ **il test che nessuno penserebbe di scrivere, ed è il più importante**:
  `POST` di un movimento con `tipo_movimento = 'FATTURA'` → **rifiutato**. È
  l'unico che si accorge se qualcuno riapre la porta di `Q3`;
* **plafond su un tipo che non ne ha** → errore che nomina il **campo**, non
  SQLSTATE — e il verso gemello, tipo con tetto **senza** plafond;
* **`DELETE` di un titolo con movimenti** → rifiutato con la frase vera, non con
  un `23503`;
* ⭐ **due emittenti, stesso soggetto** (`D10-bis`): l'operatore che vede
  l'emittente A **non** vede il titolo verso B. È RLS, ma il test va scritto
  **come applicazione** — da owner passerebbe a vuoto;
* **titolo `RISTRETTO` con zero righe**: si salva, e l'API lo **dichiara** (un
  campo nella risposta, non un colore nel template) — `Q2`;
* **la lista sfondati non inventa lo sfondamento**: un titolo di un tipo **senza**
  plafond non compare mai, qualunque sia `imponibile_utilizzato`;
* ⭐ **il residuo si legge, non si ricalcola** (`Q4`): la lista espone
  `plafond − imponibile_utilizzato`, e il test lo prova contro la **colonna** —
  un test che ri-sommasse le righe passerebbe anche se il BE avesse costruito la
  seconda verità che `D5` vieta;
* **`T3-b` · annullo di una forzatura** → nasce un **secondo movimento** di segno
  opposto e la riga originale **resta**; `imponibile_utilizzato` torna al valore
  di prima. ⛔ Il test che conta è quello che verifica che le righe siano
  **due**: uno che guardasse solo il totale passerebbe identico anche con un
  `DELETE`, cioè proprio con la cosa che Tid ha escluso;
* **`T3-b` · annullo di un movimento `FATTURA`** → rifiutato (`Q7`);
* **`T3-b` · doppio annullo** della stessa forzatura → rifiutato.

---

## 6. Fuori perimetro, dichiarato

* ⛔ **l'applicazione del titolo su una riga** — è `I2`, Fase 3. Qui si registra
  un titolo, non lo si legge;
* ⛔ **il consumo automatico del plafond** — è `I4`, e con esso l'**ordine
  deterministico** che `D15-bis` lascia al chiamante: *«il giro di lotto deve
  iterare le fatture `ORDER BY data documento, numero`»*. Non si anticipa: il
  ciclo che dovrebbe ordinare non esiste ancora;
* 📌 **i tre tipi diversi da `INTENTO` non hanno un `config.iva` da applicare**, e
  il team DB ha deciso di **non coniarne al buio**: si sceglie fra i codici a
  catalogo quando si registrerà il primo titolo di quella specie. Il FE quindi
  **non** propone un default di `iva_id` per tipo;
* 📌 **gli indici sulle colonne di ambito** sono un «no» rimandato del team DB:
  si accendono se la query di `I2` entrerà dall'articolo. Non è roba di questo
  piano.

---

## 7. Diario

| Data | Cosa |
| --- | --- |
| 2026-08-29 (revisione) | Revisione critica su richiesta di Tid: **otto rilievi**, tutti corretti (§8). 🔴 Il primo è un bug vero — i campi obbligatori non erano guardati e uscivano come violazioni di `NOT NULL`, perché mi ero fidato dei serializer `required` mentre in questo progetto **servono lo schema OpenAPI e non validano**. 🟠 E la catena a tre anelli della PATCH era senza presidio: la stessa forma che il progetto ha già pagato **due volte** su `vendite.contratti`. Aggiunto il guardrail gemello |
| 2026-08-29 | Piano scritto dopo il push della Fase 2, su domanda di Tid. ⭐ La voce non è «un CRUD in più»: senza, `I2` nascerebbe **verde e non provato**, perché lo stadio B leggerebbe tabelle che nessuno può riempire. Sei decisioni di forma proposte, la più delicata è `Q3` — dall'API si scrive **solo** `FORZATURA`, perché un `POST` con `FATTURA` consumerebbe plafond senza una fattura, su precisamente il numero che l'Agenzia delle Entrate verifica |

---

## 8. Avanzamento

### ✅ `T1` — BE: repository + service + rotte (2026-08-29)

| File | Cosa |
| --- | --- |
| `apps/anagrafiche/db/titoli_iva_repository.py` | le tre tabelle, display field via JOIN, `residuo` calcolato in SQL, `ambiti_count` |
| `apps/anagrafiche/services/titoli_iva_service.py` | i guard di `Q2`/`Q3`/`Q5`/`Q6`, ownership, normalizzazione dell'ambito |
| `apps/anagrafiche/api/views_titoli_iva.py` | sei view sulla grammatica di `api.md` |
| `apps/anagrafiche/api/urls.py` | le sei rotte |
| `apps/core/db/dbops_repository.py` | `config.tipi_titolo_iva` nella **whitelist dei lookup** (`feedback_lookup_whitelist_first`), non un endpoint suo |
| `apps/anagrafiche/tests/services/test_titoli_iva_service.py` | **12 presidi** |

⭐ **Due difetti trovati rileggendo il codice appena scritto, prima di provarlo:**

* **un N+1**: `ambito_incompleto` chiedeva le righe di ambito **per ogni titolo**
  della lista. Ora il conteggio arriva dalla stessa query (`ambiti_count`), e il
  test lo presidia con `list_ambiti.assert_not_called()`;
* **un `float` su un importo fiscale**: il binario d'arrivo è una colonna
  `numeric`, e un float introdurrebbe un errore di rappresentazione proprio sul
  numero che l'Agenzia delle Entrate verifica. Ora `Decimal`, con il test che
  asserisce anche il **tipo**.

### ⭐ La verifica che conta: lo smoke sul DB vero

Le sentenze SQL sono state provate una per una con `EXPLAIN` sullo schema vero
**prima** di scrivere il service — i nomi di colonna si verificano, non si
credono. Poi il percorso intero, in transazione annullata: **13/13 verdi**.

⚠️ **E la prima corsa è fallita, il che è il suo valore**: `InsufficientPrivilege`
sulla `INSERT`. La RLS delle tre tabelle **morde davvero**, e lo smoke girava
senza il contesto operatore. Rifatto con le GUC `app.ruolo_applicativo` e
`app.current_user_id` — cioè quello che il middleware fa a ogni richiesta vera.
⛔ Girarlo da owner avrebbe dato tredici verdi **senza esercitare la RLS**, che è
il «verde per sottrazione» che `AGENTS.md` vieta.

⚠️ **Secondo inciampo, e vale come metodo**: al primo errore atteso la
transazione si abortiva e tutti i passi successivi sembravano rotti. Ogni passo
che *deve* fallire sta ora nel suo savepoint.

**Cosa lo smoke ha esercitato che i test mockati non possono:** i guard di
coerenza plafond↔tipo **nei due versi**, il rifiuto delle righe di ambito su un
titolo `TUTTO`, l'accumulatore che muove `imponibile_utilizzato`, il rifiuto del
consumo sotto zero, e ⭐ **lo sfondamento che NON si blocca** e compare nella
lista di presidio con residuo negativo — cioè la decisione del team DB provata
dal lato che la giustifica.

📌 Verificato dopo il rollback: le tre tabelle sono a **zero righe**.

**Suite backend: 4194 test OK** (`ZEROERP_TEST_DB_E2E=1`).

### ✅ `T2` — FE: drawer del titolo + sezione sul soggetto (2026-08-29)

| File | Cosa |
| --- | --- |
| `anagrafiche/components/TitoloIvaDrawer.vue` | il drawer del singolo titolo, **autonomo**: emittente, tipo, IVA, validità, prova documentale, plafond, ambito master-detail |
| `anagrafiche/components/TitoliIvaSoggettoDrawer.vue` | la lista dei titoli del soggetto, apre il drawer sopra |
| `anagrafiche/components/SoggettoDrawer.vue` | sezione «Titoli IVA» con riepilogo e «Gestisci» |
| `anagrafiche/api/anagrafiche.js` | i dieci client |
| `core/constants.js` | `MANAGE_ICONS.TITOLI_IVA` |
| `core/db/dbops_repository.py` | `config.tipi_titolo_iva` fra le lookup **specializzate** |
| `anagrafiche/services/soggetti_service.py` | `titoli_iva` composto nel dettaglio soggetto |
| `locales/it.json`, `en.json` | 49 chiavi per lingua |

#### ⛔ Il difetto che si sarebbe visto solo a video

Il drawer deve mostrare il campo **plafond solo se il tipo ha un tetto**
(`ha_plafond`). Avevo scritto un handler `@change` che leggeva `opt.ha_plafond`
dall'opzione selezionata. ⚠️ **`LookupSelect` emette l'ID, non l'opzione** — e il
lookup generico proietta solo `id/codice/codice_interno/descrizione/attivo`.
Quindi la condizione sarebbe stata **sempre falsa** e il campo plafond **non
sarebbe mai comparso**, senza nessun errore: si sarebbe scoperto provando a
registrare una dichiarazione d'intento e non trovando dove scrivere il tetto.

⭐ **La sede giusta esisteva già**: `_LOOKUP_SPECIALIZZATE` nel repository dei
lookup — *«relazioni che estendono il contratto generico con UNA colonna in più
per il frontend, senza endpoint dedicati … le prossime relazioni aggiungono una
riga qui, non 70 di SQL»*. Una riga, come il meccanismo prometteva. E il drawer
legge `ha_plafond` dalla **stessa cache** che alimenta il Select
(`useGlobalLookup` per chiave: una sola fetch condivisa), non da un evento.

#### Due scelte di forma da non ri-discutere

* ⛔ **`TitoliIvaSoggettoDrawer` NON adotta `useSoggettoRuoloCollection`**, ed è
  una non-adozione motivata — la stessa forma con cui quel composable dichiara di
  non coprire `IndirizziSoggettoDrawer`. Quel backbone possiede la macchina a
  stati di un **form inline a card**; un titolo ha figli (ambiti, e col registro
  ne avrà due), quindi vuole un drawer suo e qui non resta nessuno stato di form
  da condividere. Riusarlo vorrebbe dire tenere una `formMode` che nessuno
  accende;
* ⭐ **il riepilogo nella sezione del soggetto non costa un round-trip**: i titoli
  sono composti dentro `SoggettiService.get_soggetto`, come contatti, indirizzi,
  ruoli e conti. È il pattern già in casa, non uno nuovo.

#### Verifiche

* **shape check sul DB vero**: ogni campo legato dai due template esiste davvero
  nel payload — 9/9 lista, 14/14 dettaglio, 5/5 ambito. ⭐ È il controllo che
  prende i nomi sbagliati, che **non danno errore**: rendono una cella vuota;
* `eslint` pulito, `npm run build` OK, guard i18n **verde** (49 chiavi × 2
  lingue, parità integra), suite backend **4194 OK**.

### ✅ `T3-a` — registro dei movimenti + forzatura (2026-08-29)

Dentro il `TitoloIvaDrawer`: il registro in sola lettura (data, movimento,
imponibile, documento, motivo) e il verbo **«Forza una rettifica»** in un
`AppDialog`, con importo, data e **motivo obbligatorio**.

* ⭐ **Il totale non si ricalcola**: si mostra `imponibile_utilizzato`, che il
  trigger tiene pari alla somma del registro. Sommare le righe a video sarebbe
  una seconda verità sullo stesso numero — il difetto che `D5` esiste per
  evitare. Per la stessa ragione, dopo ogni scrittura si **rilegge il dettaglio**
  dal BE invece di aggiornare il totale lato client;
* ⭐ **Il registro compare solo dove un tetto esiste**: su un tipo senza plafond
  nessuno scrive movimenti, e un pannello sempre vuoto è peggio di uno assente;
* **Il segno resta libero, lo zero no**: una forzatura corregge in entrambe le
  direzioni — in diminuzione è il caso più frequente — mentre un movimento che
  non muove niente non è una correzione, è rumore nel registro;
* 📌 Rinominata `ricaricaAmbiti` → `ricaricaDettaglio`: dopo il registro il nome
  diceva meno di quello che la funzione fa.

### ✅ `T4` — la lista dei titoli sfondati (2026-08-29)

`TitoliIvaSfondatiView` + voce di menu + rotta. La riga apre il
`TitoloIvaDrawer` di `T2` — che è la ragione per cui quel drawer è nato
autonomo.

* ⭐ **È l'altra metà di una decisione del team DB**: lo sfondamento non si
  blocca, perché *«una forzatura esiste per registrare fatturazioni fuori dal
  sistema, e impedire di scriverla impedirebbe di accorgersene»*. Senza questa
  schermata quella decisione resterebbe una metà sola;
* mostra l'**eccedenza**, non il residuo negativo: è il numero che interessa, e
  si legge senza fare il segno a mente;
* ⭐ **il menu è un file, non un seed DB** (`navigation.js`): verificato prima di
  pianificarla — se fosse stato un seed, la voce sarebbe stata una dipendenza dal
  team DB e non l'avrei potuta fare;
* `onActivated` oltre a `onMounted` (`feedback_keepalive_onactivated`): sotto
  KeepAlive il rientro nella tab non rimonta, e una lista di **presidio** che
  mostra dati vecchi è peggio di una vuota.

#### Verifiche

* **shape check sul DB vero** anche qui: un titolo portato deliberatamente a
  sfondamento compare in lista, con **10/10** i campi che la vista lega e
  l'eccedenza giusta;
* `eslint` pulito, `npm run build` OK, guard i18n **verde**, suite backend
  **4194 OK**.

### 🔎 Revisione critica del codice — 2026-08-29

> Richiesta di Tid a lavoro finito, come per la Fase 1. **Otto rilievi sul codice
> appena scritto**, tutti corretti. ⭐ Il primo è un bug vero, e nasce da una cosa
> che sapevo e non ho applicato.

#### 🔴 R1 · I campi obbligatori non erano guardati: errore grezzo dal DB

`create_titolo` guardava **solo** `emittente_fiscale_id`. Un payload senza
`valido_dal`, `tipo_titolo_iva_id` o `iva_id` arrivava fino alla `INSERT` e
usciva come violazione di `NOT NULL` — **provato sul DB vero**: tre casi su tre
davano `ProgrammingError`/`IntegrityError` grezzo.

⛔ **Perché è successo, ed è la parte che conta**: avevo scritto i serializer con
i campi `required` e mi ero fidato. Ma in questo progetto i serializer di
`extend_schema` servono lo **schema OpenAPI** e non validano niente —
`handle_post_json` passa il payload grezzo al service. È scritto nel codice, e
l'avevo già visto costruendo `T1`: la validazione di merito sta nei service, ed è
il motivo per cui ne sono pieni. **Ho seguito l'apparenza del serializer invece
del percorso della richiesta.**

#### 🟠 R2 · L'`UPDATE` poteva svuotare una colonna `NOT NULL`

L'altro verso dello stesso guard: una PATCH con `valido_dal: ""` normalizzava a
`NULL` e usciva come `23502`. Ora c'è `_NON_ANNULLABILI`, e il presidio prova
**anche il verso che non deve bloccare** — svuotare `valido_al` significa «senza
scadenza» ed è legittimo. Un guard scritto largo avrebbe rotto l'operazione più
frequente.

#### 🟠 R3 · La catena a tre anelli, di nuovo, e stavolta senza presidio

`_UPDATE_KEYS` → `_normalizza_titolo` → `_TITOLO_UPDATE_COLS`: **la stessa forma**
che ha prodotto un difetto silenzioso su `vendite.contratti` due volte —
`fatturazione_immediata` nel 2026-07-27 e i riferimenti dell'atto il 2026-08-29,
dove il mapper era finito nel builder sbagliato. Qui i tre anelli erano allineati
per fortuna, e **niente lo garantiva**.

⭐ Aggiunto `TitoliIvaCatenaUpdateTests`, gemello di quello dei contratti: ogni
chiave accettata deve **attraversare** il mapper e arrivare al repository, e ogni
chiave accettata dev'essere scrivibile. *Un difetto che il progetto ha già pagato
due volte non è un rischio teorico: è un rischio misurato.*

#### 🟠 R4 · Nessun guard di versione sulle fetch dei due drawer

Aprire un titolo, chiuderlo e riaprirne un altro più in fretta del ritorno della
prima fetch: la risposta stantia sovrascrive il form del titolo giusto, **senza
nessun errore**. Il progetto ha un BB apposta (`useFetchVersion`) e i drawer
fratelli lo usano. Ora lo usano anche questi due.

#### 🟡 R5 · Lo stesso numero formattato in tre modi diversi

`residuo` e `imponibile_utilizzato` erano `formatCurrency` nella vista di
presidio e **grezzi** (`750.00`) nel drawer e nella lista. Ora passano tutti da
`formatCurrency`.

#### 🟡 R6 · Un avviso dove l'operatore non poteva agire

L'avviso «questo titolo non copre nessuna merce» compariva anche in
**creazione**, dove le righe di ambito non si possono ancora aggiungere: diceva
di fare una cosa impossibile. Ora solo in edit, dove c'è il pulsante per
rimediare.

#### 🟡 R7 · Una lista di presidio senza limite

`list_titoli_sfondati` non aveva `LIMIT`. Una lista che *dovrebbe* essere quasi
vuota non è una lista limitata: se un giorno torna diecimila righe, la schermata
cade proprio quando c'è più da guardare. Tetto **dichiarato** (`_SFONDATI_LIMIT`),
con l'ordinamento per eccedenza decrescente che tiene in cima i casi peggiori.

#### 🟡 R8 · Un'icona cablata e una toolbar non reattiva

`icon="pi pi-verified"` scritto a mano nel `SoggettoDrawer` invece di
`MANAGE_ICONS.TITOLI_IVA` (`feedback_css_centralizzazione`), e `pageActions`
della vista come array costante invece di `computed`: le label si risolvono al
setup e non seguirebbero il cambio lingua.

#### ✅ Un sospetto verificato e caduto

`formatCurrency(undefined)` — temevo una stringa `NaN` prima del caricamento del
dettaglio: il BB gestisce già `null`/`undefined` con un placeholder.

#### Verifiche dopo le correzioni

Suite backend **4200 OK** (6 presidi nuovi), smoke end-to-end sul DB vero
**13/13**, build FE OK, `eslint` pulito, guard i18n verde.

### ✅ `T3-b` — l'annullo della forzatura (2026-08-31)

Sbloccata dal DB il 2026-08-31 (`annulla_movimento_id` + `CHECK` + FK + unique +
guard, brief [brief-db-titoli-iva-movimenti-annullo.md](brief-db-titoli-iva-movimenti-annullo.md)),
e chiusa lo stesso giorno.

| File | Cosa |
| --- | --- |
| `titoli_iva_repository.list_movimenti` | ⭐ legge la **vista** `vw_stiva_movimenti_dettaglio` e non più la tabella |
| `titoli_iva_repository.annulla_movimento` | delega alla madre `fn_annulla_movimento_titolo_iva` |
| `titoli_iva_service.annulla_movimento` | ownership a due livelli (titolo del soggetto, movimento del titolo) + motivo obbligatorio |
| `views_titoli_iva` + `urls` | `POST …/movimenti/<id>/annulla/` |
| `TitoloIvaDrawer.vue` | colonna azione **spenta col motivo** + `AppDialog` |
| `it.json` · `en.json` | i 5 motivi emessi dal DB + 3 chiavi della UI |

⛔ **Le precondizioni non sono state ricopiate.** Sono cinque e vivono in
`script.fn_check_annullo_movimento_titolo_iva` — la **stessa** funzione da cui la
vista prende il motivo per spegnere il pulsante e da cui la madre prende il
codice per rifiutare. Riscriverle nel service avrebbe significato che tooltip e
rifiuto possono divergere: è il difetto che quella funzione esiste per togliere.

⚠️ **Il verbo è `annulla`, non una `DELETE`**: l'azione non cancella niente,
aggiunge una riga. La grammatica URL del progetto vuole che il nome dica cosa
l'azione **è**.

#### Le prove — `smoke-titoli-iva-annullo-movimento.py`, 7 casi, tutto verde

⭐ **Il caso si COSTRUISCE**: `soggetti_titoli_iva` è vuota, quindi uno smoke che
cercasse il soggetto sarebbe passato **a vuoto** — verde per sottrazione. Qui
titolo e forzatura si fabbricano, e alla fine si annulla tutto.

| Prova | Esito |
| --- | --- |
| la vista espone le cinque colonne dell'annullo | ✅ |
| ⭐ sulla forzatura viva l'annullo è **ammesso** (il gemello positivo) | ✅ motivo `None` |
| il contro-movimento è una **riga nuova**, e l'originale resta | ✅ |
| ⭐ **l'accumulatore torna a zero DA SOLO** | ✅ — è la ragione per cui `Q7` scartò il flag |
| la vista blocca già il secondo annullo (`GIA_ANNULLATO`, `E_UN_ANNULLO`) | ✅ |
| ⚠️ e la **madre rifiuta davvero** | ✅ — senza, il tooltip sarebbe una decorazione |

⭐ **E il codice di dominio arriva intatto al backend**: verificato che
`E_TITOLO_IVA_ANNULLO_NON_AMMESSO` esce dal campo strutturato dell'eccezione.
⚠️ Finché `F0` non è applicata quel codice non ha ancora la sua classe, quindi
risolve come 400 invece che 409 (`CONFLITTO_STATO`): si sana col seed.

⛔ **Un difetto trovato nella fixture dello smoke, e vale la pena scriverlo**: la
prima versione univa `emittenti_fiscali_billing_account` sulla **PK**
dell'emittente. Quel ponte lega il **soggetto-ruolo**. È la stessa trappola
`feedback_emittente_pk_vs_soggetto_ruolo` che questo cantiere ha già nominato tre
volte — qui il database l'ha respinta con un errore di colonna, ma su una JOIN
valida avrebbe dato **zero righe** senza dire niente.

### ✅ Il cantiere di Fase 2 è chiuso

