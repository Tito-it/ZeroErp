# Piano BE/FE — Fase 1 del cantiere IVA (risolutore e regime cliente)

> **Destinatario:** backend (`dev/backend-tid`) e frontend. Nessuna azione DB in
> questo piano, **salvo una** — e sta dichiarata nel §3.3, con il brief da
> passare al team DB.
>
> **Base.** Questo documento non ri-discute niente: la fonte è
> [brief-db-be-iva-risolutore-e-regime-cliente.md](brief-db-be-iva-risolutore-e-regime-cliente.md),
> le decisioni sono nel suo §D / §D-bis, il processo in quattro fasi nel suo §5.
> Qui c'è **solo la Fase 1, e solo la metà BE/FE**: la metà DB è chiusa e
> applicata.
>
> **Origine.** Richiesta di Tid del 2026-08-29, a valle della riga scritta dal
> team DB nel §8-bis del brief madre: *«⛔ Richiesta al BACKEND — da fare
> adesso»*.
>
> **Stato.** 2026-08-29 — ✅ **`S1`, `S2`, `S3-a` e `S4` sono scritte, riviste e
> verdi**; `S3-b` è **gated** su un changeSet DB, richiesto con
> [brief-db-fn-create-contratto-codici-atto.md](brief-db-fn-create-contratto-codici-atto.md).
> Avanzamento nel **§8**, che include la **revisione critica** del 2026-08-29 e i
> sei difetti che ne sono usciti — fra cui una regressione dura sulla creazione
> contratto che nessuna delle verifiche automatiche poteva vedere.
>
> **Correlati:**
> [brief-db-fn-create-contratto-codici-atto.md](brief-db-fn-create-contratto-codici-atto.md) (figlio, `S3-b`) ·
> [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) ·
> [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) ·
> [vendite.contratti](/dbzero/vendite/tabelle/contratti) ·
> [fn_create_contratto](/dbzero/vendite/funzioni/fn_create_contratto) ·
> [fn_update_cliente](/dbzero/anagrafiche/funzioni/fn_update_cliente)

---

## 0. ⛔ Il fatto che cambia l'urgenza: il DB è **già applicato**

Il §8-bis del brief madre avvisa il backend di **un** effetto: *«un payload che
contiene una delle sei chiavi non viene respinto: viene ignorato in silenzio,
perché la whitelist non le conosce più»*. È vero, **ed è solo uno dei quattro
percorsi** — quello che passa da `anagrafiche.fn_update_cliente`, che è una
funzione madre con whitelist interna.

⚠️ **Gli altri tre non passano da nessuna whitelist: sono SQL diretto sulla
tabella.** Lì la colonna non esiste più, quindi non c'è nessun silenzio — c'è un
`UndefinedColumn` e una `500`.

Verificato sulla doc auto-generata (2026-08-29): `anagrafiche.clienti` **non ha
più** le sei colonne; `anagrafiche.soggetti` ha `split_payment` e `cliente_pa`;
`vendite.contratti` ha `codice_cig`, `codice_cup`, `codice_commessa`;
`config.stati_doc_fiscale` ha `congela_fiscale`.

| # | Percorso | Cosa fa oggi | Effetto |
| --- | --- | --- | --- |
| 1 | `POST /api/v1/anagrafiche/clienti/` | `ClientiRepository.create_cliente` costruisce `INSERT INTO anagrafiche.clienti (… iva_id, cliente_pa, split_payment, codice_cig, codice_cup, codice_commessa …)`. ⛔ E `iva_id` **c'è sempre**: `ClientiService.crea_cliente` lo inietta col parametro `DEFAULT_IVA_ID` quando il chiamante non lo passa | 🔴 **500 su OGNI creazione cliente** |
| 2 | `GET /api/v1/anagrafiche/clienti/<id>/` | `get_cliente` seleziona `cl.iva_id, cl.cliente_pa, cl.split_payment, cl.codice_cig, cl.codice_cup, cl.codice_commessa` + `LEFT JOIN config.iva iva ON iva.id = cl.iva_id` | 🔴 **500 sul dettaglio cliente** |
| 3 | `GET /api/v1/vendite/preventivi/form-defaults/?billing_account_id=…` | `BillingAccountRepository.get_cliente_defaults` seleziona `cl.iva_id` e fa il `LEFT JOIN config.iva` | 🔴 **500 sui defaults preventivo**, ogni volta che c'è un BA |
| 4 | `PATCH /api/v1/anagrafiche/clienti/<id>/` | passa da `anagrafiche.fn_update_cliente(jsonb)`, che le sei chiavi non le conosce più | 🟠 **salva, non segnala, non scrive** — è il caso descritto dal §8-bis |

⭐ **Perché la differenza conta, e non è pedanteria.** Il caso 4 è il rischio che
il brief madre aveva previsto e accettato consapevolmente (*«è il comportamento
meno peggiore dei due»*). I casi 1-3 non erano previsti perché la richiesta al BE
è stata scritta guardando **la whitelist**, non **le query**. La lezione è quella
già in memoria (`feedback_bb_legge_non_trasporta`): *i punti che toccano una
colonna si cercano dal percorso che li attraversa, non dal punto che li
dichiara.*

⚠️ **Conseguenza sulla priorità.** La slice `S1` non è «pulizia»: è **il
ripristino di un CRUD rotto**. Va per prima, e non si spezza.

---

## 1. Perimetro — cosa entra in questo piano

Dal §5 del brief madre, la **Fase 1** è `I0 · I8 · I9 · I10`. Ripartite fra i
lati:

| Voce | Metà DB | Metà BE/FE | In questo piano |
| --- | --- | --- | --- |
| **`I0`** — `clienti.iva_id` via (`D7-bis`), `split_payment`/`cliente_pa` su `soggetti` (`D8`) | ✅ applicata | 🔴 da fare | **`S1`** (togliere) + **`S2`** (rimettere sul soggetto) |
| **`I8`** — CIG/CUP/commessa dal cliente al contratto (`D9`) | ✅ applicata | 🔴 da fare | **`S1`** (togliere) + **`S3`** (rimettere sul contratto) |
| **`I9`** — gate IVA su ordini e preventivi (`R-3`) | ✅ applicata | 🟡 debito dichiarato dal DB: due `reason_key` mancanti | **`S4`** |
| **`I10`** — `congela_fiscale` (`D15`) | ✅ applicata | ⛔ **niente**: nessun consumatore BE/FE | §6, come osservazione |

⛔ **Cosa NON entra, ed è dichiarato**: `I7` (Fase 2), `I2`/`I3`/`I4`/`I5`
(Fase 3), `I6` (Fase 4). In particolare `I6` — «l'IVA di riga non si digita» — è
**decisa** (`D1`) e sembra a portata di mano: il brief madre avverte che *«una
voce sbloccata non è una voce da anticipare»*, e questo piano la lascia dov'è.

