# Brief DB — la chiave del contatore: gli assi si dichiarano, non si assumono

> **Destinatario:** team DB (`dev/db-tid`). Aperto il 2026-09-01.
>
> **In una riga:** il contatore dei registri distingue i numeri su **quattro**
> assi — `(registro_id, anno, mese, serie)` — ma i documenti che quei numeri li
> ricevono ne portano al massimo tre, e nessuno controlla che li portino. Dove
> il contatore discrimina su un asse che il documento non sa esprimere, consegna
> un numero che il documento non è in grado di ospitare.
>
> **Origine.** Non da un difetto in campo: è emersa il 2026-09-01 scrivendo il
> guard sulla forma del numero ([brief CRUD registri](brief-be-fe-crud-registri-di-numerazione.md)
> §8), chiedendosi *perché* `serie_default` potesse restare fuori dal divieto. La
> risposta — «perché la serie distingue i documenti» — vale per tre documenti su
> cinque. Poi le domande di Tid, che hanno spostato il cantiere due volte:
> *«allora tutti i documenti che si numerano sui registri devono avere la chiave
> completa?»* e *«non conviene dichiararlo nella famiglia?»*. Sì a entrambe, e
> la seconda ha cambiato la forma della cura.
>
> ⛔ **Nessuna misura decide niente qui.** I conteggi sono **fatti datati** e
> servono a un uso solo: dire se qualcosa *smentisce* il piano. A decidere è la
> struttura.
>
> **Correlati:**
> [brief-db-prefisso-sul-registro](../work-done/brief-db-prefisso-sul-registro-e-allineamento-contatori.md) ·
> [brief-db-registri-di-numerazione-emittente-e-trasloco](../work-done/brief-db-registri-di-numerazione-emittente-e-trasloco.md) ·
> [vendite.famiglie_documento](/dbzero/vendite/tabelle/famiglie_documento)

---

## 1. ⭐ L'invariante, e l'asimmetria che la governa

> **Tutto ciò che discrimina il CONTATORE deve poter discriminare anche il
> DOCUMENTO.**

Il contatore vive su `uq_regprog_key`. Ogni combinazione è un **secchio** che
riparte da 1. Se il documento non porta uno di quegli assi nel proprio vincolo di
unicità, il contatore gli può dare un numero che per lui è **già usato**.

⭐ **E i due versi non sono simmetrici** — è la regola che dice quale asse va
dichiarato e quale no:

| | Effetto |
| --- | --- |
| il **contatore** ha un asse che il **documento** non ha | ⛔ **collisione** |
| il **documento** ha un asse che il **contatore** non ha | ✅ **innocuo** — il documento è solo più specifico |

⇒ Un asse va **dichiarato** solo quando può mancare al documento. Un asse che
tutti i documenti portano è sicuro in entrambi i versi, e dichiararlo
creerebbe una seconda sorgente di verità.

⚠️ **E il difetto non si vede finché quell'asse non si muove.** È per questo che
è rimasto invisibile: gli assi che mancano oggi sono fermi.

---

## 2. Come sta oggi — struttura, verificata il 2026-09-01

| Asse del contatore | `fatture` | `ddt` | `ordini` | `resi` | `commesse` |
| --- | --- | --- | --- | --- | --- |
| `registro_id` | ✅ | ✅ | ✅ | ✅ | ⛔ |
| `anno` | ✅ | ✅ | ✅ | ✅ | ~ dentro la stringa |
| `serie` | ✅ | ✅ | ✅ | ⛔ | ⛔ |
| `mese` | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ |

```text
fatture   uq_fatture_numero              (registro_id, anno, COALESCE(serie,''), numero)
ddt       uq_ddt_v_anno_serie_numero     (registro_id, anno, serie, numero)
ordini    uq_ordini_v_anno_serie_numero  (registro_id, anno, serie, numero)
resi      uq_resi_anno_numero            (registro_id, anno, numero)          ⛔ senza serie
commesse  uq_commesse_codice             (codice)                             ⛔ una stringa sola
```

⚠️ **`vendite.commesse` non ha nemmeno `registro_id`**: ha `codice` e
`emittente_soggetto_ruolo_id`. Del registro che l'ha numerata non resta traccia
se non dentro la stringa.

---

## 3. ⛔ Il caso `resi`

