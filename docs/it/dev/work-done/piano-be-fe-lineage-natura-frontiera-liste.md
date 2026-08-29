# Piano BE/FE — la natura della frontiera nelle liste documento

> **Cos'è.** Il piano di sviluppo **backend e frontend** che discende dal §3.5 di
> [brief-db-lineage-residui-root-e-sorgente-ddt.md](brief-db-lineage-residui-root-e-sorgente-ddt.md).
> Quel brief è del team DB e contiene le **decisioni** e i changeSet; questo
> contiene **che cosa si costruisce sopra**: repository, componente, liste,
> presidi.
>
> ⚠️ **Divisione delle sedi.** Una decisione di modello si aggiorna **solo** nel
> brief DB; un passo BE/FE **solo** qui. Se una decisione cambia, si cambia là e
> qui si riporta il passo che ne discende — mai il contrario.
>
> **Stato al 2026-08-29 — ✅ CHIUSO, meno una coda dichiarata.** Il DB ha
> consegnato tutto e **più di quanto chiesto**: oltre alla natura sulle sette
> viste di lista (`20260829-01`), il `20260829-02` ha portato nel grafo anche il
> **codice del tipo** (`tipo_codice_interno`, `frontiera_tipo_codice_interno`) e
> ha reso canonico il suffisso `_interno` sulle nature. BE e FE sono allineati,
> il chip dice la parola giusta, gli undici join scritti a mano sono diventati due.
> ✅ **E la coda di NOMI è chiusa in giornata** (§7-bis): i tre alias
> `natura_doc_codice` costruiti a mano nel BE sono passati al nome fedele — due
> da soli, il terzo **insieme al seed `ui.lista_colonna` id 494**, perché una
> metà sola svuotava la colonna a video.
>
> ⛔ **Restano solo il collaudo in app** (§6) e **15 voci di debito di naming** di
> altri domini, ora sorvegliate dal gemello Python del guardrail (§5).
>
> ⚠️ **E il rename aveva rotto tre cose vive**, trovate misurando e non
> aspettando un ticket: il pannello «Passaggi» di tutti e sette i domini, il
> filtro per natura della lista fatture (500 secco) e il Tag della natura su
> ogni riga di quella lista (sparito in silenzio). §1.5.
>
> **Correlati:**
> [vw_documento_lineage](/dbzero/vendite/views/vw_documento_lineage) ·
> [api_lineage_passaggi](/backend/vendite/manual/api_lineage_passaggi) ·
> [catalogo BB frontend](../frontend/catalogo-building-block-frontend.md)

---

## 0. In una pagina

| | Cosa | Dove |
| --- | --- | --- |
| ✅ **Fatto dal DB** | `20260828-22…25` (natura sulla summary, arco `U`, `rango_origine`, `COMMENT`) **e** `20260829-01/02`: natura + **codice del tipo** sulle sette viste di lista, suffisso `_interno` canonico | §1.1 · §2 |
| 🔴 **Rotture del rename, sanate** | Pannello «Passaggi» (7 domini), filtro natura lista fatture, Tag natura di riga: tutte e tre riparate e provate sul DB vero | §1.5 |
| ✅ **BE: fatto il 2026-08-29** | I sette repository fanno `SELECT v.*`: la colonna arriva **da sola** il giorno del DB-1. Restavano la **de-duplicazione** in `get_lineage_nodo` e la settima sorella nel registro del presidio: **entrambe chiuse**, 4142 test verdi | §3 |
| ✅ **FE: fatto** | `LineageFrontieraChip` usa `lineageDocumentoLabel`; le sei liste passano la natura e leggono i nomi nuovi; la lista fatture torna a mostrare il Tag. Build pulita, lint pulito, guard i18n pulito | §4 |
| ✅ **Il presidio si è ribaltato** | Il vecchio test pretendeva che ogni repository **decodificasse**; ora pretende che **nessuno ridecodifichi**, e il lato positivo sta nel pgTAP (test 40..46). Più un presidio nuovo sui `.vue` per la prop | §5 |
| ⛔ **Coda dichiarata** | §3.6 (il numero nudo `1`) e i tre alias `natura_doc_codice` non allineati — entrambi vogliono una decisione, non una toppa | §7 · §7-bis |

⭐ **La cosa non ovvia di questo cantiere**: il lavoro BE che il brief prevedeva
(*«sei repository: `v.frontiera_natura_doc_codice` nella `SELECT`»*) **non
esiste**, perché quei repository selezionano `v.*`. Il lavoro si è spostato
tutto in due punti diversi: un `CREATE OR REPLACE` in più al DB, e un presidio
che deve cambiare forma per continuare a presidiare.

---

## 1. Il terreno, misurato il 2026-08-28

> ⚠️ Misure come **fatto datato**, non come motivo: qui servono a dire cosa è
> già in piedi, non a decidere la forma del lavoro.

### 1.1 Il DB della voce 3 è applicato

`DATABASECHANGELOG` contiene `20260828-22`, `-23`, `-24`, `-25`, e
`information_schema` conferma `vendite.vw_documento_lineage.frontiera_natura_doc_codice`.

⚠️ **La riga di stato del brief DB dice ancora «Provati, NON applicati»**: è
stantia dal migrate. Non la correggo io — la sede di quella frase è il brief del
team DB (§8).

### 1.2 ⛔ E il pezzo che manca è ancora DB

Le viste di lista proiettano il lineage per **colonne esplicite**, non con
`lin.*`. Verificato su tutte e sette con `pg_get_viewdef`: quattro occorrenze
`frontiera_*` per vista, sempre le stesse quattro.

| vista | `frontiera_tipo_id` | `_codice` | `_stato_codice_interno` | `_fase` | **`_natura_doc_codice`** |
| --- | :-: | :-: | :-: | :-: | :-: |
| `vw_contratti_lista` | ✅ | ✅ | ✅ | ✅ | 🔴 |
| `vw_preventivi_lista` | ✅ | ✅ | ✅ | ✅ | 🔴 |
| `vw_offerte_commerciali_lista` | ✅ | ✅ | ✅ | ✅ | 🔴 |
| `vw_ordini_lista` | ✅ | ✅ | ✅ | ✅ | 🔴 |
| `vw_ddt_lista` | ✅ | ✅ | ✅ | ✅ | 🔴 |
| `vw_resi_lista` | ✅ | ✅ | ✅ | ✅ | 🔴 |
| `vw_fatture_lista` | ✅ | ✅ | ✅ | ✅ | 🔴 |

### 1.3 ⭐ Le sorelle sono SETTE, non sei — e la settima è già dentro per metà

Il brief dice «le sei `vw_*_lista`». Sul codice le liste documento che portano
il lineage sono **sette**: c'è anche `vendite.fatture` (`ui.lista_definizione`
id **48**, vista `vw_fatture_lista`).

| | sei | settima (`fatture`) |
| --- | --- | --- |
| colonne `frontiera_*` sulla vista | ✅ | ✅ |
| `SELECT v.*, s.codice_interno AS frontiera_tipo_codice` nel repository | ✅ | ✅ **c'è già** |
| `pratica_numero` / `fase` nella whitelist ORDER BY | ✅ | ✅ **c'è già** |
| colonna `transito` a catalogo (`ui.lista_colonna`) | ✅ (liste 4…9) | 🔴 **no** |
| `LineageFrontieraChip` montato nel `.vue` | ✅ | 🔴 **no** |
| dentro `_WHITELISTS` di `test_lineage_liste_be.py` | ✅ | 🔴 **no** |

⛔ **Non è «una lista che non c'entra»: è una lista dentro per metà e fuori dal
presidio.** Il repository fatture decodifica già `frontiera_tipo_codice` — cioè
paga già il costo — per un chip che oggi nessuno rende. Il giorno in cui qualcuno
aggiungerà la colonna «Transito» alla lista fatture, quel chip nascerà con
l'etichetta sbagliata: è **esattamente** il difetto del §3 del brief DB, in un
posto dove il presidio non guarda.