---

## 2. Le decisioni da prendere prima di partire

> Sono tre, tutte dentro la Fase 1, e nessuna era già decisa nel brief madre —
> quindi sono state decise **qui** e non vanno ri-discusse a valle.
>
> ✅ **Tutte e tre approvate da Tid il 2026-08-29**, nella forma proposta. Il
> testo che segue conserva la proposta e il suo argomento perché è così che ci si
> è arrivati.

### Q1 · ✅ **DECISA (Tid, 2026-08-29)** — i tre codici sul contratto sono modificabili anche in **ATTIVO**

Oggi `vendite.contratti` ha una whitelist di PATCH **per stato**
(`_CONTRATTO_PATCH_ALLOWED_BY_STATE` in `contratti_service.py`): in `ATTIVO`
restano editabili solo `valido_al` e `meta`; in `CESSATO` e `ANNULLATO` niente.
La regola scritta accanto dice: *«per cambi sostanziali in stati post-DRAFT serve
creare un nuovo contratto»*.

⭐ **Proposta: sì, ammessi anche in `ATTIVO`.** I tre codici non sono un *cambio
sostanziale*: non toccano prezzo, validità o perimetro — non producono **nessun**
effetto finché la fattura non ne fa lo snapshot (`I4`, Fase 3). E il caso reale è
esattamente quello: negli appalti PA il CIG arriva quando arriva, e può arrivare
a contratto già attivo. Negarlo costringerebbe a creare un contratto nuovo **per
un pezzo di carta**, che è il contrario di ciò che quella regola protegge.

⛔ In `CESSATO`/`ANNULLATO` restano **fuori**: lì la regola è immutabilità piena e
non c'è ragione di scalfirla.

⚠️ **Il sì fa crescere il lavoro FE di un pezzo preciso**: oggi
`ContrattoDrawer.buildPayload()` in stati post-DRAFT **ritorna `{}`** e il
pulsante Salva è spento (`isReadonly`). Serve un ramo `ATTIVO` che spedisca i
soli campi ammessi. Il delta è identificato e sta nel §3.3.

### Q2 · ✅ **DECISA (Tid, 2026-08-29)** — il dettaglio cliente **non** conserva nessuna vista dei valori spostati

Le sei colonne se ne vanno dal cliente, ma l'operatore che apre un cliente
continua a chiedersi «questo è in split payment?».

⭐ **Proposta: no, non in Fase 1.** Un campo di sola lettura che ripete un dato
che vive altrove è la premessa dell'errore che questo cantiere sta chiudendo — un
valore che sembra appartenere a una sede e non ci appartiene. Il posto per
guardarlo è il **soggetto** (`S2`), che è dove ora vive. Se poi si vorrà una
riga riassuntiva sul cliente, è una voce sua, con il suo perché.

### Q3 · ✅ **DECISA (Tid, 2026-08-29)** — `/vendite/preventivi/form-defaults/` perde le tre chiavi, senza deprecazione

Il payload oggi espone `iva_id`, `iva_codice`, `iva_descrizione`. Nessun
consumatore le legge — il `PreventiviDrawer.vue` porta il commento *«per
termine/iva sovrascriviamo solo se vuoti»* ma l'`apply` tocca **solo** il termine
di pagamento, e `vendite.preventivi` una colonna IVA di testata non ce l'ha.

⭐ **Proposta: si tolgono e basta**, senza deprecazione. Non c'è produzione
(`project_no_produzione_solo_sviluppo`) e non c'è consumatore. ⚠️ Va tolto **anche
il commento**, che dal momento della rimozione afferma il falso.

---

## 3. Le quattro slice

### 3.1 `S1` — 🔴 **Il cliente smette di scrivere le sei chiavi** (BE + FE)

> ⛔ **Prima di tutto il resto, e non si spezza**: finché resta com'è, creare un
> cliente e aprirne uno danno `500`.

**Backend — cinque file, e il perimetro è chiuso** (verificato con la ricerca
sui nomi di colonna nudi in tutto `backend/apps`, poi ristretta a chi tocca
`anagrafiche.clienti`: nessun altro lettore, né in `portale`, né in `pratiche`,
né in `ui`):

| File | Cosa |
| --- | --- |
| [clienti_repository.py](../../../../backend/apps/anagrafiche/db/clienti_repository.py) | le sei chiavi da `_OPTIONAL` di `create_cliente` (~167-169); le sei colonne + il `LEFT JOIN config.iva` dalla `SELECT` di `get_cliente` (~381-386, ~425); le sei chiavi da `_UPDATE_ALLOWED` (~445-447); ⭐ **e il metodo `get_default_iva_id` intero** (~58-63), che senza consumatori non ha più lavoro |
| [clienti_service.py](../../../../backend/apps/anagrafiche/services/clienti_service.py) | `iva_id` dalla lista degli int (~227), **il blocco del default `DEFAULT_IVA_ID`** (~231-233), `cliente_pa`/`split_payment` dalla lista delle stringhe (~234, resta `garanzia_tipo`), il ciclo dei tre codici (~238-240) |
| [views_clienti.py](../../../../backend/apps/anagrafiche/api/views_clienti.py) | `iva_id` dal serializer di create (~84); `iva_id`, `cliente_pa`, `split_payment` da quello di update (~125-129) |
| [billing_account_repository.py](../../../../backend/apps/anagrafiche/db/billing_account_repository.py) | `cl.iva_id`, `iva.codice`, `iva.descrizione` e il `LEFT JOIN config.iva` da `get_cliente_defaults` (~281-289); ⚠️ aggiornare anche il commento «Risultato: dict con termine_pagamento_id/**iva_id**/modalita_pagamento_id» |
| [vendite_form_defaults_service.py](../../../../backend/apps/vendite/services/vendite_form_defaults_service.py) | `iva_id`/`iva_codice`/`iva_descrizione` dallo scheletro del payload (~453-454) e dall'`update` (~519-520) — decisione `Q3` |

⚠️ **`DEFAULT_IVA_ID` come parametro di sistema resta a DB**: qui si toglie il
**lettore**, non il seed. Se dopo la Fase 3 nessuno lo legge davvero, è il team DB
a decidere se ritirarlo — non questo piano.

**Frontend — due file:**

| File | Cosa |
| --- | --- |
| [ClienteDrawer.vue](../../../../frontend/src/anagrafiche/components/ClienteDrawer.vue) | l'import di `IvaSelect` (~33); `useParameterDefaults(['DEFAULT_IVA_ID'])` (~55) e il blocco che lo applica (~255-257); le sei chiavi da `defaultForm` (~135-137), da `populateFormFromDetail` (~163-170) e da `buildEditablePayload` (~270-277); il campo IVA nella sezione **Pagamento** (~477-479); ⭐ **l'intera sezione «Pubblica Amministrazione»** (~504-531): `h4`, i due `Select` e il blocco condizionale `v-if="form.cliente_pa === 'S'"` con i tre `InputText` |
| [PreventiviDrawer.vue](../../../../frontend/src/vendite/preventivi/components/PreventiviDrawer.vue) | il commento *«per termine/iva sovrascriviamo solo se vuoti»* (~578) — **solo il commento**: il codice tocca già il solo termine di pagamento |