`vendite.resi` **non ha la colonna `serie`**. `trgfn_resi_gen_numero` non passa
nessuna serie, quindi eredita il `serie_default` del registro — e **non la scrive
da nessuna parte**.

Cambiando `serie_default` su un registro `RESO` **a metà anno**: si apre un
secchio nuovo che riparte da 1 → il primo reso prova a scrivere il numero 1 →
`uq_resi_anno_numero` non ha la serie e quel numero nell'anno esiste già →
**violazione**. La transazione fallisce e col rollback torna indietro **anche
l'incremento del contatore**, quindi al tentativo dopo riparte da 1 e sbatte di
nuovo.

⇒ **Non un dato sporco: un reso che non si numera più**, con un errore che parla
del numero e non nomina la causa.

⭐ **Il morso è confinato all'anno**: `reset_policy` è `ANNUALE` e il reso scrive
`anno` dalla stessa chiamata che gli dà il numero. Cambiare `serie_default` **a
gennaio**, prima del primo reso, non rompe niente — e non lo nota nessuno.

⚠️ Il rollback del contatore è **dedotto dal meccanismo, non provato su un reso
vero**: costruirne uno richiede DDT e partita. Il resto è struttura verificata.

---

## 4. ⛔ Il caso `commesse` — lo stesso difetto, scritto altrimenti

L'unicità è su **una stringa sola**, che incorpora sigla, anno e progressivo —
non la serie, non il registro. Stessa dinamica del §3.

⚠️ **La cura non è la stessa**: sul reso manca *una colonna*, qui manca **tutto
l'aggancio**. Allineare la commessa significa decidere come si aggancia al
registro — modello, non `ALTER TABLE`. **Resta fuori dal piano**, e il presidio
la dichiarerà come debito invece di ignorarla.

---

## 5. ✅ La forma della cura — l'asse si DICHIARA sulla famiglia

> **Decisione di Tid, 2026-09-01.**

⛔ **La prima proposta era sbagliata nel bersaglio**: dare la colonna `serie` ai
resi sistemava il **sintomo su una tabella**. Il sesto documento che entra
domani sui registri avrebbe avuto lo stesso problema, e nessuno gliel'avrebbe
chiesto.

⭐ La cura sta dove una famiglia **entra** nei registri: `vendite.famiglie_documento`.

### 5.1 Tre cose diverse che si chiamano «serie»

| Cosa | Dove sta | Che natura ha |
| --- | --- | --- |
| `serie` sul documento | `fatture.serie`, `ddt.serie`, `ordini.serie` | **il fatto**: quale serie è stata usata |
| `serie_default` | `registri_fatturazione` | **la scelta**: cosa usa questo sezionale |
| `colonna_serie` | `famiglie_documento` | **la capacità**: questa famiglia una serie *può* averla, e si chiama così |

> **Sulla FAMIGLIA si dichiara ciò che il documento PUÒ esprimere. Sul REGISTRO
> si sceglie ciò che quel sezionale FA.**

⛔ **`serie_default` non si sposta.** Resta sul registro, dov'è giusto che stia.

### 5.2 ⭐ Il nome della colonna, non un booleano

`famiglie_documento.colonna_serie text NULL` — `NULL` = la famiglia non ha una
serie.

Un `gestisce_serie boolean` messo a `true` su una famiglia la cui tabella non ha
la colonna riporterebbe il difetto di partenza, **e nessuno se ne accorgerebbe**.
Col nome, il presidio verifica che la colonna esista davvero.

⭐ **Ed è già l'idioma della tabella**: `colonna_numero` e
`colonna_billing_account` esistono esattamente per questo — *«il numero si chiama
`numero` su fatture ma `codice` sulla commessa: il predicato derivato deve
saperlo e non può dedurlo»*.

Valori: `FATTURA`/`DDT`/`ORDINE` → `'serie'` · `RESO`/`COMMESSA` → `NULL`.

#### ⛔ E sulla famiglia NON va un default della serie — `prefisso` e `serie` sono opposti

| Famiglia | prefissi distinti | serie distinte |
| --- | ---: | ---: |
| `FATTURA` | **1** | **6** |
| `DDT` · `ORDINE` · `RESO` · `COMMESSA` | 1 | 1 |

Il **prefisso** ha un default sulla famiglia (`prefisso_default`) perché il suo
mestiere è **essere uguale**: tutti i DDT cominciano per `DDT`. La **serie** fa
il mestiere opposto — esiste per **differire**, ed è ciò che separa i sezionali
di una stessa famiglia e di uno stesso emittente (Back-office, Front-office, NC).