⭐ **Quindi la settima entra**, e per simmetria di modello, non perché costi poco
([[feedback_simmetria_modello_no_meta_scope]]): la colonna sulla vista e la riga
nel registro del presidio. Il chip e la colonna a catalogo **no** — quelli sono
una decisione di UI che non è di questo cantiere.

### 1.4 🟢 Quel che non serve fare, e va detto

* **Le chiavi i18n esistono tutte e due le lingue**: `vendite.lineage.natura_fattura`,
  `natura_nota_credito`, `natura_nota_debito` in `it.json` e `en.json`.
* **`lineageDocumentoLabel(t, te, tipo, natura)` esiste** in `lineageLabels.js` ed
  è già usata da `DocumentoCollegamentiBar` e da `LineagePassaggiContenuto`:
  cambia la **chiamata**, non la regola.
* **L'export delle liste non è toccato**: la colonna «Transito» ha
  `campo_sorgente = frontiera_codice`, quindi l'export scrive il codice grezzo e
  non passa da nessuna etichetta. Nessun punto di traduzione lì
  ([[feedback_bb_legge_non_trasporta]]: i punti che traducono si **cercano** —
  questo è stato cercato, ed è vuoto).
* **Il pannello «Passaggi» è già corretto**: `get_lineage_nodo` la natura della
  frontiera se la ricava da sé. È proprio il motivo per cui va de-duplicato (§3.1).
* **Le voci 1 e 2 del brief DB (rango e arco `U`) non hanno lavoro BE/FE**: la
  chiave i18n `vendite.lineage.tipo_ddt_vendita` c'è già, quindi una commessa che
  nasce da un DDT si rende senza toccare niente. Restano **due righe di collaudo** (§6).

### 1.5 🔴 Quello che il rename aveva rotto, e che nessuno aveva ancora visto

Il `20260829-02` ha rinominato `natura_doc_codice` → `natura_doc_codice_interno`
**anche dove il backend la leggeva**. Tre cose erano rotte sul database di
sviluppo, e due delle tre non c'entrano col lineage:

| # | Cosa | Sintomo | Sede |
| --- | --- | --- | --- |
| **R-1** | `get_lineage_nodo` leggeva `l.natura_doc_codice` e `l.frontiera_natura_doc_codice` | **500** sul pannello «Passaggi» di tutti e **sette** i domini | `vendite_repository` |
| **R-2** | `list_lineage_passaggi` leggeva `p.from/to_natura_doc_codice` da `fn_documento_lineage` | **500** sullo stesso pannello | `vendite_repository` |
| **R-3** | il filtro della lista fatture: `WHERE v.natura_doc_codice = %s` | **500** su ogni filtro per natura | `fatture_repository` |
| **R-4** | la lista fatture rendeva il Tag da `data.natura_doc_codice` | il Tag della natura **spariva da ogni riga**, senza errore | `FattureSearchTable.vue` |

⛔ **R-4 è la peggiore delle quattro**, ed è la ragione per cui vanno cercate e
non aspettate: le tre `500` qualcuno le segnala. Una colonna che smette di
comparire non la segnala nessuno — si guarda la lista e sembra che quelle
fatture una natura non ce l'abbiano.

⚠️ **E non è stata la suite a trovarle.** `get_lineage_nodo` è **mockato** in
tutti i test che lo toccano: i 4142 test erano verdi con il pannello a 500. Le
quattro sono uscite leggendo i nomi delle colonne dal database e ri-eseguendo
l'SQL **estratto dai file** ([[feedback_rinomina_db_binding_mockato]]).

---

## 2. ✅ DB-1 — consegnato, e più largo del richiesto

> **Destinatario: team DB, su `dev/db-tid`.** ⛔ Nessuna azione DB parte da qui
> ([[feedback_db_actions_passaggio_team]]), e il BE/FE **aspetta** questo punto
> prima di scrivere la riga che lo consuma ([[feedback_be_fe_attende_prerequisiti_db]]).
>
> ⭐ **Sede naturale: la coda del §3.4 del brief DB**, che questa richiesta la
> nomina già (*«Poi le sei `vw_*_lista` la portano avanti come già fanno con
> `frontiera_fase`»*). Non è un cantiere nuovo: è il pezzo di quella voce che il
> `20260828-22` non ha coperto.

> ✅ **Chiuso il 2026-08-29** con `20260829-01` (la natura sulle sette viste) e
> `20260829-02` (il **codice del tipo** nel grafo + il suffisso `_interno`
> canonico). Verificato colonna per colonna su `information_schema`, e il pgTAP
> `test-colonne-lineage-liste-v1.sql` le enumera per nome (test **31..46**).
> ⭐ La seconda parte non era in DB-1: è nata dalla richiesta di estrazione
> (§2-bis) e il team l'ha fatta **nello stesso giro**, che era esattamente il
> motivo per cui gliel'ho chiesta prima e non dopo.

**La richiesta era.** Un `CREATE OR REPLACE VIEW` per ciascuna delle **sette**
viste di lista, che porti avanti `lin.frontiera_natura_doc_codice` dalla summary,
esattamente come già porta `lin.frontiera_fase`.

**Le cose da non ripetere**, tutte già pagate una volta in questo stesso cantiere:

* ⚠️ **La colonna va in ULTIMA posizione.** `CREATE OR REPLACE VIEW` può solo
  **appendere**: metterla accanto alle sorelle `frontiera_*` significa
  `DROP … CASCADE`. È la stessa avvertenza del §3.4 del brief DB, e vale una
  seconda volta perché qui le viste sono sette.
* ⚠️ **`security_invoker=on` va ripetuto in ogni `CREATE OR REPLACE`.** È una
  reloption invisibile in `pg_get_viewdef`, e un replace che non la ripete la
  **azzera senza errori** — sette occasioni invece di una.
* ⚠️ **Il join al lineage resta `LEFT`**, come sulle sorelle: un documento senza
  genealogia compare senza genealogia, non sparisce.
* ⛔ **Niente da fare sul catalogo `ui.lista_colonna`**: la natura non è una
  colonna della lista, è un **attributo del chip** che la colonna `transito` già
  esistente rende. Nessun seed nuovo, nessun preset.