⚠️ **La sezione PA sparisce, non si svuota.** Se restasse il `<h4>` con dentro
niente, il drawer mostrerebbe un titolo senza campi — che è peggio di un campo
sbagliato, perché non ha nemmeno un modo di essere notato.

**i18n:** in `it.json` e `en.json` cadono `anagrafiche.clienti.field_iva`,
`select_iva`, `section_pa`, `field_cliente_pa`, `field_split_payment`,
`field_codice_cig`, `field_codice_cup`, `field_codice_commessa`. ⭐ Le ultime
cinque **non si cancellano: si spostano** con il campo — `field_cliente_pa` e
`field_split_payment` sotto `anagrafiche.soggetti.*` (`S2`), i tre codici sotto
`vendite.contratti.field_codice_*` (`S3`). Il testo è già scritto e già tradotto.
⚠️ `field_iva` e `select_iva` invece **spariscono**: l'IVA sul cliente non ha una
nuova sede, per decisione `D7-bis`.

**Test da adeguare** (nessuno di questi è una regressione da introdurre — sono
test che descrivono un dominio che non esiste più):

* `apps/anagrafiche/tests/services/test_clienti_service.py` (~382, ~388, ~397, ~481, ~488)
* `apps/anagrafiche/tests/services/test_clienti_repository.py` (~52-81) — ⚠️ il caso *«stringa vuota su campo nullable → `None` nel jsonb»* è costruito su `codice_cig`/`codice_cup`: la **proprietà** resta valida (`feedback_null_vs_empty`), cambia il **veicolo**. Va riscritto su un campo nullable ancora vivo, non cancellato. È la stessa lezione dei due pgTAP adeguati dal team DB.
* `apps/anagrafiche/tests/api/test_clienti_api.py` (~50, ~82)

---

### 3.2 `S2` — `split_payment` e `cliente_pa` **sul soggetto** (BE + FE)

Sede decisa da `D8`. Le colonne **esistono già** (`character(1)`, `NOT NULL
DEFAULT 'N'`, `CHECK ('S','N')`) e il travaso una tantum è **già passato**: qui
si costruisce solo chi le legge e chi le scrive.

⭐ **Voce corta, e la ragione è strutturale**: l'aggiornamento del soggetto **non**
passa da una funzione madre — `SoggettiRepository.update_soggetto` è un `UPDATE`
diretto con whitelist Python (`_ALLOWED`, ~413). Nessun prerequisito DB.

**Backend:**

| File | Cosa |
| --- | --- |
| [soggetti_repository.py](../../../../backend/apps/anagrafiche/db/soggetti_repository.py) | `s.split_payment`, `s.cliente_pa` nella `SELECT` di `get_soggetto` (~293); le due chiavi in `_ALLOWED` di `update_soggetto` (~413) |
| [views_soggetti.py](../../../../backend/apps/anagrafiche/api/views_soggetti.py) | le due chiavi nel serializer `SoggettoUpdateReq` (~114-118) |

⚠️ **In creazione non serve niente**, ed è voluto: `fn_crea_soggetto_pf` / `_pg`
non le conoscono, le colonne hanno `DEFAULT 'N'`, e un soggetto nasce «non PA,
non in scissione» — che è la direzione sicura già motivata dal team DB (*«un
soggetto di cui nessuno ha detto nulla non è in scissione»*). Chi deve dire il
contrario lo dice **dopo**, e per farlo c'è la PATCH.

**Frontend** — [SoggettoDrawer.vue](../../../../frontend/src/anagrafiche/components/SoggettoDrawer.vue):
i due `Select` `S`/`N` in una sezione nuova (`section_dati_fiscali`), visibile in
**edit**, accanto a `codice_fiscale`/`partita_iva` — è lì che il dato appartiene,
perché discende dalla partita IVA. Le opzioni sono le stesse `paOptions` che
oggi vivono in `ClienteDrawer`.

⚠️ **La 2ª occorrenza di `paOptions` è già qui** (`feedback_regola_del_2_estrai_bb`):
il primo consumatore era `ClienteDrawer`, il secondo è `SoggettoDrawer`. Ma il
primo **muore** in `S1`, quindi l'occorrenza resta **una**: si sposta la costante,
non si estrae un building block. ⭐ Se invece si decidesse un `SiNoSelect` a
catalogo, va dichiarato a Tid **prima**, come vuole la regola — non deciso
strada facendo.

---

### 3.3 `S3` — CIG, CUP e commessa **sul contratto** (⛔ DB + BE + FE)

Sede decisa da `D9`. Le tre colonne **esistono già** su `vendite.contratti`.

#### ⛔ Il prerequisito DB, e non si può aggirare

`vendite.fn_create_contratto(jsonb, jsonb)` è una **funzione madre atomica** che
inserisce le sole chiavi presenti **in una whitelist interna**
(`v_testata_allowed`). Le tre colonne non ci sono. Quindi:

> se il BE le manda in **CREATE**, la fn le **scarta in silenzio**: il contratto
> nasce, l'operatore non vede errori, e i tre codici non vanno da nessuna parte.

⭐ **È esattamente il difetto già costato un giro su questa stessa funzione**, e
sta scritto nel commento di `_CREATE_KEYS_TESTATA`: *«rev 2026-07-27:
`fatturazione_immediata` aggiunta a `v_testata_allowed` — senza questa voce la
chiave veniva scartata in silenzio»*. Farlo due volte sarebbe la forma peggiore
di regressione: quella già documentata accanto al punto in cui si ripete.

📌 **Brief al team DB (`dev/db-tid`), voce unica** — ✅ **scritto il 2026-08-29**:
[brief-db-fn-create-contratto-codici-atto.md](brief-db-fn-create-contratto-codici-atto.md).
In sintesi: estendere `v_testata_allowed`
di `vendite.fn_create_contratto` con `'codice_cig'`, `'codice_cup'`,
`'codice_commessa'`; changeSet nuovo con numerazione successiva, corpo preso
dalla doc auto-gen e **non** dallo YAML che la definisce oggi
(`feedback_ripiego_ogni_codice_vivo` sulla stessa forma: partire dallo YAML
farebbe regredire le revisioni intermedie). ⚠️ Le tre colonne sono **nullable**,
quindi qui non c'è la trappola «chiave assente vs chiave `null`» che vale per
`fatturazione_immediata`.

