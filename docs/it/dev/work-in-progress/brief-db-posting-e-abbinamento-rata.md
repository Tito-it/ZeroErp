# Brief DB — posting contabile e abbinamento alla rata

> **Cos'è.** Il **piano di sviluppo lato database** del cantiere descritto in
> [brief-incassi-riconciliazione-rate-promemoria.md](brief-incassi-riconciliazione-rate-promemoria.md).
> Quel documento contiene la **misura del terreno e le decisioni** (D1…D9); questo
> contiene **l'analisi critica di quelle decisioni al 2026-08-21** e i **passi**
> che le realizzano, changeSet per changeSet.
>
> **Perché due documenti e non uno.** Cambia il *soggetto*, non il *lato*: là si
> decide **che cosa** deve succedere, qui **in quale ordine si scrive**. È lo
> stesso rapporto che nel cantiere fondi lega §1-7 al §8. ⚠️ E vale l'avvertenza
> che quel cantiere ha già pagato (registro, notte 11): **due sedi sullo stesso
> argomento divergono al primo aggiornamento**. La regola operativa qui è secca:
> *le decisioni di dominio si aggiornano **solo** nel brief madre; i passi e le
> misure **solo** qui.* Se una decisione cambia, si cambia là e si riporta qui il
> passo che ne discende — mai il contrario.
>
> **Scritto il 2026-08-21**, rimisurando il terreno contro la doc auto-generata
> `dbzero` e i changelog. Il brief madre è fermo al **2026-08-15 sera**: da allora
> il cantiere fondi è atterrato quasi per intero, e **tre cose che quel brief dà
> per vere non lo sono più**.
>
> ⛔ **Niente è stato applicato.** Nessuna migrazione, nessuna scrittura sul
> database. Questo documento è un piano.
>
> 🔴 **Prima di iniziare lo sviluppo vanno chiuse le domande di §5.** Sono nove,
> tutte insieme in coda, e almeno cinque cambiano *cosa* si scrive — non *come*.

---

## 0. In una pagina