**Il presidio che si chiede insieme** (§5.1): un pgTAP che enumeri le sette
viste e pretenda la colonna su **tutte**, nella forma del pgTAP **13** (elenco
chiuso che fallisce apposta quando l'insieme cresce). ⛔ Non un test che itera su
`information_schema` filtrando `like 'vw_%_lista'`: quello resta verde
aggiungendo una vista che non ha la colonna — nell'elenco entra chi c'è, non chi
dovrebbe esserci.

⚠️ **Fino a DB-1 il §3 del brief resta a video sbagliato**, e non su un caso
limite: la colonna «Transito» della lista resi chiama «Fattura» **ogni** nota di
credito, perché il pgTAP 35 asserisce che l'arco `S` arriva sempre lì.

---

## 2-bis. ✅ L'estrazione — undici traduzioni scritte a mano, ora due

> **Chiesta il 2026-08-29 dopo l'ok di Tid, consegnata dal team DB in giornata.**
> ⭐ Dichiarata **prima** e non estratta di iniziativa
> ([[feedback_regola_del_2_estrai_bb]]).

**Il fatto.** Il grafo esponeva il tipo solo come **id**, e ogni consumatore che
voleva il codice si scriveva lo stesso `LEFT JOIN config.sorgenti`: **undici
volte** nel backend — sette repository di lista, due in `get_lineage_nodo`, due
in `list_lineage_passaggi`. ⚠️ *(Nel primo censimento avevo scritto «dieci»:
`get_lineage_nodo` ne aveva **due**, non uno — il tipo del nodo e quello della
frontiera.)*

**L'argomento non era il conteggio**, ed è il punto: nella **stessa vista** la
*natura* usciva già in chiaro come codice e il *tipo* no. Due attributi dello
stesso nodo, due convenzioni.

**Dopo.**

| | prima | dopo |
| --- | ---: | ---: |
| join a `config.sorgenti` nei 7 repository di lista | 7 | **0** |
| in `get_lineage_nodo` | 2 | **0** |
| in `list_lineage_passaggi` | 2 | **2** |

⚠️ **I due che restano non sono un residuo dimenticato**: `fn_documento_lineage`
espone `from_tipo_id`/`to_tipo_id` e **non** i codici, e quei due join servono
anche per `key_selector` (la traduzione uid → id di dominio). Finché la funzione
non porta i codici, lì il join è l'unico modo — ed è **una** sede, non sette.

---

## 3. Backend

> Nessuna rotta nuova, nessun contratto nuovo: `docs/it/dev/api.md` non cambia.
> Le liste rispondono già `v.*` dentro `paginated_envelope`, quindi il campo
> nuovo esce **da solo** il giorno del DB-1.

### 3.1 ✅ BE-1 · De-duplicare la natura della frontiera in `get_lineage_nodo`

> **Fatto il 2026-08-29.** Il join è sparito, la `SELECT` legge
> `l.frontiera_natura_doc_codice`. **Provato con una chiamata vera, non con un
> mock** ([[feedback_rinomina_db_binding_mockato]]): l'SQL **estratto dal file**
> ed eseguito in `BEGIN`/`ROLLBACK` in contesto operatore sul reso 24 risponde
> 25 colonne nell'ordine della mappa e `frontiera_natura_doc_codice =
> NOTA_CREDITO`. E il confronto fra le due strade su **tutto** il grafo — 439
> nodi, `IS DISTINCT FROM` e non `<>` — dà **0 divergenze** su **82** righe che
> una natura ce l'hanno davvero: il conteggio non è verde per sottrazione.

**Oggi** `VenditeRepository.get_lineage_nodo` si ricava
`frontiera_natura_doc_codice` con un join suo:

```sql
LEFT JOIN vendite.vw_documento_lineage_nodi nfr
       ON nfr.tipo_id = l.frontiera_tipo_id
      AND nfr.uid     = l.frontiera_uid
```

**Dal `20260828-22` quella stessa colonna è sulla vista**, e sono due copie della
stessa regola in due sedi. ⛔ **Si toglie la copia, non si sceglie la migliore**
([[feedback_duplicazione_nasconde_il_bug]]): il join sparisce e la `SELECT` legge
`l.frontiera_natura_doc_codice`.

⭐ **E non è cosmesi.** La vista risolve la frontiera dentro la sua CTE, con il
tie-break su `pipeline_rank`; il join del repository ricalcola la stessa cosa
dall'esterno. Finché coincidono nessuno se ne accorge; il giorno in cui la regola
della frontiera cambia in un solo posto, il pannello e le liste dicono due cose
diverse sullo **stesso** documento — e nessuna delle due dà errore.

⚠️ **Perimetro invariato**: `vw_documento_lineage` è `security_invoker` come
`vw_documento_lineage_nodi`, quindi togliere il join non allarga né stringe la
RLS. Da verificare esplicitamente in fase di esecuzione, non da dare per buono
([[feedback_rls_conteggio_zero_non_e_un_dato]]).

* File: [vendite_repository.py](../../../../backend/apps/vendite/db/vendite_repository.py) (`get_lineage_nodo`)
* Invariati: `types.py` (`LineageNodoRow.frontiera_natura_doc_codice` **c'è già**),
  `vendite_service.get_documento_passaggi`, `lineage_views.py`, il payload FE.

### 3.2 ✅ BE-2 · La settima sorella entra nel registro del presidio

> **Fatto il 2026-08-29.** `fatture_repository` è in `_WHITELISTS`; i tre test
> esistenti la coprono, verdi al primo giro.

`_WHITELISTS` in
[test_lineage_liste_be.py](../../../../backend/apps/vendite/tests/services/test_lineage_liste_be.py)
elenca sei repository. Entra `fatture_repository` (§1.3): i tre test esistenti la
coprono **senza scriverne uno nuovo**, che è la regola dichiarata in testa a quel
file.

⚠️ **Verificato prima di proporlo, non dopo**: `_ORDER_COLS_FATTURE` ha già
`pratica_numero` e `fase` e non ha `frontiera_codice`, quindi i test 1 e 2
passano; il repository ha già la decodifica, quindi passa il 3. L'aggiunta non
accende un rosso — chiude un buco.

⭐ **E il commento in testa al file va corretto**, perché dice «6 liste» e
diventerebbe la frase falsa che nessuno rilegge.

### 3.3 ⛔ Quel che il brief chiedeva e NON va fatto

Il §3.5.1 dice *«sei repository: `v.frontiera_natura_doc_codice` nella SELECT»*.
Tutti e sette fanno `SELECT v.*, s.codice_interno AS frontiera_tipo_codice`:
**la colonna arriva senza toccare niente**. Aggiungerla a mano sarebbe una
proiezione ridondante che duplica `v.*` e, il giorno di un rename a DB, l'unica
riga che si rompe.

⛔ **E soprattutto non si aggiunge un join nel BE**, la tentazione che il §3.2 del
brief nomina per rifiutarla: le viste di lista non espongono `frontiera_uid`, e
qualunque scorciatoia (join a `vendite.fatture` + `config.nature_doc_fiscale`
filtrando `frontiera_tipo_id = FATTURA`) è **il tipo cablato nel backend**,
moltiplicato per sette. [[feedback_no_quick_fix_soluzione_assoluta]].

---

## 4. Frontend

### 4.1 ✅ FE-1 · `LineageFrontieraChip`: la natura vince sul tipo

> **Fatto il 2026-08-29.**

Un prop e una chiamata, in
[LineageFrontieraChip.vue](../../../../frontend/src/vendite/_shared/lineage/LineageFrontieraChip.vue):

```diff
-import { lineageTipoLabel } from './lineageLabels'
+import { lineageDocumentoLabel } from './lineageLabels'

 defineProps({
   isTransitato: { type: Boolean, default: false },
   tipoCodice:   { type: String, default: null },
+  naturaCodice: { type: String, default: null },
   …
 })
```

⚠️ **Il gate resta su `isTransitato && tipoCodice`, e non si tocca.** La natura è
NULL su sette tipi di nodo su otto **ed è corretto**: metterla nel gate
spegnerebbe il chip su ogni documento non fiscale — cioè quasi tutti.

⭐ **La regola non si riscrive qui**: `lineageDocumentoLabel` è già la sede unica
(*la natura vince sul tipo quando c'è, anche quando dice «FATTURA»*), scritta il
2026-08-21 per questo identico motivo. Il chip smette di essere l'unico
consumatore di `lineageTipoLabel`, che resta esportata perché è il ramo di
fallback della funzione stessa.

### 4.2 ✅ FE-2 · Le sei liste passano il prop — tutte e sei

> **Fatto il 2026-08-29**, e con una riga in più per lista: il **tipo** cambia
> nome (`frontiera_tipo_codice` → `frontiera_tipo_codice_interno`), quindi le
> sei liste toccavano comunque quella riga. ⚠️ Senza il rename del tipo il chip
> sarebbe rimasto **muto** (il gate è su `tipoCodice`): la prop nuova da sola
> non bastava.

| lista | file |
| --- | --- |
| preventivi | [PreventiviList.vue](../../../../frontend/src/vendite/preventivi/components/PreventiviList.vue) |
| offerte | [OfferteSearchTable.vue](../../../../frontend/src/vendite/offerte/components/OfferteSearchTable.vue) |
| ordini | [OrdiniSearchTable.vue](../../../../frontend/src/vendite/ordini/components/OrdiniSearchTable.vue) |
| contratti | [ContrattiSearchTable.vue](../../../../frontend/src/vendite/components/ContrattiSearchTable.vue) |
| ddt | [DdtSearchTable.vue](../../../../frontend/src/vendite/ddt/components/DdtSearchTable.vue) |
| resi | [ResiSearchTable.vue](../../../../frontend/src/vendite/resi/components/ResiSearchTable.vue) |

```diff
 <LineageFrontieraChip :is-transitato="data.is_transitato" :tipo-codice="data.frontiera_tipo_codice"
+  :natura-codice="data.frontiera_natura_doc_codice"
   :codice="data.frontiera_codice" :stato="data.frontiera_stato_codice_interno"
   :fase="data.frontiera_fase" :n-attivi="data.n_discendenti_attivi" />
```

⛔ **Una prop dichiarata e non passata è un cancello che sembra esserci**
([[feedback_bb_legge_non_trasporta]]): la lista che se la dimentica continua a
scrivere «Fattura» e **non dà nessun errore**. È il motivo per cui FE-2 non è un
dettaglio di FE-1 ma un passo con un presidio suo (§5.2).

⚠️ **Nessun header di licenza da aggiungere**: sono file **modificati**, non
nuovi, e il cricchetto `scripts/check_license.py` guarda gli aggiunti.

---

## 5. I presidi — la parte che vale

### 5.1 P-1 · La colonna sulle sette viste (pgTAP, con DB-1)

Vedi §2. Elenco **chiuso** delle sette viste, non un `LIKE` su
`information_schema`.

### 5.2 ✅ P-2 · ⭐ Il gemello che non può essere lo stesso test

> **Fatto il 2026-08-29**, nella forma prevista qui: `LineageListeChipPropTests`
> deriva l'elenco da chi **monta** `LineageFrontieraChip` (`rglob` sui `.vue`,
> commenti esclusi) con un minimo dichiarato, e verifica **due** props — la
> natura e il nome nuovo del tipo.
> ⭐ **E il test 3 si è ribaltato**: pretendeva che ogni repository
> *decodificasse*; ora pretende che **nessuno ridecodifichi**. Il lato positivo
> — «la vista espone davvero la colonna» — non è scoperto: sta nel pgTAP
> `test-colonne-lineage-liste-v1.sql`, test **31..46**, dove può stare.
> ⚠️ L'assenza si asserisce sul pattern **esatto** rimosso (alias `v` compreso):
> `preventivi_repository` ha altri join legittimi a `config.sorgenti`, e un
> `assertNotIn("config.sorgenti")` li boccerebbe a caso.

Il brief chiede *«un test gemello di `test_ogni_lista_decodifica_il_tipo_della_frontiera`»*.
⛔ **Quel test non ha gemello possibile in quella forma**: legge il **sorgente
del repository** cercando `AS frontiera_tipo_codice`, e la natura nel sorgente
del repository **non compare** — arriva da `v.*`. Un test scritto per analogia
sarebbe rosso il primo giorno e verrebbe cancellato, oppure verde a vuoto.

Il presidio onesto guarda **dove la traduzione avviene davvero**, cioè il
frontend, e ha un precedente in casa: `apps/core/tests/test_liste_configurabili_seed.py`
legge già i `.vue` per presidiare il contratto di `<ListaConfigurabile>` (il
difetto dello slot `#actions`, 2026-08-24).

**Il test**, in `test_lineage_liste_be.py` accanto ai tre esistenti: per ognuna
delle sei liste che montano `LineageFrontieraChip`, il sorgente `.vue` deve
passare `:natura-codice="data.frontiera_natura_doc_codice"` sullo stesso tag.

⚠️ **E il registro delle sei liste dev'essere UNO.** Un secondo elenco scritto a
mano nel test è la trappola che quel file dichiara in testa: una lista nuova non
accende nessun rosso, la copertura sparisce in silenzio. L'elenco si deriva da
chi **monta** il componente (`rglob('*.vue')` + presenza di `LineageFrontieraChip`),
con un conteggio minimo dichiarato — così una lista nuova entra da sola e una
lista che smette di montarlo si vede.

### 5.3 P-3 · Cosa NON si presidia, e perché va scritto

* **La regola dell'etichetta** (`lineageDocumentoLabel`) non prende un test suo:
  non c'è runner FE (`package.json` ha `dev`/`build`/`lint`/`format`, nessun
  vitest). Introdurne uno è una decisione di stack, non un passo di questo piano
  — va nominata perché è il buco vero, non perché si chiuda qui.