⚠️ **Come si procede intanto** (`feedback_be_fe_attende_prerequisiti_db`): la
**PATCH** non dipende da quella funzione — passa da `_UPDATE_WRITE_COLS`, che è
Python. Quindi `S3` si spezza in due, e la prima metà **non aspetta**:

* **`S3-a` — la PATCH**, subito;
* **`S3-b` — la CREATE**, dopo l'applicazione del changeSet DB. Finché non è
  applicato, le tre chiavi **non vanno messe** in `_CREATE_KEYS_TESTATA` e il
  drawer non le mostra in creazione: metterle prima vorrebbe dire spedire una
  chiave che il DB butta via.

#### Backend — `S3-a` (PATCH), la catena a **tre anelli**

⭐ **Il progetto ha già un presidio scritto per questo**, ed è la ragione per cui
la voce è a basso rischio: `ContrattiCatenaUpdateTests`
(`apps/vendite/tests/services/test_contratti_service.py:2899`) confronta fra loro
i tre anelli. Se se ne aggiorna uno solo, **il test lo dice**.

| Anello | File | Cosa |
| --- | --- | --- |
| 1 | `contratti_service.py` · `_UPDATE_KEYS_TESTATA` (~158) | le tre chiavi |
| 2 | `contratti_service.py` · `_build_update_data_testata` (~2027) | ⚠️ il mapper **copia campo per campo**: la whitelist da sola non basta |
| 3 | `contratti_repository.py` · `_UPDATE_WRITE_COLS` (~725) | le tre colonne |

+ `_SELECT_COLS_CONTRATTO` (~90) per esporle nel `GET` di dettaglio — senza,
il drawer non le rilegge dopo il salvataggio.
+ `_CONTRATTO_PATCH_ALLOWED_BY_STATE["ATTIVO"]` (~182), per `Q1`.

#### Backend — `S3-b` (CREATE), dopo il DB

`_CREATE_KEYS_TESTATA` (~110) + `_build_create_data_testata` (~1934), con la
stessa avvertenza dell'anello 2.

#### Frontend

[ContrattoDrawer.vue](../../../../frontend/src/vendite/components/ContrattoDrawer.vue):
tre `InputText` in una sezione «Riferimenti cliente» (o dentro i dati generali —
scelta di layout, non di modello); le tre chiavi in `populateFromDetail` (~221) e
in `buildPayload` (~424).

⚠️ **`buildPayload` va aperto** (`Q1`): oggi in stati post-DRAFT ritorna
`{}` di proposito. Serve un ramo che, in `ATTIVO`, spedisca i soli campi ammessi
dalla whitelist per stato — e la whitelist FE del commento «Profilo A» va
riscritta di conseguenza, altrimenti dice il falso.

**i18n:** `vendite.contratti.field_codice_cig` / `_cup` / `_commessa`, testo
riusato da `anagrafiche.clienti.*`.

📌 **Fuori perimetro, e già dichiarato dal team DB**: la colonna sulla **riga di
fattura** (non sulla testata: `fatture_righe` porta una sorgente per riga fra 15
tipi, quindi una fattura può mescolare più contratti) si costruisce con `I4`,
**insieme a chi la riempie**. Aggiungerla ora ricreerebbe la voce 2 del brief
madre — un campo che promette una cosa che non succede.

---

### 3.4 `S4` — Le due `reason_key` mancanti (FE)

Debito dichiarato due volte dal team DB nel §8-bis. Il DB espone il motivo
dell'azione spenta, il FE non sa tradurlo: l'operatore vede un pulsante spento
**senza il perché**, che è il caso che `api.md` §«Capability di riga» esiste per
evitare.

| Chiave | Stato |
| --- | --- |
| `vendite.ddt.azione_reason.iva_mancante` | ✅ c'è, it + en |
| `vendite.ordini.azione_reason.iva_mancante` | 🔴 **manca** |
| `vendite.preventivi.azione_reason.iva_mancante` | 🔴 **manca** |

⭐ **Il testo esiste già** ed è quello del DDT — *«Una o più righe hanno un prezzo
ma nessuna aliquota IVA: scegli l'aliquota, oppure togli il prezzo se la merce
non si valorizza.»* ⚠️ Sui **preventivi** va adattato: lì il guard esclude anche
le righe a quantità zero, e la riga si nomina per **descrizione** e non per
numero (`preventivi_righe` non ha `riga_nr`). Un messaggio che promette un
perimetro più largo di quello vero manda l'operatore a cercare una riga che il
guard non ha guardato.

⛔ **Va fatta con `S1`, non dopo.** È l'unica delle quattro che non tocca nessun
file delle altre, e lasciarla in coda significa tenere due pulsanti muti in
produzione di sviluppo per tutta la durata del cantiere.

---

## 4. L'ordine, e perché è questo

> ✅ **Eseguito in quest'ordine il 2026-08-29.** Resta scritto perché le ragioni
> valgono anche dopo: sono le stesse che rendono `S3-b` non anticipabile.

```text
S1  clienti: togliere            🔴 ripristina un CRUD rotto — PRIMA di tutto
S4  reason_key ordini/prev.       ⭐ indipendente, in parallelo a S1
S2  soggetti: i due flag          dopo S1 (l'i18n si sposta da lì)
S3a contratti: PATCH              dopo S1 (idem) — non aspetta il DB
--- brief al team DB: v_testata_allowed di fn_create_contratto ---
S3b contratti: CREATE             ⛔ solo ad applicazione avvenuta
```

⚠️ **`S1` non si spezza in BE-poi-FE.** Se il BE smette di accettare le sei
chiavi e il FE continua a mandarle, il drawer resta pieno di campi che non
salvano nulla — cioè il difetto della voce 2 del brief madre, riprodotto durante
la sua stessa correzione. E se il FE le toglie prima, la `POST` resta rotta lo
stesso, perché il default `DEFAULT_IVA_ID` lo inietta il **service**, non il
client. Le due metà sono una slice sola.

⭐ **`S2` e `S3` vanno dopo `S1` per una ragione pratica e una di merito.**
Pratica: le chiavi i18n si **spostano**, e spostare da un file che qualcuno sta
ancora modificando produce conflitti inutili. Di merito: finché il cliente porta
ancora i campi, per un attimo lo **stesso dato** avrebbe due sedi editabili — ed
è precisamente la forma che questo cantiere sta togliendo.

---

## 5. Presidi attesi

> Uno per slice, e nessuno è un test di copertura: ognuno prova la cosa che, se
> sbagliata, non darebbe nessun sintomo.
>
> ✅ **Tutti scritti**, tranne quello di `S3-b` che non è ancora scrivibile.
> ⭐ La revisione critica ne ha aggiunti due che qui non erano previsti, e sono i
> più utili dei due gruppi — l'**invariante CREATE ⊇ UPDATE** e la **purezza** del
> normalizzatore dei flag: entrambi nascono da difetti reali, non da un elenco.
> Il consuntivo è nel §8.