⇒ Un `serie_default` sulla famiglia dovrebbe rispondere «quale delle sei?», e non
c'è risposta: collasserebbe proprio la distinzione per cui la serie esiste.

⚠️ Il conteggio è un **fatto datato**: serviva a smentire il ragionamento se le
sei serie fossero risultate uguali. Il motivo sta nel modello.

#### ⚠️ E nemmeno l'OBBLIGATORIETÀ, e non è una dimenticanza

«Questa famiglia **deve** avere una serie» è una domanda diversa da «può
averla», e non entra in questo cantiere:

1. **non serve al difetto** — il difetto è l'opposto, una serie dove il documento
   non sa tenerla. L'obbligatorietà è completezza di dominio, non sicurezza;
2. **nessuna regola di dominio la sostiene**: `uq_fatture_numero` usa
   `COALESCE(serie,'')`, quindi il vuoto è un valore legittimo. Che oggi tutti e
   sei i registri FATTURA ce l'abbiano è **popolazione**, e non decide;
3. ⛔ **sarebbe la quarta** colonna dichiarata e non implementata di questa
   famiglia di tabelle, dopo `mese`, `reset_policy` e i valori tolti dal CHECK.

Se servirà è una decisione sua, col suo guard.

### 5.3 ⛔ Sul registro si RIFIUTA, non si ignora

Se un registro `RESO` accettasse un `serie_default` e il motore lo ignorasse in
silenzio, avremmo ricreato il difetto che il cantiere del prefisso ha appena
tolto da `config.sistema_codici`: *un campo editabile dal pannello che
l'amministratore cambia senza ottenere niente e senza modo di accorgersene*.

⚠️ **Non può essere un `CHECK`**: la condizione attraversa `famiglie_documento`, e
un CHECK non fa sottoquery. Serve un **guard `_a10_`**, in `INSERT` **e**
`UPDATE`: un registro non deve nemmeno *nascere* con una serie che la sua
famiglia non porta.

⭐ **E il motivo passa da una `fn_check_*` che il guard CHIAMA** (§12.5.2), perché
serve anche alla maschera: il campo `serie_default` va disabilitato **col
perché**, non lasciato grigio.

### 5.4 Il terreno è pulito — verificato il 2026-09-01

| | |
| --- | --- |
| registri con `serie_default` valorizzata | **6, tutti `FATTURA`** — DDT, ORDINE, RESO, COMMESSA sono tutti a NULL |
| righe del mirror CSV `registri_fatturazione.csv` | **3, tutte `FATTURA`** (Front-office `R2`, Back-office `R1`, NC vuota) |
| `fn_provision_registri_emittente` | **non** imposta `serie_default` |

⭐ **E questo corregge una mia obiezione precedente.** Avevo scritto che un guard
su `serie_default` non era montabile perché il mirror la riscrive a ogni migrate:
vero per un divieto **secco**, falso per uno **condizionale** — il mirror tocca
solo le fatture, che sono la famiglia dove la serie è legittima.

---

## 6. ✅ `mese` sparisce

> **Decisione di Tid, 2026-09-01.**

`mese` sta nella chiave del contatore e **non compare in nessun vincolo di
unicità di nessun documento**. È innocuo solo perché è **inchiodato** in due
punti: `v_mese := 0` nel corpo vivo di `fn_get_next_progressivo`, e
`chk_registri_fatturazione_reset` che ammette solo `ANNUALE`.

⛔ **Una dimensione dormiente in una chiave non è inutilizzata: è ARMATA.** Un
reset mensile farebbe collidere **tutti e cinque** i documenti, non i due del
§3-§4. E a tenerla chiusa non è un vincolo: è una **rinuncia**, che si revoca per
distrazione.

⭐ E col §5 la revoca ha una strada pulita: se un giorno servisse, `mese` torna
come `colonna_mese` sulla famiglia **insieme** alla colonna sui documenti. Cioè
il lavoro vero. Tenerla adesso non anticipa niente.

### 6.1 Il censimento dei LETTORI — verificato il 2026-09-01

Il censimento si fa sulla **lettura**, non sulla parola: «mese» nel progetto è
quasi sempre `competenza_mese` o «il primo del mese».