* **La lista fatture** entra nel presidio BE ma **non** in P-2: non monta il chip.
  Se un giorno lo monterà, P-2 la prende da sola (§5.2, elenco derivato).

---

## 6. Collaudo in app

Ordine di esecuzione dei controlli, tutti in contesto operatore
([[feedback_rls_query_contesto_sistema]]: senza GUC le tabelle RLS appaiono
vuote e lo zero somiglia a un dato).

| # | Dove | Cosa deve dire |
| --- | --- | --- |
| **C-1** | lista **resi**, riga del reso 24 | `→ Nota di credito 1 · IN_CORSO` — **non** «Fattura». È il caso del §3.1 del brief |
| **C-2** | lista **ordini** | la riga misurata il 2026-08-26 (1 ordine con frontiera NC) dice «Nota di credito» |
| **C-3** | le altre quattro liste | nessuna regressione: dove la frontiera **non** è fiscale l'etichetta è quella di prima, non «—» |
| **C-4** | pannello «Passaggi» delle commesse **188** e **15370** | l'origine c'è: `n_sorgenti = 1`, root `DDT0000030` / `DDT0010839`. Non più la stringa `vendite.lineage.nessuna_origine` — **verifica dell'arco `U`, voce 2 del brief** |
| **C-5** | lista **DDT**, righe `DDT0000030` e `DDT0010839` | la colonna «Transito» mostra la commessa nata da lì |
| **C-6** | drawer di un documento qualsiasi | il pannello «Passaggi» dice **la stessa cosa** della lista sulla stessa frontiera — è la prova che BE-1 non ha spostato niente |

⚠️ **C-6 è il controllo di BE-1 e va fatto sullo stesso documento di C-1**: due
sedi che dicono la stessa cosa è il risultato atteso della de-duplicazione, e
l'unico modo di vederlo è guardarle insieme.

### 6-bis. Doc da allineare nel giro di FE-2

* [catalogo-building-block-frontend.md](../frontend/catalogo-building-block-frontend.md),
  riga di `LineageFrontieraChip`: dice *«sulle 5 liste
  (preventivi/offerte/ordini/contratti/ddt)»* — sono **sei** dal 2026-08-25
  (resi), e con FE-1 il chip cambia regola di etichetta. ⚠️ Si allinea **quando
  la regola cambia davvero**, non prima: un catalogo che descrive un componente
  che ancora non fa quella cosa è la stessa frase falsa di segno opposto.

---

## 7. ⛔ Fuori perimetro, e resta aperto

* **§3.6 del brief DB — il numero nudo.** A lavoro finito il chip dirà
  `→ Nota di credito 1 · IN_CORSO`: l'etichetta è giusta, **il codice resta `1`**
  perché `vw_documento_lineage_nodi` espone `fatture.numero` come `codice` del
  nodo. ⚠️ Non è un fix rimasto indietro: è la **decisione** *«qual è il codice
  parlante di una fattura, e chi lo possiede»* — oggi l'identità sono tre colonne
  (`anno`, `serie`, `numero`, tutte nullable) e le composizioni in giro per il
  progetto sono già sei. Comporne una settima dentro questo cantiere sarebbe il
  quick-fix che il progetto rifiuta.
  ✅ **La metà «chi lo possiede» è DECISA da Tid il 2026-08-29: UNA SOLA SEDE.**
  ⛔ Resta aperta l'altra metà — **quale** sede (colonna generata, funzione,
  vista) e **quale forma** — e con lei la bonifica delle sei composizioni
  esistenti, che è il lavoro vero. Non è di questo cantiere: vuole un brief suo.
  ⚠️ E la decisione presa **vincola già da adesso**: nessuno dei passi qui sotto
  può comporre un codice fattura per conto proprio, nemmeno «solo per il chip».