* **`S1` · il test che nessuno penserebbe di scrivere**: `POST` di creazione
  cliente **senza** `iva_id` nel payload → il cliente nasce. È il caso che oggi
  fallisce, e fallisce proprio perché il payload non la porta: il default se la
  metteva da solo. Un test che manda `iva_id` esplicito passerebbe a vuoto in
  entrambi i mondi;
* **`S1` · e il suo gemello sull'altro lato**: `GET` di dettaglio cliente →
  `200`, e il dict di risposta **non** contiene le sei chiavi. Un `assertEqual`
  sullo status non basta: la `SELECT` è dove il difetto vive;
* **`S1` · `/vendite/preventivi/form-defaults/` con un `billing_account_id`
  valido** → `200` e nessuna chiave `iva_*`. ⚠️ Senza il BA la funzione ritorna
  presto e **non tocca** la query rotta: un test senza BA sarebbe verde per
  sottrazione;
* **`S2` · il travaso non si ripete**: `PATCH` di `split_payment = 'S'` su un
  soggetto → rileggendolo, `'S'`. E il **valore non trasborda** su un secondo
  soggetto: la sede è il soggetto, non il ruolo, e la simmetria va provata;
* **`S2` · il `CHECK` morde dal BE**: `PATCH` con `split_payment = 'Y'` → errore,
  non un salvataggio che diventa «non applicare lo split» al primo `= 'S'`. Il
  pgTAP lo prova a DB; qui si prova che l'errore **arriva all'API** con la sua
  classe, e non come `500`;
* **`S3` · la catena a tre anelli**: `ContrattiCatenaUpdateTests` esiste già e
  copre il caso — va **rilanciato**, non riscritto. ⭐ Se passa con le tre chiavi
  in un solo anello, allora il presidio non presidiava e quello è il difetto da
  segnalare;
* **`S3-b` · il test che avrebbe risparmiato il giro del 2026-07-27**: `POST` di
  creazione contratto **con** i tre codici → rileggendo il contratto, ci sono. È
  l'unico che si accorge di una whitelist DB non estesa, perché la fn non
  solleva: scarta;
* **`S4` · la chiave si risolve**: la `reason_key` esposta dal DB
  (`vendite.ordini.azione_reason.iva_mancante`) trova una traduzione in **it e
  in en**. ⚠️ Se il FE usa `labelOrCode` come altrove, la mancanza si vede come
  un codice a video e nessun test fallisce da solo.

⭐ **Il test che chiude la Fase 1**, e va scritto una volta sola: cercare le sei
colonne **per nome nudo** in tutto `backend/` e `frontend/src/` → zero
occorrenze fuori dai test adeguati. È la forma di ricerca che il team DB ha
dovuto imparare due volte (`grep` sui nomi di colonna soli, senza vincoli di
prossimità e senza il nome della tabella): qui costa una riga.

---

## 6. Fuori perimetro, dichiarato

* ⛔ **`I6`, `I7`, `I2`…`I5`**: sono Fase 2, 3 e 4. In particolare `I6` è
  **decisa** ma va **per ultima** — il brief madre spiega perché, e il fatto che
  sia sbloccata la rende più facile da anticipare per sbaglio, non meno;
* 📌 **`PRE_FISCALI = ['DRAFT', 'EMESSA']` in
  [LottoDrawer.vue](../../../../frontend/src/vendite/components/LottoDrawer.vue) (~730)**
  — trovato guardando `I10`, e **non è la stessa domanda**. Quella lista risponde
  a «l'azione fallirebbe?», non a «il documento è congelato fiscalmente?», e per
  la regola 3 di `D15` le due domande non si appoggiano l'una sull'altra. ⚠️ Resta
  però una **terza copia** di una soglia che ora è dichiarata a DB, e vive in un
  template Vue: se un giorno il BE esporrà `congela_fiscale` nel payload delle
  capability, quel `const` va sostituito. Non si fa qui, e non si fa senza un ok;
* 📌 **Il ritiro del parametro `DEFAULT_IVA_ID`**: qui muore il lettore. Se il
  seed vada tolto lo decide il team DB, a Fase 3 chiusa;
* ⛔ **Qualunque misura sui dati**. Non ce n'è nessuna in questo piano ed è
  voluto: la domanda «quanti clienti avevano un CIG?» non decide niente. Decide
  che il modello ammetteva un CIG per fornitura mentre il CIG nomina un
  contratto, e tanto basta.

---

## 7. Diario

| Data | Cosa |
| --- | --- |
| 2026-08-29 | Piano scritto su richiesta di Tid, a valle della *«Richiesta al BACKEND»* del §8-bis del brief madre. ⛔ **Verificato che il DB è già applicato** (doc auto-gen: le sei colonne non ci sono più su `clienti`, le due sono su `soggetti`, le tre su `contratti`, `congela_fiscale` su `stati_doc_fiscale`) — quindi l'effetto non è il solo «silenzio» descritto dal §8-bis: **tre percorsi su quattro sono `500`**, perché sono SQL diretto sulla tabella e non passano dalla whitelist di `fn_update_cliente`. `S1` diventa un ripristino, non una pulizia. ⛔ **Trovato un prerequisito DB non censito**: `vendite.fn_create_contratto` ha una whitelist interna, quindi in CREATE i tre codici verrebbero **scartati in silenzio** — è lo stesso difetto già costato un giro su `fatturazione_immediata` il 2026-07-27, documentato nel commento accanto. `S3` si spezza in PATCH (subito) e CREATE (dopo il DB). Aperte tre decisioni: `Q1` i tre codici in `ATTIVO`, `Q2` nessuna vista residua sul cliente, `Q3` le tre chiavi via da `form-defaults` |
| 2026-08-29 (esecuzione) | ✅ Tid approva `Q1`, `Q2`, `Q3` nella forma proposta. Applicate **`S1`, `S2`, `S3-a`, `S4`**; `S3-b` resta gated e va al team DB con un brief suo. ⛔ **Il guardrail `ContrattiCatenaUpdateTests` ha trovato un errore vero**: `_apply_codici_atto` era finita nel mapper di CREATE invece che in quello di UPDATE — i due blocchi finali sono identici e la sostituzione ha preso il primo. Sarebbe stato **doppiamente silenzioso**: PATCH che risponde 200 senza scrivere, e CREATE che spedisce chiavi che la fn madre scarta. *Il guardrail scritto per `fatturazione_immediata` ha ripreso lo stesso difetto alla prima colonna aggiunta dopo.* ⭐ Scoperto anche che tre test su `clienti` erano **verdi descrivendo un contratto morto**: mockano il repository, quindi la whitelist non passa di lì. Verifiche: 4158 test backend OK, i18n guard verde, build FE OK |

---

## 8. Avanzamento — cosa è scritto e cosa resta