| Dove | Chi legge `registri_fatturazione_progressivi.mese` |
| --- | --- |
| funzioni PL/pgSQL | **una sola**: `vendite.fn_get_next_progressivo` |
| viste · backend Python · pgTAP · CSV di seed | **nessuno** |

⚠️ `fn_calcola_data_documento` la nomina **solo in un commento**.

### 6.2 Cosa la tiene attaccata

```text
uq_regprog_key                 UNIQUE (registro_id, anno, mese, serie)
uq_registri_progressivi_scope  UNIQUE INDEX (registro_id, anno, COALESCE(mese,0), COALESCE(serie,''))
chk_regprog_mese_valid         CHECK (mese = 0 OR mese BETWEEN 1 AND 12)
                               NOT NULL
```

### 6.3 ⭐ E si scopre un UNIQUE ridondante che il presidio non vede

Le quattro colonne sono **tutte `NOT NULL`** ⇒ i `COALESCE` di
`uq_registri_progressivi_scope` sono **no-op**, e quell'indice esprime la
**stessa chiave** di `uq_regprog_key`.

⛔ **`dbops.vw_duplicate_indexes` non lo segnala** (verificato: zero righe): il
confronto lavora sulle colonne, e qui una chiave è colonne e l'altra è
**espressioni**.

⭐ *Un duplicato nascosto dietro espressioni che non fanno niente è invisibile
proprio al presidio nato per i duplicati.* Si toglie nello stesso giro, e la
cecità va **dichiarata**.

### 6.4 Il fatto datato che avrebbe potuto smentire il piano

Le righe di `registri_fatturazione_progressivi` sono **10, tutte con `mese = 0`**
⇒ nessuna riga distinta collassa sulla chiave nuova. ⚠️ Serviva a cercare un
controesempio, non a decidere.

---

## 7. ✅ `reset_policy` diventa vera e funzionante

> **Decisione di Tid, 2026-09-01.**

### 7.1 Oggi è dichiarata e mai letta

```text
chk_registri_fatturazione_reset   CHECK (reset_policy = 'ANNUALE')     — un valore solo
fn_get_anno_registro              v_anno := EXTRACT(YEAR FROM p_data)  — hardcoded
```

Censito il 2026-09-01: `fn_numera_fattura_opz_emessa` e `fn_assign_numero_fattura`
la nominano **solo nei commenti**; `fn_provision_registri_emittente` la **scrive**
e basta. **Nessuna funzione ramifica su `reset_policy`.**

⇒ È la **terza** colonna di questa famiglia dichiarata e non letta, dopo `mese` e
i valori tolti dal CHECK.

### 7.2 ⭐ Perché questa si accende invece di sparire, a differenza di `mese`

È l'asimmetria del §1, applicata:

* accendere **`MENSILE`** è **pericoloso** — nessun documento porta il mese ⇒ il
  contatore discriminerebbe su un asse che il documento non ha ⇒ collisione;
* accendere **`NESSUNA`** è **sicuro** — tutti i documenti portano `anno` ⇒ il
  contatore userebbe **meno** assi, non di più, e cade nel verso innocuo.

⭐ E la numerazione continua fra gli anni è una cosa che i gestionali fanno
davvero su DDT e ordini. Il parametro esiste già, sul registro: manca solo che
qualcuno lo legga.

### 7.3 ⛔ Due `anno` che si chiamano uguale, e non vanno confusi

| | Cosa significa | Sotto `NESSUNA` |
| --- | --- | --- |
| `registri_fatturazione_progressivi.anno` | **la chiave del secchio** | diventa `0` — un secchio solo |
| `fatture.anno`, `ddt.anno`, `ordini.anno`, `resi.anno` | **l'anno del documento** | resta **l'anno solare**, sempre |

⇒ **`fn_get_anno_registro` non si tocca**: risponde a *«che anno è il
documento»*, e la risposta non cambia. Ha **quattro** chiamanti
(`fn_assegna_numero_documento`, `fn_assign_numero_fattura`,
`fn_get_next_progressivo`, `fn_get_or_create_commessa`) e cambiarle la firma li
toccherebbe tutti per un motivo che non li riguarda.

⭐ **La politica si legge dove serve, e serve in un punto solo**:
`fn_get_next_progressivo` è **l'unica funzione che legge `progressivi.anno`**
(censito). Lì `v_anno` diventa:

```text
ANNUALE  → vendite.fn_get_anno_registro(p_data)
NESSUNA  → 0
```

⇒ Raggio d'azione: **una funzione**.

### 7.4 ⚠️ Il sentinella `0`, e perché non è il ritorno di `mese = 0`

Sembrano la stessa cosa e non lo sono:

* `mese = 0` significava *«questo asse non è usato da nessuno, mai»* — un
  segnaposto per una funzione non implementata;
* `anno = 0` significherà *«questo registro non azzera per anno»* — un valore con
  un **lettore vivo**, che una politica dichiarata sceglie.

⚠️ **Ma la coerenza fra i due — `anno = 0` ⟺ registro `NESSUNA` — non la può
tenere un `CHECK`**, perché attraversa due tabelle. La tiene la funzione, ed è il
presidio del §9 a verificarla.

### 7.5 Cosa cambia, in concreto

* `chk_registri_fatturazione_reset` riammette **`NESSUNA`** (⛔ non `MENSILE`: quello
  è l'asse che il §6 toglie);
* `fn_get_next_progressivo` legge la politica del registro;
* il **pavimento** non si tocca: `fn_get_pavimento_sequenza` e compagne leggono i
  progressivi **senza filtrare per anno** (censito), quindi guardano già
  attraverso gli anni — che è ciò che `NESSUNA` vuole.

---

## 8. Il piano

> ⛔ Ordine vincolante: **prima il codice, poi lo schema** dove una colonna cade.
> ⚠️ L'autogen ordina per NN mescolando `00_schema` e `20_code`: l'ordine si
> impone con la **numerazione**, non con la cartella.

| Passo | Cosa | Dove |
| --- | --- | --- |
| **M-1** | `fn_get_next_progressivo` senza `mese` **e** che legge `reset_policy` | `20_code/vendite` |
| **M-2** | `chk_regprog_mese_valid` e `uq_registri_progressivi_scope` via; `uq_regprog_key` su `(registro_id, anno, serie)`; `DROP COLUMN mese` | `00_schema/vendite`, NN > M-1 |
| **R-1** | `chk_registri_fatturazione_reset` riammette `NESSUNA` | `00_schema/vendite` |
| **S-1** | `famiglie_documento.colonna_serie` + seed dei cinque valori | `00_schema` + CSV `80_data` |
| **S-2** | `script.fn_check_registro_serie_ammessa` — la pure check §12.5.1 | `20_code/script` |
| **S-3** | Il guard `_a10_` su `registri_fatturazione` (INSERT + UPDATE OF `serie_default`, `famiglia_documento`) che la **chiama** | `20_code/vendite` |
| **P-1** | I presidi del §9 | `db/pgtap/vendite` |

⚠️ **M-1 fa due cose insieme di proposito**: toglie `mese` e accende
`reset_policy` nella **stessa** riscrittura della chiave del secchio. Separarle
significherebbe riscrivere due volte lo stesso `v_anno`/`v_mese`, con una
revisione intermedia che non corrisponde a nessuno stato voluto.

⛔ **Un codice errore nuovo serve** per il rifiuto della serie (§5.3): il rifiuto
non esiste ancora, quindi non c'è nessuna madre muta da sanare — è lo stesso
ragionamento del guard sulla forma del numero.

---

## 9. ⭐⭐ I presidi — l'invariante, non i casi

⛔ **Un test che verificasse «resi non ha la serie» proverebbe l'oggi.** Il
difetto non è una colonna mancante: è che **nessuno controlla** che i documenti
numerati sui registri portino la chiave del contatore. È così che `resi` e
`commesse` sono entrati col trasloco senza che niente diventasse rosso.

Tre controlli, tutti **derivati**:

1. **La dichiarazione è vera** — per ogni famiglia con `colonna_serie`
   valorizzata, quella colonna **esiste** sulla tabella dichiarata **e** compare
   nel vincolo di unicità del numero;
2. **Il registro rispetta la dichiarazione** — nessun registro di una famiglia
   con `colonna_serie NULL` ha `serie_default` valorizzato;
3. **Il secchio rispetta la politica** — `anno = 0` se e solo se il registro è
   `NESSUNA` (§7.4).

Nessun elenco a mano da nessuna parte. Il giorno che una famiglia nuova entra sui
registri senza la chiave completa, il test è **rosso prima del merge**.

⭐ È la forma del test 6 di `test-fn-check-registro-disattivabile-v1.sql` —
*«il giorno che ne compare una quarta diventa rosso»* — che su questa stessa
tabella ha già funzionato una volta.

⚠️ **`commesse` sarà rossa dal primo giorno**, ed è debito **dichiarato**: o si
esclude con un motivo scritto, o il test nasce a fallire. La scelta va fatta
esplicitamente, non per omissione.

---

## 10. ⛔ Cosa non si tocca

* **`serie_default` non si sposta** e non si vieta in blocco: resta sul registro,
  e il divieto è **condizionato** alla dichiarazione della famiglia.
* **`fn_get_anno_registro`** non cambia firma: risponde all'anno del *documento*,
  non a quello del secchio (§7.3).
* **`MENSILE`** non rientra nel CHECK: è l'asse che il §6 toglie.
* **`config.sistema_codici`** non c'entra: la forma del numero è uscita di lì il
  2026-08-31 di proposito.
* **`commesse`** resta fuori dal piano (§4), dentro il presidio come debito.
* **Nessuna migrazione si applica** senza che Tid lo dica, per quel comando.

---

## 11. ✅ Stato dello sviluppo — **APPLICATO** il 2026-09-01

| Passo | Esito | File |
| --- | --- | --- |
| **R-1** | ✅ | `00_schema/vendite/20260901-06` — il CHECK riammette `NESSUNA` |
| **M-1** | ✅ | `20_code/vendite/20260901-07` — via `mese`, e `reset_policy` si legge |
| **M-2** | ✅ | `00_schema/vendite/20260901-08` — via la colonna e l'UNIQUE ridondante |
| **S-1a** | ✅ | `00_schema/vendite/20260901-09` — `famiglie_documento.colonna_serie` |
| **S-2** | ✅ | `20_code/script/20260901-10` — `fn_check_registro_serie_ammessa` |
| **S-3** | ✅ | `20_code/vendite/20260901-11` — il guard che la **chiama** |
| **S-1b** | ✅ | `80_data/20260901-12` + `famiglie_documento_colonna_serie.csv` |
| — | ✅ | codice `E_REGISTRO_SERIE_NON_AMMESSA` (`DATO_ERRATO`) + messaggio, append ai due CSV |
| **P-1** | ✅ **9/9 verdi** | `db/pgtap/vendite/test-chiave-contatore-assi-dichiarati-v1.sql` |

✅ **Applicato da Tid il 2026-09-01, pgTAP verdi.** I nove changeSet del
2026-09-01 risultano `EXECUTED` sul `databasechangelog`, e lo stato strutturale
è quello voluto:

| | |
| --- | --- |
| colonna `mese` | **non esiste più** |
| `uq_registri_progressivi_scope` (il duplicato invisibile) | **non esiste più** |
| chiave del secchio | `UNIQUE (registro_id, anno, serie)` |
| `chk_registri_fatturazione_reset` | ammette `ANNUALE` **e** `NESSUNA` |
| guard della serie | **montato** |
| `E_REGISTRO_SERIE_NON_AMMESSA` | **a catalogo** |

E il seed è quello dichiarato: `FATTURA`/`DDT`/`ORDINE` → `serie`,
`RESO`/`COMMESSA` → `NULL`.

### 11.1 Come è stato provato

L'SQL **estratto dai sei YAML**, eseguito **nell'ordine di numerazione** su una
transazione con `ROLLBACK`, col seed e il codice errore aggiunti dentro. Poi il
pgTAP nella stessa forma.

| Prova | Esito |
| --- | --- |
| `ANNUALE`: il secchio porta l'anno solare | ✅ |
| `NESSUNA`: due documenti di **anni diversi** prendono 1 e 2 | ✅ il contatore non riparte |
| registro `RESO` con serie, in **INSERT** | ✅ rifiutato |
| lo stesso **senza** serie | ✅ passa (il gemello positivo) |
| `UPDATE` che mette una serie su un `RESO` | ✅ rifiutato |
| il mirror CSV che riscrive `serie_default` sulle 6 fatture | ✅ passa — **il migrate non si rompe** |

### 11.2 ⚠️ Tre cose trovate scrivendo, che il piano non prevedeva

**1. Il seed non poteva stare in `00_schema`.** Era la strada che sembrava
ovvia — la colonna nasce lì — ed è quella del precedente `prefisso_default`
(`20260831-51`). ⛔ Ma su un database **ricostruito da zero** `00_schema` gira
quando la tabella è ancora **vuota**: l'`UPDATE` non tocca nessuna riga, le
famiglie arrivano dopo dal mirror, e il valore resta `NULL` in CI mentre su dev
è popolato. ⇒ Il seed vive in `80_data`, con un **CSV dedicato** e la chiave
naturale `codice_interno` — il pattern di `registri_fatturazione_politica_data`.

📌 **E ne discende un sospetto su `prefisso_default`, che non è di questo
brief**: seminata con un `UPDATE` in `00_schema` e assente dal mirror, potrebbe
essere `NULL` su un database ricostruito — e a leggerla è
`fn_provision_registri_emittente`, che darebbe ai registri nuovi un prefisso
vuoto. **Da verificare**, non è un'affermazione.

**2. Il guard della serie ha due accorgimenti che tengono in piedi il migrate**,
e sono la ragione per cui non è un `CHECK` né un guard ingenuo:

* in `UPDATE` confronta i **valori**, perché il mirror `20260127-57` riscrive
  `serie_default` a ogni migrate e `UPDATE OF` scatta comunque;
* il ramo «famiglia non trovata» della check **tace** — su un database
  ricostruito il mirror dei registri gira **prima** di quello delle famiglie
  (`includeAll` ordina per nome file), e senza quel ramo il migrate di un DB
  nuovo fallirebbe. ⚠️ Non è fail-open: in esercizio la FK garantisce la riga, e
  lo stato finale lo verifica il test 6.

**3. La trappola dell'auto-gen è scattata.** Il corpo di `fn_get_next_progressivo`
è stato preso dalla funzione **viva** — che è la fonte giusta per il corpo — ma
`pg_get_functiondef` **scioglie i `%TYPE` della firma** in tipi concreti. La
firma è stata ripresa da `20260831-06`, l'ultimo YAML che la dichiara.
⇒ **Il corpo dal vivo, la firma dall'ultimo YAML.**

### 11.3 ⚠️ Un difetto trovato leggendo l'output, non il codice

Il messaggio di `E_REGISTRO_SERIE_NON_AMMESSA` diceva *«Registro %s: la famiglia
%s…»* e riceveva `(serie, famiglia)`: a video usciva **«Registro X1»**, dove `X1`
è la **serie**. Arità giusta — due segnaposto, due valori — e frase **falsa**.

⇒ Corretto in *«La famiglia %s non gestisce le serie: questo sezionale non può
portare la serie %s»*, coi valori riordinati.

⭐ **La lezione, che vale oltre questo caso**: l'ordine dei `VARIADIC` non si
verifica contando i segnaposto, si verifica **leggendo la frase resa**. Un
cancello sull'arità non lo avrebbe visto.

### 11.4 🔭 Cosa resta

* ⚠️ **Due `reason_key`** ora emesse dal database e assenti dai `locales`, e
  `check_i18n_keys.py` è **rosso** finché il FE non le aggiunge — è il
  comportamento voluto (§12.3), non un incidente:
  * `amministrazione.registri_fatturazione.forma_blocco.ha_numerato`
  * `amministrazione.registri_fatturazione.serie_blocco.non_gestita`

  ⛔ Vanno in `it.json` **e** `en.json` nello stesso giro del lavoro frontend.
  Chi apre una PR prima di allora la trova rossa, e non per colpa sua.
* ⚠️ **`script.fn_check_registro_forma_modificabile` ha la firma senza `%TYPE`**
  (`p_registro_id bigint` invece di `vendite.registri_fatturazione.id%TYPE`,
  come fa la gemella). ⛔ È in un changeSet **già pushato**, quindi non si
  modifica. ⭐ E un changeSet correttivo sarebbe **un no-op sul database**:
  `%TYPE` si risolve allo stesso `bigint` e la firma non sta in `prosrc`. ⇒ È un
  **debito di sorgente**, non di comportamento: si paga alla prossima revisione
  di quella funzione, o con un changeSet dedicato se si preferisce la coerenza
  degli YAML. Decisione a Tid.
* ⛔ **`commesse` resta scoperta** (§4): dichiara `colonna_serie NULL`, quindi i
  presidi la proteggono dal prendere una serie — ma la sua unicità resta su una
  **stringa sola**, senza registro né serie. Debito dichiarato.