* **La colonna «Transito» sulla lista fatture** (§1.3): oggi non c'è. Aggiungerla
  è una scelta di UI, non un passo di questo piano.
* **Il gemello `ATTIVITA_CONSUMI`** (§2.4-ter del brief DB): prima di un arco
  servirebbe un **nodo**. Altro cantiere.
* **Un runner di test frontend** (§5.3): buco reale, decisione di stack.

---

## 7-bis. ⛔ La coda dei NOMI, e perché non l'ho chiusa da solo

Il `20260829-02` ha reso canonico il suffisso `_interno` per un codice che viene
da `codice_interno`. Ma **tre** posti nel backend costruiscono `natura_doc_codice`
con un alias **scritto a mano** su `config.nature_doc_fiscale`, e il rename non
li ha toccati perché non leggono nessuna vista:

| dove | alimenta | rotto oggi? |
| --- | --- | --- |
| `list_lotto_fatture` | drawer del lotto + lista `vendite.lotto_fatture` (id 45) | **no** |
| `get_fattura_testata` | drawer fattura | **no** |
| `_legame_rettifiche` | legami di rettifica, interno | **no** |

⭐ **E questo risponde alla domanda che il team DB ha girato a noi**: la colonna
`ui.lista_colonna` **id 494** (`campo_sorgente = 'natura_doc_codice'`, `vista_sql`
NULL) **non** è rotta, perché quel payload prende il nome dal proprio alias e non
da una vista rinominata. Verificato leggendo la query, non per esclusione.

⛔ **Ma restano due nomi per la stessa cosa**, ed è il difetto che tutto questo
cantiere esiste per togliere. Allinearli è giusto e **non lo posso fare da solo**:
il rename dell'alias di `list_lotto_fatture` richiede che il seed della colonna
494 cambi nello stesso giro, altrimenti la colonna «Natura» del drawer lotto
diventa vuota — cioè esattamente il difetto silenzioso che stiamo chiudendo, ma
causato da noi.

**Quindi**: un giro corto BE + un seed DB, insieme. Non una toppa da una parte
sola ([[feedback_no_quick_fix_soluzione_assoluta]]).

> ✅ **2026-08-29 — due delle tre sono chiuse.** `get_fattura_testata` e
> `_legame_rettifiche` sono passate a `natura_doc_codice_interno` insieme al loro
> consumatore (`FatturaDrawer`): lì **nessun seed le legava**, ed era la
> distinzione che serviva fare — non «le tre insieme», ma «quelle che si possono
> muovere da sole».
> ✅ **E il 2026-08-29 anche la terza**, `list_lotto_fatture`, **con le due metà
> insieme**: il seed dal team DB, l'alias e il frontend da qui. La coda dei nomi
> è chiusa.

---

## 8. Code lasciate al team DB

| | Cosa | Perché non la chiudo io |
| --- | --- | --- |
| ✅ **D-1** | **DB-1** (§2): la colonna sulle sette viste di lista + il pgTAP | **Chiuso il 2026-08-29** (`20260829-01`), e insieme è arrivata l'estrazione del §2-bis (`20260829-02`) |
| ✅ **D-2 / D-3** | Riga di stato stantia e «sei viste» invece di sette nel brief DB | Chiusi dal team nella stessa ondata |
| 🔴 **D-4** | Il seed `ui.lista_colonna` **id 494** (lista 45, `vendite.lotto_fatture`), se si allinea l'alias `natura_doc_codice` → `_interno` | §7-bis: è un giro **BE + seed insieme**. Da solo, uno dei due lati spegne la colonna «Natura» del drawer lotto |
| ✅ **D-6** | Il seed `ui.lista_colonna` **id 494** + l'alias nel BE | **Chiusa il 2026-08-29**: seed dal team DB (`6325a8d98`), alias e frontend da qui, nello stesso giro |
| 🟡 **D-5** | `fn_documento_lineage` espone `from_tipo_id`/`to_tipo_id` e non i codici: sono i **due** join sopravvissuti all'estrazione | §2-bis. Non urgente e non un difetto: una sede sola, non sette. Da valutare quando quella funzione si riapre |

---

## 9. Ordine di esecuzione

```
DB-1 ─────────────────────────────┐   (team DB, dev/db-tid)
                                  ▼
BE-1 (de-dup) ── BE-2 (registro) ── FE-1 (prop) ── FE-2 (sei liste) ── P-2 ── collaudo
        ▲                    ▲
        └── indipendenti da DB-1: si possono fare subito
```

* ✅ **BE-1** e **BE-2** non dipendevano da DB-1 e sono **chiuse il 2026-08-29**:
  la summary la colonna ce l'aveva già, e il registro del presidio è codice di test.
* **FE-1** si può scrivere prima di DB-1 (il prop nasce con default `null` e il
  chip si comporta come oggi), ma **non serve a niente finché il dato non
  arriva**: senza DB-1 `data.frontiera_natura_doc_codice` è `undefined` su tutte
  le righe, e il chip resta identico. ⚠️ Ed è la forma peggiore di verde: tutto
  scritto, tutto passante, niente cambiato a video.
* ✅ **FE-1, FE-2 e P-2 chiusi il 2026-08-29**, appena DB-1 è entrato nel repo.
  Resta il solo **collaudo in app** (§6), che è l'unica cosa che non si fa da
  qui.

⭐ **È andata così**, ed è la ragione per cui l'ordine valeva la pena di
scriverlo: BE-1 e BE-2 il 28, DB-1 consegnato la sera, tutto il resto il 29 in un
giro solo. ⚠️ Con la sorpresa del §1.5 in mezzo: il DB ha consegnato **più** di
quanto chiesto, e il di più era un **rename** — cioè lavoro non previsto e non
rimandabile.

---

## 10. Registro

### 2026-08-28 · Stesura

Piano scritto dal §3.5 del brief DB, con il terreno **misurato sul codice e sul
database vivo**, non sui documenti.

⭐ **Tre cose che il brief non poteva sapere e che cambiano il piano:**

1. **I quattro changeSet sono applicati** (§1.1), mentre il brief li dà «provati,
   non applicati». Il BE/FE non aspetta più il migrate — aspetta un pezzo diverso.
2. **Il pezzo che manca è ancora DB** (§1.2): la colonna sta sulla summary e non
   sulle sette viste di lista, che proiettano quattro colonne `frontiera_*`
   esplicite. Il §3.5.1 del brief — *«sei repository: la colonna nella SELECT»* —
   **non ha lavoro dentro**: i repository fanno `SELECT v.*`.
3. **Le sorelle sono sette** (§1.3), e la settima è dentro per metà: il
   repository fatture decodifica già il tipo della frontiera per un chip che
   nessuno rende, e sta fuori dal registro del presidio.

⛔ **E il gemello del presidio richiesto non esiste nella forma richiesta**
(§5.2): il test esistente legge il sorgente del repository, e lì la natura non
compare. Il presidio si sposta dove la traduzione avviene — i `.vue` — con un
precedente già in casa.

**Nessun file di codice scritto, nessuna migrazione, nessuna decisione presa.**

### 2026-08-29 · BE-1 e BE-2 chiuse, e DB-1 consegnato

**Scritte le due cose che non dipendono dal DB.** `get_lineage_nodo` non
ricalcola più la natura della frontiera con un join suo (BE-1) e
`fatture_repository` è entrata nel registro del presidio delle liste (BE-2).
**Suite intera: 4142 test verdi, 9 skip, zero regressioni.**