> Scritto il 2026-08-29, subito dopo l'esecuzione. ⭐ Le tre decisioni `Q1`/`Q2`/`Q3`
> sono state approvate da Tid nella forma proposta, e il lavoro le applica.

### ✅ `S1` — il cliente smette di scrivere le sei chiavi

| File | Cosa |
| --- | --- |
| `apps/anagrafiche/db/clienti_repository.py` | sei chiavi via da `_OPTIONAL` (create), dalla `SELECT` di `get_cliente` e da `_UPDATE_ALLOWED`; `LEFT JOIN config.iva` e `iva_descrizione` rimossi; ⭐ **`get_default_iva_id` eliminata** |
| `apps/anagrafiche/services/clienti_service.py` | sei chiavi via, **e con loro il default `DEFAULT_IVA_ID`** |
| `apps/anagrafiche/api/views_clienti.py` | `iva_id` dal serializer di create; `iva_id`/`cliente_pa`/`split_payment` da quello di update |
| `apps/anagrafiche/db/billing_account_repository.py` | `cl.iva_id` + join + le due descrizioni da `get_cliente_defaults` |
| `apps/vendite/services/vendite_form_defaults_service.py` | le tre chiavi `iva_*` dal payload di `/vendite/preventivi/form-defaults/` (`Q3`) |
| `frontend/.../ClienteDrawer.vue` | `IvaSelect`, `useParameterDefaults(['DEFAULT_IVA_ID'])`, `paOptions`, le sei chiavi da form/populate/payload, e **l'intera sezione «Pubblica Amministrazione»** |
| `frontend/.../PreventiviDrawer.vue` | il commento che dal 2026-08-29 affermava il falso |

⭐ **`DEFAULT_IVA_ID` resta un parametro vivo, e non è una svista**: lo legge il
form-defaults dell'**articolo** (`catalogo_service.py`). È corretto — l'aliquota
ordinaria della merce è lo **stadio A** del risolutore, ed è la domanda a cui
quel parametro risponde davvero. Qui è morto il lettore *sbagliato*.

### ✅ `S2` — i due flag sul soggetto

`soggetti_repository.py` (proiezione di `get_soggetto` + `_ALLOWED` di
`update_soggetto`), `views_soggetti.py` (serializer), `soggetti_service.py`
(guard `_valida_flag_fiscali`), `useSoggettoForm.js` (i due campi, default `'N'`),
`SoggettoDrawer.vue` (sezione «Dati fiscali», solo in edit).

⭐ **Il guard nel service non è ridondante rispetto al `CHECK` a DB**, ed è la cosa
che vale la pena non ri-discutere: `update_with_dedup` traduce **qualunque**
`IntegrityError` nel messaggio di duplicato, quindi senza guard un
`split_payment = 'Y'` sarebbe arrivato all'operatore come *«Codice fiscale o
partita IVA duplicata»* — un messaggio che afferma il falso su un campo che non
ha toccato. Il `CHECK` resta la difesa dura.

⚠️ **In creazione non si manda niente**, ed è voluto: le colonne hanno
`DEFAULT 'N'`, che è la direzione sicura — un soggetto di cui nessuno ha detto
nulla **non** è in scissione.

### ✅ `S3-a` — i tre codici sul contratto, in PATCH

Tre anelli + proiezione: `_UPDATE_KEYS_TESTATA`, `_build_update_data_testata`
(nuovo `_apply_codici_atto`), `_UPDATE_WRITE_COLS`, `_SELECT_COLS_CONTRATTO`;
`_CONTRATTO_PATCH_ALLOWED_BY_STATE["ATTIVO"]` per `Q1`. Lato FE
`ContrattoDrawer.vue`: `codiciAttoEditabili`, `mostraFooterSalva`,
`buildCodiciAttoPayload`, sezione «Riferimenti dell'atto» in edit.

⛔ **E qui il guardrail ha trovato un mio errore vero, che è il motivo per cui
esiste.** Avevo agganciato `_apply_codici_atto` al mapper di **CREATE** invece
che a quello di **UPDATE** — i due blocchi finali sono identici, e la sostituzione
ha preso il primo. `ContrattiCatenaUpdateTests` è diventato rosso con *«Nessun
campo aggiornabile presente nel payload»* su tutte e tre le chiavi.

⚠️ **Sarebbe stato invisibile**, ed è il caso peggiore: la PATCH avrebbe risposto
`200` senza scrivere (finché il payload portava altri campi, il guard «nessun
campo aggiornabile» non scatta), e la CREATE avrebbe spedito tre chiavi che
`fn_create_contratto` **scarta in silenzio**. Due difetti silenziosi da un solo
gesto. ⭐ *Il guardrail del 2026-07-27 ha ripreso esattamente il difetto per cui
era stato scritto, alla prima colonna aggiunta dopo.*

⚠️ **Il FE non allarga `isReadonly`**, e la scelta è deliberata: quel computed è
propagato via `provide` a **tutti** i figli, e allargarlo avrebbe sbloccato
righe, utility e pricing su un contratto attivo. L'eccezione di `Q1` resta una
condizione a sé, letta solo dai tre campi, dal footer e da `canSave`.

### ✅ `S4` — le due `reason_key`

`vendite.ordini.azione_reason.iva_mancante` e
`vendite.preventivi.azione_reason.iva_mancante`, in `it` e `en`.

⚠️ **Il testo dei preventivi non è una copia**: là il guard esclude le righe a
quantità zero (`preventivi_righe.quantita` è nullable e senza `CHECK` di
positività), quindi il messaggio dice *«righe con quantità»*. Un messaggio che
promette un perimetro più largo di quello vero manda l'operatore a cercare una
riga che il guard non ha guardato.

### ✅ `S5` — i nove codici errore senza policy (2026-08-29, dopo la Fase 2 DB)

> ⛔ **Voce non prevista da questo piano**, e due dei nove erano **un mio buco
> della Fase 1**. Trovata rispondendo alla domanda «cosa si è sbloccato con la
> Fase 2».

`api.md` §«Il cancello» è netto: *ogni codice che il DB può nominare deve avere
una policy*, e dal 2026-08-07 il registro del debito è a zero — quindi **un
codice nuovo senza policy è rosso il giorno stesso**. Lanciato il guardrail:
**rosso, nove codici**.

| Origine | Codici |
| --- | --- |
| **Fase 2 (`I7`)**, seminati dal team DB | `E_TITOLO_IVA_PLAFOND_MANCANTE`, `..._PLAFOND_NON_AMMESSO`, `..._AMBITO_NON_AMMESSO`, `..._AMBITO_SOVRAPPOSTO`, `..._UTILIZZATO_NEGATIVO`, `..._CONSUMO_NON_INVOCABILE`, `..._CONSUMO_FUORI_VALIDITA` |
| ⛔ **Fase 1 (`I9`)** — **mancati da me** | `E_ORDINE_RIGA_IVA_MANCANTE`, `E_PREV_RIGA_IVA_MANCANTE` |