| | Cosa | Dove |
| --- | --- | --- |
| ✅ **Regge** | D1 (abbinamento sulla riga, niente N:N) · D2 (stato rata derivato) · D3 (posting per testata, madre DB, correzione = importo negativo) · D5 (perimetro dal conto di incasso) · D9 (transizioni dichiarate, `STORNATA` ritirato, annullamento solo in bozza) | §1.1 |
| ⭐ **Superato dai fatti** | La «metà fondi» della slice 1 **è fatta**: Fasi A/B/C/E/F applicate il 15-16/08. `fn_sync_pagamento_fondo_fattura` **non esiste più**. La dipendenza si è **invertita**: ora è il cantiere fondi ad aspettare `pagamenti` | §1.2 |
| 🔴 **Misure sbagliate** | B-2 è sbagliato a metà (il guard **c'è già**, e il difetto è un altro e peggiore) · «due pgTAP rossi in baseline» è **falso** · la scadenza della metà fondi non esiste più | §1.3 |
| 🔴 **Difetti nuovi, armati dalla slice 1** | Un vincolo che tiene `centri_riscossione` a **due righe in tutto** · il sync dei fondi **riscrive righe già postate** · un fondo interamente postato **si auto-annulla** · la testata riusata accorpa bonifici distinti · righe aggiunte a una testata `CHIUSA` escono dalla bilancia | §1.4 |
| 📋 **Il piano** | Slice **0** (terreno) → **1** (posting) → **2** (rata) → **3** (perimetro) | §2 |
| ❓ **Domande aperte** | Nove, in coda | §5 |

---

## 1. Analisi critica

### 1.1 Ciò che regge, e non si riapre

Rimisurato contro la struttura viva. Le decisioni portanti del brief madre **non
hanno bisogno di essere riaperte**, e tre di esse hanno guadagnato una conferma
che al momento in cui furono prese non c'era.

| Decisione | Verifica al 2026-08-21 |
| --- | --- |
| **D1** — abbinamento sulla riga contabile, fino alla rata, niente tabella N:N | ✅ La riga è davvero l'unità di allocazione: `vendite_contabili_righe` porta `importo`, `fattura_id`, `billing_account_id` e uno stato proprio. ⚠️ E la FK a `vendite.fatture_scadenze` **incontra davvero la RLS**: policy `rls_fatture_scadenze_ef_whitelist` (`20260601-32`) più `ENABLE ROW LEVEL SECURITY` (`20260601-38`). La cautela di D1 è giustificata, non prudenziale |
| **D2** — stato della rata derivato, mai scritto | ✅ Confermato dai fatti: `trg_fatture_scadenze_a10_guard_congelamento_ins_upd_dlt` presidia INSERT, UPDATE **e** DELETE. Una colonna di stato su `fatture_scadenze` non si potrebbe scrivere nemmeno volendo |
| **D3-a/b** — unità = testata, forma = una sola `SELECT fn_...()` | ✅ Regge, **con una riserva nuova**: l'unico punto d'ingresso esistente per la testata non produce l'unità che D3-a descrive. Vedi §1.4 C-4 e la domanda **Q-3** |
| **D3-c** — replay tecnico silenzioso, seconda azione parlante | ✅ Il presidio strutturale c'è già: `uq_vendite_movimenti_contabile_riga` è un indice unico parziale su `contabile_riga_id`. Il doppio movimento è **impossibile**, non improbabile |
| **D3-d** — lo storno non esiste: è una contabile con importi negativi | ✅ Il modello lo ospita: `chk_vendite_contabili_righe_importo_non_zero` vieta **lo zero**, non il negativo; `vendite_movimenti.importo` non ha vincolo di segno; il residuo è una somma e torna indietro da sé |
| **D5** — perimetro dal conto di incasso | ✅ La catena è quella descritta, e il buco è quello descritto: `anagrafiche.soggetti_ruoli_conti_bancari` **non ha** unicità su `(conto_bancario_id, uso)`, quindi lo stesso conto `INCASSO` può appartenere a due soggetti. I tre indici presenti sono tutti di **accesso**, nessuno di **unicità** |
| **D9-b** — `pagamenti` deve avere le sue transizioni dichiarate | ✅ Confermato: dieci domini hanno una tabella `transizioni_stati_*` (o `stati_*_transizioni`) con un `trgfn_*_guard_transizione` a presidio. `pagamenti` è l'unico che ha stati e **nessuna regola** su come ci si passa |
| **D9-c** — si annulla solo prima della conferma | ✅ Il modello ha già le colonne per dirlo: `vendite_contabili.data_conferma` e `user_conferma` esistono e **nessuno le scrive**. Sono la sede naturale del gesto |

### 1.2 ⭐ Superato dai fatti: il cantiere fondi è atterrato

Il brief madre, in §7, mette **dentro la slice 1** la «Fase A del cantiere
fondi». Al 2026-08-21 quella metà **è fatta**, e non solo lei.

| Cosa il brief madre dà per pendente | Stato reale |
| --- | --- |
| Fase A (CHECK soglie, sorgente DEFINITIVA, guard di corrispondenza, capienza all'applicazione, chiave a nove elementi) | ✅ **applicata** il 2026-08-15 — changeSet `20260815-03`…`-09`, pgTAP 12/12, baseline `vendite` senza regressioni |
| Fase B (registro degli atti), Fase C (proposta + elenco), coda Fase E | ✅ **applicate** lo stesso giorno — `20260815-10`…`-23` |
| Fase F (il confine col posting) | ✅ **dichiarativa e chiusa**: le sue due metà sono già nel brief madre (§1-bis «la bilancia regge da sé» e §4 «incassato ≠ postato») |
| `vendite.fn_sync_pagamento_fondo_fattura` — «il guscio vuoto che sembra il posting» | ✅ **ritirata**: la funzione **non esiste più** nel database. §1-bis e §6 del brief madre la nominano ancora al presente |
| R-1, R-2, R-3, BE-2/3/5, seed `ui.lista_*` | ✅ fatti |
| `fn_saldo_sorgente_fondo` — la formula unica | ⭐ **nuova, e ci serve**: è il modo canonico di chiedere «quanto regge ancora la sorgente». Il posting dovrà tenerne conto (§1.4 C-3) |

#### 🔴 La dipendenza si è **invertita**, e va detto in testa

Il brief madre scrive che la slice 1 *contiene* la metà fondi. Oggi è il
contrario: **il cantiere fondi aspetta `pagamenti`**.

> La **Fase D** (l'atto manuale) è ferma per scelta *«finché `pagamenti` non ha
> un processo rimborsi»* — e il processo rimborsi è esattamente la **D8 (b)** del
> brief madre, l'unica domanda che quel documento lascia aperta senza
> orientamento.

Ne segue una cosa pratica: **la slice 1 non deve più portarsi dietro lavoro di
`vendite`**. Il suo perimetro si restringe a `pagamenti`, più le **due
correzioni** in `vendite` che il posting *arma* (§1.4 C-2 e C-3) — che non sono
lavoro di fondi, sono il prezzo di far esistere i movimenti.

### 1.3 🔴 Le misure del brief madre che oggi sono sbagliate

Tre, e la prima cambia un requisito.

#### B-2 è sbagliato a metà — e il difetto vero è peggiore

Il brief madre scrive che postare una riga non abbinata produrrebbe *«una
violazione NOT NULL (23502), non un errore di dominio parlante»*.

✅ **Non è così.** `pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga`
ha **già** il guard: se la riga non ha `fattura_id` o `billing_account_id`
chiama `script.fn_log_and_raise_error` con il messaggio *«riga contabile non
utilizzabile per movimento»*, cioè solleva un `P0001` prima che la `NOT NULL`
entri in gioco.

🔴 **Il difetto è un altro, ed è di specie diversa: il codice è `E_GENERICO`.**
E non solo lì — **tutte e quattro** le funzioni di `pagamenti` sollevano
`E_GENERICO`, su una quindicina di punti. Il brief madre dice «nessun codice
errore di dominio `pagamenti` esiste a catalogo»; il fatto più duro è che il
codice **già scritto** viola la regola dei codici errore, e il posting verrebbe
scritto accanto a lui.

> **Conseguenza sul requisito.** Il vincolo 2 di §3.0 («il posting rifiuta
> prima, con un codice suo») **resta vero**, ma non è «aggiungere un guard che
> manca»: è **dare un nome** a un rifiuto che già esiste e **bonificare i
> vicini**, altrimenti la stessa area risponde con codici di due specie a
> seconda di quale funzione si tocca.

⚠️ Il guard esistente ha comunque un buco proprio: scatta **solo** se
`NEW.contabile_riga_id IS NOT NULL`. Un movimento inserito senza riga — strada
che il modello ammette, la colonna è nullable — non incontra nessun controllo e
sbatte davvero sulla `NOT NULL`. Non è il percorso del posting, ma è il percorso
di chiunque scriva a mano.

#### «Due dei quattro pgTAP sono rossi in baseline» — falso

`db/pgtap/baseline-rossi.tsv` ha **19 righe** e **nessuna** è di `pagamenti`. Il
file `baseline-rossi-ci.tsv` che `AGENTS.md` nomina **non esiste** nel repo.

⚠️ Questo non rende i quattro test più affidabili: **restano tutti e quattro
costruiti sul modulo «cerca il centro, se non c'è inserilo»** — verificato riga
per riga. Cambia solo la spiegazione di perché nessuno se ne accorge: non sono
rossi per altro, sono **verdi perché si fabbricano il dato**.

⚠️ E uno di essi, `test-enti-incasso-psp.sql`, **non ha `BEGIN;`** in testa e
chiude con un `DELETE FROM pagamenti.centri_riscossione`: è un test **non
transazionale** che cancella righe di catalogo. Oggi non fa danni perché il
`DELETE` è filtrato sul suo scope, ma è la classe di test che contamina le corse
successive.

#### La scadenza della «metà fondi» non esiste più

§7 del brief madre porta un riquadro rosso: *«se un altro lavoro arriva prima su
quel terreno, il tampone va con lui»*. ✅ **Non serve più**: il tampone è
applicato dal 15/08. Il riquadro va marcato come chiuso.

### 1.4 🔴 Difetti nuovi, misurati — e li **arma la slice 1**

Questi non sono nel brief madre. Sono cinque più due minori, e i primi tre sono
bloccanti.

---

#### C-1 🔴 `centri_riscossione` non può contenere più di **due righe**

Il vincolo `uq_centri_riscossione_compensazione` è un **UNIQUE totale su una
colonna booleana**:

```sql
CREATE UNIQUE INDEX uq_centri_riscossione_compensazione
  ON pagamenti.centri_riscossione USING btree (is_compensazione)
```

Non è parziale — e l'auto-gen stampa i predicati quando ci sono: lo si vede due
righe sopra, su `uq_vendite_movimenti_contabile_riga … WHERE (contabile_riga_id
IS NOT NULL)`. Quindi: **una sola riga con `true`, una sola con `false`, e
basta.**

**Come ci si è arrivati** — il changeSet `20260211-14`:

```yaml
- addUniqueConstraint:
    columnNames: is_compensazione
    constraintName: uq_centri_riscossione_compensazione
    where: "is_compensazione = true"      # ← ignorato
```

`addUniqueConstraint` **non ha** un attributo `where`: quello si dichiara su
`createIndex`. Non è arrivata nessuna protesta, è stato generato un
`ALTER TABLE … ADD CONSTRAINT … UNIQUE (is_compensazione)`, e l'intenzione —
*«un solo centro di compensazione»* — è diventata *«due centri in tutto»*.

🔴 **Conseguenza diretta sul piano.** Il passo 3 di D9-d-1 del brief madre
(«aggiungere i centri reali: banca, poste, cassa») **oggi non è eseguibile**: il
terzo `INSERT` viola il vincolo. Il prerequisito della slice 1 ha a sua volta un
prerequisito, e non è una riga di seed: è un cambio di vincolo.

⭐ **Ed è invisibile per una ragione istruttiva**: la tabella ha esattamente due
righe, cioè il massimo che il vincolo consente. Un vincolo **saturo** e un
vincolo **rispettato** hanno lo stesso aspetto finché non si prova ad aggiungere.

⚠️ **Corollario asimmetrico.** `is_fondo_fattura` non ha **nessuna** unicità:
oggi si possono avere N centri fondo-fattura, e
`fn_sync_contabili_fondo_fattura` ne prende uno con `ORDER BY c.id LIMIT 1`.
Deterministico, ma arbitrario: la scelta la fa l'ordine degli id, non una regola.
I due flag vanno resi simmetrici, ciascuno con un **unico parziale**.

*Lezione, e vale oltre il caso: un attributo che lo strumento non conosce non è
un errore, è silenzio. Un vincolo dichiarato «parziale» in YAML va **riletto
sull'oggetto vivo**, non sul file che lo crea.*

---

#### C-2 🔴 Il sync dei fondi **riscrive righe già postate**

`vendite.fn_sync_contabili_fondo_fattura` cerca la propria riga così:

```sql
SELECT cr.id INTO v_riga_id FROM pagamenti.vendite_contabili_righe cr
 WHERE cr.attivo IS TRUE
   AND COALESCE(cr.meta->>'origine','') = 'FONDO_FATTURA'
   AND COALESCE(cr.meta->>'fondo_source_id','') = r.source_id::TEXT
 ORDER BY cr.id DESC LIMIT 1;
```

**Nessun filtro sullo stato.** Se la trova, la aggiorna: `stato_id` torna ad
`ABBINATA`, `importo` viene riscritto, `fattura_id` riassegnato.

🔴 **Il giorno del posting quella riga può essere `POSTATA`, con un
`vendite_movimenti` già esistente.** Verrebbe riportata indietro attraverso uno
stato dichiarato **finale**, con l'importo cambiato mentre il movimento conserva
il vecchio — e il movimento **non si risincronizza**, perché il trigger di
mirror sta su `vendite_movimenti` e scatta sull'INSERT/UPDATE *del movimento*,
non della riga.

Esito: la riga rientra nel saldo contabile *e* il movimento resta nel saldo
movimenti. **Lo stesso denaro contato due volte**, su una fattura che nessuno
sta guardando.

⚠️ **E il percorso è vivo, non ipotetico**: `fn_ricalcola_totali_fattura` chiama
`fn_sync_contabili_fondo_fattura` **incondizionatamente**, come ultima
istruzione. Ogni ricalcolo della fattura figlia ci passa.

---

#### C-3 🔴 Un fondo interamente postato **si auto-annulla**

`vendite.fn_saldo_sorgente_fondo` scorpora il contributo del fondo stesso, e lo
fa con questo filtro sullo stato della riga contabile:

```sql
AND st.is_postabile IS TRUE          -- ← il punto
```

Il conto, **prima** del posting — ed è ciò che tiene in piedi il meccanismo oggi:

```text
saldo(movimenti)      = totale                       (nessun movimento)
saldo_contabile_tot   = importo_fondo                (riga ABBINATA, postabile)
saldo_contabile_own   = importo_fondo                (la stessa riga, scorporata)
→ saldo_sorgente      = totale − (importo − importo) = totale       ≠ 0   ✅
```

**Dopo** il posting:

```text
saldo(movimenti)      = totale − importo_fondo       (il movimento esiste)
saldo_contabile_tot   = 0                            (POSTATA non è postabile)
saldo_contabile_own   = 0                            ← lo scorporo smette di funzionare
→ saldo_sorgente      = totale − importo_fondo
```

Se il fondo copriva **interamente** la sorgente, quel valore è **zero** — e a
zero scatta questo ramo:

```sql
UPDATE vendite.fatture_fondi_fattura_source
   SET stato = 'ANNULLATO',
       motivo = COALESCE(s.motivo, 'Sorgente gia coperta: saldo effettivo zero…')
```

🔴 **Un fondo `ASSEGNATO`, il cui denaro si è già mosso, viene portato ad
`ANNULLATO` dal primo ricalcolo dopo il posting.** Il `COMMENT` della funzione
dichiara di sapere che quell'automatismo *«opera su fondi GIÀ ASSEGNATI — il
denaro si è già mosso»* e lo lascia in piedi per scelta; ciò che non poteva
sapere è che il posting gli avrebbe fatto scattare il ramo **nel caso normale**.

⭐ **Il rimedio è piccolo e va deciso ora**: lo scorporo deve contare anche il
contributo **postato**. La forma esatta è una decisione — vedi **Q-4**.

> **Il filo che unisce C-2 e C-3.** Il brief madre, in §1-bis, verifica che «con
> un posting atomico la bilancia regge da sé» e ne conclude che *«non c'è un
> secondo lavoro da fare»*. La verifica è giusta e la conclusione è **troppo
> larga**: regge la **bilancia** (i due termini si scambiano lo stesso importo),
> non regge il **codice che quei termini li legge e li riscrive**. C-2 e C-3
> sono entrambi in `vendite`, entrambi su percorso vivo, ed entrambi invisibili
> finché non esiste un movimento.
>
> *Verificare che un'identità algebrica si conservi non è verificare che i
> consumatori la usino ancora bene.*

---

#### C-4 ⚠️ La testata riusata **accorpa bonifici distinti**

`pagamenti.fn_get_or_create_vendite_contabile` — l'unico punto d'ingresso — nel
ramo ordinario (né compensazione né lotto) riusa una testata esistente a parità
di `(centro_riscossione_id, ente_incasso_id, data_contabile, data_registrazione,
stato_id)`.

Due bonifici arrivati **lo stesso giorno sullo stesso canale** finiscono **nella
stessa testata**.

Per i fondi fattura è il comportamento voluto — è un raccoglitore. Ma D3-a dice
*«la contabile **è** il movimento bancario»* e ne fa **l'unità del posting**: con
questo ingresso, «posta la contabile» significa postare anche le righe di un
incasso che non c'entra.

Non è un difetto del codice esistente: è una **collisione fra due significati
della stessa tabella**, raccoglitore e documento. Va sciolta prima di scrivere il
posting — **Q-3**.

---

#### C-5 ⚠️ Una riga aggiunta a una testata `CHIUSA` esce dalla bilancia

`fn_get_saldo_fattura_contabili` esclude le righe la cui **testata** è in stato
finale (`COALESCE(cs.is_final, false) IS FALSE`). Nessun vincolo impedisce però
di inserire una riga `ABBINATA` sotto una testata `CHIUSA` o `ANNULLATA`. Quella
riga:

- **non entra** nel saldo contabile — la testata è finale;
- **non entra** nel saldo movimenti — non è postata;
- **non verrà mai postata**, se il posting parte dalla testata.

È denaro dichiarato che non compare da nessuna parte, e la differenza
`saldo − saldo_contabile` la legge come «manca copertura»: **il fondo si
rigenera**. È lo stesso buco di B-1, dall'altro lato, e le transizioni dichiarate
da sole **non lo chiudono** — governano lo stato della testata, non ciò che le
viene appeso dopo.

---

#### C-6 ⚠️ `obsoleto_dal` **non esiste** in `pagamenti`

D9-a prescrive di ritirare `STORNATA` col pattern `obsoleto_dal`, *«non con
`attivo = false`»*. ✅ La regola è giusta. ⚠️ La colonna **non c'è**:
`obsoleto_dal` esiste su sei tabelle in tutto il database
(`config.codici_errore`, `config.classi_errore`, quattro in `pratiche`) e su
**nessuna** di `pagamenti`.

Il ritiro non è quindi «una riga di CSV»: è **una colonna nuova** su
`vendite_contabili_righe_stati` — e, per simmetria, sulla gemella — più il
consumo, perché una colonna che nessuno legge non ritira niente.

⚠️ Vale anche l'inverso: **oggi il fallback di lookup dello stato è fail-open**.
`fn_sync_contabili_fondo_fattura` cerca `ABBINATA` per `codice_interno` e, se non
lo trova, ripiega su *«un qualunque stato attivo, `ORDER BY s.id LIMIT 1`»* —
cioè `IMPORTATA`. Un catalogo mal configurato non produce un errore: produce
righe nello stato sbagliato. Il ritiro di `STORNATA` è l'occasione per chiudere
anche questo.

---

#### C-7 ⚠️ Nessun indice sulle colonne che le bilance interrogano

| Tabella | Colonne lette a ogni saldo | Indici presenti |
| --- | --- | --- |
| `vendite_contabili_righe` | `fattura_id`, `contabile_id`, `stato_id` | **solo la PK** |
| `vendite_movimenti` | `fattura_id`, `attivo` | PK + l'unico su `contabile_riga_id` |
| `vendite_contabili` | `stato_id` | PK + due unici |

Gli indici FK in questo progetto sono **opt-in** (`dbops.fk_index_policy`), e per
`pagamenti` il seed copre **solo `sepa_mandati`** (tre righe). Quindi ogni
chiamata a `fn_get_saldo_fattura` e `fn_get_saldo_fattura_contabili` è un **seq
scan**, e `fn_saldo_sorgente_fondo` le chiama **entrambe più una terza query**,
per ogni fondo, a ogni ricalcolo.

Oggi è gratis: zero righe. Il costo si presenta insieme ai dati, cioè esattamente
quando la slice 1 comincia a produrne.

⚠️ **Non è una micro-ottimizzazione da rimandare**: gli indici FK qui **non
nascono da soli**, vanno **seminati** in `dbops.fk_index_policy` con
`consentito = true` e — memoria del progetto — con `dll_command` **sempre
valorizzato**, anche a `consentito = false`, perché un CHECK lo impone e la
procedura ne estrae il nome per il DROP.

---

#### C-8 ℹ️ Due asimmetrie minori, da sanare passando

- `vendite_contabili_righe_stati.codice_interno` è **nullable**; la gemella
  `vendite_contabili_stati.codice_interno` è `NOT NULL`. Entrambe portano
  `trgfn_lock_columns('codice_interno', …)`: su una riga con `codice_interno`
  NULL il lock impedisce di valorizzarlo **dopo**. Oggi tutte e sette le righe ce
  l'hanno, quindi è sanabile senza bonifica;
- il CSV `vendite_contabili_righe_stati.csv` **non porta la colonna `id`** e il
  loader usa `primaryKey: "codice"`. Non è un difetto — l'upsert funziona — ma
  significa che gli id di quegli stati **non sono un contratto**: chi scrive una
  funzione non deve mai inciderli, sempre risolverli per `codice_interno`.

---

## 2. Il piano DB

Quattro slice. La **0** è nuova e non è nel brief madre: raccoglie ciò che deve
esistere **prima** che la slice 1 sia scrivibile, compreso il difetto C-1 che
oggi la blocca del tutto.

> ℹ️ **Numerazione.** I passi sono identificati logicamente (`P-1`, `S1-3`…). Il
> numero `YYYYMMDD-NN` va assegnato **al momento della scrittura** rileggendo la
> sequenza — è **globale per data fra tutte le cartelle**, non per cartella. Al
> 2026-08-21 l'ultimo assegnato è `20260821-05`.
>
> ⚠️ **Regola trasversale a tutti i passi su oggetti esistenti**: corpo preso
> dalla **doc auto-generata** `dbzero`, mai da uno YAML di migrazione; nuovo file
> con numerazione successiva; `runOnChange: false` nello stato committato.

---

### 2.0 Slice 0 — Il terreno

Nessuno di questi passi ha valore di dominio. Tutti sono **prerequisiti**: senza,
la slice 1 o non si scrive, o si scrive su un terreno che in CI non esiste.

| | Passo | Fase | Cosa fa | Perché ora |
| --- | --- | --- | --- | --- |
| **P-1** | Vincoli di `centri_riscossione` | `00_schema` | `DROP CONSTRAINT uq_centri_riscossione_compensazione`, poi `CREATE UNIQUE INDEX … (is_compensazione) WHERE is_compensazione` e il gemello `… (is_fondo_fattura) WHERE is_fondo_fattura` | 🔴 **C-1**: senza, il seed dei centri reali fallisce alla terza riga |
| **P-2** | CSV + loader `centri_riscossione` | `80_data` | CSV nuovo con **prima** le due righe già esistenti (id 37 e 38, valori identici), **poi** i centri reali; loader `loadUpdateData` sul modello di `20260213-04` (`runOnChange: true` + `validCheckSums: ANY`) | 🔴 D9-d-1: su un DB ricostruito la tabella è **vuota**, e in CI non funzionano né fondi fattura né compensazioni |
| **P-3** | Resync sequenza IDENTITY di `pagamenti` | `90_end` | `setval` forward-only sulle sequenze di `pagamenti.*`, sul modello di `20260616-02` (che copre `config`) | ⚠️ `id` è `GENERATED BY DEFAULT AS IDENTITY`: un loader con id espliciti **non avanza la sequenza**, e il primo insert automatico collide con la pkey. Oggi `pagamenti` **non è coperto** da nessun resync |
| **P-4** | `vendite_contabili.stato_id` `NOT NULL DEFAULT BOZZA` | `00_schema` | La colonna dice ciò che `fn_get_or_create_vendite_contabile` già fa. Backfill banale: **0 righe** | D9-d-2: da quando lo stato è il cancello fra brogliaccio e registro, una testata senza stato passa i filtri di **entrambi** |
| **P-5** | Coda di P-4 su `fn_get_saldo_fattura_contabili` | `20_code` | Togliere il `LEFT JOIN` e il `COALESCE(cs.is_final, false)`, che diventano codice morto | Un ramo che racconta un caso impossibile è una descrizione falsa del dominio. Nello **stesso lotto** di P-4, non dopo |
| **P-6** | Codici errore di dominio `pagamenti` | `80_data` | Append ai CSV `codici_errore.csv` e `messaggi_errore.csv`, **con la classe**. Nessun loader nuovo: i mirror `runOnChange` esistenti ripescano il CSV | ⚠️ Prerequisito trasversale del brief madre. E un codice non è registrato finché non ha **entrambi** — codice e messaggio di ripiego |
| **P-7** | Bonifica `E_GENERICO` in `pagamenti` | `20_code` | Le quattro funzioni esistenti passano ai codici di P-6 | §1.3: il posting non può nascere pulito accanto a quindici `E_GENERICO`. ⚠️ Cambia il **messaggio**: i consumatori si cercano **dal nome di chi solleva**, non dal testo |
| **P-8** | Doc `manual/` di `sepa_mandati` | doc | L'unica tabella dello schema senza documentazione concettuale, e non è nell'elenco della guida | §3.5 del brief madre. Debito documentale che diventa trappola quando qualcuno progetterà l'addebito SEPA |

⚠️ **P-1 deve precedere P-2 nella timeline.** `00_schema` gira prima di
`80_data`, quindi l'ordine è garantito dalla **fase** — ma se per qualsiasi
ragione P-1 finisse in `80_data` o in un `sql` inline, l'ordine si romperebbe e
la rottura si vedrebbe **solo in CI**.

⚠️ **P-6 prima di P-7 e di tutta la slice 1**, per la ragione geometrica
opposta: `20_code` gira **prima** di `80_data`, quindi una `preCondition` su un
codice errore dentro un changeSet di `20_code` cercherebbe un seed che arriva due
fasi dopo. Trappola già pagata nel cantiere fondi (§8.2-bis, nota 3): **la
preCondition non si mette**, la dipendenza si rispetta nell'ordine di scrittura.

---

### 2.1 Slice 1 — Posting

Chiude: **B-1**, **B-2**, **D3**, **D9**, più i difetti nuovi **C-2**, **C-3**,
**C-5**.

Non tocca le rate. Non tocca il perimetro. Fa esistere **un movimento vero**, che
è la cosa senza la quale tutto il resto si progetta al buio.

| | Passo | Fase | Cosa fa |
| --- | --- | --- | --- |
| **S1-1** | `obsoleto_dal` sui due cataloghi di stato | `00_schema` | Colonna `date` nullable su `vendite_contabili_righe_stati` e `vendite_contabili_stati`. ⚠️ **C-6**: senza, D9-a non è eseguibile |
| **S1-2** | Ritiro di `STORNATA` | `80_data` | `obsoleto_dal` valorizzato **nel CSV**, non con un `UPDATE` diretto. ✅ Verificato nel brief madre: nessuna funzione, vista, riga di backend o frontend nomina `STORNATA` in `pagamenti` |
| **S1-3** | `pagamenti.transizioni_stati_contabile` + `…_contabile_riga` | `00_schema` | Forma già in uso: `(stato_da_id, stato_a_id, attivo, meta)`, UNIQUE sulla coppia, CHECK `da <> a`. **In `pagamenti`**, perché le transizioni stanno dove stanno gli stati |
| **S1-4** | Seed delle due matrici | `80_data` | CSV + loader. Le transizioni ammesse discendono da D9-c: `ANNULLATA` raggiungibile **solo** da `BOZZA`; `POSTATA` solo da `ABBINATA`; nessuna uscita da uno stato finale — grafo esatto in **Q-1** |
| **S1-5** | `trgfn_vendite_contabili_guard_transizione` + gemello riga | `20_code` | `BEFORE UPDATE OF stato_id`, sul modello di `trgfn_resi_guard_transizione`. ⚠️ Un guard restrittivo va confrontato coi pgTAP esistenti **prima**; e una FK nuova fa nascere un guard generico che può **oscurare** quello scritto a mano (i BEFORE ROW girano in ordine alfabetico) |
| **S1-6** | Guard **stato ↔ nullità** sulla riga contabile | `20_code` | `BEFORE INSERT OR UPDATE` su `vendite_contabili_righe`. ⭐ È lo **stesso** guard che nella slice 2 dovrà reggere la rata: si scrive **una volta sola**, con la nullità già prevista. Forma in **Q-2** |
| **S1-7** | Guard **riga sotto testata finale** | `20_code` | `BEFORE INSERT OR UPDATE` su `vendite_contabili_righe`: nessuna riga nuova o riattivata sotto una testata `is_final`. 🔴 **C-5** |
| **S1-8** | 🔴 `fn_sync_contabili_fondo_fattura` non tocca righe finali | `20_code` (`vendite`) | Il lookup e l'aggiornamento si restringono alle righe **non finali**; su una riga finale la funzione decide esplicitamente. 🔴 **C-2**, decisione in **Q-5** |
| **S1-9** | 🔴 `fn_saldo_sorgente_fondo` conta anche il contributo postato | `20_code` (`vendite`) | Lo scorporo smette di filtrare `is_postabile` e comprende il postato/movimentato. 🔴 **C-3**, forma in **Q-4** |
| **S1-10** | ⭐ **La madre**: `pagamenti.fn_posta_contabile(p_contabile_id)` | `20_code` | Il cuore. Dettaglio sotto |
| **S1-11** | Indici e `fk_index_policy` | `80_data` + `90_end` | Seed `consentito = true` con `dll_command` valorizzato per `vendite_contabili_righe(fattura_id)`, `(contabile_id)` e `vendite_movimenti(fattura_id)`. 🔴 **C-7** |
| **S1-12** | pgTAP | test | Vedi §2.4 |
| **S1-13** | Doc `manual/` | doc | Le funzioni e le tabelle nuove, più la **riscrittura al presente** di `fn_get_saldo_fattura` — il cui manuale descrive un residuo che oggi non esiste — e della guida `gestione-dei-pagamenti.md` |

#### ⭐ S1-10 — la madre, in dettaglio

```text
pagamenti.fn_posta_contabile(p_contabile_id bigint)
  RETURNS TABLE(movimenti_creati integer, righe_postate integer, righe_saltate integer, esito text)
  LANGUAGE plpgsql        ← mai `sql`: servono due statement separati
```

**Corpo, nell'ordine:**

1. **guard di parametro** — `NULL` o `<= 0` è un errore, non si normalizza in
   silenzio;
2. **lock della testata** — `SELECT … FOR UPDATE`, per non postare due volte in
   parallelo. ⚠️ Se servisse un advisory lock, **forma a due argomenti**
   (namespace + chiave), mai a uno;
3. **guard di stato della testata** — non finale, e nello stato da cui la
   matrice di S1-4 ammette il passaggio;
4. **selezione delle righe** — solo quelle `is_postabile`, cioè `ABBINATA`. Le
   `SOSPESA` restano dove sono: è D3-a, e non richiede nessun meccanismo nuovo;
5. **rifiuto parlante** — una riga postabile priva di `fattura_id` o
   `billing_account_id` viene rifiutata **qui**, col codice di P-6, prima che ci
   arrivi il trigger di mirror (B-2 riletto secondo §1.3);
6. **due statement separati**, mai una CTE unica: 🔴 con la RLS attiva padre e
   figlio nella stessa snapshot non si vedono e il `WITH CHECK` nega
   fail-closed. Prima l'`INSERT` dei movimenti, **poi** l'aggiornamento delle
   righe a `POSTATA`;
7. **conferma della testata** — `data_conferma`, `user_conferma`, transizione di
   stato. Vedi **Q-6**: la testata va a `CHIUSA` sempre, o solo se non restano
   righe lavorabili;
8. **ripetizione** — l'indice unico `uq_vendite_movimenti_contabile_riga` rende
   il doppio movimento impossibile. La funzione **non** deve trattarlo come un
   errore tecnico da inghiottire: se non c'è nulla da postare, lo **dice**
   (D3-c). Forma esatta in **Q-7**.

**Ciò che la funzione NON fa**, e va scritto perché è una scelta:

- non crea, non modifica e non annulla fondi fattura. §3-bis del brief madre:
  *i fatti si aggiungono, i saldi si leggono, le decisioni le prende una
  persona*;
- non tocca le rate — non esistono ancora nel modello dell'abbinamento;
- non registra nulla in `error_log` di suo: lo fa `fn_log_and_raise_error`
  quando solleva.

---

### 2.2 Slice 2 — Abbinamento alla rata

Chiude: **D1**, **D1-bis**, **D2**.

| | Passo | Fase | Cosa fa |
| --- | --- | --- | --- |
| **S2-1** | `scadenza_id` su `vendite_contabili_righe` | `00_schema` | Colonna nullable + FK a `vendite.fatture_scadenze`. ⚠️ **Da collaudare con un pgTAP prima di impegnarsi**: la tabella puntata ha la **RLS attiva**, e l'integrità referenziale va verificata identica per l'operatore e per il canale di sistema |
| **S2-2** | `scadenza_id` su `vendite_movimenti` + mirror | `00_schema` + `20_code` | Colonna + estensione di `trgfn_vendite_movimenti_sync_contabile_from_riga`, che oggi copia tre campi e ne copierà quattro |
| **S2-3** | Guard di **coerenza** | `20_code` | `scadenza_id` deve appartenere alla `fattura_id` della stessa riga: due colonne che convivono possono contraddirsi |
| **S2-4** | Guard di **quadratura** | `20_code` | `0 ≤ Σ imputato alla rata ≤ importo della rata`. 🔴 **Asimmetrico**: il limite **superiore** è forzabile, quello inferiore no (D1-bis). ⛔ E **nessuna** quadratura per **fattura**: su un documento a credito l'intervallo si inverte e diventa vuoto |
| **S2-5** | La forzatura | `00_schema` + `80_data` + `20_code` | Flag + motivo obbligatorio sulla riga; azione di processo a catalogo (`config.azioni_processo`, area 7); il guard la legge. Vedi **Q-8** |
| **S2-6** | `pagamenti.fn_get_saldo_rata(p_scadenza_id)` | `20_code` | Gemella di `fn_get_saldo_fattura`, per rata. ⚠️ E deve nascere già capace di distinguere **incassato** da **postato**: i centri `is_fondo_fattura` e `is_compensazione` non sono cassa (§4 del brief madre) |
| **S2-7** | Elenco delle rate sovra-incassate | `20_code` | Una vista. ⚠️ Senza, la forzatura è un modo di **nascondere** denaro, non di registrarlo |
| **S2-8** | Indici, pgTAP, doc | vari | `vendite_contabili_righe(scadenza_id)` in `fk_index_policy` |

---

### 2.3 Slice 3 — Perimetro e coda operativa

Chiude: **D5**, **B-3**.

| | Passo | Fase | Cosa fa |
| --- | --- | --- | --- |
| **S3-1** | `enti_incasso.soggetto_ruolo_conto_bancario_id` | `00_schema` | Colonna + FK, **obbligatoria per `tipo = BANCA`** come già lo è `bank_branch_id` (il modello è `chk_enti_incasso_bank_branch_tipo`). ⚠️ Un ente senza conto produce una coda invisibile: si fallisce alla **configurazione**, dove se ne accorge chi può rimediare |
| **S3-2** | 🔴 Unicità **conto `INCASSO` → un solo soggetto** | `00_schema` | Indice unico parziale su `soggetti_ruoli_conti_bancari (conto_bancario_id) WHERE uso = 'INCASSO'`. È **il pezzo che regge il perimetro**: una verità di dominio su cui poggia la sicurezza dev'essere un vincolo, non un'assunzione. ⚠️ Da verificare sui dati esistenti prima — 8 legami in archivio |
| **S3-3** | Configurazione dei conti dei due emittenti | dato | Non è un passo di codice, è configurazione. Ma senza, S3-1 rende inconfigurabile ogni ente |
| **S3-4** | Guard di scope in **scrittura** su `vendite_contabili_righe` | `20_code` | `script.trgfn_guard_emittente_scope('fattura','fattura_id')`, come già su `vendite_movimenti`. ⚠️ Ma **solo quando `fattura_id` è valorizzato**: il caso `DA_ABBINARE` è per definizione senza fattura, e lì il perimetro si deriva dal **conto** |
| **S3-5** | RLS in **lettura** su `pagamenti.*` | `00_schema` | Le tre transazionali. ⚠️ Il predicato non può essere solo «via fattura»: la coda «da abbinare» ha `fattura_id` NULL e sparirebbe **per tutti** — ed è **esattamente** il difetto che D5 esiste per evitare. ⚠️ Memoria: uno zero può essere fail-closed, non un dato |
| **S3-6** | pgTAP di scope + doc | test | ⚠️ Un test di scope **non** si scrive svuotando `app.current_user_id`: non è fail-closed. Il cancello è `app.ruolo_applicativo` |

---

### 2.4 Le verifiche

⚠️ **Il terreno è quasi vuoto**: 2 rate, 0 contabili, 0 movimenti. Nessuna misura
sui dati veri potrà smentire un'ipotesi sbagliata di disegno, e **ogni fixture
rischia di confermare un ramo morto**. Per questo:

- si asserisce la **quadratura**, non i singoli valori: `Σ movimenti = Σ righe
  postate`, `Σ allocazioni ≤ importo rata`;
- `throws_ok` **sempre con lo SQLSTATE** — `P0001` per un errore di dominio.
  Senza, il test accetta anche il crash del guard;
- ⚠️ e **non si nomina il meccanismo nell'asserzione**: il cantiere fondi ha
  pagato esattamente questo — «rifiutato dal CHECK» quando a rifiutare era il
  trigger, perché i **BEFORE ROW girano prima dei CHECK**. Si asserisce il
  *fatto*, non l'ipotesi su chi lo produce;
- il verbo va chiamato in un'**istruzione separata** dall'asserzione: la
  snapshot di statement legge *prima* delle scritture, e il rosso accuserebbe la
  funzione invece del test;
- i quattro pgTAP esistenti di `pagamenti` vanno **rivisti**: tre si fabbricano
  il centro (dopo P-2 non serve più), uno non è transazionale (§1.3);
- baseline: `scripts/pgtap-baseline.sh pagamenti` e `… vendite` **prima e
  dopo**. Le due correzioni in `vendite` (S1-8, S1-9) toccano funzioni che
  `test-fondi-fattura.sql` esercita da mesi.

Copertura minima per la slice 1:

| # | Che cosa verifica |
| --- | --- |
| 1 | Il posting crea **un** movimento per riga `ABBINATA`, e **zero** per `SOSPESA` |
| 2 | `Σ movimenti = Σ righe postate` sulla testata |
| 3 | Dopo il posting `fn_get_saldo_fattura` **cambia** — è la prova che la slice serve |
| 4 | Una riga postabile senza `fattura_id` è rifiutata con il **codice di dominio**, `P0001` |
| 5 | Ripostare la stessa testata non crea un secondo movimento **e lo dice** |
| 6 | Una transizione non dichiarata è rifiutata (per la testata **e** per la riga) |
| 7 | `ANNULLATA` da uno stato diverso da `BOZZA` è rifiutata |
| 8 | 🔴 **C-2**: un ricalcolo della figlia dopo il posting **non** riporta la riga ad `ABBINATA` |
| 9 | 🔴 **C-3**: un fondo interamente postato **non** finisce ad `ANNULLATO` |
| 10 | 🔴 **C-5**: una riga non si inserisce sotto una testata finale |
| 11 | 🔴 **C-1**: `centri_riscossione` accetta **tre** centri non-compensazione |
| 12 | Il centro di banca **esiste dopo il solo giro delle migrazioni** — cioè su un DB ricostruito |

---

### 2.5 Ordine e dipendenze

```text
Slice 0 ── P-1 → P-2 → P-3          (i centri: vincolo, seed, sequenza)
        ├─ P-4 → P-5                (stato testata NOT NULL + codice morto)
        ├─ P-6 → P-7                (codici errore, poi bonifica)
        └─ P-8                      (doc, in qualunque momento)
                │
Slice 1 ────────┼── S1-1 → S1-2                    (obsoleto_dal, ritiro STORNATA)
                ├── S1-3 → S1-4 → S1-5             (transizioni)
                ├── S1-6, S1-7                     (guard sui dati)
                ├── S1-8, S1-9   ← in `vendite`, e vanno INSIEME a S1-10
                └── S1-10 → S1-11 → S1-12 → S1-13
                │
Slice 2 ────────┴── S2-1 … S2-8
                │
Slice 3 ────────┴── S3-1 … S3-6
```

| Dipendenza | Perché |
| --- | --- |
| **P-1 prima di P-2** | Il vincolo saturo respinge il terzo centro: senza, il loader fallisce **in CI**, non su dev |
| **P-6 prima di tutto il resto** | Un codice errore va a catalogo in `80_data`, che gira **dopo** `20_code`: la dipendenza si rispetta scrivendo nell'ordine, **non** con una preCondition |
| **P-4 con P-5** | La colonna obbligatoria e la rimozione del ramo morto sono la stessa decisione. Separarle lascia in giro codice che descrive un caso impossibile |
| 🔴 **S1-8 e S1-9 con S1-10** | Sono la condizione perché il posting non arrechi danno. Applicare la madre senza di loro significa **armare** C-2 e C-3 nello stesso momento in cui si crea il primo movimento |
| **S1-3/4/5 prima di S1-10** | La madre fa una transizione: se la matrice non c'è, la fa senza regola — e la regola arriverebbe dopo, su dati già scritti |
| **Slice 2 dopo Slice 1** | Il guard stato ↔ nullità (S1-6) nasce già prevedendo `scadenza_id`, ma la colonna arriva dopo: la slice 1 si collauda **senza aver deciso niente della 2** |
| **Slice 3 in coda** | La RLS in lettura su una tabella vuota non si può collaudare in modo significativo |

⚠️ **Una slice non è una PR.** La slice 0 può stare da sola. La slice 1 **non si
spezza fra S1-9 e S1-10**: è la coppia che rende sicuro il primo movimento.

---

### 2.6 Cosa il piano **non** fa, e perché

| Non fa | Perché |
| --- | --- |
| **Import del flusso bancario** (D6) | `enti_incasso` è a **0 righe**: non esiste un canale da cui un file possa arrivare, e prima serve la colonna del conto (S3-1) |
| **Abbinamento automatico** (D4) | Una regola di match si tara sui casi veri; con zero incassi si scriverebbe immaginandoli. E finché non esiste l'abbinamento **manuale**, un automatismo non ha dove atterrare |
| **Riferimento di pagamento `RF…`** (§3.6) | È una **proposta**, non una decisione. E il suo posto naturale è il blocco `2.4 DatiPagamento`, che è il passo **2** dell'ordine di Tid |
| **Processo rimborsi** | È D8 (b), l'unica domanda del brief madre senza orientamento — e la Fase D del cantiere fondi lo aspetta. Vedi **Q-9** |
| **Toccare il meccanismo dei fondi** | Le due correzioni S1-8/S1-9 sono il **prezzo del posting**, non un intervento sul meccanismo: quello ha un cantiere suo, e §3-bis dice che nessun automatismo tocca il fondo in base agli incassi |
| **Lista scadenze / scadenzario** | Richiede la slice 2 per non avere colonne false, più cinque prerequisiti FE/BE |

---

## 3. Richieste al backend (fuori perimetro DB)

⛔ Il perimetro di questo cantiere è `db/`. Le richieste al BE si **scrivono**,
non si eseguono.

| | Richiesta | Da quale passo |
| --- | --- | --- |
| **BE-1** | Rigenerare `error_policies_generated.py` dopo P-6: i codici nuovi a catalogo **non hanno classe** lato backend finché non si rigenera, e il cancello `test_error_codes_db_policy_guardrail` lo vede | P-6 |
| **BE-2** | Esporre il posting come **una** chiamata a `fn_posta_contabile` — nessuna orchestrazione Python, nessun `transaction.atomic()` attorno a più statement: l'atomicità è **nella funzione** | S1-10 |
| **BE-3** | Mappare l'esito «niente da postare» su un messaggio che **si vede**: D3-c dice che il replay tecnico tace e la seconda azione voluta parla, e questa distinzione la fa il BE | S1-10 |
| **BE-4** | L'app `apps/pagamenti/` è uno **stub vuoto** (`views.py` = una riga di commento) e `frontend/src/pagamenti/` sono due `.gitkeep`: prima di un posting usabile serve tutto il giro | slice 1 |
| **BE-5** | L'endpoint dell'elenco rate sovra-incassate | S2-7 |

---

## 4. Dove guardare

| Cosa | Dove |
| --- | --- |
| Le decisioni di dominio | [brief-incassi-riconciliazione-rate-promemoria.md](brief-incassi-riconciliazione-rate-promemoria.md) §2-bis |
| Il modello pagamenti in prosa | [gestione-dei-pagamenti.md](/guide/gestione-dei-pagamenti) |
| Le rate: struttura e cosa NON sono | [dbzero/vendite/manual/fatture_scadenze.md](/dbzero/vendite/manual/fatture_scadenze) |
| Il cantiere fondi (chiuso tranne la Fase D) | [brief-db-fondo-fattura-ricalcolo-e-governo.md](brief-db-fondo-fattura-ricalcolo-e-governo.md) §8 |
| Il vincolo difettoso di C-1 | `db/changelog/migrations_v2/00_schema/pagamenti/20260211-14-create-centri-riscossione-mctit.yaml` |
| Le due funzioni da correggere | `vendite.fn_sync_contabili_fondo_fattura` · `vendite.fn_saldo_sorgente_fondo` |
| Il modello di una matrice di transizioni | `vendite.transizioni_stati_commessa` + `vendite.trgfn_commesse_guard_transizione` |
| Il modello di un loader CSV di catalogo | `80_data/changelog/20260213-04-upsert-pagamenti-lu-vendite-contabili-stati-mctit.yaml` |
| Il modello di un resync di sequenze | `90_end/20260616-02-resync-config-identity-sequences-mctit.yaml` |

---

## 5. ❓ Domande aperte — da chiudere **prima** di iniziare

> Nove. Le prime cinque cambiano **cosa si scrive**; le ultime quattro cambiano
> **quanto**. Nessuna è una preferenza di stile.

---

### Q-1 · Il grafo delle transizioni della **riga** contabile

D9-b dice che le transizioni vanno dichiarate, non **quali**. Sette stati, e
almeno quattro archi non sono ovvi:

| Arco | La domanda |
| --- | --- |
| `SOSPESA → ABBINATA` | Una riga sospesa si può risolvere **verso l'alto**, o deve tornare prima a `DA_ABBINARE`? |
| `ABBINATA → DA_ABBINARE` | Si può **disfare** un abbinamento non ancora postato? (Io direi sì: `ABBINATA` non ha ancora mosso denaro) |
| `SCARTATA → *` | `SCARTATA` è `is_final`. Davvero non si torna indietro, nemmeno da un errore di battitura? |
| `IMPORTATA → ?` | Chi la porta via da lì, dato che l'import (D6) è fuori dalla prima slice? Oggi **nessuno**: uno stato senza uscite dichiarate |

⭐ Serve la matrice completa, non un principio. E la stessa domanda vale, più
piccola, per la **testata**: `BOZZA → IMPORTATA` ha senso, se l'import non
esiste?

---

### Q-2 · Il guard **stato ↔ nullità**: quale metà si presidia?

Il verso «`ABBINATA` ⇒ `fattura_id` valorizzato» è chiaro. L'altro no:

> **`DA_ABBINARE` con `fattura_id` già valorizzato — si vieta o si tollera?**

Vietarlo è più pulito. Ma c'è un caso reale: *«so di chi sono i soldi, non so su
quale documento»* — cioè `billing_account_id` noto e `fattura_id` no. E c'è il
caso opposto della slice 2: fattura nota, **rata** no.

Il guard va scritto **una volta sola** e deve già prevedere `scadenza_id`.
Quindi la domanda vera è: **quante combinazioni di nullità sono legittime?**
Propongo tre livelli progressivi (`billing_account` → `fattura` → `scadenza`)
con la regola *«non si salta un livello»* — ma è una decisione di dominio.

---

### Q-3 · La contabile è un **documento** o un **raccoglitore**?

🔴 **Questa è la più importante.** D3-a dice *«la contabile **è** il movimento
bancario»* e ne fa l'unità del posting. Ma `fn_get_or_create_vendite_contabile`
**riusa** la testata a parità di `(centro, ente, data_contabile,
data_registrazione, stato)` — quindi due bonifici dello stesso giorno finiscono
insieme, e postare l'uno posta l'altro (§1.4 C-4).

Tre strade:

| | Strada | Costo |
| --- | --- | --- |
| **a** | Il punto d'ingresso prende un modo «**non riusare**» per gli incassi manuali; i fondi fattura continuano a raccogliere | Un parametro nuovo, ma il significato della tabella resta doppio |
| **b** | L'unità del posting diventa **la riga**, non la testata | ⛔ Contraddice D3-a, e con essa il *«posta tutto il pronto, lascia lì il resto»* che rende `SOSPESA` gratis |
| **c** | Il posting accetta un **sottoinsieme** di righe della testata | ⛔ È (b) travestito: riapre «postata a metà» |

⭐ La mia proposta è **(a)**, perché è l'unica che non tocca una decisione presa.
Ma va detto esplicitamente, perché cambia una firma.

---

### Q-4 · Come si scorpora il contributo **postato** in `fn_saldo_sorgente_fondo`

🔴 **C-3**: oggi lo scorporo filtra `is_postabile IS TRUE` e dopo il posting
smette di funzionare. Due forme:

| | Forma | Nota |
| --- | --- | --- |
| **a** | Estendere il filtro a `is_postabile OR codice_interno = 'POSTATA'` | Semplice, ma incide un codice di stato dentro una formula |
| **b** | Sommare il **movimento** invece della riga, quando la riga è postata | Più fedele — il movimento **è** il fatto — ma la funzione dovrebbe leggere una terza tabella |

⚠️ E c'è una domanda sotto: `is_postabile` sta descrivendo due cose diverse —
*«può ancora essere postata»* e *«conta come copertura in lavorazione»*. Dopo il
posting le due si separano. **Serve un terzo flag** sul catalogo degli stati
(qualcosa come `conta_come_copertura`), o basta l'enumerazione?

---

### Q-5 · Che cosa fa il sync dei fondi quando trova una riga **già postata**

🔴 **C-2**. Restringere il lookup alle righe non finali è il minimo, ma poi:

- **non fa niente** e va avanti — silenzioso, però un fondo il cui importo cambia
  dopo il posting resta scoperto;
- **crea una riga nuova** con la differenza — coerente con «i fatti si
  aggiungono», ma raddoppia le righe per un fondo;
- **solleva** un errore di dominio — onesto, ma fa fallire
  `fn_ricalcola_totali_fattura`, che è su percorso vivo della pipeline.

⚠️ La terza opzione fa cadere un lotto di fatturazione. La prima nasconde. Non
c'è una risposta ovvia.

---

### Q-6 · Dopo il posting, la testata va a `CHIUSA`?

| Caso | Domanda |
| --- | --- |
| Tutte le righe postate | `CHIUSA` è ovvia |
| Restano righe `SOSPESA` | La testata **non** può chiudersi: resterebbero righe lavorabili sotto un documento finale (C-5 al contrario). Quindi resta `VALIDATA`? E chi la chiude poi? |
| Restano righe `DA_ABBINARE` | Idem |

⚠️ Serve anche sapere **da quale stato** si posta: oggi
`fn_sync_contabili_fondo_fattura` crea le sue testate direttamente in
`VALIDATA`, saltando `BOZZA`. Se il posting parte solo da `VALIDATA`, il gesto
umano ha bisogno di un passo «valida» che oggi non esiste.

---

### Q-7 · «Niente da postare»: errore, o esito?

D3-c distingue il **replay tecnico** (silenzio) dalla **seconda azione voluta**
(messaggio). A livello DB sono lo stesso `SELECT`.

- se la funzione **solleva**, il BE deve catturare per distinguere — e il DB
  **scrive comunque in `error_log` prima di sollevare**: catturare l'eccezione
  non basta, è la trappola già registrata nel cantiere DDT senza prezzo;
- se la funzione **ritorna zeri**, il BE decide — ma allora la distinzione fra
  «fatto» e «non c'era niente da fare» esce dal DB.

⭐ Propongo il ritorno a zeri **più** una colonna d'esito nel `RETURNS TABLE`
(`esito text`: `POSTATA` / `NULLA_DA_POSTARE`), così il DB dice il fatto e il BE
decide come raccontarlo. Ma va confermato.

---

### Q-8 · La forzatura del sovra-incasso: azione propria o `approva_rimessa`?

Il brief madre lascia la scelta aperta e propende per una azione **nuova**
(*«la semantica è diversa»*). ✅ Verificato: `config.azioni_processo` ha già
`id 5, area 7, approva_rimessa`.

E una seconda metà non decisa: la forzatura è **a un tempo** (chi ha il permesso
forza) o **a due tempi** (chi opera propone, chi approva conferma), sul modello
`prezzo_override_manuale` + `approva_prezzo_override` che il progetto ha già in
`vendite`?

⚠️ A due tempi serve uno **stato intermedio** sulla riga, e quindi tocca Q-1.

---

### Q-9 · Il **processo rimborsi**: entra in questo cantiere o no?

🔴 È **D8 (b)** del brief madre — *«dove si vede un credito grande che va
rimborsato? Oggi da nessuna parte»* — ed è **il blocco della Fase D** del
cantiere fondi, che aspetta espressamente `pagamenti`.

Due letture, e cambiano il perimetro:

| | Lettura | Conseguenza |
| --- | --- | --- |
| **a** | È una **quarta slice** di questo cantiere | Il cantiere fondi si sblocca; il perimetro cresce |
| **b** | È un cantiere **suo**, che comincia quando esiste un movimento | La slice 1 basta a sbloccarlo; ma resta scritto da qualche parte che qualcuno deve aprirlo |

⭐ Con D3-d il rimborso **non è una macchina nuova** — è una contabile con
importi negativi, cioè la stessa che si sta facendo. Quel che manca non è il
gesto: è **l'elenco che lo fa venire in mente a una persona**. Il che fa
propendere per (b), ma è una decisione di priorità, non di disegno.

---

## 6. Registro delle revisioni

| Data | Cosa |
| --- | --- |
| 2026-08-21 | Stesura. Rimisurato il terreno contro la doc auto-generata e i changelog. ⭐ **Il cantiere fondi è atterrato** (Fasi A/B/C/E/F applicate, `fn_sync_pagamento_fondo_fattura` ritirata) e **la dipendenza si è invertita**: è la Fase D ad aspettare `pagamenti`. 🔴 **Corrette tre misure del brief madre**: B-2 è sbagliato a metà — il guard **c'è già** e il difetto vero è che sollevano tutti `E_GENERICO`; nessun pgTAP di `pagamenti` è in baseline (e uno non è transazionale); la scadenza della «metà fondi» non esiste più. 🔴 **Cinque difetti nuovi misurati, tre bloccanti**: `uq_centri_riscossione_compensazione` è un UNIQUE **totale** su un booleano — il `where:` scritto su `addUniqueConstraint` è stato **ignorato**, e la tabella non può contenere più di **due righe**, il che rende ineseguibile il prerequisito della slice 1; `fn_sync_contabili_fondo_fattura` **riscriverebbe righe già postate** perché il lookup non filtra lo stato; un fondo interamente postato **si auto-annulla** perché lo scorporo di `fn_saldo_sorgente_fondo` filtra `is_postabile`. Piano in **quattro** slice (la 0 è nuova), nove domande aperte in §5 |