⭐ **La prova di BE-1 non è la suite**, ed è il punto: quel metodo è **mockato**
in tutti e quindici i test che lo toccano, quindi un SQL rotto sarebbe passato
verde ([[feedback_rinomina_db_binding_mockato]]). L'SQL è stato **estratto dal
file** ed eseguito sul database vivo in contesto operatore — 25 colonne
nell'ordine della mappa, `NOTA_CREDITO` sul reso 24 — e le due strade sono state
confrontate su tutti i **439** nodi del grafo: **0 divergenze**, su **82** righe
con una natura non nulla. ⚠️ `IS DISTINCT FROM` e non `<>`: la natura è NULL su
sette tipi di nodo su otto, e con `<>` quelle righe non sarebbero mai entrate nel
conteggio — il test sarebbe stato verde anche se la colonna non avesse funzionato.

⚠️ **E la stessa corsa ha ri-mostrato il §3.6**: sul reso 24 `frontiera_codice`
vale **`1`**. L'etichetta si sistema con FE-1, il numero nudo no — resta la
decisione aperta del §7.

**DB-1 consegnato al team DB** (§2): la colonna sulle sette viste di lista, il
pgTAP nella sua sede naturale — `db/pgtap/vendite/test-colonne-lineage-liste-v1.sql`,
i test 1..18 — e le due note di stato sul brief madre.

### 2026-08-29 · Il DB consegna più del richiesto, e il cantiere si chiude

**Il team DB ha fatto DB-1 e l'estrazione nello stesso giro** (`20260829-01/02`),
più il rename che rende canonico il suffisso `_interno`. Fast-forward su
`Tito-dev`, e poi tutto il resto del piano in una sessione.

🔴 **La prima cosa trovata non era nel piano: il rename aveva rotto quattro
cose** (§1.5) — il pannello «Passaggi» di tutti e sette i domini, il filtro per
natura della lista fatture, e il Tag della natura su **ogni riga** di quella
lista. ⚠️ **La suite era verde su tutte e quattro**: `get_lineage_nodo` è
mockato, e un SQL rotto lì non lo vede nessun test. Sono uscite leggendo i nomi
delle colonne dal database e ri-eseguendo l'SQL **estratto dai file**
([[feedback_rinomina_db_binding_mockato]]).
⛔ E la quarta è la più cattiva delle quattro: le tre `500` qualcuno le segnala,
una colonna che smette di comparire no.

**Fatto**: le quattro riparazioni · l'estrazione lato BE (**undici** join
scritti a mano → **due**, e i due che restano sono dichiarati e motivati) · FE-1 e FE-2 ·
il presidio ribaltato + quello nuovo sui `.vue` · i due cataloghi BB.

**Provato**: **4144 test verdi**, 9 skip, zero regressioni · build frontend
pulita · `eslint` pulito sugli otto file toccati · `check_i18n_keys.py` pulito ·
e — la parte che conta — **le sette liste e le due query del pannello eseguite
sul database vero** in contesto operatore, non mockate: le sette viste portano
entrambe le colonne nuove, il pannello risponde `NOTA_CREDITO` sul reso 24, e il
filtro per natura della lista fatture pianifica invece di dare 500.

⭐ **La lezione del giro, ed è sui NOMI**: un rename lato DB non rompe solo chi
legge quella colonna — rompe **due specie diverse** di consumatore, e solo la
prima fa rumore. Chi la legge in una `WHERE` dà 500; chi la legge in una cella
smette di disegnare. La seconda si trova solo cercandola.

**Resta**: il collaudo in app (§6), la coda dei nomi (§7-bis, vuole un seed DB) e
la decisione del §3.6 sul codice parlante della fattura — per cui Tid ha già
deciso la metà che conta: **una sola sede**.

### 2026-08-29 · Rilettura critica del codice appena scritto

Su richiesta di Tid, riletto **il mio stesso diff** cercando i difetti e non le
conferme. **Sette**, e sei non davano nessun errore.