⛔ **Perché li ho mancati, ed è la lezione**: della coda FE di `I9` avevo visto
**solo** il debito che il team DB aveva *scritto* nel brief — le due `reason_key`
i18n (`S4`). Un codice errore nuovo ha **due** code lato BE, non una:
`feedback_ripiego_ogni_codice_vivo` lo dice per esteso — *policy generata **E**
ripiego senza `%s`*. Ho seguito la richiesta invece della regola, ed è lo stesso
errore di metodo che il §0 rimprovera alla «Richiesta al BACKEND» del brief
madre: **ci si muove sul percorso, non sull'elenco che qualcun altro ha scritto**.

**Cosa è stato fatto:**

* `error_policies_generated.py` **rigenerato** con `manage.py genera_error_policies`
  (803 → 812 voci). ⚠️ Il file è generato e non si tocca a mano: la classe di un
  codice si cambia **a catalogo**. Le classi sono quelle già decise dal team DB
  nel CSV — `DATO_ERRATO` ×5, `TECNICO` ×2, `CONFLITTO_STATO` ×2;
* ⭐ **il diff è stato guardato prima di fidarsi**, per la regola «mai rigenerare
  col DB avanti rispetto a git»: conteneva **esattamente** i nove attesi e la
  riga di conteggio nell'header, niente altro. Se avesse portato un decimo
  codice, sarebbe stato un codice applicato al DB e non ancora in git — e il
  rigenerato lo avrebbe cementato senza che nessuno lo avesse letto;
* i **nove ripieghi** in `error_messages_fallback.py`, **senza segnaposto**: i
  messaggi a catalogo hanno tutti dei `%s`, e il ripiego serve proprio quando
  quegli argomenti non arrivano. ⭐ Per i due di `I9` la frase è **la stessa** del
  gemello `E_DDT_RIGA_IVA_MANCANTE`, adattata al documento: è la stessa regola su
  tre sedi, e tre frasi diverse la farebbero sembrare tre regole.

**Verifica:** guardrail `test_error_codes_db_policy_guardrail` **verde**,
`genera_error_policies --check` dice *«allineato al catalogo»*, suite backend
**4182 test OK** con `ZEROERP_TEST_DB_E2E=1` (24 in più della corsa senza E2E:
i test che parlano col DB prima non giravano).

### 🟡 `S3-b` — la CREATE, gated sul DB

⛔ **Non fatta, ed è una scelta.** `vendite.fn_create_contratto` ha una whitelist
interna (`v_testata_allowed`) che non conosce i tre codici e li **scarta in
silenzio**. Brief passato al team DB:
[brief-db-fn-create-contratto-codici-atto.md](brief-db-fn-create-contratto-codici-atto.md).

Il segnalibro è un test: `test_create_contratto_non_mappa_ancora_i_codici_atto`
asserisce oggi che le tre chiavi **non** sono in `_CREATE_KEYS_TESTATA`, e **si
inverte** quando il changeSet è applicato. Nel `ContrattoDrawer` la sezione è
sotto `v-if="isEdit"` per la stessa ragione.

### 🔎 Revisione critica del codice — 2026-08-29

> Richiesta di Tid a lavoro finito. Sei rilievi sul codice **appena scritto**,
> tutti corretti. ⭐ Il primo è una regressione dura che nessuna delle verifiche
> precedenti poteva vedere.

#### 🔴 R1 · `buildPayload()` rompeva la **creazione contratto**

`ContrattoDrawer.buildPayload()` non serve solo la PATCH: `handleSave` lo
**spreada** dentro il payload di CREATE (`...buildPayload()`). Avendoci messo i
tre riferimenti dell'atto nel ramo DRAFT, la create spediva `codice_cig`,
`codice_cup`, `codice_commessa` — e `crea_contratto` chiama
`validate_allowed_keys(payload, allowed=_CREATE_KEYS_TESTATA)`, che le chiavi
ignote **non le ignora: rifiuta l'intero payload**. Creare un contratto dal
drawer sarebbe fallito sempre, con *«Payload contratto non valido»*.

⛔ **Nessuna verifica lo avrebbe preso**: i 4158 test backend erano verdi, il
build FE pure, ed eslint non ha niente da dire su un oggetto ben formato. Il
difetto vive nel **giunto** fra il payload builder del FE e la whitelist del BE —
cioè in un punto che nessuno dei due lati collauda da solo.

**Corretto** con `if (isEdit.value) Object.assign(...)`, e — perché non basta
correggere — con due presidi:

* ⭐ un **guardrail BE nuovo**, `test_update_keys_accettate_anche_in_create_salvo_eccezioni`:
  rende esplicito l'invariante su cui il frontend si regge da sempre senza che
  fosse scritto da nessuna parte — *ogni chiave accettata in UPDATE dev'essere
  accettata anche in CREATE, o il drawer deve cancellarla*. Oggi l'eccezione è
  **una sola e dichiarata** (i tre codici, fino a `S3-b`); il test si accorge sia
  di una nuova eccezione non dichiarata, sia del momento in cui questa smette di
  servire;
* il commento in testa a `buildPayload` che **nomina la trappola**, invece di
  lasciarla implicita in uno spread trenta righe più sotto.

#### 🟠 R2 · Il validatore dei flag fiscali **mutava il payload del chiamante**

`_valida_flag_fiscali` scriveva `payload[key] = val.strip().upper()` su quello
che è `request.data` della view: un effetto collaterale che il nome «valida» non
annuncia (`feedback_estrarre_non_condividere_stato`), e che su un `QueryDict`
immutabile avrebbe **sollevato**. Ora è `_normalizza_flag_fiscali`, ritorna una
**copia**, e il nome dice quello che fa. Presidio: il test asserisce che il dict
originale resta intatto.

#### 🟠 R3 · Un flag assente diventava `'N'`, cioè **spegneva** lo split payment

In `SoggettoDrawer.populateFromDetail` avevo scritto `(data.split_payment || 'N')`,
e `handleSave` spediva sempre i due flag. Se una risposta non porta il campo, il
form dice `'N'` e il salvataggio **scrive** `'N'` su un soggetto che era `'S'`.

⭐ È la direzione sbagliata dello stesso errore che il travaso a DB aveva risolto
con `bool_or`: *omettere lo split payment è un errore fiscale, applicarlo in più
è un errore visibile*. Ora `?? null` («non lo so») e le chiavi si spediscono solo
se valorizzate: chiave assente = colonna non toccata.

#### 🟡 R4 · I tre nomi ripetuti quattro volte