| # | Difetto | Perché non si vedeva |
| --- | --- | --- |
| **1** | Il presidio ribaltato cercava le stringhe nel sorgente **commenti compresi** | ⛔ E i repository di lista hanno, **in commento**, la storia del join rimosso: bastava scriverla per esteso e il test diventava rosso per la prosa. È **già successo** in questo repo il 2026-08-26 su `test_liste_configurabili_seed` |
| **2** | `assertNotIn("AS frontiera_tipo_codice\n")` — ancorato al fine riga | Una regressione si riscrive quasi sempre con la **virgola**: `AS frontiera_tipo_codice,`. Sarebbe passata. **Provato**: la mutazione con virgola era verde prima, rossa dopo |
| **3** | `_MIN_LISTE = 6` scritto a mano | Numero magico che invecchia in silenzio. Ora le liste attese si derivano dal **seed** (`ui.lista_colonna`, chi dichiara «transito»), e il presidio prende anche il verso opposto: colonna a catalogo e chip non montato |
| **4** | `assertIn("<LineageFrontieraChip")` | ⛔ **Trovato dalla prova di mutazione, non dalla rilettura**: la sottostringa dice di sì anche a `<LineageFrontieraChipV2>`, cioè a un componente diverso con un contratto di props diverso |
| **5** | `_vue_per_lista()` con `mappa[codice] = file` | Due componenti che montano la stessa lista → **l'ultimo vince in silenzio** e il presidio ne guarda uno a caso. Ora li tiene tutti e li verifica tutti |
| **6** | `lineageTipoLabel` restava **esportata** senza più nessun consumatore | ⛔ È la funzione che scriveva «Fattura» su una nota di credito: lasciarla esportata è un grilletto carico: la porta da cui il difetto rientra. Non è più esportata — resta il ramo di ripiego della sorella |
| **7** | L'header del file di test mentiva in **tre** punti | Nome del test 4 sbagliato nell'indice, `Scopo` che diceva ancora «decodifica» (l'opposto di ciò che il test fa ora), nota sull'estrazione superata dai fatti |

⭐ **E una che NON era un difetto, verificata invece che assunta.** Togliendo da
`get_lineage_nodo` la `JOIN` (INNER) a `config.sorgenti` è sparito un filtro, e
il Python fa `str(row[1])`: su un NULL avrebbe prodotto la **stringa `"None"`**.
Non succede, e la ragione è **strutturale e non statistica**:
`vw_documento_lineage` legge `FROM vw_documento_lineage_nodi`, e la vista nodi
costruisce ogni ramo con una `JOIN sorgenti` **interna** — un nodo senza
sorgente attiva non esiste proprio. La garanzia non è sparita col join: si è
**spostata**, ed è scritta in un commento perché il prossimo lettore non la
trovi da solo.

#### La prova: sei mutazioni, e una ha trovato un buco

I due presidi sono stati rotti apposta, uno alla volta:

| mutazione | atteso | esito |
| --- | --- | --- |
| tolgo la prop natura da una lista | 🔴 | 🔴 |
| una lista perde il blocco del chip | 🔴 | 🔴 |
| `<LineageFrontieraChipV2>` al posto del chip | 🔴 | 🔴 (dopo il fix **4**) |
| il tipo torna al nome vecchio | 🔴 | 🔴 |
| rimetto il join con spaziatura diversa | 🔴 | 🔴 |
| **un commento che cita il join rimosso** | 🟢 | 🟢 (dopo il fix **1**) |

⛔ **La terza riga è il punto**: la prima volta era **verde**, e il difetto non
era nel codice sotto test ma **nel test appena scritto**. *Un presidio si
verifica rompendolo, non rileggendolo* — la rilettura mi aveva fatto trovare sei
difetti su sette, il settimo l'ha trovato la mutazione.

**Verificato dopo i sette fix**: 4168 test, tutti verdi · build frontend pulita ·
`eslint` pulito · `check_i18n_keys.py` pulito · e l'SQL del pannello
**ri-eseguito sul database vero**, perché i commenti che ho aggiunto stanno
*dentro* la stringa della query e un `--` fuori posto non lo vede nessun test.

### 2026-08-29 (2) · Il nome fedele arriva al payload, e nasce il cancello che mancava

**Segnalato dal team DB** (§3-ter.5 del brief), e la segnalazione era giusta:
dopo il `20260829-02` lo stesso valore aveva **due nomi** a seconda
dell'endpoint. Le sette liste fedeli end-to-end, il drawer «Passaggi» che
leggeva la colonna fedele e la **ri-aliasava al nome vecchio in Python**.

⛔ **La mia difesa del giorno prima era sbagliata a metà.** Avevo scritto che
pannello e liste chiamano le cose in modo diverso perché sono *due trasporti
diversi*, e la parte sul **prefisso** regge (il payload annida, quindi
`frontiera.tipo_codice` invece di `frontiera_tipo_codice`). Ma il **suffisso**
non è trasporto: `_codice` contro `_codice_interno` è un nome diverso per lo
stesso genere di valore — e quel valore il FE lo usa come **logica**, per la
chiave i18n e per instradare. ⭐ La prova sta nello stesso payload: lo **stato**
diceva già `stato_codice_interno`. Non due regole: **una regola applicata a
metà**.

**Fatto**: ri-aliasature via, nome fedele fino al payload, `types.py`, service,
i due `.vue`, e la doc API con la nota BREAKING. Il nome della **rotta** non
cambia: si tocca ciò che il BE espone, non ciò che riceve.

⛔ **E il buco era più grande della voce.** Applicando le tre regex del
guardrail SQL ai file Python del backend: **25** violazioni in sette file, non
7. La voce segnalava un caso; sotto c'era una famiglia — che è la conferma che
la sede è quella. Perché il guardrail CI (`check_naming_stato_codice.sql`)
scansiona `pg_views`/`pg_matviews`/`pg_proc`: **l'SQL scritto in Python non lo
vede nessuno**.

**Quindi non ho chiuso solo il caso: ho costruito il gemello mancante.**
`apps/core/tests/test_naming_codice_interno_python.py` trascrive le tre regole e
le applica ai repository. Le **18** residue entrano in un **registro del debito
che deve calare**, chiavato su *(file, alias)* e **non** sul numero di riga — una
riga che si sposta farebbe rosso per il motivo sbagliato, e un presidio che
boccia a caso viene spento ([[feedback_whitelist_dal_percorso_reale]]).

⚠️ **Provato rompendolo**: alias nuovo → rosso; voce del registro sanata e non
tolta → rosso; **commento** che cita un alias → verde. E la copia locale dello
spogliatore di commenti, nata un'ora prima, è morta subito: la terza occorrenza
ha trovato **una sede** invece di diventare la terza copia.

**Verificato**: 4170 test verdi · build e lint puliti · guard i18n pulito · e le
due query del pannello **eseguite sul database vero**, che ora rispondono
`tipo_codice_interno` / `frontiera_natura_doc_codice_interno`.

⭐ **E il §3.6 l'ha chiuso il DB nello stesso giro**: `fn_numero_documento_fattura`
e il nodo che la legge. Verificato: il nodo fattura ora dice **`103 - VX2`**,
cioè esattamente la forma decisa da Tid. Il BE/FE non ha dovuto toccare niente —
il codice viaggia già come `codice` del nodo.

### 2026-08-29 (3) · La bonifica: tre schermate smettono di comporre

**L'ultimo pezzo del §3.6**, e la seconda metà della decisione di Tid: la sede
unica esisteva (`fn_numero_documento_fattura`, `20260829-15`) ma **tre schermate
componevano ancora per conto loro**, in tre modi diversi e nessuno dei tre era
quello deciso.

| dove | prima | ora |
| --- | --- | --- |
| `FatturaDrawer` | `serie numero/anno` → `VX2 103/2026` | `103 - VX2` dalla sede unica |
| `LottoDrawer` | `serie numero` → `VX2 103` | idem |
| `DashboardCompetenzaView` | `serie numero/anno` | idem |

**Quattro payload BE** portano ora il numero composto — `get_fattura_testata`,
`_legame_rettifiche`, `list_lotto_fatture`, `list_dash_competenza_errori` — e
lo leggono dalla **funzione DB**, non ricomponendolo.
⚠️ **`list_dash_competenza_attivita` NO, di proposito**: spedisce anche lui
`fattura_serie`/`numero`, ma **nessuno lo compone**. Aggiungere un campo che
nessuno legge è la definizione di «per completezza», che il team DB ha
esplicitamente escluso.
⭐ E il **ripiego resta al frontend**: il DB risponde NULL sul non-numerato, e
chi rende sceglie la frase — «non numerata» nel drawer fattura, un trattino
altrove. Un placeholder scritto a DB avrebbe tolto la scelta a entrambi.

#### ⛔ Due difetti trovati scrivendo, e nessuno dei due dava errore

**1 · Le colonne mappate per INDICE.** `list_lotto_fatture` e
`list_dash_competenza_errori` costruiscono il dict con `row[0]`, `row[1]`…:
inserire una colonna in mezzo **sposta tutto quello che segue di una casella**.
Nessun errore — solo la data nel campo del billing account e il totale in quello
del soggetto. Corretti gli indici e, ⚠️ **una riga fuori dal dict** che il primo
giro aveva mancato: `errore_meta = jsonb_out(row[22])`, che stava *prima* del
blocco e non era stata spostata.
⭐ **Provato eseguendo davvero i due metodi** contro il database, in transazione
annullata, e guardando *dove atterrano i valori*: `numero_documento` = `7 - R2`
accanto a `numero` 7, `serie` R2, `data` 2026-08-17. Contare le colonne a mano
non è una prova.

**2 · Codice morto in `vendite_repository`** (non mio, verificato in `HEAD` e
prima del mio primo commit): dentro `get_registro_codice`, **dopo un `return`
incondizionato**, ci sono ~100 righe irraggiungibili che duplicano il corpo di
`list_dash_competenza_errori`. ⚠️ **Mi ha quasi fatto scrivere nel ramo morto**:
la stringa che cercavo compariva due volte, e l'asserzione «una sola occorrenza»
ha fermato la sostituzione. Da lì in poi l'ho ancorata alla firma del metodo
vivo.

> ✅ **Rimosso su ok di Tid, 2026-08-29**: **103 righe**. I confini presi per
> **contenuto** e non per numero di riga, il commento `Scopo:` del metodo
> successivo preservato (stava dentro l'intervallo ma non era morto), e il
> metodo vivo gemello ri-eseguito **contro il database** dopo la cancellazione.
> ⭐ **E poi la domanda che conta: ce ne sono altri?** Cercati con l'AST su tutto
> `backend/apps` — istruzioni che seguono un `return`/`raise`/`continue`
> incondizionato nello stesso blocco: **zero**. Quello era l'unico, e adesso è
> un fatto misurato invece di una speranza.
> ⚠️ Perché la ricerca valeva la pena: il codice morto non è «brutto», è
> **pericoloso in un modo specifico** — duplica un metodo vivo, quindi chi cerca
> una stringa la trova due volte e può correggere la copia sbagliata. È
> esattamente quello che stava per succedere qui.

#### Il registro del debito ha imparato a calare

Chiavato su *(file, alias)* non vedeva che avevo sanato **2 occorrenze su 3**
nello stesso file: la voce restava «viva» e il debito sembrava fermo. Ora conta
le **occorrenze**, e i due test dicono due cose diverse — *non cresce* e *si
aggiorna quando cala*. ⚠️ Provato rompendolo in tre modi: alias nuovo → rosso;
una occorrenza in più su una voce nota → rosso; **una sanata su due** → rosso,
che era il caso cieco.

**Verificato**: 4170 test verdi · build e lint puliti · guard i18n pulito · e i
quattro payload **eseguiti davvero** sul database (`103 - VX2` sulla numerata,
`None` sulla non numerata, `11 - R2` su un legame di rettifica reale).

### 2026-08-29 (4) · La coda dei nomi si chiude, e il cancello si accende da solo

Il team DB ha fatto la sua metà di D-6 (`6325a8d98`): `ui.lista_colonna` id 494,
`campo_sorgente` → `natura_doc_codice_interno`. ⚠️ **Applicata già sul DB di
sviluppo**, quindi in quel momento la colonna «Natura» del drawer lotto era
**rotta**: il catalogo chiedeva un nome che il payload non portava — e non lo
dice nessuno, la colonna esce vuota.

**Fatta la metà BE nello stesso giro**: alias in `list_lotto_fatture`, chiave del
dict, `LottoFattureRow`, e il `Tag` in `LottoDrawer`.

⭐ **E il cancello scritto ieri si è acceso da solo**, che è la prima volta che
serve davvero: togliendo l'ultimo `natura_doc_codice` il debito è calato e
`test_il_registro_si_aggiorna_quando_il_debito_cala` è diventato **rosso**,
chiedendo di aggiornare il registro. È esattamente il caso cieco che la versione
a soli insiemi non vedeva, e per cui era stato riscritto a conteggi poche ore
prima. Registro: da **16 occorrenze in 13 punti** a **15 in 12**.
⛔ La voce è stata **tolta**, non messa a zero: un registro che tiene gli zeri è
un elenco di eccezioni con l'aria di un debito.

⭐ **La prova non è «il test è verde», ed è il punto**: ho verificato che
**catalogo e payload tornino a dire la stessa cosa** — `ui.lista_colonna` id 494
chiede `natura_doc_codice_interno`, e il payload di `list_lotto_fatture` porta
quella chiave con dentro `FATTURA`. Il contratto rotto era quello, non un test.

**Verificato**: 4170 test verdi · il presidio seed↔whitelist (che legge il CSV
cambiato) verde · guard i18n verde — ⭐ e regge perché il team DB ha lasciato
stare `codice` e `etichetta_i18n_key`: la seconda è una chiave i18n, non un nome
di colonna, e rinominarla avrebbe rotto la traduzione per allineare una cosa che
non c'entrava · build e lint puliti.

### 2026-08-29 (5) · Rilettura critica del secondo giro

Su richiesta di Tid, riletto il diff di giornata. **Sei cose**, e la più
importante non è un difetto ma una **classe** di difetto.

| # | Cosa | Perché contava |
| --- | --- | --- |
| **1** | `list_lotto_fatture` mappava le colonne **per indice** | ⛔ Non ho corretto solo l'istanza: il metodo è passato all'**accesso per nome** (`rows_to_list`, che è già l'idioma di quel file). Inserire una colonna non può più spostare niente. È il difetto su cui ero già inciampato una volta oggi, e una riga (`errore_meta`) era sfuggita persino alla correzione |
| **2** | `list_dash_competenza_errori` mappa ancora per indice | Non convertibile allo stesso prezzo: passa da `_query_paged_view`, un helper **condiviso** con otto chiamanti. ⭐ **Dichiarato dove morde**, con scritto cosa succede a chi tocca la SELECT — non è la stessa cosa che averlo risolto, ed è meglio che lasciarlo muto |
| **3** | «Sede UNICA del formato» scritto sopra una funzione che **non lo è più** | Il commento di `numeroDocumento` in `FatturaDrawer` rivendicava un ruolo passato al database. ⛔ Un commento che dice il falso su *dove sta una regola* è peggio di nessun commento: manda la prossima modifica nel posto sbagliato |
| **4** | Altri due commenti stantii | «serie, numero e anno» nei legami; «l'etichetta a video la compone il FE» nel drawer lotto — dove il FE non compone più niente |
| **5** | Le tre regex del gemello Python **potevano divergere** dal guardrail SQL | Le due trascrizioni della stessa regola sono il difetto che questo cantiere ha passato tre giorni a togliere, e io ne avevo appena create due. Ora un test **rilegge il file SQL** e pretende che le tre righe siano ancora quelle: se la regola cambia di là, questo file diventa rosso invece di presidiare una regola che non esiste più |
| **6** | La sostituzione «per conteggio» stava per colpire di nuovo | `rows = cursor.fetchall()` compare **due volte** con lo stesso contorno. L'assert l'ha fermata, e la sostituzione è stata **ancorata alla firma del metodo** — la stessa lezione del codice morto, imparata due volte in un giorno |

⭐ **La differenza fra il primo e il secondo giro di rilettura**: il primo aveva
corretto sei istanze, questo ha tolto una **classe** (l'accesso per indice, dove
si poteva) e ha chiuso una **deriva** (le due trascrizioni). Un'istanza corretta
torna; una classe rimossa no.

⚠️ **E una cosa che NON ho toccato perché è una scelta di UI, non un difetto**:
`documentoLabel` compone `«103 - VX2 — 31/07/2026»` — il trattino *dentro* il
numero e la lineetta *fra* numero e data si somigliano a colpo d'occhio. ⭐ La
frase con cui Tid ha dichiarato il formato usava una parola al posto del segno:
*«fattura n. 1 - VX2 **del** 21/08/2026»*. Sostituire `—` con `del` è una riga,
ma è una decisione sua e si vede solo in app: va al collaudo, non a me.

**Provato**: 4171 test verdi · i due metodi ri-eseguiti **contro il database**
dopo la conversione per nome · il guard della deriva rotto apposta (cambiando
una regola nel file SQL → rosso) · build, lint e guard i18n puliti.

### 2026-08-29 (6) · Passata sui documenti, e tre di loro dicevano il falso

Domanda di Tid: *«hai aggiornato i documenti allo stato di sviluppo?»*. La
risposta onesta era **no, non tutti** — e le prime due bugie le avevo scritte io
il giorno prima.

| documento | diceva | verità di oggi |
| --- | --- | --- |
| catalogo BB **backend** | *«le chiavi del payload NON cambiano: il contratto verso il FE è del BE e non specchia i nomi di colonna»* | ⛔ Cambiate poche ore dopo. ⭐ E non era sbagliata a metà: era sbagliata **nella metà che conta** — il *prefisso* il payload lo cambia davvero (annida), il *suffisso* no |
| catalogo BB **frontend** | *«pannello e liste chiamano le stesse cose con nomi diversi: non è una svista da uniformare, sono due trasporti diversi»* | ⛔ Uniformati lo stesso giorno |
| **cinque manuali API** (`api_offerte`, `api_ordini`, `api_contratti`, `api_preventivi`, `api_ddt`) + `api_fatture_list` | *«`frontiera_tipo_codice` (decodificato dal repo via `config.sorgenti`)»* | ⛔ Nome **e** sorgente cambiati entrambi. È la categoria peggiore: sono i manuali che uno sviluppatore apre per sapere **cosa risponde l'endpoint oggi** |

⭐ **E la passata ne ha trovata una che non era mia**: `api_resi.md` diceva
*«nessuna colonna lineage sulla lista resi»*, falso dal **2026-08-25**, da quando
i resi sono la sesta sorella. Tre giorni di documentazione ferma su un endpoint
che nel frattempo aveva preso tre colonne.

⚠️ **Distinzione tenuta**, e non è pedanteria: la prosa **storica** (i brief in
`work-done`, il racconto di questo piano, il testo originale delle richieste)
cita i nomi vecchi ed è **giusto che li citi** — è un registro datato. Ho toccato
solo ciò che descrive **il contratto di oggi**. Un documento storico riscritto
smette di dire quando le cose sono cambiate.

⭐ **Registrato anche il presidio nuovo nel catalogo BB backend**: un cancello
che nessuno sa che esiste è un cancello che il prossimo aggira senza saperlo.

⛔ **La lezione, ed è la stessa del §3-ter.5 vista dall'altra parte**: il team DB
mi ha segnalato un disallineamento che il *loro* guardrail non poteva vedere. Qui
il disallineamento era fra **codice e documentazione**, e non c'è nessun
guardrail che lo veda — l'ha visto una domanda.

---

{% include-markdown "signature-core.md" %}