`codice_cig`/`_cup`/`_commessa` comparivano in `_CODICI_ATTO_MAX_LEN`,
`_UPDATE_KEYS_TESTATA`, nella whitelist `ATTIVO` e in `_UPDATE_WRITE_COLS`. Le
prime tre stanno nello stesso modulo e ora **derivano** da `_CODICI_ATTO`.

⚠️ **`_UPDATE_WRITE_COLS` resta esplicita apposta**: è il **terzo anello**, e
`ContrattiCatenaUpdateTests` esiste per confrontare i tre anelli fra loro —
derivarla dallo stesso oggetto renderebbe il confronto vero *per costruzione*,
cioè spegnerebbe il guardrail invece di superarlo.

#### 🟡 R5 · Hardcode lato frontend

`['DRAFT', 'ATTIVO']` e i tre `maxlength` numerici erano cablati inline. Ora sono
`STATI_CODICI_ATTO_EDITABILI` e `CODICI_ATTO_MAX_LEN`, con il commento che dice
di cosa sono lo specchio (la whitelist per stato del BE e le colonne di
`vendite.contratti`). ⛔ **Non ho toccato i sette `'DRAFT'` preesistenti** dello
stesso file: sono l'idioma del componente e non sono roba di questo cantiere.

#### 🟡 R6 · Un'asserzione morta in un test mio

`assertFalse(hasattr(repo, "get_default_iva_id") and ...)`: su un `MagicMock`
`hasattr` è **sempre** vero, quindi la prima clausola era logica morta che
mascherava l'intenzione. Ora `repo.get_default_iva_id.assert_not_called()`.

#### ✅ Due sospetti verificati e caduti

* **le due guard DB sull'UPDATE di un contratto ATTIVO**
  (`trgfn_contratti_lock_post_attivazione`, `trgfn_contratti_guard_transizione_stato`)
  sono dichiarate `BEFORE UPDATE OF <colonne specifiche>` — pricing la prima,
  `stato_doc_contratto_id` la seconda: **non scattano** su una PATCH dei tre
  codici. `Q1` regge anche a livello DB, non solo di whitelist Python;
* il **dettaglio soggetto** passa da `SoggettiService.get_soggetto` →
  `SoggettiRepository.get_soggetto`, cioè dalla proiezione che ho esteso: il
  drawer i due flag li riceve davvero.

### Verifiche eseguite

| Cosa | Esito |
| --- | --- |
| `apps.anagrafiche.tests` | **430 test, OK** |
| `apps.vendite.tests` | **1754 test, OK** (2 skip preesistenti) |
| Suite backend intera (`apps`) | **4158 test, OK** (9 skip preesistenti) — rilanciata dopo la revisione critica |
| `scripts/check_i18n_keys.py` | **verde**, incluso *«nessuna chiave emessa dal DB risulta irrisolvibile»* — è la prova di `S4` |
| `npm run build` (frontend) | **OK** |
| `eslint` sui cinque file toccati | **pulito** |

⚠️ **Nessuna di queste verifiche tocca il DB vero.** I test Django sono su
repository mockati: provano la **catena Python**, non che la colonna esista. Le
prove sulla struttura sono i pgTAP già scritti e applicati dal team DB.

### Test adeguati, e perché non erano rattoppi

Sette test descrivevano un dominio che non esiste più. In tutti la **proprietà**
resta e cambia il **veicolo** — è la stessa forma dei due pgTAP adeguati dal team
DB il 2026-08-29:

* `test_clienti_repository`: `iva_id` → `modalita_pagamento_id` nei due test di
  whitelist; ⭐ il test *«stringa vuota → NULL»* portava `codice_cig`/`codice_cup`
  e ora porta `garanzia_tipo` — l'unico campo stringa rimasto in whitelist,
  quindi le due metà stanno in **due chiamate** invece che in due colonne;
* `test_clienti_service` e `test_clienti_api`: stesso scambio di veicolo.
  ⚠️ **Questi erano verdi**, e questa è la parte da guardare: mockano il
  repository, quindi la whitelist non passa di lì — asserivano che il service
  inoltra `iva_id`, cosa che il repository vero ora scarta. Un test verde che
  descrive un contratto morto;
* `test_vendite_form_defaults_service`: il dict del repo non porta più `iva_id`, e
  l'assenza delle tre chiavi nel payload è **asserita**.

**Presidi nuovi** (dal §5): creazione cliente **senza** `iva_id`; le sei chiavi
scartate in create e in update; i due flag fiscali sul soggetto (ok,
normalizzazione, valore ignoto → `E_ANAG_VALIDAZIONE`); i tre codici in `ATTIVO`,
stringa vuota → NULL, lunghezza eccessiva → errore parlante, `CESSATO` rifiuta,
e il segnalibro di `S3-b`.
| 2026-08-29 (revisione critica) | Su richiesta di Tid, rilettura del codice appena scritto. **Sei rilievi, tutti corretti** (§8). 🔴 Il primo è una **regressione dura**: `ContrattoDrawer.buildPayload()` è spreadato dentro il payload di CREATE, quindi le tre chiavi nuove arrivavano a un endpoint che `validate_allowed_keys` fa **rifiutare per intero** — la creazione contratto sarebbe fallita sempre. ⛔ **Nessuna verifica poteva vederlo**: vive nel giunto fra il payload builder del FE e la whitelist del BE, che nessuno dei due lati collauda da solo. Corretto, e reso visibile con un guardrail BE nuovo che dichiara l'invariante *«ogni chiave di UPDATE dev'essere accettata anche in CREATE»* e la sua unica eccezione, con scadenza a `S3-b`. 🟠 Altri due difetti silenziosi: un validatore che **mutava `request.data`**, e un flag assente che diventava `'N'` **spegnendo** lo split payment — la direzione sbagliata dello stesso errore che il travaso a DB aveva risolto con `bool_or`. 🟡 Poi de-duplicazione dei tre nomi, hardcode FE estratti, un'asserzione morta. ✅ Verificate e cadute due ipotesi: le guard DB su contratto ATTIVO sono `UPDATE OF`-scoped su altre colonne, e il dettaglio soggetto passa dalla proiezione estesa. Suite backend 4158 OK, i18n verde, build FE OK |
| 2026-08-29 (dopo la Fase 2 DB) | Il team DB applica la **Fase 2** (`I7`: `soggetti_titoli_iva`, ambiti, movimenti, RLS, guard, primitiva di consumo). Cercando cosa si fosse sbloccato lato BE/FE è saltato fuori che il **cancello dei codici errore era rosso**: nove codici che il DB può nominare senza policy — sette di `I7` e ⛔ **due di `I9` che avevo mancato io** in Fase 1, avendo letto il debito *scritto* nel brief (le due `reason_key`) invece della **regola** (`feedback_ripiego_ogni_codice_vivo`: policy **e** ripiego). Chiusa come slice `S5`. ⭐ `fn_create_contratto` **non** è stata estesa: `S3-b` resta gated. |

