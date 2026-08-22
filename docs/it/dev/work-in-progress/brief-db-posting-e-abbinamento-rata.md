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
> ~~⛔ **Niente è stato applicato.** Nessuna migrazione, nessuna scrittura sul
> database. Questo documento è un piano.~~
>
> ~~✅ **Superato il 2026-08-21: il LOTTO 1 è applicato.**~~ → ⭐ **Superato a
> sua volta: al 2026-08-22 sono applicati i LOTTI 1, 2, 3 e 4.** Trentacinque
> changeSet in tutto. ⭐ **Il primo movimento contabile del progetto esiste**, e
> `fn_get_saldo_fattura` ha smesso di rispondere «residuo = totale» per
> costruzione. Restano da scrivere i lotti **5, 6 e 7**. Stato e verifiche, un
> lotto per sezione: **§6.7** (1), **§6.9** (2), **§6.10** (3), **§6.11** (4).
>
> ✅ **Il piano è scrivibile.** Le nove domande di §5 sono **tutte chiuse**
> (2026-08-21) e i cinque difetti hanno un rimedio deciso. Restano barrate col
> loro perché: tre si sono chiuse **senza essere decise**, ed è la cosa più utile
> da sapere per chi arriva dopo.
> ⭐ E due domande che il piano dava per risolte sono state riaperte e chiuse
> **scrivendo**: lo sdoppiamento del caso 14 (lotto 3) e la chiusura della
> distinta come conseguenza del registrare (lotto 4).
>
> ⭐ **§6.8 dice da dove si riparte**: ~~il lotto 2~~ → il **lotto 5**, la rata.
> §6 resta la mappa dei sette lotti, con le scorciatoie che l'assenza di
> produzione consente.

---

## 0. In una pagina

| | Cosa | Dove |
| --- | --- | --- |
| ✅ **Regge** | D1 (abbinamento sulla riga, niente N:N) · D2 (stato rata derivato) · D3 (posting per testata, madre DB, correzione = importo negativo) · D5 (perimetro dal conto di incasso) · D9 (transizioni dichiarate, `STORNATA` ritirato, annullamento solo in bozza) | §1.1 |
| ⭐ **Superato dai fatti** | La «metà fondi» della slice 1 **è fatta**: Fasi A/B/C/E/F applicate il 15-16/08. `fn_sync_pagamento_fondo_fattura` **non esiste più**. La dipendenza si è **invertita**: ora è il cantiere fondi ad aspettare `pagamenti` | §1.2 |
| 🔴 **Misure sbagliate** | B-2 è sbagliato a metà (il guard **c'è già**, e il difetto è un altro e peggiore) · «due pgTAP rossi in baseline» è **falso** · la scadenza della metà fondi non esiste più. ⭐ **E tre misure di questo brief si sono rivelate sbagliate a loro volta scrivendo il lotto 1** (E_GENERICO, transazionalità dei pgTAP, resync sequenze) | §1.3 · §2.0 |
| ✅ **Difetti nuovi — tutti chiusi** | Erano otto, misurati scrivendo il piano. Al 2026-08-22 restano aperti **zero**: C-1 e C-1-bis (i due vincoli mai nati) col lotto 1, C-5 (le due porte) e la metà azionabile di C-8 col lotto 2, C-2/C-3/C-6 col lotto 3, C-7 col lotto 4 — e la **terza porta** di C-5, che nessuno aveva nominato, col lotto 4 insieme alla chiusura automatica che la rendeva raggiungibile. ⭐ Ogni sezione di §1.4 porta in testa quando e come | §1.4 |
| 📋 **Il piano, logico** | Slice **0** (terreno) → **1** (posting) → **2** (rata) → **3** (perimetro) → **4** (sistemazioni) | §2 |
| ⭐ **Il piano, operativo** | **Sette lotti** — che cosa si scrive, si prova e si applica insieme. Non coincidono con le slice | §6 |
| ✅ **Stato** | **LOTTI 1, 2, 3, 4 e 5 CHIUSI** — 44 changeSet applicati (`20260821-11`…`-34`, `20260821-48`…`-55`, `20260822-01`…`-12`), 9 pgTAP nuovi, doc manuale completa. ⭐ `pagamenti` ha un **vocabolario, due matrici e sette guard**; il fondo fattura ha il suo **quarto stato**; C-2, C-3, C-5 e C-6 sono chiusi. ⭐ **E il primo movimento esiste**, ⭐ **e adesso sa a quale RATA appartiene**. **Prossimo: lotto 6 — il perimetro** | §6.7 · §6.9 · §6.10 · §6.11 · §6.12 |
| ✅ **Domande aperte** | **Zero** — tutte e nove chiuse il 21/08, tre **senza essere decise**. Resta il solo dettaglio **D15-e** | §5 |

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
| **D10** — il fondo vale il residuo **alla nascita**, e poi non insegue (Tid, 2026-08-21) | ✅ Confermata **alla luce del posting**, ed è già così nel codice: il numero lo dà `fn_saldo_sorgente_fondo`, che sull'esempio «fattura 20, incasso 11» risponde **9**. ⭐ Il posting non introduce la regola, la **accende**. 🔴 E lascia un caso senza destinazione — il credito di chi paga *dopo* il fondo non torna nel fondo e **oggi non compare da nessuna parte**: rafforza **Q-9** |
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
E non solo lì — ~~**tutte e quattro** le funzioni di `pagamenti` sollevano
`E_GENERICO`, su una quindicina di punti~~ → 🔴 **rimisurato il 2026-08-21
scrivendo P-7: sono SETTE funzioni e VENTICINQUE punti**, non quattro e quindici.
La stima era per difetto quasi del doppio, e la differenza non è cosmetica: nove
dei venticinque stanno tutti dentro `fn_get_or_create_vendite_contabile`, cioè
l'unico punto d'ingresso della testata. Il brief madre dice «nessun codice
errore di dominio `pagamenti` esiste a catalogo»; il fatto più duro è che il
codice **già scritto** viola la regola dei codici errore, e il posting verrebbe
scritto accanto a lui.

| Funzione | Punti `E_GENERICO` |
| --- | ---: |
| `fn_get_or_create_vendite_contabile` | 9 |
| `trgfn_vendite_movimenti_sync_contabile_from_riga` | 5 |
| `trgfn_vendite_contabili_guard_ente_centro` | 4 |
| `trgfn_enti_incasso_guard_psp` | 3 |
| `fn_get_saldo_fattura` | 2 |
| `fn_get_saldo_fattura_contabili` | 1 |
| `trgfn_vendite_contabili_lotti_guard_compensazione` | 1 |

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

~~⚠️ E uno di essi, `test-enti-incasso-psp.sql`, **non ha `BEGIN;`** in testa e
chiude con un `DELETE FROM pagamenti.centri_riscossione`: è un test **non
transazionale** che cancella righe di catalogo.~~

🔴 **Falso anche questo, verificato il 2026-08-21.** Tutti e quattro i file hanno
il preambolo completo — `BEGIN;`, la riga di contesto operatore,
`SET CONSTRAINTS ALL IMMEDIATE` — e chiudono in `ROLLBACK`. Il `DELETE` finale di
`test-enti-incasso-psp.sql` sta **dentro** la transazione, quindi non cancella
niente. Il file era stato sanato il 2026-08-18, tre giorni prima che questo brief
lo misurasse: la misura leggeva una versione vecchia.

⭐ *La lezione è la stessa che il brief predica altrove, applicata a sé:* una
misura invecchia, e va rifatta prima di costruirci sopra un passo. Il presidio
statico esiste già ed è `scripts/guardrail_pgtap_preambolo.py`, che oggi passa su
463 file — chiedere a lui era più veloce che guardare i file.

#### La scadenza della «metà fondi» non esiste più

§7 del brief madre porta un riquadro rosso: *«se un altro lavoro arriva prima su
quel terreno, il tampone va con lui»*. ✅ **Non serve più**: il tampone è
applicato dal 15/08. Il riquadro va marcato come chiuso.

### 1.4 🔴 Difetti nuovi, misurati — e li **arma la slice 1**

Questi non sono nel brief madre. Sono cinque più tre minori, e i primi tre sono
bloccanti.

> ⭐ **Sono fatti, non domande** — ma tre di essi ne generano una, perché il
> rimedio ammette più forme. La corrispondenza difetto → domanda, e i **due sensi
> diversi** in cui i tre sono «bloccanti», stanno nella tabella in testa a
> **§5**: leggerla prima di decidere da dove partire.

---

#### C-1 ✅ ~~🔴 `centri_riscossione` non può contenere più di **due righe**~~ — **CHIUSO** (lotto 1)

> ✅ **Chiuso il 2026-08-21** dal passo P-1: l'unico totale su un booleano è
> diventato un **unico parziale**, e i due ruoli sono simmetrici. I cinque
> centri reali sono seminati.


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

---

#### C-1-bis ✅ ~~🔴 E c'è un **secondo** vincolo mai nato, nello stesso file~~ — **CHIUSO** (lotto 1)

> ✅ **Chiuso il 2026-08-21** (P-1): `chk_centri_riscossione_ruolo_esclusivo`
> adesso esiste davvero, e un centro non può più essere compensazione **e**
> fondo fattura insieme.


Trovato il 2026-08-21 scrivendo il rimedio di C-1. Il changeSet successivo,
`20260211-21`, aggiunge la colonna `is_fondo_fattura` e — dichiara — un CHECK di
coerenza:

```sql
ALTER TABLE pagamenti.centri_riscossione
  ADD CONSTRAINT chk_centri_riscossione_ruolo_esclusivo
  CHECK NOT (is_compensazione = true AND is_fondo_fattura = true);
```

✅ **Quel vincolo non esiste nel database.** Verificato sull'auto-gen: i vincoli
vivi su `centri_riscossione` sono **tre** — la PK e i due UNIQUE — e nessun
CHECK. Che l'auto-gen i CHECK li stampi è dimostrato dalla tabella accanto:
`enti_incasso` ne mostra due. E il nome
`chk_centri_riscossione_ruolo_esclusivo` compare in **un solo posto** in tutto il
repository: quel file.

**Perché non è nato.** Nel YAML il blocco `- sql:` è annidato **dentro
`addColumn.columns:`**, alla pari di `- column:`, invece di essere un cambio
fratello sotto `changes:`. La lista dei `columns` accetta definizioni di colonna:
un `sql` lì dentro non è un errore, è **una voce che non viene eseguita**. La
colonna è nata, il vincolo no.

🔴 **Conseguenza**: oggi un centro può essere **contemporaneamente** compensazione
e fondo fattura. Non succede — le due righe sono una per tipo — ma è
esattamente la porta che si apre nel momento in cui P-2 popola la tabella. E i
due ruoli sono letti da percorsi diversi (`fn_sync_contabili_fondo_fattura`
cerca `is_fondo_fattura`, `trgfn_vendite_contabili_guard_ente_centro` legge
`is_compensazione`): una riga che dice sì a entrambi li soddisfa **entrambi**.

> ⭐ **Due vincoli mancanti, stesso file, stesso giorno, stessa causa: un blocco
> che lo strumento ha ignorato senza dire niente.** Il che sposta la lezione da
> «attenzione a quell'attributo» a qualcosa di più largo — vedi sotto.

---

#### ⭐ La lezione, che vale oltre il caso

*Un'istruzione che lo strumento non capisce non produce un errore: produce
**silenzio**.* Un `where:` su un `addUniqueConstraint`, un `- sql:` annidato nel
posto sbagliato: nessuno dei due si lamenta, entrambi spariscono, e il file di
migrazione continua a **dichiarare l'intenzione giusta** — quindi chi rilegge il
file non ha motivo di dubitare.

**Il rimedio operativo, non teorico**: un vincolo si verifica **sull'oggetto
vivo** (`docs/it/dbzero/<schema>/tabelle/<nome>.md`), mai sul file che dice di
averlo creato. È la stessa regola già scritta per i corpi delle funzioni,
estesa ai vincoli — e questa volta l'ha pagata due volte lo stesso file.

⚠️ **E valeva come sospetto retroattivo**: se in `20260211-14` e `-21` due
vincoli su tre erano evaporati, la stessa forma andava cercata **altrove**.

✅ **Cercata il 2026-08-21 (passo P-0): nessun altro colpito.** 2804 file YAML
analizzati strutturalmente. ⭐ Il che **restringe la lettura del difetto**: non è
una malattia diffusa nel changelog, sono **due sviste nello stesso schema, in due
changeSet consecutivi, sulla stessa tabella, lo stesso giorno**. Dettaglio ed
esito nel riquadro di §2.0.

---

#### C-2 ✅ ~~🔴 Il sync dei fondi **riscrive righe già postate**~~ — **CHIUSO** (lotto 3)

> ✅ **Chiuso il 2026-08-22**, e non con la toppa che questa sezione discute:
> il quarto stato del fondo (`ESEGUITO`, changeSet `-49`/`-50`/`-51`) porta
> l'atto **fuori dal filtro `ASSEGNATO`** del ciclo, quindi il sync non arriva
> più a quella riga. Resta come **rete** il fail-closed di S1-8 (`-52`), che
> salta e registra un `W_` se l'invariante fosse rotta. L'analisi qui sotto
> resta perché spiega perché il rimedio ovvio era sbagliato.


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

##### ⭐ Che cosa cambia davvero su una riga già postata — misurato il 2026-08-21

Non tutto ciò che l'`UPDATE` scrive è un danno, e distinguere serve a scrivere il
rimedio giusto. **L'importo NON può cambiare**, e lo impediscono tre presidi
messi dalla Fase B:

| Presidio | Effetto |
| --- | --- |
| `trgfn_lock_columns('importo', 'E_FONDO_ATTO_IMMUTABILE', …)` su `fatture_fondi_fattura_source` | l'importo del fondo è **immutabile** |
| `fn_genera_fondi_fattura_source` **create-only** dal 2026-08-15 | il ramo che riallineava l'importo è stato rimosso |
| `fn_fondo_fattura_proponibile` passo 2 — «atto unico» | un fondo esistente, **in qualunque stato**, blocca ogni nuova proposta |

E la riga contabile viene scritta con `r.importo`, cioè **quel** valore congelato.
Quindi su una riga già postata l'`UPDATE` non cambia il numero: cambia

- 🔴 **`stato_id`, che torna ad `ABBINATA`** — il danno, e da solo basta a
  produrre il doppio conteggio;
- ⚠️ `data_valuta`, ricalcolata su `current_date` a ogni giro;
- ⚠️ `contabile_id` e `motivo_sospeso`.

> ⭐ **Ne segue che su una riga in stato finale non c'è nulla che debba
> legittimamente cambiare.** Non è «non facciamo niente e speriamo»: è che non
> c'è niente da fare. È ciò che rende il rimedio una scelta obbligata invece di
> una decisione — vedi sotto.

##### 🔴 E il rimedio ovvio è sbagliato: «restringere il lookup» **peggiora**

La funzione ha **due rami**: se trova la sua riga la aggiorna, **se non la trova
la crea**. Restringere la ricerca alle sole righe non finali significa che su una
riga già postata la ricerca **non trova niente** — e si finisce nel ramo
`INSERT`, che ne scrive **una seconda**. Stesso doppio conteggio, dalla porta
accanto, e stavolta con due righe invece di una.

**La forma giusta è l'opposta:** il lookup deve **continuare a trovare** la riga
in qualunque stato; è l'**azione** a cambiare — riga in stato finale ⇒ `CONTINUE`,
si passa al fondo successivo senza toccare niente.

*Lezione: quando una funzione ha un ramo «se non lo trovo lo creo», restringere
la ricerca non disattiva il ramo — lo attiva.*

##### ✅ E dal 2026-08-21 nemmeno questo serve: il rimedio sta **un livello sopra**

Decisione **D11**: un fondo il cui trasferimento è stato registrato passa a un
quarto stato, **`ESEGUITO`**. Il ciclo di `fn_sync_contabili_fondo_fattura`
filtra `stato = 'ASSEGNATO'`, quindi **non arriva più a quella riga**: non c'è
nessun `UPDATE` da correggere, perché non c'è nessun `UPDATE`.

**C-2 non si tampona: smette di essere raggiungibile.** Di S1-8 resta una rete
fail-closed — salta e logga un `W_` — per il caso in cui l'invariante fosse
rotta. Vedi §2.1.

---

#### C-3 ✅ ~~🔴 Un fondo interamente postato **si auto-annulla**~~ — **CHIUSO** (lotto 3)

> ✅ **Chiuso il 2026-08-22**, dallo stesso quarto stato: un fondo registrato
> non è più `ASSEGNATO`, quindi non entra nel ciclo che lo annullerebbe. E il
> `-52` sposta la ricerca della riga **prima** del calcolo del saldo, così
> nemmeno un'invariante rotta finirebbe nel ramo di annullamento.


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

~~⭐ Il rimedio è piccolo e va deciso ora: lo scorporo deve contare anche il
contributo postato.~~

##### ✅ Rimedio deciso il 2026-08-21, e **non è nella formula**

**D11**: col quarto stato `ESEGUITO` il fondo postato esce dal ciclo, e
`fn_saldo_sorgente_fondo` **non viene più chiamata su di lui**. La formula resta
com'è ed è corretta — il suo scorporo vale finché la riga è in lavorazione, ed è
esattamente quando le viene chiesto.

⚠️ Resta da **dichiarare l'assunzione** nel `COMMENT` e presidiarla con un pgTAP
(**S1-9**).

##### ⚠️ C-2 e C-3 sono **in fila**, non affiancati

Sull'esempio reale (fattura di minimo da 20, incasso di 11, fondo da 9) dopo il
posting il conto è `20 − 11 − 9 = 0`: **scatta C-3**, e la funzione esce dal ramo
`CONTINUE` senza arrivare all'`UPDATE`. C-2 resta invisibile.

🔴 **Ma nel momento in cui si corregge C-3** lo scorporo restituisce di nuovo 9,
la funzione tira dritto, **arriva all'`UPDATE`** e trascina indietro la riga.
Correggerne uno solo **scopre** l'altro — la trappola già registrata nel progetto
(*«togliere un automatismo scopre ciò che l'automatismo copriva»*). ⛔ **S1-8 e
S1-9 non si separano.**

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

#### C-4 ⚠️ Il brief si contraddice su **che cosa sia una contabile**

> 🔴 **Rimisurato il 2026-08-21, e la prima stesura di questo punto era
> sbagliata.** Diceva che `fn_get_or_create_vendite_contabile` contraddice D3-a
> riusando la testata. **Il codice non contraddice niente**: contraddirsi è il
> brief, e il codice implementa la lettura giusta.

`pagamenti.fn_get_or_create_vendite_contabile` — l'unico punto d'ingresso — nel
ramo ordinario riusa una testata esistente a parità di
`(centro_riscossione_id, ente_incasso_id, data_contabile, data_registrazione,
stato_id)`. Due incassi dello stesso giorno sullo stesso canale finiscono nella
**stessa testata**.

##### ⭐ Che cosa modella davvero la testata — l'evidenza è nelle colonne

| Nella testata c'è | Nella testata **non** c'è |
| --- | --- |
| centro di riscossione, ente di incasso | ❌ nessun **importo** |
| data contabile, data registrazione | ❌ nessun riferimento bancario (CRO, TRN, numero operazione) |
| stato, `data_conferma`, `user_conferma` | ❌ niente che identifichi **una** operazione |

E il riferimento della banca sta **sulla riga**: `vendite_contabili_righe.riferimento_ente`,
che il brief madre definisce *«il dato che **arriva** dalla banca»*.

> **La testata non modella un movimento bancario: modella una distinta** — la
> giornata di quel canale. Il singolo incasso è la **riga**, ed è lì che sta la
> sua identità. Il riuso non è un difetto: è il comportamento coerente con ciò
> che la tabella è.

##### 🔴 Il difetto è nel brief madre: due frasi, due definizioni

| Dove | Che cosa dice | |
| --- | --- | --- |
| Intestazione, nota sul nome | *«il documento che **raccoglie N importi arrivati insieme** e li prepara»* | ✅ la distinta — ed è quella che il codice implementa |
| **D3-a**, giustificazione | *«La contabile **è** il movimento bancario»* | 🔴 il singolo bonifico |

La seconda è una frase scritta di passaggio per motivare una decisione — e sta
**esattamente nella riga che dice a chi scriverà il posting che cosa deve fare**.

##### ⭐ E D3-a funziona **solo** con la lettura «distinta»

La parte migliore di D3-a è: *«una riga dubbia va in `SOSPESA`, che non è
postabile — quindi "posta la contabile" significa naturalmente registra tutto il
pronto, lascia lì il resto»*.

Quel ragionamento **richiede più righe**. Con una testata per bonifico, e quindi
una riga sola, non c'è nessun «resto» da lasciare lì: o posti quell'unica riga o
non posti niente.

> **La decisione D3-a è giusta; la sua giustificazione dice il contrario di ciò
> su cui si regge.** Si corregge la frase, non la decisione.

##### ✅ Due fatti che tolgono metà preoccupazione

- **Fondi e incassi veri non condividono mai una testata**: il riuso include il
  **centro di riscossione**, e sono centri diversi (`FONDI_FATTURA` contro
  `BANCA`). Denaro vero e trasferimenti interni sono già separati;
- **una distinta chiusa non si riapre**: il riuso include anche lo **stato**,
  quindi il primo incasso successivo alla validazione apre una distinta **nuova**.

##### ⚠️ Ciò che resta è **operativo**, non di modello

```text
Lunedì, canale banca, distinta unica.
  Anna  inserisce e abbina tre incassi
  Marco inserisce e abbina altri due, e non ha finito di controllarli
  Anna preme «registra»  →  registra anche i due di Marco
```

Il posting per testata resta la decisione giusta, ma su una distinta condivisa
**chi conferma conferma anche il lavoro altrui**. Non è un errore di dati: è un
gesto più largo di quanto chi lo compie si aspetti.

⭐ E il modello ha già dove metterlo: `data_conferma` e `user_conferma` esistono
sulla testata e **nessuno le scrive**.

⛔ **Ciò che non va fatto**: un permesso «si confermano solo le righe proprie».
Spaccherebbe l'unità della distinta e rientrerebbe dalla finestra la postatura
parziale che D3-a esclude dalla porta.

#### C-5 ✅ ~~⚠️ Una riga aggiunta a una testata `CHIUSA` esce dalla bilancia~~ — **CHIUSO** (lotti 2 e 4)

> ✅ **Le porte erano due, e sono diventate tre.** Ingresso e uscita le ha
> chiuse il lotto 2 (`-28` e `-29`); la **terza** — una riga che sta già lì e
> *diventa pronta* — l'ha chiusa il lotto 4 (`20260822-01`), perché prima non
> era raggiungibile e la chiusura automatica della madre la rende reale.


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

##### 🔴 Le porte sono **due**, e la seconda è quella che capita davvero

| | Come ci si arriva | |
| --- | --- | --- |
| **Ingresso** | si **aggiunge** una riga a una distinta già finale | prevista fin dalla prima stesura → **S1-7** |
| **Uscita** | si **chiude** una distinta che ha ancora righe **registrabili** | 🔴 **non prevista, ed è la strada naturale**: si registra, restano due righe non pronte, qualcuno chiude comunque |

⭐ Si chiude con una regola sola e leggibile:

> **Una distinta non si chiude finché ha righe pronte da registrare.**

Chi vuole chiudere ha due strade oneste — registrarle, oppure portarle a
`SOSPESA`/`SCARTATA`, cioè **dire che cosa ne è stato**. Ciò che non si può fare
è chiudere lasciandole a metà. → guard **S1-20**.

##### ⭐ E sotto c'è la stessa confusione del fondo, un piano più giù

| Stato finale | Vuol dire | Le sue righe |
| --- | --- | --- |
| `CHIUSA` | **è fatta** | dovrebbero essere tutte registrate |
| `ANNULLATA` | **non è mai successa** | non devono contare in nessun conto |

Sono **opposti**, e `fn_get_saldo_fattura_contabili` li tratta identici perché
guarda un solo attributo: `is_final`.

> È **esattamente** la coppia che D11 ha separato sul fondo — «annullato perché
> non si fa più» contro «annullato perché già eseguito». Qui si chiama
> `CHIUSA` / `ANNULLATA`, e un unico flag le appiattisce.

🔴 **E il filtro, nel caso `CHIUSA`, non protegge niente**: le righe registrate
sarebbero escluse comunque, perché non sono più postabili. L'unica cosa che quel
filtro riesce a escludere è **proprio la riga anomala**. *Un filtro che nasconde
ciò che non sa gestire sembra un presidio finché non si guarda che cosa esclude
davvero.*

ℹ️ Con S1-7 e S1-20 l'anomalia non può più nascere, e la confusione fra i due
stati finali resta **innocua**: non serve un terzo attributo sul catalogo.

---

#### C-6 ✅ ~~⚠️ `obsoleto_dal` **non esiste** in `pagamenti`~~ — **CHIUSO** (lotti 2 e 3)

> ✅ **Le due metà sono cadute in due lotti diversi**: la colonna
> `obsoleto_dal` e il ritiro di `STORNATA` col lotto 2 (`-24`/`-30`); il
> **fallback fail-open** del lookup di stato col lotto 3 (`-52`), dove uno
> stato mancante è diventato un errore di configurazione invece di una riga
> nello stato sbagliato.


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

#### C-7 ✅ ~~⚠️ Nessun indice sulle colonne che le bilance interrogano~~ — **CHIUSO** (lotto 4)

> ✅ **Chiuso il 2026-08-22** (S1-11), e non solo con tre indici: sono state
> **decise tutte** le FK di `pagamenti` che nessuno aveva deciso, quindi
> `dbops.vw_fk_senza_indice` per quello schema è a **zero righe**.


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

#### C-8 ✅ ~~ℹ️ Due asimmetrie minori, da sanare passando~~ — **CHIUSA la metà azionabile** (lotto 2)

> ✅ La prima — `codice_interno` nullable — è stata sanata passando dal
> changeSet `20260821-24`, come prescritto. ℹ️ La seconda **non era un
> difetto** e resta come nota di lettura: gli id di quel catalogo non sono
> un contratto, e si risolvono sempre per `codice_interno`.


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
> sequenza — è **globale per data fra tutte le cartelle**, non per cartella.
> ⚠️ **Il numero va riletto al momento di scrivere, non copiato da qui.** Questa
> stessa nota ne è la prova: diceva *«l'ultimo assegnato era `20260821-05` la
> mattina e `-06` nel pomeriggio»*, e a fine giornata si era arrivati a **`-39`**.
> ⭐ **E non basta rileggere una volta sola**: il 2026-08-21 Tid ha avvisato che
> **un altro processo genera changeSet in parallelo**, quindi il progressivo può
> essere preso *mentre* si lavora. Si rilegge **prima di ogni file**:
>
> ```bash
> find db/changelog/migrations_v2 -name 'YYYYMMDD-*' -type f \
>   | sed 's#.*/YYYYMMDD-##;s/-.*//' | sort -n | tail -1
> ```
>
> e a fine lotto si controlla che non siano nati **duplicati** (`uniq -d` sulla
> stessa lista): due file con lo stesso numero non li segnala nessuno finché
> l'autogen non li ordina.
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
| **P-0** | ✅ **FATTO** — caccia agli altri vincoli evaporati | verifica | 2804 YAML analizzati strutturalmente: **nessun altro colpito**. Due falsi allarmi identificati e scritti, perché chi ripete la verifica li ritroverà. Dettaglio sotto | La domanda «quanti altri?» ha una risposta: **zero** |
| **P-1** | ✅ **APPLICATO** (`20260821-11`) — Vincoli di `centri_riscossione` | `00_schema` | **Tre** vincoli, non uno: i due unici parziali e il CHECK mai nato. Dettaglio sotto | 🔴 **C-1** e **C-1-bis**: senza il primo il seed dei centri reali fallisce alla terza riga; senza il terzo la tabella accetta un centro che è due ruoli insieme |
| **P-2** | ✅ **APPLICATO** (`20260821-20` + CSV) — CSV + loader `centri_riscossione`, col resync di sequenza in coda | `80_data` | CSV nuovo con **prima** le due righe già esistenti (id 37 e 38, valori identici), **poi** i centri reali; loader `loadUpdateData` sul modello di `20260213-04` (`runOnChange: true` + `validCheckSums: ANY`) | 🔴 D9-d-1: su un DB ricostruito la tabella è **vuota**, e in CI non funzionano né fondi fattura né compensazioni |
| **P-3** | ⭐ **SUPERATO DAI FATTI, e riassorbito in P-2** — ~~Resync sequenza IDENTITY di `pagamenti` in `90_end`~~ | — | Il `setval` forward-only sta **dentro il changeSet del seed** (P-2), che è la forma idiomatica del progetto. Nessun file nuovo in `90_end` | 🔴 La misura era sbagliata: `90_end/20260818-72-resync-identity-sequences-globale` (2026-08-18, `runAlways`, forward-only) copre **tutti** gli schemi, `pagamenti` compreso. Dettaglio sotto |
| **P-4** | ✅ **APPLICATO** (`20260821-12`) — `vendite_contabili.stato_id` `NOT NULL DEFAULT BOZZA` | `00_schema` | La colonna dice ciò che `fn_get_or_create_vendite_contabile` già fa. Backfill banale: **0 righe** | D9-d-2: da quando lo stato è il cancello fra brogliaccio e registro, una testata senza stato passa i filtri di **entrambi** |
| **P-5** | ✅ **APPLICATO** (`20260821-13`, insieme a P-7 sulla stessa funzione) — Coda di P-4 su `fn_get_saldo_fattura_contabili` | `20_code` | Togliere il `LEFT JOIN` e il `COALESCE(cs.is_final, false)`, che diventano codice morto | Un ramo che racconta un caso impossibile è una descrizione falsa del dominio. Nello **stesso lotto** di P-4, non dopo |
| **P-6** | ✅ **APPLICATO** (append ai due CSV, **15** codici) — Codici errore di dominio `pagamenti` | `80_data` | Append ai CSV `codici_errore.csv` e `messaggi_errore.csv`, **con la classe**. Nessun loader nuovo: i mirror `runOnChange` esistenti ripescano il CSV | ⚠️ Prerequisito trasversale del brief madre. E un codice non è registrato finché non ha **entrambi** — codice e messaggio di ripiego |
| **P-7** | ✅ **APPLICATO** (`20260821-13`…`-19`, sei changeSet) — Bonifica `E_GENERICO` in `pagamenti`. ⭐ Siti vivi oggi: **zero**. ⚠️ Ha avuto un **P-7-bis** (`-21`…`-23`): vedi §6.7 | `20_code` | ~~Le quattro funzioni esistenti~~ → **le SETTE funzioni esistenti**, su **venticinque** punti, passano ai codici di P-6 | §1.3: il posting non può nascere pulito accanto a venticinque `E_GENERICO`. ⚠️ Cambia il **messaggio**: i consumatori si cercano **dal nome di chi solleva**, non dal testo — cercati, nessuno asserisce su quei testi |
| **P-8** | ✅ **CHIUSO** — Doc `manual/` di `sepa_mandati` + voce nella guida | doc | ~~L'unica tabella dello schema senza documentazione concettuale~~ → il `manual/` **esisteva già** (rev 2026-08-21, 64 righe, scritto dalla passata di copertura documentale). Restava solo la seconda metà: la tabella **non era nell'elenco** di `gestione-dei-pagamenti.md`, né fra le tabelle né nell'albero del modello. Aggiunta il 2026-08-21 | §3.5 del brief madre. Debito documentale che diventa trappola quando qualcuno progetterà l'addebito SEPA |

#### ⭐ P-0 — il metodo della caccia *(eseguita: esito nel riquadro sotto)*

Non era un passo di codice. Due forme cercate nei changelog, e per ogni riscontro
**un confronto con l'auto-gen**, che è l'unica prova:

| Forma sospetta | Come si cerca | Che cosa produce |
| --- | --- | --- |
| `where:` su `addUniqueConstraint` | l'attributo esiste **solo** su `createIndex` | un unico che nasce **totale** invece che parziale |
| `- sql:` annidato dentro `columns:` di un `addColumn` / `createTable` | indentazione alla pari di `- column:` invece che di un cambio sotto `changes:` | il blocco **non viene eseguito**: la colonna nasce, il vincolo no |

⚠️ **Il confronto va fatto sull'oggetto vivo, uno per uno.** Un riscontro nel
grep non prova che il vincolo manchi (potrebbe essere stato rifatto da un
changeSet successivo), e l'assenza di riscontri non prova che non ci siano altre
forme silenziose. Era una battuta di caccia mirata, non un audit: chiudeva la
domanda «quanti altri, nel raggio di questo cantiere?».

⭐ **E l'avvertenza si è rivelata giusta due volte**: un indice risultava
dichiarato e non vivo (era stato droppato di proposito da un changeSet
successivo), e due forme che *sembravano* il difetto si sono rivelate valide solo
guardando l'oggetto. *Senza il confronto col vivo, la caccia avrebbe prodotto tre
falsi positivi su tre.*

ℹ️ Se emerge qualcosa fuori da `pagamenti`, **non lo si ripara qui**: si annota e
si apre dove vive. Questo cantiere non diventa una bonifica generale.

#### ✅ P-0 — **ESEGUITO il 2026-08-21. Nessun altro colpito.**

Scansione **strutturale** (non testuale) di **2804 file YAML**, tutti parsati
senza errori. Esito, forma per forma:

| Forma cercata | Occorrenze | Colpiti |
| --- | ---: | --- |
| `where:` su un change che non lo prevede | **3** in tutto il changelog | **1** — `20260211-14`, cioè **C-1**. Le altre due sono su `delete` e `createIndex`, che lo prevedono |
| Un change annidato dentro `columns:` | **1** | **1** — `20260211-21`, cioè **C-1-bis** |
| ⭐ *(generalizzazione)* un change **fuori da `changes:`** | 7 | **0** — vedi sotto |

##### ⭐ Due forme che **sembravano** difetti e non lo sono

La caccia ha prodotto due falsi allarmi, e vale la pena scriverli: chi ripete la
verifica li ritroverà, e senza questa nota li «correggerebbe».

**1 · Un change dichiarato direttamente sotto `changeSet`, fuori da `changes:`**
— 7 casi (5 indici trigram, 2 `loadUpdateData`). ✅ **È una forma valida**, e non
per deduzione: i cinque indici trigram **esistono** nell'auto-gen
(`ix_soggetti_ragione_sociale_completa_trgm`, `ix_config_comuni_descrizione_trgm`,
`ix_catalogo_articoli_descrizione_trgm` …), e senza i due seed non ci sarebbero né
valute né stati — su cui poggia mezzo database.

**2 · `createIndex` con `columns: [ { name: x } ]`**, senza il wrapper `column:`
— 54 casi. ✅ **Valida**: verificato sull'auto-gen che
`ix_causali_onere_attivo` e `ix_causali_onere_ordine` esistono davvero.

##### ⭐ E la conclusione cambia la lettura del rischio

I due vincoli evaporati non sono la punta di una malattia diffusa. Sono **due
sviste nello stesso schema, in due changeSet consecutivi (`20260211-14` e `-21`),
sulla stessa tabella, lo stesso giorno**.

> **Non è «il changelog è pieno di queste»: è «quella tabella è stata costruita
> male, una volta».** Il che restringe il rimedio a P-1 e chiude la domanda
> «quanti altri?» con un numero: **zero**.

##### 🔵 Due residui minori, annotati e non lavorati

- ⚠️ **Il rollback di `20260727-37` non restituisce ciò che ha tolto**: droppa
  `ix_tipi_indirizzi_allowed_ambito_attivi` (partial, `WHERE attivo = true`) e lo
  ricrea **senza il `WHERE`**. Innocuo in pratica — quell'indice fu giudicato
  ridondante e i rollback qui non si eseguono — ma è un rollback che mente;
- ⚠️ **Non è verificabile se `createIndex` onori davvero `where:`**: l'unico
  esemplare del repository è stato droppato nel 2026-07-27, quindi non c'è un
  oggetto vivo da guardare. 🔴 **Regola prudenziale, e P-1 la applica già**: per
  un indice **parziale** si usa SQL esplicito, non l'attributo di `createIndex`.

ℹ️ Nulla di tutto questo esce da `pagamenti`, quindi — come previsto — **non si
apre nessuna bonifica altrove**.

#### ⭐ P-3 — perché il passo sparisce, e dove è finito

La riga di P-3 diceva: *«`pagamenti` non è coperto da nessun resync»*, e proponeva
un file in `90_end` sul modello di `20260616-02` (che copre `config`).

🔴 **Non è più vero dal 2026-08-18.** `90_end/20260818-72-resync-identity-sequences-globale`
copre **ogni schema** — filtra sul proprietario, non su una lista di nomi — gira
`runAlways` dopo tutto `80_data`, ed è **forward-only** (confronta il più alto id
già erogato, non `last_value`). Verificato applicato: `databasechangelog` lo
registra all'ultimo migrate.

⭐ **Ma il resync non sparisce: cambia sede.** L'intestazione di quel file dice
di sé una cosa che vale come istruzione: *«è una RETE, non il presidio primario.
Il presidio resta la forma 1: un seed nuovo con id espliciti dovrebbe continuare a
riallineare la propria sequenza da sé»* — la forma che 19 changeSet di `80_data`
già usano, cioè il `setval` **dentro il changeSet che crea la deriva**. Quindi il
resync sta in **P-2**, in coda al loader.

⚠️ E ci sta **forward-only**, non nella forma corta `setval(seq, MAX(id), true)`
usata da alcuni seed più vecchi: quella, su una tabella da cui si cancellassero
righe, riporterebbe **indietro** la sequenza e gli id verrebbero riusati.

> *Un passo di un piano non è una cosa da fare: è una cosa che deve risultare
> vera. Prima di scriverlo si guarda se lo è già diventata.*

---

#### ⭐ P-1 — i tre vincoli, in concreto

```sql
-- 1) l'unico "parziale" che parziale non è mai stato (C-1)
ALTER TABLE pagamenti.centri_riscossione
  DROP CONSTRAINT uq_centri_riscossione_compensazione;

CREATE UNIQUE INDEX uq_centri_riscossione_compensazione
  ON pagamenti.centri_riscossione (is_compensazione)
  WHERE is_compensazione;

-- 2) il gemello che non è mai esistito: oggi i centri fondo-fattura
--    possono essere N, e chi ne sceglie uno prende il primo per id
CREATE UNIQUE INDEX uq_centri_riscossione_fondo_fattura
  ON pagamenti.centri_riscossione (is_fondo_fattura)
  WHERE is_fondo_fattura;

-- 3) il CHECK dichiarato in 20260211-21 e mai nato (C-1-bis)
ALTER TABLE pagamenti.centri_riscossione
  ADD CONSTRAINT chk_centri_riscossione_ruolo_esclusivo
  CHECK (NOT (is_compensazione AND is_fondo_fattura));
```

⚠️ **`DROP CONSTRAINT`, non `DROP INDEX`**: l'oggetto vivo è un **vincolo** —
l'indice ne è solo il supporto e sparisce con lui. Il rimpiazzo invece è un
**indice**, perché in PostgreSQL l'unicità parziale si esprime solo così: non
esiste un `UNIQUE … WHERE` come vincolo di tabella. È la ragione tecnica per cui
l'intenzione originale non poteva essere espressa con `addUniqueConstraint`, e
quindi la ragione per cui era destinata a sparire.

⚠️ **Applicabile senza sanatoria**, verificato: le due righe presenti sono una
per ruolo, quindi tutti e tre i vincoli passano sul dato di oggi. ⛔ Ma è una
verifica sul **dev**: il vincolo va scritto perché regga domani, non perché oggi
non incontri nessuno.

⭐ **Effetto collaterale buono, da notare:**
`fn_sync_contabili_fondo_fattura` sceglie il centro con
`WHERE is_fondo_fattura ORDER BY c.id LIMIT 1`. Con il secondo indice quel
`LIMIT 1` smette di essere una **scommessa sull'ordine degli id** e diventa la
lettura di una riga che il database garantisce unica. La funzione non si tocca:
cambia ciò su cui si appoggia.

ℹ️ **Il pgTAP che lo prova** non asserisce l'esistenza dei vincoli — asserisce il
**comportamento**: un terzo centro non-compensazione **entra**, un secondo centro
di compensazione **no**, un centro che dice sì a entrambi i ruoli **no**.
Asserire «il vincolo esiste» verificherebbe l'ipotesi su chi lo impedisce, non il
fatto.

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
| **S1-1** | ✅ **SCRITTO** (`-24`) — `obsoleto_dal` sui due cataloghi di stato, + `codice_interno` NOT NULL (C-8) e la bandiera `richiede_abbinamento` | `00_schema` | Colonna `date` nullable su `vendite_contabili_righe_stati` e `vendite_contabili_stati`. ⚠️ **C-6**: senza, D9-a non è eseguibile |
| **S1-2** | ✅ **SCRITTO** (`-30` + CSV) — Ritiro di `STORNATA` | `80_data` | `obsoleto_dal` valorizzato **nel CSV**, non con un `UPDATE` diretto. ✅ Verificato nel brief madre: nessuna funzione, vista, riga di backend o frontend nomina `STORNATA` in `pagamenti` |
| **S1-3** | ✅ **SCRITTO** (`-25`) — `pagamenti.transizioni_stati_contabile` + `…_contabile_riga` | `00_schema` | Forma già in uso: `(stato_da_id, stato_a_id, attivo, meta)`, UNIQUE sulla coppia, CHECK `da <> a`. **In `pagamenti`**, perché le transizioni stanno dove stanno gli stati |
| **S1-4** | ✅ **SCRITTO** (`-31`, SQL con lookup per `codice_interno`, non CSV: vedi §6.9) — Seed delle due matrici | `80_data` | CSV + loader. Le transizioni ammesse discendono da D9-c: `ANNULLATA` raggiungibile **solo** da `BOZZA`; `POSTATA` solo da `ABBINATA`; nessuna uscita da uno stato finale — grafo esatto in **Q-1** |
| **S1-5** | ✅ **SCRITTO** (`-26`) — `trgfn_vendite_contabili_guard_transizione` + gemello riga | `20_code` | `BEFORE UPDATE OF stato_id`, sul modello di `trgfn_resi_guard_transizione`. ⚠️ Un guard restrittivo va confrontato coi pgTAP esistenti **prima**; e una FK nuova fa nascere un guard generico che può **oscurare** quello scritto a mano (i BEFORE ROW girano in ordine alfabetico) |
| **S1-6** | ✅ **SCRITTO** (`-27`, guidato dalla bandiera di catalogo) — Guard **stato ↔ nullità** sulla riga contabile | `20_code` | `BEFORE INSERT OR UPDATE` su `vendite_contabili_righe`. ⭐ È lo **stesso** guard che nella slice 2 dovrà reggere la rata: si scrive **una volta sola**, con la nullità già prevista. Forma in **Q-2** |
| **S1-7** | ✅ **SCRITTO** (`-28`, tre mosse: nascere, riattivare, spostare) — Guard **riga sotto testata finale** | `20_code` | `BEFORE INSERT OR UPDATE` su `vendite_contabili_righe`: nessuna riga nuova o riattivata sotto una testata `is_final`. 🔴 **C-5** |
| **S1-8** | ✅ **APPLICATO** (`-52`) — 🛟 Rete: il sync **non lavora** una riga registrata | `20_code` (`vendite`) | ⚠️ **Non è più il rimedio** — dopo S1-15/S1-16 un fondo postato non è più `ASSEGNATO` e il ciclo non lo vede. Resta come **fail-closed** sull'invariante: se un fondo `ASSEGNATO` avesse una riga registrata, si **salta e si logga un `W_`**, non si aggiorna in silenzio. ⛔ Un `W_` si **logga**, non si solleva: questa funzione è su percorso vivo della pipeline |
| **S1-9** | ✅ **APPLICATO** (`-53`) — ~~`fn_saldo_sorgente_fondo` conta il contributo postato~~ → **doc + pgTAP** | doc + test | ✅ **Non serve più toccare la formula**: nessun chiamante le passa più un fondo postato (i tre filtrano `ASSEGNATO` o `DISPONIBILE`). Resta da **scrivere l'assunzione** nel `COMMENT` — *«lo scorporo vale finché la riga è in lavorazione, ed è garantito da ESEGUITO»* — e un pgTAP che asserisce l'invariante, perché un'assunzione non presidiata è la prossima trappola |
| **S1-10** | ✅ **APPLICATO** (`20260822-02`) — ⭐ **La madre**: `pagamenti.fn_posta_contabile(...)` | `20_code` | Il cuore, e dal 2026-08-21 porta anche **ricevuta e dichiarazione** (D13). Dettaglio sotto |
| **S1-11** | ✅ **APPLICATO** (`20260822-03`) — Indici e `fk_index_policy` | `80_data` + `90_end` | Seed `consentito = true` con `dll_command` valorizzato per `vendite_contabili_righe(fattura_id)`, `(contabile_id)` e `vendite_movimenti(fattura_id)`. 🔴 **C-7** |
| **S1-12** | ✅ **APPLICATO** — pgTAP (20 asserzioni) | test | Vedi §2.4 |
| **S1-14** | ✅ **APPLICATO** (`-48`, `-52`, `-53`, `-54`) — ⭐ `vendite_contabili_righe.fondo_source_id` — **colonna vera**, non JSON | `00_schema` + `20_code` | Colonna + FK a `vendite.fatture_fondi_fattura_source`, indice in `fk_index_policy`; i **tre** lettori esistenti (`fn_sync_contabili_fondo_fattura`, `fn_reset_fondi_fattura`, `fn_saldo_sorgente_fondo`) passano dalla colonna. Backfill banale: **0 righe**. Dettaglio sotto |
| **S1-15** | ✅ **APPLICATO** (`-49` il CHECK, `-50` la matrice) — ⭐ Quarto stato del fondo: **`ESEGUITO`** | `00_schema` + `20_code` | Il vocabolario è un **CHECK** (`chk_fondi_source_stato`), non una lookup: si sostituisce. Più la matrice: `ASSEGNATO → ESEGUITO` ammessa, `ESEGUITO` **terminale** (`trgfn_fondi_source_guard_transizione`) |
| **S1-16** | ✅ **APPLICATO** (`-51`) — ⭐ Il **trigger** che scrive `ESEGUITO` | `20_code` | Su `pagamenti.vendite_contabili_righe`, quando la riga entra in uno stato **registrato** e porta `fondo_source_id`. ⭐ È ciò che rende il rimedio **non dimenticabile**: scatta sul fatto, non su chi si ricorda |
| **S1-17** | ✅ **APPLICATO** (`-54`, DROP+CREATE: `updated_source` → `deleted_source`) — ⭐ Il reset diventa **DELETE** | `20_code` (`vendite`) | `fn_reset_fondi_fattura`: l'atto **non eseguito** si cancella invece di tornare `DISPONIBILE`; un `ESEGUITO` **non si tocca mai** — si segnala e basta. 🔴 Sparisce il ramo che scriveva `ANNULLATO` contraddittorio |
| **S1-22** | ✅ **SCRITTO** (`-33`, insieme alla restrizione della riapertura) — ⭐ La quadratura col totale dichiarato scatta a **`VALIDATA`** | `20_code` | **D14-a-bis**: il controllo si sposta dal posting al gesto «ho finito di inserire», dove l'operatore è ancora nel flusso. ⚠️ E `VALIDATA → BOZZA` (riapertura per correggere) è **solo per la manuale** |
| **S1-21** | ✅ **SCRITTO** (`-30` + CSV) — ⚠️ `SCARTATA` **non è più uno stato finale** | `80_data` | D14-a ammette `SCARTATA → SOSPESA`: il CSV la marca `is_final = true` e va corretto. ⛔ Un catalogo che dichiara una cosa mentre la matrice ne permette un'altra insegna il falso |
| **S1-20** | ✅ **SCRITTO** (`-29`) — 🔴 Guard: **non si chiude una distinta con righe registrabili** | `20_code` | `BEFORE UPDATE OF stato_id` su `vendite_contabili`: il passaggio a uno stato finale è rifiutato se restano righe `is_postabile`. È la **seconda porta** di C-5, quella che capita davvero |
| **S1-18** | ✅ **SCRITTO** (`-32`) — ⭐ `origine` (**tre** valori: nasce `GENERATA`, D12-b-bis) + `importo_dichiarato` sulla testata | `00_schema` | Vocabolario chiuso `MANUALE`/`AUTOMATICA` (stessa forma di `fatture_fondi_fattura_source.origine`) + `importo_dichiarato` **nullable**, con CHECK «`AUTOMATICA` ⇒ dichiarato NOT NULL». **D12-b/c**. Tabella a **0 righe** |
| **S1-19** | ✅ **SCRITTO** (`-34`, DROP+CREATE: la firma passa da 8 a 9 parametri) — La distinta manuale è **per operatore** | `20_code` | `fn_get_or_create_vendite_contabile`: il ramo manuale **non riusa più a parità di giornata**. **D12-a** — ⭐ è ciò che rende il lock inutile invece di costruirlo |
| **S1-13** | ✅ **FATTO** — Doc `manual/` | doc | Le funzioni e le tabelle nuove, più la **riscrittura al presente** di `fn_get_saldo_fattura` — il cui manuale descrive un residuo che oggi non esiste — e della guida `gestione-dei-pagamenti.md` |

#### ⭐ S1-14 … S1-17 — «un atto eseguito non è un atto annullato» (Tid, 2026-08-21)

> **La decisione sta nel brief madre, D11.** Qui ci sono i passi e le trappole
> che sono emerse progettandoli.

##### Perché uno **stato** e non una colonna — l'argomento è misurabile

Tutti e tre i lettori dei fondi filtrano **sullo stato**:

| Chi | Filtra | Effetto di un quarto stato |
| --- | --- | --- |
| `fn_sync_contabili_fondo_fattura` | `stato = 'ASSEGNATO'` | 🔴 **C-2 e C-3 spariscono**: il ciclo non vede più il fondo postato |
| `fn_applica_fondi_fattura` | `stato = 'DISPONIBILE'` | non lo applica due volte |
| `vw_fondi_fattura_da_decidere` (capienza) | `stato = 'DISPONIBILE'` | non lo mostra come «non più capiente» |

> ⭐ **Un fondo che esce da `ASSEGNATO` esce da tutti e tre gratis.** Una colonna
> affiancata non lo otterrebbe: i tre continuerebbero a filtrare `stato`, e
> andrebbero modificati **tutti e tre ricordandosene**. È la differenza fra una
> correzione **strutturale** e tre toppe coordinate.

##### ⚠️ Il vocabolario degli stati è un **CHECK**, non una lookup

`fatture_fondi_fattura_source.stato` è una `varchar` presidiata da
`chk_fondi_source_stato`. Aggiungere `ESEGUITO` **non è un append a un CSV**: è
sostituire un vincolo in `00_schema`, forward-only. E la matrice delle
transizioni non è una tabella ma un `CASE` dentro
`trgfn_fondi_source_guard_transizione` — si riscrive lì.

⚠️ **Ordine obbligato**: prima il CHECK e la matrice (S1-15), **poi** il trigger
che scrive lo stato (S1-16). Invertendoli, il primo posting fallirebbe con
«transizione non ammessa» dentro la transazione del posting.

##### ⚠️ Il legame riga ↔ fondo è oggi una stringa in un JSON, e lo si sta rendendo portante

`meta ->> 'fondo_source_id'` non è una relazione: nessuna integrità, nessun
indice, nessuna garanzia che il valore sia un id valido. Ed è già letto in
**tre** posti — `fn_sync_contabili_fondo_fattura`, `fn_reset_fondi_fattura`,
`fn_saldo_sorgente_fondo`. La «regola del 2» è superata da un pezzo.

Appenderci sopra una macchina a stati lo rende **portante**, e un legame portante
va scritto come tale: colonna + FK (S1-14).

🔴 **E la FK apre una trappola nel reset.** `fn_reset_fondi_fattura` fa oggi
tutto in **un unico statement** a CTE: cancella le righe contabili e aggiorna
l'atto. Con S1-17 l'aggiornamento diventa una **cancellazione dell'atto**, e
dentro un solo statement **l'ordine fra CTE non è garantito** rispetto ai
vincoli: la FK potrebbe scattare prima che le righe figlie siano sparite.

Due strade, da scegliere scrivendo: **spezzare in due statement** (prima le
righe, poi gli atti) oppure dichiarare la FK `DEFERRABLE INITIALLY DEFERRED`.
⭐ **Preferisco spezzare**: è la stessa forma già imposta al posting dalla RLS
(§ S1-10 punto 6), e una FK differita nasconde l'ordine invece di dichiararlo.

##### ⚠️ Il trigger di S1-16 scrive **da `pagamenti` verso `vendite`**

Va saputo, non scoperto:

- l'oggetto scritto, `vendite.fatture_fondi_fattura_source`, **non ha RLS** —
  quindi il trigger non incontra il problema «il padre non lo vedo»;
- le colonne bloccate da `trgfn_lock_columns` su quella tabella sono `importo`,
  `fattura_sorgente_id`, `tipo_fondo_fattura_id` e `origine`: **`stato` non è
  fra quelle**, quindi il trigger può scriverlo;
- ⚠️ ma scrivendo `stato` fa scattare `trgfn_fondi_source_guard_transizione`:
  è la ragione dell'ordine obbligato di cui sopra.

##### ⭐ Che cosa diventa il reset, e perché il DELETE è **più** sicuro del vecchio UPDATE

| | Oggi | Con S1-15/S1-17 |
| --- | --- | --- |
| Righe contabili del fondo | DELETE | DELETE (invariato) |
| Riga applicata sulla figlia | DELETE | DELETE (invariato) |
| L'atto **non eseguito** | UPDATE → `DISPONIBILE`, con l'importo **vecchio congelato** | **DELETE** — il giro successivo ne crea uno nuovo, letto sul residuo **di adesso** (D10 applicata a un atto nuovo) |
| L'atto **eseguito** | 🔴 UPDATE → `ANNULLATO`, **lasciando `fattura_figlia_id` valorizzato**: un record che si contraddice | **non si tocca**: è `ESEGUITO`, il reset lo **segnala** nel diario e va avanti |

> **La regola sta in una riga: si cancella solo ciò che non è stato eseguito.
> `ESEGUITO` non si cancella mai.** Ed è il quarto stato a renderla applicabile:
> senza una parola per «eseguito», un reset che cancella non saprebbe da cosa
> tenere le mani lontane.

⚠️ **Due conseguenze da conoscere**, entrambe accettate:

1. **`fatture_fondi_fattura_source` non è storicizzata** (nessuna colonna
   `storicizza`, a differenza per esempio di `fatture_scadenze`): un DELETE è
   definitivo. ✅ Accettato — *un atto mai eseguito è una **proposta**, non un
   fatto*, e §3-bis dice che sono i **fatti** a doversi solo aggiungere;
2. **il DELETE riapre la rigenerazione**, ed è voluto: oggi è la regola
   dell'«atto unico» a impedire al giro notturno di ricreare un fondo, e quella
   guarda se un atto esiste **in qualunque stato**. Cancellandolo, il giro
   successivo lo rifà — leggendo il residuo corrente. È il comportamento
   cercato, ma è un **cambio reale** rispetto a oggi.

##### 🛟 E la rete che resta (S1-8): un `W_`, non un rifiuto

Dopo S1-16 l'invariante è: *un fondo `ASSEGNATO` non ha righe registrate*.
Incontrarne uno significa che l'invariante è rotta — e allora **non si aggiorna
in silenzio**: si salta la riga e si **logga** un codice `W_`.

⛔ **Non si solleva.** `fn_sync_contabili_fondo_fattura` è chiamata da
`fn_ricalcola_totali_fattura`, che è su percorso vivo della pipeline: un errore
lì fa cadere un lotto di fatturazione. E vale la regola del progetto — *i codici
`W_` si loggano e non si sollevano; un `W_` sollevato diventa un HTTP 500*.

#### ⭐ S1-10 — la madre, in dettaglio

```text
pagamenti.fn_posta_contabile(
    p_contabile_id   bigint,
    p_righe_attese   integer,     ← D13: quante righe registrabili ho visto
    p_totale_atteso  numeric      ←      e per che totale
)
RETURNS TABLE(movimenti_creati integer, righe_postate integer,
              righe_saltate    integer, totale_postato numeric,
              esito            text)
LANGUAGE plpgsql        ← mai `sql`: servono due statement separati
```

🔴 **La firma si decide adesso.** Non si sta scegliendo *se* costruire la
dichiarazione: si sta scegliendo **se la funzione ha quei parametri**.
Aggiungerli dopo crea un **overload**, e coi valori di default le chiamate
diventano ambigue — trappola già registrata nel progetto.

**Corpo, nell'ordine:**

1. **guard di parametro** — `NULL` o `<= 0` è un errore, non si normalizza in
   silenzio;
2. **lock della testata** — `SELECT … FOR UPDATE`, per non postare due volte in
   parallelo. ⚠️ Se servisse un advisory lock, **forma a due argomenti**
   (namespace + chiave), mai a uno;
3. **guard di stato della testata** — non finale, e nello stato da cui la
   matrice di S1-4 ammette il passaggio;
4. ⭐ **quadratura della distinta** (D12-e), **solo se `importo_dichiarato` è
   valorizzato**: somma di **tutte** le righe = totale dichiarato. ⚠️ Non può
   stare in un trigger di riga — durante il caricamento la somma torna solo alla
   fine;
5. ⭐ **dichiarazione** (D13): le righe **registrabili adesso** e il loro totale
   devono corrispondere a `p_righe_attese` / `p_totale_atteso`. Se no si
   **rifiuta e non si registra nulla**: il posting è irreversibile, e un avviso
   dopo non ripara niente. ⚠️ È un controllo **diverso** dal precedente — quello
   guarda tutta la distinta contro ciò che è arrivato, questo guarda ciò che si
   sta registrando contro ciò che l'operatore ha visto;
4. **selezione delle righe** — solo quelle `is_postabile`, cioè `ABBINATA`. Le
   `SOSPESA` restano dove sono: è D3-a, e non richiede nessun meccanismo nuovo;
5. **rifiuto parlante** — una riga postabile priva di `fattura_id` o
   `billing_account_id` viene rifiutata **qui**, col codice di P-6, prima che ci
   arrivi il trigger di mirror (B-2 riletto secondo §1.3);
6. **due statement separati**, mai una CTE unica: 🔴 con la RLS attiva padre e
   figlio nella stessa snapshot non si vedono e il `WITH CHECK` nega
   fail-closed. Prima l'`INSERT` dei movimenti, **poi** l'aggiornamento delle
   righe a `POSTATA`;
7. **conferma della testata** — `data_conferma` e `user_conferma`, colonne che
   esistono e che oggi nessuno scrive (**D13**), più la transizione di stato.
   Vedi **Q-6**: la testata va a `CHIUSA` sempre, o solo se non restano
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
| **S2-1** | ✅ **APPLICATO** (`20260822-04`) — `scadenza_id` su `vendite_contabili_righe` | `00_schema` | Colonna nullable + FK a `vendite.fatture_scadenze`. ⚠️ **Da collaudare con un pgTAP prima di impegnarsi**: la tabella puntata ha la **RLS attiva**, e l'integrità referenziale va verificata identica per l'operatore e per il canale di sistema |
| **S2-2** | ✅ **APPLICATO** (`-05` + `-09`) — `scadenza_id` su `vendite_movimenti` + mirror | `00_schema` + `20_code` | Colonna + estensione di `trgfn_vendite_movimenti_sync_contabile_from_riga`, che oggi copia tre campi e ne copierà quattro |
| **S2-3** | ✅ **APPLICATO** (`-06` la domanda fuori dalla RLS, `-08` il guard) — Guard di **coerenza** | `20_code` | `scadenza_id` deve appartenere alla `fattura_id` della stessa riga: due colonne che convivono possono contraddirsi |
| **S2-4** | ✅ **APPLICATO** (`-08`) — ⚠️ **la descrizione qui accanto è SCADUTA**: D14-e ha superato l'asimmetria di D1-bis, la regola è simmetrica e senza estremi fissi (§6.12) — Guard di **quadratura** | `20_code` | `0 ≤ Σ imputato alla rata ≤ importo della rata`. 🔴 **Asimmetrico**: il limite **superiore** è forzabile, quello inferiore no (D1-bis). ⛔ E **nessuna** quadratura per **fattura**: su un documento a credito l'intervallo si inverte e diventa vuoto |
| **S2-5** | ✅ **APPLICATO** (`-04` le colonne, `-08` il guard) — La forzatura | `00_schema` + `20_code` | **Flag** + **motivo facoltativo** sulla riga; il guard rifiuta il primo tentativo con un messaggio parlante e accetta il secondo, che porta la conferma. ⛔ **Nessuna azione di processo, nessun permesso, un tempo solo** — D14-d, che supera D1-bis |
| **S2-6** | ✅ **APPLICATO** (`-07`, e risponde **tre** numeri) — `pagamenti.fn_get_saldo_rata(p_scadenza_id)` | `20_code` | Gemella di `fn_get_saldo_fattura`, per rata. ⚠️ E deve nascere già capace di distinguere **incassato** da **postato**: i centri `is_fondo_fattura` e `is_compensazione` non sono cassa (§4 del brief madre) |
| **S2-7** | ✅ **APPLICATO** (`-10`, e si chiama `vw_rate_fuori_capienza`: il nome del piano diceva meno di ciò che contiene) — Elenco delle rate sovra-incassate | `20_code` | Una vista. ⚠️ Senza, la forzatura è un modo di **nascondere** denaro, non di registrarlo |
| **S2-8** | ✅ **APPLICATO** (`-11` + test + doc) — Indici, pgTAP, doc | vari | `vendite_contabili_righe(scadenza_id)` in `fk_index_policy` |

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

### 2.3-bis Slice 4 — Le sistemazioni *(D15)*

Chiude **D15** e **sblocca la Fase D del cantiere fondi**. Sta dopo la slice 2:
l'elenco si costruisce sui saldi, e i saldi diventano veri col posting e con
l'abbinamento alla rata.

| | Passo | Fase | Cosa fa |
| --- | --- | --- | --- |
| **S4-1** | `pagamenti.compensazioni` → **`pagamenti.sistemazioni`** | `00_schema` | Rinomina + allargamento: `destinazione` (`RIPORTO`/`RIMBORSO`/`COMPENSAZIONE`), importo, cliente, documenti coinvolti, stato, motivo. **0 righe**: la rinomina costa oggi quanto un'ora, fra sei mesi una migrazione |
| **S4-2** | Il verso del legame | `00_schema` | 🔵 **Da confermare (D15-e)**: `sistemazioni.contabile_id` farebbe **sparire** `vendite_contabili.compensazione_id`, la sua FK, il suo unico e il parametro `p_compensazione_id` — invece di rinominarli |
| **S4-3** | `vw_eccedenze_da_sistemare` | `20_code` | La vista: documenti il cui residuo ha **cambiato segno**, **raggruppati per cliente**. ⚠️ È una **vista**, non una tabella: i saldi si leggono, non si conservano |
| **S4-4** | I tre verbi | `20_code` | Riusano meccanismi esistenti: fondo `origine = MANUALE`, contabile a importi negativi, contabile di compensazione. ⭐ **Nessuna macchina nuova** |
| **S4-5** | Codici errore, pgTAP, doc | vari | |

⚠️ `centri_riscossione.is_compensazione` **resta com'è**: parla del *centro*, non
dell'atto.

📮 Con S4-4 si può **chiudere BE-4 e la Fase D** del cantiere fondi, ferma per
scelta finché `pagamenti` non ha questa porta.

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
  dopo**. ⚠️ I passi in `vendite` (S1-14…S1-17) toccano il **reset**, che
  `test-fondi-fattura.sql` esercita da mesi — incluso il ramo «reset bloccato da
  contabile CHIUSA», che con S1-17 cambia comportamento: **quella sezione va
  riscritta, non è una regressione**.

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
| 9 | 🔴 **C-3**: un fondo interamente postato **non** finisce ad `ANNULLATO` — passa a **`ESEGUITO`** |
| 9-bis | Il trigger scrive `ESEGUITO` **nella stessa transazione** del posting, e `ESEGUITO → *` è rifiutato |
| 9-ter | Il reset **cancella** l'atto non eseguito e **non tocca** un `ESEGUITO`, che si limita a segnalare nel diario |
| 9-quater | ⭐ L'invariante di S1-9: **nessun fondo `ASSEGNATO` ha una riga registrata**. È l'assunzione su cui `fn_saldo_sorgente_fondo` regge |
| 10 | 🔴 **C-5**, porta d'ingresso: una riga non si inserisce sotto una distinta finale |
| 10-bis | 🔴 **C-5**, porta d'uscita: una distinta con righe ancora registrabili **non si chiude** |
| 11 | 🔴 **C-1 / C-1-bis**: un **terzo** centro non-compensazione entra; un **secondo** centro di compensazione no; un centro che è **due ruoli insieme** no |
| 12 | Il centro di banca **esiste dopo il solo giro delle migrazioni** — cioè su un DB ricostruito |
| 13 | **D13**: una dichiarazione che non corrisponde **rifiuta e non registra nulla** (nessun movimento creato) |
| 14 | **D12-c**: su una distinta con `importo_dichiarato` valorizzato che non quadra, il posting rifiuta; senza dichiarazione, procede |
| 15 | **D12-a**: due operatori che aprono una distinta manuale nello stesso giorno e canale ne ottengono **due diverse** |

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
                ├── S1-14 → S1-15 → S1-16 → S1-17  ← in `vendite`: colonna, stato,
                │                                     trigger, reset. ORDINE OBBLIGATO
                ├── S1-8, S1-9                     (rete + doc dell'invariante)
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
| 🔴 **S1-14 → S1-15 → S1-16, in quest'ordine** | S1-16 scrive uno stato che S1-15 deve aver già reso ammissibile, leggendo una colonna che S1-14 deve aver già creato. Invertirli fa fallire **il primo posting**, dentro la sua transazione |
| 🔴 **S1-15/S1-16 con S1-10** | Sono la condizione perché il posting non arrechi danno: senza, si crea il primo movimento e **contemporaneamente** il primo modo di rovinarlo (C-2 e C-3) |
| **S1-17 dopo S1-15** | Il reset può cancellare solo se esiste la parola che gli dice da cosa tenere le mani lontane |
| **S1-3/4/5 prima di S1-10** | La madre fa una transizione: se la matrice non c'è, la fa senza regola — e la regola arriverebbe dopo, su dati già scritti |
| **Slice 2 dopo Slice 1** | Il guard stato ↔ nullità (S1-6) nasce già prevedendo `scadenza_id`, ma la colonna arriva dopo: la slice 1 si collauda **senza aver deciso niente della 2** |
| **Slice 3 in coda** | La RLS in lettura su una tabella vuota non si può collaudare in modo significativo |

⚠️ **Una slice non è una PR, e non è un lotto.** Le slice dicono *che cosa rende
vera quale cosa*; i **lotti** di **§6** dicono *che cosa si applica insieme*. La
slice 1, per esempio, si applica in **tre** lotti — e non si spezza fra il terzo
e il quarto, perché è lì che sta la garanzia del primo movimento.

---

### 2.6 Cosa il piano **non** fa, e perché

| Non fa | Perché |
| --- | --- |
| **Import del flusso bancario** (D6) | `enti_incasso` è a **0 righe**: non esiste un canale da cui un file possa arrivare, e prima serve la colonna del conto (S3-1). ⭐ **Ma dal 2026-08-21 il modello lo aspetta**: `origine` e `importo_dichiarato` entrano già in slice 1 (S1-18), e **D12** ne fissa le regole — immutabilità dei fatti, quadratura col totale dichiarato, percorso degli stati. I due **guard** vanno con D6: prima non hanno righe su cui agire |
| **Abbinamento automatico** (D4) | Una regola di match si tara sui casi veri; con zero incassi si scriverebbe immaginandoli. E finché non esiste l'abbinamento **manuale**, un automatismo non ha dove atterrare |
| **Riferimento di pagamento `RF…`** (§3.6) | È una **proposta**, non una decisione. E il suo posto naturale è il blocco `2.4 DatiPagamento`, che è il passo **2** dell'ordine di Tid |
| **Processo rimborsi** | È D8 (b), l'unica domanda del brief madre senza orientamento — e la Fase D del cantiere fondi lo aspetta. Vedi **Q-9** |
| **Il processo rimborsi** | ~~fuori~~ → ✅ **è la slice 4** (D15): una vista, un registro e tre verbi che riusano meccanismi esistenti |
| **Toccare il *meccanismo* dei fondi** | S1-14…S1-17 aggiungono al fondo **una tappa di ciclo di vita** che il posting crea (`ESEGUITO`) e rendono onesto il reset. Non toccano **come si decide un fondo**: quello ha un cantiere suo, e §3-bis resta — nessun automatismo tocca il fondo in base agli incassi |
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

> ✅ **ZERO. Tutte e nove chiuse il 2026-08-21**, in un giro solo con Tid.
>
> Restano qui **barrate, non cancellate**: ognuna porta il *perché* della
> risposta, e tre di esse si sono chiuse **senza essere decise** — vale la pena
> sapere come.
>
> 🔵 **Un solo dettaglio proposto e non deciso**: **D15-e**, il verso del legame
> fra `sistemazioni` e la contabile (passo S4-2).

### ⭐ Domande e difetti sono due cose diverse — ecco dove si incrociano

I **difetti** di §1.4 sono **fatti misurati**: non si decidono, si constatano. Le
**domande** sono **decisioni non prese**. Tre difetti però *generano* una
domanda, perché il rimedio ammette più di una forma difendibile; gli altri no,
perché il rimedio è forzato.

| Difetto (§1.4) | Serve una decisione? | Dove va a finire |
| --- | --- | --- |
| **C-1** + **C-1-bis** — due vincoli mai nati | ❌ no: il rimedio è **forzato** (due indici parziali + il CHECK) | passo **P-1** — ✅ P-0 già fatto: nessun altro colpito |
| **C-2** — il sync riscrive righe postate | ❌ **no** (✅ **Q-5 chiusa** il 21/08) | risolto **per costruzione** da S1-15/S1-16; S1-8 resta come rete |
| **C-3** — il fondo postato si auto-annulla | ❌ **no** (lo era: ✅ **Q-4 chiusa** il 21/08 — **D11** lo toglie dal ciclo) | passi **S1-15/S1-16** |
| **C-4** — il brief si contraddice su cosa sia una contabile | ❌ **no** (✅ **Q-3 chiusa** il 21/08 — **D12**/**D13**) | passi **S1-18/S1-19**, frase corretta nel brief madre |
| **C-5** — riga sotto distinta finale, **due porte** | ❌ no | passi **S1-7** (ingresso) e **S1-20** (uscita) |
| **C-6 · C-7 · C-8** | ❌ no | S1-1 · S1-11 · passando |

E al contrario: **sei domande su nove non hanno nessun difetto dietro** — Q-1,
Q-2, Q-6, Q-7, Q-8 e Q-9 nascevano da ciò che il brief madre aveva lasciato
aperto, o che il piano ha fatto emergere scrivendo. ✅ Tutte chiuse il 2026-08-21.

#### 🔴 «Bloccante» vuol dire due cose, e cambiano il momento in cui si parte

| | Che cosa blocca | Conseguenza pratica |
| --- | --- | --- |
| **C-1** | **meccanicamente**: il terzo `INSERT` non passa | Non aspetta nessuna risposta. **P-1 e P-2 si scrivono subito**, a domande ancora aperte |
| **C-2**, **C-3** | **la correttezza**: non impediscono di scrivere il posting, lo rendono **dannoso il giorno in cui gira** | Servono **prima** Q-4 e Q-5: senza, non si scrive la correzione — e senza la correzione non si applica la madre (vincolo «S1-8/S1-9 insieme a S1-10») |

> ⭐ **In pratica: nessuna slice aspetta più una decisione.** Il piano è completo
> e si può scrivere.

---

### ~~Q-1 e Q-2 · Il percorso della riga e il suo bagaglio~~

> ✅ **CHIUSE INSIEME il 2026-08-21 da Tid** — decisione **D14** nel brief madre.
> Erano due domande perché le avevo poste separate; sono **la stessa domanda
> fatta due volte**: Q-1 il **percorso**, Q-2 il **bagaglio**. Una tabella sola.

**Esito, in breve:**

- `SOSPESA → ABBINATA` **diretta**, `ABBINATA → DA_ABBINARE` ammessa,
  `SCARTATA → SOSPESA` ammessa;
- 🔴 **`SCARTATA` non è più finale** → il catalogo va corretto (**S1-21**);
- **`POSTATA` resta l'unico stato terminale**, ed è giusto: è l'unico dopo il
  quale esiste un fatto;
- ⭐ il database **rifiuta la coerenza** («questa rata è di questa fattura?») e
  **segnala la capienza** («c'è ancora spazio?»), perché la seconda è un fatto
  del mondo;
- ⭐ e la capienza è **una regola sola**, valida per fatture e note di credito, a
  livello rata **e** fattura: *un movimento normale riduce il residuo e non lo
  supera*.

⭐ **Il passaggio che ha sciolto il nodo** non è stato rispondere alle domande: è
stato accorgersi che le quattro situazioni portate da Tid — documento già
saldato, pagamento oltre il totale, pagamento su un documento a credito, rimborso
più grande del credito — **erano lo stesso caso**. *Quattro domande a cui si
risponde una volta sola sono il segno che la domanda era una.*

🔴 **E la nuova forma scioglie una trappola registrata in §5 del brief madre**:
il divieto di replicare la quadratura a livello fattura valeva per l'**intervallo
a estremi fissi**, che su un documento a credito si inverte. La regola di D14 non
ha estremi, quindi passa accanto alla trappola — e il controllo si può fare a
entrambi i livelli senza il filtro «solo se il totale è positivo».

### ~~Q-3 · Che cos'è una contabile, e come si rende consapevole la conferma~~

> ✅ **CHIUSA il 2026-08-21 da Tid** — decisioni **D12** e **D13** nel brief
> madre. Restano **sei** domande.

**Esito, in breve:**

- la testata è una **distinta**, non un movimento bancario (frase di D3-a
  corretta) — ma il raggruppamento **non è la giornata**;
- **manuale = il lotto di lavoro di un operatore** · **automatica = il file**;
- ⭐ così il **lock chiesto da Tid non si costruisce**: la distinta manuale è
  proprietà, non oggetto conteso — niente colonne di blocco, scadenze del lock,
  sblocco d'emergenza, guard su chi tiene la chiave;
- il posting **dichiara la propria portata** (ricevuta + dichiarazione +
  `user_conferma`), e la dichiarazione resta come **rete** anche senza contesa.

⭐ **La forma della chiusura, e vale per le sei rimaste.** La domanda si è chiusa
**allargandosi**: chiedendo il lock, Tid ha portato in scena i flussi esterni; da
lì è emerso che le distinte sono di **due specie**, e quella manuale ha un
confine naturale che rende la contesa impossibile. *Il presidio più economico non
è quello meglio costruito: è quello che il modello rende inutile.*

### ~~Q-4 · Come si scorpora il contributo postato in `fn_saldo_sorgente_fondo`~~

> ✅ **CHIUSA il 2026-08-21 — non rispondendo, ma togliendole l'oggetto.**
> Restano **sette** domande.

La domanda era: *«lo scorporo filtra `is_postabile` e dopo il posting smette di
funzionare — si estende il filtro, o si somma il movimento?»* E sotto ne stava
una di fondo: *`is_postabile` fa due mestieri, serve un terzo flag sul catalogo?*

⭐ **La decisione D11 — il quarto stato `ESEGUITO` — le rende entrambe senza
oggetto.** Nessun chiamante passa più a quella formula un fondo postato: i tre
lettori filtrano `ASSEGNATO` o `DISPONIBILE`, e un fondo postato non è né l'uno
né l'altro. Lo scorporo continua a chiedere *«fra le righe in lavorazione, quali
sono mie?»* — e la risposta torna giusta, perché adesso **la domanda gli arriva
solo quando ha senso porla**.

⚠️ **Ciò che resta non è una decisione ma un debito da saldare subito**:
l'assunzione va **scritta** nel `COMMENT` della funzione e **presidiata** da un
pgTAP → passo **S1-9**. Una formula che regge grazie a un invariante scritto
altrove, e che non lo dichiara, è la prossima trappola di questa stessa specie.

> ⭐ **La forma di questa chiusura vale più della chiusura.** Q-4 e Q-5 sono
> cadute entrambe **senza essere decise**: una perché una misura ha mostrato che
> lo scenario non esisteva, l'altra perché una decisione presa un livello sopra
> le ha tolto l'oggetto. *Prima di rispondere a una domanda di progetto, conviene
> chiedersi se sia ancora una domanda.*

### ~~Q-5 · Che cosa fa il sync dei fondi quando trova una riga già postata~~

> ✅ **CHIUSA il 2026-08-21, prima ancora di essere posta a Tid** — e non da una
> decisione: da una **misura**. Restano **otto** domande.

La domanda presupponeva che l'importo di un fondo potesse cambiare dopo il
posting (*«era 100 e diventa 80: che si fa della differenza?»*), e proponeva tre
strade — tacere, aggiungere una riga di conguaglio, sollevare.

🔴 **Quello scenario non esiste.** La Fase B lo ha chiuso il 2026-08-15 con tre
presidi che si sovrappongono:

| Presidio | Effetto |
| --- | --- |
| `trgfn_lock_columns('importo', 'E_FONDO_ATTO_IMMUTABILE', …)` | l'importo del fondo è **immutabile** |
| `fn_genera_fondi_fattura_source` **create-only** | nessun ramo che riallinea l'importo |
| `fn_fondo_fattura_proponibile`, «atto unico» | un fondo esistente in **qualunque** stato blocca ogni nuova proposta |

E la riga contabile è scritta con quel valore congelato. Quindi **su una riga
già postata non c'è nulla che debba legittimamente cambiare**: il rimedio non è
una scelta fra tre, è l'unico che resta — **saltarla**.

⚠️ **Ciò che resta da sapere è un'altra cosa, e sta in S1-8**: il modo *ovvio* di
saltarla — restringere il lookup — è sbagliato, perché fa cadere nel ramo
`INSERT`. Il lookup deve trovare, l'azione deve astenersi.

> ⭐ **Perché vale la pena tenere la domanda barrata invece di cancellarla.**
> Era una domanda vera **il 2026-08-09**, quando fu scritta nel brief madre; ha
> smesso di esserlo il 15/08, quando un altro cantiere ha congelato l'atto — e
> nessuno se n'è accorto perché i due lavori si guardavano da lontano. *Una
> domanda aperta va rimisurata prima di essere posta: può essere stata chiusa da
> un lavoro che non sapeva di rispondere.*

---

### ~~Q-6 · Il percorso della distinta~~

> ✅ **CHIUSA il 2026-08-21 da Tid** — **D14-a-bis** nel brief madre. I cinque
> stati esistenti vanno bene; la matrice è quella.

Due cose ne discendono e cambiano il piano:

- ⭐ **`VALIDATA` è il gesto «ho finito di inserire»**, quindi la quadratura col
  totale dichiarato (D12-c) si sposta **lì**, non nel posting: l'errore si vede
  mentre l'operatore è ancora nel flusso. → passo **S1-22**;
- ⚠️ **`ANNULLATA` da qualunque stato non registrato**, non solo da `BOZZA` come
  diceva la prima stesura di S1-4.

---

### ~~Q-7 · «Niente da postare»: errore, o esito?~~

> ✅ **CHIUSA il 2026-08-21 da Tid: opzione B.** La funzione **non solleva** —
> risponde normalmente e dichiara l'esito (`POSTATA` / `NULLA_DA_POSTARE`) dentro
> la ricevuta che D13 le ha già dato.

**La ragione, in una riga:** un errore dovrebbe significare che **qualcosa non
funziona**; «non c'era niente da fare» non è qualcosa che non funziona — è una
risposta, e per giunta vera.

⚠️ E c'era un costo concreto nell'altra strada: in questo progetto il database
**scrive nel registro degli errori prima di sollevare**, quindi ogni pulsante
premuto due volte avrebbe lasciato un errore che errore non è — rumore in mezzo
alle cose vere.

✅ Non si perde D3-c (*«chi preme conferma una seconda volta deve sentirselo
dire»*): il messaggio lo mette il frontend leggendo l'esito. **Il database dice
il fatto, chi parla con la persona decide come raccontarlo.**

---

### ~~Q-8 · La forzatura del sovra-incasso: azione propria o `approva_rimessa`?~~

> ✅ **CHIUSA il 2026-08-21 da Tid**: *«per il permesso cade»*. Nessuna delle due
> — **nessuna azione di processo**, e **un tempo solo**, non il pattern
> proponi/approva. Restano il **flag** di forzatura e un **motivo facoltativo**.

⚠️ **Supera D1-bis di agosto**, che chiedeva la forzatura *«gated da un'azione di
processo»* e con motivo **obbligatorio**. Di quella decisione resta l'ultimo
requisito, che è quello che conta: **visibile dopo** — il flag sulla riga e
l'elenco a valle (**S2-7**).

⭐ E non è un cedimento: il presidio si è spostato di forma. Il database **non
accetta in silenzio** — rifiuta il primo tentativo con un messaggio parlante e
accetta il secondo, che porta la conferma. *Chi fa una cosa fuori dall'ordinario
lo dice*, ed è la stessa forma di **D13**.

---

### ~~Q-9 · Il processo rimborsi~~

> ✅ **CHIUSA il 2026-08-21 da Tid** — **D15** nel brief madre. Era l'ultima
> domanda aperta, e si è chiusa **restringendosi**.

**Esito:** non è un processo da costruire. Le tre azioni — riporto su fattura,
rimborso con bonifico, compensazione — **hanno già tutte il loro meccanismo**.
Mancano solo **una vista** (le eccedenze da sistemare, raggruppate per cliente) e
**un registro delle decisioni**, che si ottiene allargando e rinominando il
guscio `pagamenti.compensazioni` → **`pagamenti.sistemazioni`**.

⭐ **La forma della chiusura**: la domanda chiedeva quanto perimetro dare a un
«processo rimborsi». La risposta è stata **misurare che cosa esiste già** — e
sono venute fuori tre macchine su tre. *Prima di dimensionare un lavoro, contare
quanto ne è già costruito da altri cantieri.*

🔵 **Resta un dettaglio proposto e non deciso** (D15-e): girare il verso del
legame — `sistemazioni.contabile_id` invece di `vendite_contabili.compensazione_id`
— che farebbe **sparire** una colonna e un parametro invece di rinominarli.

**Dove sta nel piano:** dopo la slice 2, perché l'elenco si costruisce sui saldi
e i saldi diventano veri col posting e con l'abbinamento alla rata. → **slice 4**,
§2.3-bis.

---

## 6. ⭐ Il piano è **scrivibile**: i lotti di sviluppo

> ✅ **Al 2026-08-21 non resta nessuna decisione da prendere.** Le nove domande
> sono chiuse, i cinque difetti hanno un rimedio deciso, e i tre bloccanti sono
> risolti — due per costruzione, uno con un cambio di vincolo. Da qui si scrive.

### 6.1 Slice e lotti non sono la stessa cosa

Le **slice** di §2 sono **logiche**: dicono quale cosa rende vera quale altra. I
**lotti** qui sotto sono **operativi**: dicono che cosa si scrive, si prova e si
applica *insieme*. Non coincidono — e confonderli fa perdere giri, perché un
lotto si dimensiona su quanto si può **collaudare in un colpo**, non su quanto è
concettualmente affine.

### 6.2 Che cosa permette l'assenza di produzione

⭐ **Nessuna delle tabelle toccate ha righe** (`vendite_contabili`,
`vendite_contabili_righe`, `vendite_movimenti`, `compensazioni`,
`fatture_fondi_fattura_source`), e non esiste un ambiente di produzione. Quindi
si sceglie **sempre la strada corta**, e va detto esplicitamente perché altrove
sarebbe sbagliata:

| | Si fa | Invece di |
| --- | --- | --- |
| **1** | `NOT NULL` e vincoli nuovi **direttamente** | colonna nullable + backfill + `SET NOT NULL` in tre changeSet |
| **2** | **`DROP` + `CREATE`** su firma che cambia (`fn_get_or_create_vendite_contabile`) | un overload di compatibilità che poi nessuno toglie |
| **3** | **Rinomina secca** `compensazioni` → `sistemazioni` | tabella nuova + vista di compatibilità + deprecazione |
| **4** | Il ramo morto si toglie **nello stesso lotto** che lo rende morto (`OR NULL` di `fn_get_saldo_fattura_contabili`) | «lo puliamo dopo» |
| **5** | Il fallback fail-open del lookup stato **si spegne subito** (oggi ripiega su «uno stato qualunque») | si lascia, «tanto non capita» |
| **6** | Le **fixture pgTAP si adeguano nello stesso lotto** che ne rompe il presupposto | si scopre il rosso al giro dopo e sembra una regressione |

🔴 **Ma una cosa NON cambia, ed è la sola cautela che resta**: il database di
sviluppo **non è ricostruito da zero**, la CI sì. Ogni lotto va quindi pensato
per funzionare **su entrambi** — è esattamente la classe di difetto di C-1 (due
righe inserite a mano che in CI non esistono).

### 6.3 Il ciclo di un lotto

```text
1. si SCRIVONO i changeSet del lotto            ← qui
2. si PROVA in BEGIN … ROLLBACK  (SQL + pgTAP)  ← qui
3. si CHIEDE il migrate                         ⛔ lo esegue Tid, a voce
4. pgTAP per davvero + pgtap-baseline.sh
5. si rigenera la doc auto-gen + si scrivono i manual/
6. commit
```

⭐ **Il passo 2 è ciò che permette lotti grossi.** Un lotto provato in transazione
annullata arriva al migrate **già verificato**, quindi il numero di round-trip
crolla — ed è il round-trip, non il migrate, la cosa cara qui.

⚠️ **Ed è anche ciò che protegge dalla regola più rigida del progetto**: un
changeSet già mergiato **non si modifica mai**. Un errore scoperto dopo l'apply
non si corregge — si corregge *in avanti*, con un changeSet nuovo. Provare prima
è l'unico modo di non accumulare correzioni.

⚠️ Nel passo 2, il `BEGIN … ROLLBACK` dev'essere **dentro il file eseguito**:
ricomporre lo script perdendo il wrapper significa scrivere davvero.

### 6.4 I sette lotti

| | Lotto | Contiene | Perché sta insieme | Prima corsa possibile |
| --- | --- | --- | --- | --- |
| **1** | ✅ **CHIUSO** (21/08: `-11`…`-20` alle 19:38, `-21`…`-23` alle 20:07) · **Il terreno** | P-0 … P-8 (P-3 riassorbito in P-2) | Non dipende da niente e sblocca tutto: senza i centri, in CI non funzionano nemmeno fondi e compensazioni | ~~subito~~ → **fatto il 2026-08-21**, §6.7 |
| **2** | ✅ **CHIUSO** (21/08, applicato alle 21:19) · **Vocabolario, transizioni e guard** | S1-1…S1-7 · S1-18…S1-22 | Tutto `pagamenti`, tutto dichiarativo: nessun verbo nuovo. Si collauda per **rifiuto** — cosa il database non lascia più fare | ~~dopo 1~~ → **scritto il 2026-08-21**, §6.9 |
| **3** | ✅ **CHIUSO** (22/08, applicato alle 00:36) · **Il fondo si difende** | S1-14…S1-17 · S1-8 · S1-9 · 🔴 **+ il fail-open di C-6** | Tutto `vendite`. ⭐ **Deve precedere il lotto 4**: la difesa atterra prima della cosa da cui difende. ⚠️ **Aggiunto il 2026-08-21**: lo spegnimento del fallback fail-open del lookup stato (C-6) sta **qui** e non nel lotto 2, benché C-6 lo leghi al ritiro di `STORNATA`. Motivo: è dentro `fn_sync_contabili_fondo_fattura`, che **S1-8 riscrive comunque** — farlo due volte in due lotti consecutivi è spreco e rischio. 🔴 E il lotto 2 lo ha reso **peggiore**: con `richiede_abbinamento` una riga che ripiegasse su `IMPORTATA` (bandiera `false`) sfuggirebbe anche al guard nuovo, e resterebbe non registrabile per sempre senza che nessun errore lo dica | ~~dopo 2~~ → **fatto il 2026-08-22**, §6.10 |
| **4** | ✅ **CHIUSO** (22/08, applicato alle 01:29) · **La madre** | S1-10 · S1-11 · S1-12 · S1-13 | ⭐ È il lotto in cui **nasce il primo movimento**, e da lì `fn_get_saldo_fattura` smette di mentire | dopo 3 |
| **5** | ✅ **CHIUSO** (22/08) · **La rata** | S2-1 … S2-8 | Slice 2 per intero | ~~dopo 4~~ → **fatto**, §6.12 |
| **6** | **Il perimetro** | S3-1 … S3-6 | Slice 3 per intero. ⚠️ La RLS su tabelle vuote non si collauda: conviene **dopo** che il lotto 4 ha prodotto dati | dopo 5 |
| **7** | **Le sistemazioni** | S4-1 … S4-5 | Slice 4. 📮 Chiude **BE-4** e sblocca la **Fase D** del cantiere fondi | dopo 5 |

⚠️ **Il lotto 3 non si spezza e non si salta.** Applicare la madre (4) senza la
difesa (3) significa creare il primo movimento **e contemporaneamente** il primo
modo di rovinarlo — C-2 e C-3 insieme, su percorso vivo della pipeline di
fatturazione.

ℹ️ I lotti **6 e 7 sono indipendenti fra loro**: entrambi partono dopo il 5, e
l'ordine fra i due è una scelta di priorità. Il 7 sblocca un altro cantiere, il 6
chiude un buco di sicurezza in lettura.

### 6.5 Che cosa si può fare **senza** aspettare un migrate

Quattro cose, ed è il modo di non stare fermi fra un lotto e l'altro:

| | Cosa | Perché non serve il migrate |
| --- | --- | --- |
| ~~**P-0**~~ | ✅ **Fatta il 2026-08-21**: era un confronto fra changelog e doc auto-gen — si legge, non si scrive. Esito: **nessun altro colpito** |
| **P-8** | Il `manual/` di `sepa_mandati` | è documentazione |
| ~~—~~ | ~~La riscrittura delle **fixture pgTAP** di `pagamenti`~~ → ✅ **non serviva**: il modulo «cerca il centro, se non c'è inserilo» usa `WHERE NOT EXISTS`, quindi col seed di P-2 il ramo di fabbricazione muore da sé; e nessuno dei quattro era non-transazionale (§1.3). I quattro sono rimasti verdi senza toccarli | i pgTAP girano in transazione |
| — | La **stesura** dei lotti successivi | scrivere non è applicare |
| ⭐ **doc** | I `manual/` degli oggetti **già applicati** — è il passo 5 del ciclo, e i lotti 1 e 2 lo hanno lasciato indietro entrambi fino a che non è stato chiesto | è documentazione, e l'auto-gen ha già il **cosa**: il `manual/` porta il **perché** |

### 6.7 ✅ Lotto 1 — CHIUSO: che cosa contiene, e che cosa è costato

✅ **CHIUSO il 2026-08-21.** Tredici changeSet, applicati in **due** migrate
eseguiti da Tid: `20260821-11` … `-20` alle **19:38**, e il passo **P-7-bis**
(`-21` … `-23`) alle **20:07**, scritto dopo il primo migrate e quindi
forward-only.

**Verifica post-migrate** (baseline rieseguita da Tid dopo il secondo giro):

| Misura | Esito |
| --- | --- |
| `pgtap-baseline.sh pagamenti` | **0 rossi su 6** |
| `pgtap-baseline.sh vendite` (199 file) | 5 rossi, **tutti già in baseline** — nessuna regressione |
| `codici-errore-baseline.sh` | **0 accumuli · 0 ristretti · 0 rientrati** — non c'era niente da riallineare |
| ⭐ Siti `E_GENERICO` vivi in `pagamenti` | **0** (erano 25) |
| ⭐ Siti `E_PARAMETRO_INVALIDO` vivi in `pagamenti` | **0** |

| Passo | File |
| --- | --- |
| **P-6** | append di **15 codici** a `80_data/sql/config/codici_errore.csv` e `messaggi_errore.csv` (id messaggio 939…953). Nessun loader nuovo: il mirror `20260614-08` è `runOnChange` e li ripesca |
| **P-1** | `00_schema/pagamenti/20260821-11-alter-centri-riscossione-vincoli-ruolo` |
| **P-4** | `00_schema/pagamenti/20260821-12-alter-vendite-contabili-stato-not-null` |
| **P-5 + P-7** | `20_code/pagamenti/20260821-13-update-fn-get-saldo-fattura-contabili-stato-obbligatorio` |
| **P-7** | `20_code/pagamenti/20260821-14` … `-19` (le altre sei funzioni) |
| **P-7-bis** | `20_code/pagamenti/20260821-21` … `-23` — i sei guard di chiamata escono da `E_PARAMETRO_INVALIDO` (forward-only, dopo il migrate) |
| **P-2 (+P-3)** | `80_data/changelog/20260821-20-upsert-pagamenti-centri-riscossione` + `80_data/sql/pagamenti/centri_riscossione.csv` |
| **P-8** | voce `sepa_mandati` in `docs/it/guide/gestione-dei-pagamenti.md` (il `manual/` c'era già) |
| test | `db/pgtap/pagamenti/test-centri-riscossione-vincoli-ruolo.sql` (10) · `test-vendite-contabili-stato-obbligatorio.sql` (7) · `test-fn-get-or-create-vendite-contabile.sql` passa da 8 a **9** asserzioni |

#### ⭐ Il passo 2 del ciclo, eseguito

Il lotto è stato applicato **in una transazione annullata**, con il
`BEGIN … ROLLBACK` **dentro il file eseguito** — e l'SQL **estratto dagli YAML**,
non ricopiato, così quello che si è provato è esattamente quello che verrà
applicato.

| Verifica | Esito |
| --- | --- |
| I 10 changeSet applicati in transazione + le 17 asserzioni dei due pgTAP nuovi + 3 anti-overload | ✅ **20/20**, `ROLLBACK` |
| I **quattro** pgTAP esistenti di `pagamenti`, col lotto iniettato dentro la loro transazione | ✅ 4/4 verdi, nessun `not ok` |
| Arità dei segnaposti: 25 chiamate a `fn_log_and_raise_error` confrontate col `%s` del messaggio a catalogo | ✅ **0 disallineamenti** — con meno valori dei segnaposti `format()` alza 22023 e l'errore di dominio **sparisce** |
| Stato del database dopo le prove | ✅ invariato: 2 centri, 0 codici nuovi, `stato_id` ancora nullable |
| `liquibase validate` | ✅ nessun errore · `status --verbose` elenca i 10 changeSet nell'ordine giusto |
| `guardrail_run_on_change.py` · `guardrail_pgtap_preambolo.py` | ✅ verdi (debito `throws_ok` invariato: 131/131) |
| Baseline `pagamenti` **prima** | 4 file esistenti verdi, 0 in baseline. I due nuovi sono rossi finché il migrate non c'è: **è atteso**, non una regressione |
| ⭐ **Secondo giro (P-7-bis)**, stessa forma | ✅ 6/6, `ROLLBACK`; i **sei** pgTAP di `pagamenti` iniettati nella loro transazione: 0 `not ok` |

⚠️ **Una cosa che la prova NON copriva**: la simulazione gira come **owner**,
perché il DDL lo pretende, quindi la RLS non era esercitata. ✅ **Colmato dai
fatti**: dopo i due migrate la baseline è stata rieseguita da Tid come
`zeroerp_app` — 0 rossi su 6.

⭐ **Che cosa ha reso il passo 2 utile, e dove non è bastato.** Le due prove in
transazione annullata hanno intercettato tutti i difetti *tecnici* prima
dell'apply: una `CREATE TABLE AS INSERT … RETURNING` che PostgreSQL non ammette,
l'arità dei segnaposti, il rischio di overload dai `%TYPE`. ⛔ **Non hanno
intercettato l'unica cosa che ha richiesto un secondo migrate**: una **decisione**
riaperta — la scelta dei codici errore. *Il round-trip caro non è il migrate: è la
decisione che si riapre dopo.*

#### 🔴 La scelta dei codici errore, rivista su segnalazione di Tid

La prima stesura mandava **tutti e sei** i guard di parametro di
`fn_get_or_create_vendite_contabile` su `E_PARAMETRO_INVALIDO`, appoggiandosi alla
tabella «Regola operativa» di
[correzione-e-generico.md](../work-done/correzione-e-generico.md) — il brief che
*ha combattuto* la battaglia contro `E_GENERICO` — che per «parametro obbligatorio
mancante o non valido» prescrive proprio quel codice.

⚠️ **Tid ha obiettato che così il problema si ribalta su BE e FE, e aveva ragione
per una ragione che il codice errore da solo non mostra**: il valore che si
passava era un **nome di parametro PL/pgSQL**. L'operatore avrebbe letto

> *«Parametro non valido: p_centro_riscossione_id (obbligatorio, > 0)»*

cioè un messaggio di qualità `E_GENERICO` **sotto un codice registrato**. Il
refactor di aprile aveva tolto quel difetto un piano più giù — dove il *codice*
era generico — e qui rientrava dalla finestra nel **valore**.

⚠️ E c'è una seconda ragione, che non è un'opinione: `docs/it/dev/api.md`
(§Tassonomia errori) dichiara `E_PARAMETRO_INVALIDO` **candidato allo split** —
113 funzioni lo nominano, 111 con verità 400 e 2 con verità 404 — e ne trae la
regola *«un codice usato per due cose si spezza a monte, non si rimappa a valle»*.

##### ⭐ La linea che divide non è «guard di parametro sì/no»: è **chi può rimediare**

| Guard | Codice | Classe | Perché |
| --- | --- | --- | --- |
| `p_centro_riscossione_id`, `p_data_contabile` | 🆕 **`E_CONTABILE_DATI_OBBLIGATORI`** (952) | `DATO_ERRATO` → 400 | li sceglie una **persona** in un form: *«Per aprire una distinta contabile serve il centro di riscossione»* |
| i quattro `<= 0` su id dove il `NULL` è **ammesso**, e lo stato interno vuoto | 🆕 **`E_PAGAMENTI_CHIAMATA_NON_VALIDA`** (953) | `TECNICO` → 500 | non escono da nessuna interfaccia: li produce solo un **chiamante rotto** |
| `fn_get_saldo_fattura` / `..._contabili`, `p_fattura_id <= 0` | 🆕 **`E_PAGAMENTI_CHIAMATA_NON_VALIDA`** (953) | `TECNICO` → 500 | stessa ragione |

##### 🔴 Secondo giro: `E_PARAMETRO_INVALIDO` esce del tutto

La prima correzione lasciava i sei guard di chiamata su `E_PARAMETRO_INVALIDO`.
⚠️ **Tid ha respinto anche quello**, con una ragione che i documenti confermano:
*«esiste ancora perché il BE deve gestire vecchie funzioni che non sono riuscito a
correggere»* — cioè **è un debito, non una sede**.

* **D11** di [brief-db-be-classe-codici-errore](../work-done/brief-db-be-classe-codici-errore.md):
  *«`E_PARAMETRO_INVALIDO` **no** — denominatore sicuro + `note`, e **cantiere
  suo**»*: uno **split rimandato**, con una classe di compromesso;
* **§9.1**: *«la regola che chiude il **rubinetto** — vietare **nuovi** codici
  generici — resta in coda: rincorrere gli esistenti senza chiudere il rubinetto è
  la forma in cui questi registri non calano mai»*.

⭐ **E il precedente esisteva già, di due giorni**: `E_VENDITE_PRICING_ESITO_ASSENTE`
(2026-08-19, `TECNICO`) nasce perché il rubinetto B-7 respinse
`E_PARAMETRO_INVALIDO` su un guard analogo — *«lì non c'è nessun parametro
invalido, c'è un'invariante rotta»*.

⚠️ **`TECNICO` non è un'etichetta: sposta lo status da 400 a 500**, ed è il punto.
`DATO_ERRATO` significa *«chi l'ha fatta può correggerlo e riprovare»*: su un bug
del chiamante non c'è niente da correggere, e un 400 manda l'operatore a cercare
un campo che non esiste. Per la stessa ragione la chiave **`campo` esce** dal
contesto di quei sei punti.

⚠️ **E questa correzione è forward-only**: il migrate del lotto 1 è girato alle
19:38 del 2026-08-21, quindi non si è potuta fare in place. Sono i changeSet
`20260821-21`, `-22`, `-23` (passo **P-7-bis**), con il corpo preso dagli YAML
applicati **dopo averli verificati identici all'oggetto vivo** — `pg_get_functiondef`
non si poteva usare perché scioglie i `%TYPE`.

ℹ️ **Cosa non cambia**: sul codice dell'operatore il campo da evidenziare viaggia
ancora nella chiave `campo`, che `fn_log_and_raise_error` fa uscire sul canale
`COLUMN`, e l'`ui_action` di `DATO_ERRATO` per quel codice è
`highlight_form_fields`.

⭐ **La decisione è presidiata**, non solo scritta: `test-fn-get-or-create-vendite-contabile.sql`
guadagna un'asserzione (test 9) che verifica che il rifiuto **nomini il dato e non
il parametro**. Un `throws_ok` con `P0001` non basterebbe: `P0001` dice «errore di
dominio», non *quale* — qui il discriminante è proprio il testo che l'operatore
leggerà.

> *Un codice registrato non garantisce un messaggio leggibile: il codice sceglie
> la frase, ma il valore che ci si infila dentro lo sceglie chi solleva.*

---

#### 📮 Le richieste che il lotto lascia aperte

* **BE-1** — rigenerare `error_policies_generated.py`: i 13 codici nuovi non
  hanno classe lato backend finché non si rigenera, e il cancello
  `test_error_codes_db_policy_guardrail` lo vede;
* dopo il migrate: `scripts/codici-errore-baseline.sh` va **riallineato**, perché
  `E_GENERICO` perde 25 punti d'uso e può risultare «ristretto». ⚠️ È una
  decisione, non una formalità: si aggiorna sapendo *perché* quella famiglia non
  è più coperta.

---

### ~~6.8 ⭐ Da dove si riparte: il **lotto 3**~~ — ✅ **fatto** (storico)

> ~~Il lotto 2~~ → ✅ **chiuso e applicato il 2026-08-21** (§6.9). Il terreno è
> posato e `pagamenti` ha un vocabolario, due matrici e sei guard.
>
> ~~Il lotto 3~~ → ✅ **chiuso e applicato il 2026-08-22** (§6.10). Il fondo ha il
> suo quarto stato e C-2, C-3 e C-6 sono chiusi.
>
> ~~Il lotto 4~~ → ✅ **chiuso e applicato il 2026-08-22** (§6.11). ⭐ **Il primo
> movimento del progetto esiste**, e `fn_get_saldo_fattura` ha smesso di
> rispondere «residuo = totale» per costruzione.
>
> ⭐ **Da dove si riparte adesso: il LOTTO 5, «la rata»** — S2-1 … S2-8, la
> slice 2 per intero. Adesso ha senso: l'abbinamento alla rata si progetta su
> movimenti che esistono, non immaginandoli.
>
> ⚠️ E prima di scriverlo vanno lette le code aperte in fondo a §6.10 e §6.11:
> due decisioni di dominio ereditate e **tre richieste al backend**, fra cui il
> verbo che chiama la madre — che oggi è pronta e non la chiama nessuno.

🔴 **Il lotto 3 — «il fondo si difende» — non si spezza e non si salta.** È tutto
in `vendite`, e **deve precedere il lotto 4**: applicare la madre del posting
senza la difesa significherebbe creare il primo movimento **e contemporaneamente
il primo modo di rovinarlo**.

| | Passo | Fase |
| --- | --- | --- |
| **S1-14** | `fondo_source_id` diventa una **colonna con FK**, non una stringa in un JSON. Tre lettori la usano già: la «regola del 2» è superata da un pezzo | `00_schema` + `20_code` |
| **S1-15** | Il quarto stato del fondo: **`ESEGUITO`**. ⚠️ Il vocabolario è un **CHECK**, non una lookup: si sostituisce in `00_schema`, e la matrice è un `CASE` dentro il guard | `00_schema` + `20_code` |
| **S1-16** | Il **trigger** che scrive `ESEGUITO` quando la riga contabile entra in uno stato registrato. ⭐ Scatta sul fatto, non su chi si ricorda | `20_code` |
| **S1-17** | Il reset diventa **DELETE**: un atto non eseguito si cancella, un `ESEGUITO` non si tocca mai | `20_code` |
| **S1-8** | 🛟 La rete: il sync **non lavora** una riga registrata — si salta e si **logga** un `W_` | `20_code` |
| **S1-9** | L'assunzione di `fn_saldo_sorgente_fondo` scritta nel `COMMENT` e presidiata da un pgTAP | doc + test |
| 🔴 **+ C-6** | Spegnere il **fallback fail-open** del lookup stato in `fn_sync_contabili_fondo_fattura` | `20_code` |

#### ⚠️ Quattro cose da sapere prima di cominciare

1. 🔴 **L'ordine S1-14 → S1-15 → S1-16 è obbligato**: il trigger scrive uno stato
   che il CHECK deve aver già reso ammissibile, leggendo una colonna che deve già
   esistere. Invertirli fa fallire **il primo posting**, dentro la sua transazione.
2. ⭐ **Il lotto 2 ha già chiuso metà di C-2**: con `POSTATA` terminale il
   database **rifiuta** il ritorno ad `ABBINATA`. ⚠️ Ma «rifiuta» su percorso vivo
   significa **una pipeline che cade** — `fn_ricalcola_totali_fattura` chiama il
   sync sempre. Il lotto 3 lo toglie dal ciclo, che è la vera soluzione.
3. 🔴 **E il lotto 2 ha peggiorato C-6**: con la bandiera `richiede_abbinamento`,
   una riga che ripiegasse su `IMPORTATA` (bandiera `false`) sfuggirebbe **anche**
   al guard nuovo, restando non registrabile per sempre senza che nessun errore lo
   dica.
4. ⚠️ **`test-fondi-fattura.sql` esercita il reset da mesi**, incluso il ramo
   «reset bloccato da contabile CHIUSA» che con S1-17 **cambia comportamento**:
   quella sezione **va riscritta, non è una regressione**.

⚠️ E vale la regola sui messaggi (§6.7, riquadro sui codici errore): i guard del
lotto 3 parlano quasi tutti a **una persona**, quindi vogliono codici di dominio e
frasi in italiano — non un codice trasversale col nome di una colonna dentro.

---

### 6.9 ✅ Lotto 2 — CHIUSO

**Undici changeSet** (`20260821-24` … `-34`), quattro pgTAP nuovi, sette codici
errore (954…960). ✅ **Applicati da Tid il 2026-08-21 alle 21:19**, ~~baseline
verificata~~ — ⚠️ **la verifica copriva `pagamenti`, non `vendite`**, e in
`vendite` è rimasto un rosso: vedi il riquadro in fondo a questa sezione.
Dati a regime: 5 transizioni sulla distinta, 10 sulla riga,
`SCARTATA` non più finale, `STORNATA` ritirata.

📚 **Doc manuale scritta nello stesso giro** (passo 5 del ciclo): otto
`manual/` nuovi — le due matrici e i sei guard — più l'aggiornamento di
`centri_riscossione`, `vendite_contabili`, `vendite_contabili_righe_stati` e
`fn_get_or_create_vendite_contabile`, e le due tabelle nuove nella guida
`gestione-dei-pagamenti.md`. ⭐ Nessun oggetto auto-generato di `pagamenti` resta
senza documentazione concettuale.

| Passo | File |
| --- | --- |
| **S1-1** (+C-8) | `00_schema/…-24-alter-stati-contabili-obsoleto-dal` — `obsoleto_dal` sui due cataloghi, `codice_interno` NOT NULL, **`richiede_abbinamento`** |
| **S1-3** | `00_schema/…-25-create-transizioni-stati-contabile` — le due matrici |
| **S1-5** | `20_code/…-26-create-trgfn-contabili-guard-transizione` — i due guard |
| **S1-6** | `20_code/…-27-create-trgfn-righe-guard-stato-dati` |
| **S1-7** | `20_code/…-28-create-trgfn-righe-guard-distinta-finale` — C-5 ingresso |
| **S1-20** | `20_code/…-29-create-trgfn-contabili-guard-chiusura` — C-5 uscita |
| **S1-2 · S1-21** | `80_data/…-30-riancora-mirror-stati-contabili` + i due CSV |
| **S1-4** | `80_data/…-31-seed-transizioni-stati-contabile` |
| **S1-18** | `00_schema/…-32-alter-vendite-contabili-origine` |
| **S1-22** | `20_code/…-33-create-trgfn-contabili-guard-validazione` |
| **S1-19** | `20_code/…-34-recreate-fn-get-or-create-vendite-contabile-per-operatore` |

#### ⭐ Le quattro decisioni di forma prese scrivendo

**1 · `richiede_abbinamento`: la regola sta nel catalogo, non nel guard.** S1-6
poteva portarsi dentro `WHERE codice_interno IN ('ABBINATA','POSTATA')`. Sarebbe
stato **un grafo scritto nel codice**, cioè ciò che S1-5 evita mettendo le
transizioni in tabella — e il catalogo è già progettato per bandiere così
(`is_postabile`, `is_final`). ⚠️ E **non era derivabile** da quelle: `ABBINATA`
pretende l'abbinamento e **non è finale**.

**2 · 🔴 `origine` è a TRE valori, e la terza è nata da una misura.** D12-b ne
prevedeva due. Misurando **chi crea davvero le distinte** è emerso che l'unico
creatore esistente — il sync dei fondi — **non è né l'uno né l'altro**: con due
valori, il **100% delle distinte di oggi** porterebbe una parola falsa. ⇒
`GENERATA` (Tid). Decisione scritta nel **brief madre, D12-b-bis**.

**3 · Le matrici nascono `{"manuale": false}`.** `scripts/check_i18n_keys.py`
cerca le `label_key` dei seed `transizioni_stati_*` nei locales e **fallisce** se
mancano — e il frontend di `pagamenti` è **due `.gitkeep`**. ⚠️ Non significa
«automatica»: significa **«non ancora esposta come pulsante»**.

**4 · Il seed delle matrici è SQL, non CSV.** Le altre matrici si seminano da CSV
con gli **id** degli stati. ⛔ Qui non si può: il CSV di
`vendite_contabili_righe_stati` non porta la colonna `id`, e inciderli in un CSV
di transizioni li renderebbe un contratto **per sbaglio**. Si risolve per
`codice_interno`, e un `loadUpdateData` non sa fare lookup. ⭐ Non è la «seconda
sorgente di verità» contro cui il progetto mette in guardia: l'SQL è l'**unica**
sorgente, e resta `runOnChange` per avere la garanzia di un mirror.

#### La prova, e la regressione che ha trovato

| Verifica | Esito |
| --- | --- |
| Gli 11 changeSet + le 31 asserzioni dei 4 pgTAP nuovi, in transazione annullata | ✅ **31/31**, `ROLLBACK` |
| I **sei** pgTAP esistenti di `pagamenti`, col lotto iniettato nella loro transazione | ✅ 6/6, dopo l'adeguamento qui sotto |
| Stato del database dopo le prove | ✅ invariato: 0 colonne nuove, 0 tabelle transizioni, `SCARTATA` ancora finale |
| Arità dei segnaposti: 54 chiamate a `fn_log_and_raise_error` | ✅ 0 disallineamenti |
| `liquibase validate` · i due guardrail statici | ✅ verdi (debito `throws_ok` invariato: 131/131) |

🔴 **La prova ha trovato una regressione, ed era il guard che funziona.**
`test-vendite-contabili-stato-obbligatorio.sql` (scritto nel lotto 1) chiudeva una
distinta che ha ancora una riga `ABBINATA` — cioè **esattamente** ciò che S1-20
ora vieta. La fixture è stata adeguata **nello stesso lotto** (§6.2 punto 6),
passando ad `ANNULLATA`.

⭐ **E il test ci ha guadagnato in precisione**: quello che verifica è il filtro su
`is_final`, e `ANNULLATA` è il caso in cui quel filtro ha davvero un mestiere — su
`CHIUSA` non protegge niente, perché le righe registrate sarebbero escluse
comunque.

#### ⚠️ Che cosa il lotto 2 NON ha fatto, e dove è finito

* **il fail-open del lookup stato (C-6)** → spostato al **lotto 3**: è dentro
  `fn_sync_contabili_fondo_fattura`, che **S1-8 riscrive comunque**. 🔴 E il lotto
  2 lo ha reso **peggiore** — vedi la riga del lotto 3 in §6.4;
* **le transizioni del flusso** (uscite da `IMPORTATA`) → con D6;
* **`VALIDATA → BOZZA` ristretta a `MANUALE`** vive nel **guard**, non nella
  matrice: una matrice `(da, a)` non porta condizioni. Chi legge la sola matrice
  non la vede — ed è la ragione per cui il codice errore la nomina.

📮 **Coda**: rigenerare `error_policies_generated.py` per i **sette** codici nuovi
(BE-1, cumulativa con quella del lotto 1).

#### 🔴 Un rosso lasciato in `vendite` — **da rivedere**

⚠️ **La riga «baseline verificata» qui sopra copriva `pagamenti`, non `vendite`.**
Il 2026-08-21, dopo l'apply, `db/pgtap/vendite/test-fondi-fattura.sql` è
rosso — e **non era in baseline**: era verde. È un rosso nuovo.

```text
ERRORE: La distinta contabile VC_2026… ha ancora 1 righe pronte da registrare:
        non si puo' chiudere.
        pagamenti.trgfn_vendite_contabili_guard_chiusura  (S1-20, changeSet -29)
```

**Chi lo ha causato, verificato e non dedotto.** Il guard è applicato a
`orderexecuted` **13257**; i due changeSet del cantiere *liste drawer lotto*
(`-38`, `-39`) sono a 13273/13274, cioè **dopo**, e quel test non nomina nulla di
ciò che toccano. È S1-20, non altro.

**Ed è il guard che funziona, come nel caso già pagato dentro il lotto 2**
(`test-vendite-contabili-stato-obbligatorio.sql`). La differenza è **dove**
stava il file: quello era in `pagamenti/` e la prova del lotto lo ha trovato;
questo è in `vendite/`, e la prova non ci è arrivata.
📌 *Un guard nuovo su una tabella di `pagamenti` va grepato su **tutta** la
suite, non sullo schema che lo ospita: chi chiude una distinta a mano può vivere
in un altro dominio.* I due pgTAP di `pagamenti` che chiudono una distinta sono
verdi (riverificati: 7/7 e 10/10).

**Il difetto era nella fixture, non nel guard.** Il test portava la distinta a
`CHIUSA` con un `UPDATE` diretto mentre la riga nata dal sync del fondo era
ancora `ABBINATA` — l'**unico** stato con `is_postabile = true` del vocabolario.

**Correzione applicata** (`db/pgtap/vendite/test-fondi-fattura.sql`): prima di
chiudere, la riga passa a **`SOSPESA`**, che è una delle due uscite indicate
dall'HINT del guard stesso. In più la distinta si sceglie **una volta** in una
temp table (`tmp_contabile_ff`) e si riusa nei due statement: prima era una
sotto-select ripetuta, cioè due scelte indipendenti sulla stessa riga.
✅ **20/20 verdi.**

⭐ **Perché non snatura il caso 14** («Reset bloccato da contabile CHIUSA»):
`vendite.fn_reset_fondi_fattura` blocca su `c.stato_id = CHIUSA` **e**
`cr.attivo IS TRUE`, e **non guarda lo stato della riga**. Sospesa, la riga resta
attiva e agganciata, la distinta si chiude, il reset è bloccato come il test
pretende.

✅ ~~🔵 **Da rivedere — la domanda vera è di dominio, non di fixture.**~~ — **CHIUSA
il 2026-08-22 da Tid: il caso 14 si SDOPPIA.** La *contabilizzazione* (distinta
chiusa, denaro mai registrato) resta qui, e lì `SOSPESA` smette di essere un
ripiego e diventa la fixture **giusta** del caso che questo file racconta; la
*registrazione* (riga `POSTATA` col suo movimento, atto `ESEGUITO`, reset che non
lo tocca) vive in `db/pgtap/vendite/test-fondo-fattura-eseguito.sql`. Il
ragionamento originale resta qui sotto perché è quello che ha portato alla
risposta.

~~`SOSPESA` è la
via più corta; `POSTATA` sarebbe più fedele a «contabilizzata», che è ciò che il
nome del caso 14 promette, ma pretende un `vendite_movimenti` (indice unico su
`contabile_riga_id`) e attraversa gli altri due guard dello stesso lotto. Se il
caso 14 deve collaudare *una distinta chiusa dopo che il denaro è stato
registrato* — e non solo *una distinta chiusa* — allora la fixture giusta è
`POSTATA` e questo è un rattoppo che regge il verde senza dire la cosa giusta.
**Decisione di dominio, non mia.**~~

~~⛔ **Perimetro NON chiuso**: gli altri file di `vendite/` che toccano
`pagamenti.vendite_contabili` non sono stati controllati — verifica a carico di
Tid (sua richiesta esplicita, 2026-08-21).~~

✅ **CHIUSO il 2026-08-21.** Cercati **tutti** i pgTAP fuori da `pagamenti/` che
nominano `pagamenti.vendite_contabili*`, `pagamenti.vendite_movimenti`,
`fn_get_or_create_vendite_contabile` o `fn_get_saldo_fattura`: sono **cinque**, e
girano tutti **verdi** sul database con il lotto 2 applicato.

| File | Esito |
| --- | --- |
| `script/test-permessi-funzioni-risoluzione.sql` | ✅ |
| `script/test-permessi-trigger-guard-emittente.sql` | ✅ |
| `vendite/test-cleanup-fattura-copertura-figlie-v1.sql` | ✅ |
| `vendite/test-fondi-fattura-governo.sql` | ✅ |
| `vendite/test-fondi-fattura.sql` | ✅ *(dopo la correzione qui sopra)* |

##### ⭐ E il difetto era nel BANCO DI PROVA, non nel lotto

La prova in transazione annullata iniettava il lotto **nei soli sei pgTAP della
cartella `pagamenti/`** — perché è la cartella dello schema che si stava
toccando. Ma un guard non difende una *cartella*: difende una **tabella**, e chi
scrive su quella tabella può stare in qualunque cartella.

> **Il perimetro di una prova non è lo schema che si modifica: è l'insieme dei
> test che toccano gli oggetti modificati.** Si trova con un `grep`, non con un
> `ls`.

⇒ Da qui in avanti, il banco di prova di un lotto inietta i changeSet in **tutti**
i pgTAP che nominano gli oggetti toccati, non in quelli della sua cartella.

---

### 6.10 ✅ Lotto 3 — CHIUSO

**Otto changeSet** (`20260821-48` … `-55`), **due** pgTAP (uno nuovo, uno
riscritto), **due** codici errore nuovi. ✅ **Applicati da Tid il 2026-08-22 alle
00:36**, doc auto-generata rigenerata nello stesso giro.

⭐ **Che cosa è cambiato, in una riga:** il fondo fattura ha una **tappa di ciclo
di vita in più** — `ESEGUITO` — e da lì i tre difetti che il posting avrebbe
armato (C-2, C-3, C-6) non sono più *raggiungibili*, invece di essere tamponati
uno per uno.

| Passo | File |
| --- | --- |
| **S1-14** | `00_schema/pagamenti/20260821-48-alter-vendite-contabili-righe-fondo-source` — la colonna + la FK |
| **S1-15** | `00_schema/vendite/20260821-49-alter-fondi-source-stato-eseguito` (il CHECK) + `20_code/vendite/20260821-50-update-trgfn-fondi-source-guard-transizione-eseguito` (la matrice) |
| **S1-16** | `20_code/pagamenti/20260821-51-create-trgfn-righe-marca-fondo-eseguito` |
| **S1-8 + S1-14 + C-6** | `20_code/vendite/20260821-52-update-fn-sync-contabili-fondo-colonna-e-rete` |
| **S1-9 + S1-14** | `20_code/vendite/20260821-53-update-fn-saldo-sorgente-fondo-colonna-e-invariante` |
| **S1-17 + S1-14** | `20_code/vendite/20260821-54-recreate-fn-reset-fondi-fattura-delete-atto` (DROP + CREATE) |
| indice | `80_data/changelog/20260821-55-upsert-dbops-fk-index-policy-fondo-source` + il suo CSV |
| codici | append di **2 codici `W_`** a `80_data/sql/config/codici_errore.csv` (nessun loader nuovo) |
| test | `db/pgtap/vendite/test-fondo-fattura-eseguito.sql` (13, **nuovo**) · `test-fondi-fattura.sql` (21 → **22**, riscritto) |

**Verifica post-migrate**

| Misura | Esito |
| --- | --- |
| `test-fondo-fattura-eseguito.sql` (nuovo) | ✅ **13/13** |
| `test-fondi-fattura.sql` (riscritto) | ✅ **22/22** |
| Gli **11 altri** pgTAP che nominano gli oggetti toccati | ✅ tutti verdi |
| `pgtap-baseline.sh pagamenti` | ✅ **0 rossi su 10** |
| `pgtap-baseline.sh vendite` (204 file) | ✅ 5 rossi, **tutti già in baseline** — nessuna regressione |

⭐ **Il perimetro della prova è stato costruito col `grep`, non con l'`ls`** — è
la lezione che il lotto 2 aveva pagato con un rosso lasciato in `vendite`. Gli
oggetti toccati sono stati cercati in **tutta** la suite: 13 file, non i 2 della
cartella.

#### ⭐ Le decisioni prese scrivendo

1. 🔵→✅ **Il caso 14 si SDOPPIA** (decisione di Tid, 2026-08-22). Era la domanda
   di dominio lasciata aperta dal lotto 2: *«se il caso 14 deve collaudare una
   distinta chiusa dopo che il denaro è stato registrato, la fixture giusta è
   `POSTATA`»*. La risposta è che sono **due fatti diversi**, e vogliono due
   file:
   * `test-fondi-fattura.sql` — la **contabilizzazione**: distinta chiusa con
     dentro denaro **mai registrato**, il reset è bloccato dalla chiusura. Qui
     `SOSPESA` smette di essere un rattoppo e diventa la fixture *giusta*;
   * `test-fondo-fattura-eseguito.sql` — la **registrazione**: riga `POSTATA` col
     suo movimento, l'atto passa a `ESEGUITO`, il reset non lo tocca.
2. ⭐ **La rete di S1-8 interroga la MATRICE, non un elenco di stati scritto
   dentro la funzione** — ed è ciò che l'ha resa più larga del difetto che
   l'aveva chiesta. Chiedendo «la matrice ammette il ritorno ad `ABBINATA` da
   dove la riga si trova?» copre anche una riga **`SCARTATA`**, caso che nessuno
   aveva visto: `SCARTATA → ABBINATA` non è ammessa, quindi il sync la forzerebbe
   e il guard del lotto 2 farebbe **cadere il ricalcolo della fattura** con un
   errore che accusa il ricalcolo.
3. ⚠️ **Il blocco «distinta CHIUSA» del reset ora ignora `attivo`**, e non è una
   svista: con la FK nuova una riga *archiviata* in una distinta chiusa
   impedirebbe comunque di cancellare l'atto. Meglio un blocco che lo **dice**
   che una violazione di vincolo che lo scopre.
4. ⭐ **`updated_source` → `deleted_source`** (DROP + CREATE: `RETURNS TABLE` non
   si cambia con `CREATE OR REPLACE`). Un nome che descrive un comportamento
   finito è peggio di un nome generico, perché si legge come se fosse stato
   verificato. ✅ **Nessun consumatore da avvisare, misurato**: `backend/` non
   nomina la funzione, e l'unico chiamante DB la invoca con `PERFORM`.
5. 🔴 **La frase del reset bloccato diceva il falso.** Era *«Minimo non
   ripristinabile: gia postato»*, mentre la condizione è che la **distinta è
   chiusa** — cioè proprio il caso in cui il denaro **non** è stato registrato.
   Adesso i due casi hanno due frasi e due codici, e la `cause` nel meta
   distingue le due varianti del secondo.
6. ⛔ **`ESEGUITO` NON entra in `uq_fondi_source_atto_vivo_automatico`.** Quel
   predicato descrive gli atti **ancora in gioco**, e un atto eseguito è
   concluso — come `ANNULLATO`, che già ne sta fuori. La garanzia «un atto solo
   per sorgente» non viene comunque da lì: viene da `fn_fondo_fattura_proponibile`
   passo 2, che blocca la proposta se un atto esiste **in qualunque stato**.
7. ⭐ **`%TYPE` esteso a FIRMA e RETURNS**, su richiesta di Tid — nei DECLARE
   c'era già in parte. ⚠️ Un `%TYPE` in firma è una **fotografia**: se
   risolvesse a un tipo diverso nascerebbe un **overload** invece di una
   sostituzione, e con un DEFAULT le chiamate diventerebbero ambigue.
   ✅ Verificato **eseguendo la forma nuova in una transazione annullata** prima
   di scriverla: `bigint`/`numeric`, identici alla firma viva, e il DEFAULT si
   conserva. Le colonne dei `RETURNS TABLE` restano `integer` perché sono
   **contatori**, non il riflesso di una colonna; gli array restano `bigint[]`
   perché `colonna%TYPE[]` non esiste in PostgreSQL.

#### ⚠️ Che cosa il lotto 3 NON ha fatto

* **la madre del posting** (S1-10 … S1-13) → è il **lotto 4**, e adesso può
  partire: la difesa che doveva precederla è atterrata;
* **gli indici di C-7** su `vendite_contabili_righe(fattura_id)`, `(contabile_id)`
  e `vendite_movimenti(fattura_id)` → vanno col lotto 4 (S1-11), insieme a chi
  li userà. Qui è entrato **solo** l'indice della FK nuova.

#### 📮 Le code che il lotto lascia aperte

* **BE-1** (cumulativa con lotti 1 e 2) — rigenerare `error_policies_generated.py`:
  i due `W_` nuovi non hanno classe lato backend finché non si rigenera;
* 🔵 **decisione di dominio** — `ASSEGNATO → DISPONIBILE` resta **ammessa** dalla
  matrice del fondo, ma dal lotto 3 **non la percorre più nessuno** (il reset
  cancella). Toglierla è un candidato dichiarato: si decide, non si fa passando;
* 🔵 **decisione di dominio, il rubinetto in `vendite`** — le tre funzioni
  toccate sollevano ancora `E_PARAMETRO_INVALIDO` passando come valore il **nome
  del parametro PL/pgSQL**: è esattamente il difetto che il lotto 1 ha tolto da
  tutta `pagamenti`. Non è stato corretto qui perché
  `E_PAGAMENTI_CHIAMATA_NON_VALIDA` (953) è dichiarato **a catalogo per le
  funzioni di `pagamenti`**, e usarlo da `vendite` contraddirebbe la sua nota.
  Le due strade sono coniare il gemello (`E_VENDITE_CHIAMATA_NON_VALIDA`) o
  allargare il perimetro del 953 — ed è una scelta, non una rifinitura.

---

### 6.11 ✅ Lotto 4 — CHIUSO: **il primo movimento esiste**

**Tre changeSet** (`20260822-01` … `-03`), un pgTAP nuovo da **20 asserzioni**,
tre codici errore nuovi (961…963) e un messaggio allargato. ✅ **Applicati da Tid
il 2026-08-22 alle 01:29**, auto-gen rigenerata nello stesso giro.

⭐ **Che cosa è cambiato, in una riga:** `pagamenti.fn_get_saldo_fattura` ha
smesso di rispondere *«residuo = totale»* per costruzione. Fino a ieri nessuna
funzione del database scriveva `vendite_movimenti`; da oggi il denaro
**dichiarato** su una distinta diventa denaro **registrato**, e conta nei saldi.

| Passo | File |
| --- | --- |
| **C-5, quarta porta** | `20_code/pagamenti/20260822-01-update-trgfn-righe-guard-distinta-finale-quarta-mossa` |
| **S1-10** | `20_code/pagamenti/20260822-02-create-fn-posta-contabile` |
| **S1-11** | `80_data/changelog/20260822-03-upsert-dbops-fk-index-policy-posting` + il suo CSV |
| **P-6** | append di **3 codici** (961 `E_CONTABILE_NON_TROVATA`, 962 `E_CONTABILE_NON_REGISTRABILE`, 963 `E_CONTABILE_DICHIARAZIONE_NON_CORRISPONDE`) ai due CSV, più l'**allargamento** del messaggio 958 |
| **S1-12** | `db/pgtap/pagamenti/test-fn-posta-contabile.sql` (20) |
| **S1-13** | `manual/fn_posta_contabile.md` (nuovo), `manual/trgfn_..._guard_distinta_finale.md`, `manual/vendite_contabili.md`, guida `gestione-dei-pagamenti.md` |

**Verifica**

| Misura | Esito |
| --- | --- |
| Passo 2 del ciclo — lotto iniettato in **16 file** del perimetro, in transazione annullata | ✅ 15 verdi + 1 rosso **della simulazione**, non del lotto (sotto) |
| `test-fn-posta-contabile.sql` col migrate applicato | ✅ **20/20** |
| `pgtap-baseline.sh pagamenti` | ✅ **0 rossi su 11** |
| I 6 file del perimetro fuori da `pagamenti/` (vendite, script, rls) | ✅ tutti verdi |
| `dbops.vw_fk_senza_indice` per `pagamenti` | ✅ **0 righe**: ogni FK ha o il suo indice o il suo no scritto |
| Firma della madre (`pg_get_function_identity_arguments`) | ✅ una sola, nessun overload |

⚠️ **L'unico rosso della prova era della prova.** `rls/test-role-batch-fatturazione-postura.sql`
falliva l'asserzione «no over-grant» nella simulazione e **non** col runner vero.
La ragione è che la simulazione gira come **owner** (il DDL lo pretende) e quel
test legge `information_schema.role_table_grants`, che è **filtrata per utente**:
da owner si vedono grant che `zeroerp_app` non vede. Verificato eseguendolo come
owner **senza** il lotto iniettato: stesso rosso.
📌 *Un rosso in una simulazione va attribuito prima di essere inseguito: il
runner, il ruolo e la visibilità dei cataloghi cambiano l'esito quanto il codice.*

#### ⭐ Le decisioni prese scrivendo

1. 🔵→✅ **La chiusura è una CONSEGUENZA, non una scelta** (decisione di Tid,
   2026-08-22). Il brief lasciava la domanda aperta in §S1-10 punto 7 («sempre,
   o solo se non restano righe lavorabili?») e Q-6 aveva risposto sugli stati ma
   non su questo. Registrato, la distinta va a `CHIUSA`.
2. ⭐ **E il prezzo si paga nello stesso lotto**: la **quarta mossa** del guard
   sulla distinta finale. Le tre mosse esistenti (nascere, riattivare, spostare)
   non coprivano *«una riga che sta già lì e diventa pronta»* — un caso che fino
   a ieri non era raggiungibile, perché chiudeva una persona che sapeva che cosa
   ci lasciava dentro. Con la chiusura automatica diventa reale: una riga
   `DA_ABBINARE` abbinata il giorno dopo sarebbe denaro pronto sotto una distinta
   che il posting rifiuta. ⛔ Senza quel guard, la decisione 1 avrebbe aperto la
   terza porta di C-5.
3. ⚠️ **Il messaggio 958 si allarga invece di spezzarsi.** Diceva «non accetta
   altre righe», falso sulla mossa nuova. Il codice però non si spezza: il
   criterio è che un codice nasce quando cambia il **rimedio**, e il rimedio è lo
   stesso — quel denaro, se va registrato, vuole una distinta nuova. Arità
   invariata, quindi nessun rischio su `format()`.
4. ⭐ **La dichiarazione (D13) è facoltativa ma LEGATA**: o tutti e due i
   parametri o nessuno. Mezza dichiarazione non si può verificare, e accettarla
   in silenzio significherebbe registrare senza controllo *credendo* di averlo
   fatto. Assente, si registra ciò che c'è — è la strada dei processi
   automatici, che non hanno un operatore che guarda. Simmetrico a
   `importo_dichiarato`, facoltativo sulla manuale.
5. ⭐ **`data_conferma` / `user_conferma` si scrivono REGISTRANDO**, col
   `COALESCE` che tiene la prima volta: la conferma è l'atto di registrare, non
   quello di chiudere.
6. ⭐ **I due statement sono legati da un ARRAY DI ID**, non dal ripetere il
   predicato. La RLS impone di spezzare; ripetere la condizione avrebbe portato
   a `POSTATA` anche una riga aggiunta nel frattempo da un'altra sessione,
   **senza il suo movimento**. È la differenza fra spezzare e spezzare bene.
7. ⭐ **S1-11 ha chiuso il registro delle FK, non solo aggiunto tre indici.**
   Sei vincoli di `pagamenti` non avevano **nessuna riga di policy** — quattro
   nati col lotto 2 — e `vw_fk_senza_indice` conta come «da coprire» tutto ciò
   che non è deciso. Ora quella vista, per `pagamenti`, è a zero.

#### ⚠️ Che cosa il lotto 4 NON ha fatto

* **la rata**: `scadenza_id` non esiste ancora sulle righe — è la **slice 2**,
  lotto 5. La madre è scritta per non doverla riaprire: il guard stato ↔ nullità
  nasceva già prevedendo la rata facoltativa;
* **il perimetro** (RLS in lettura su `pagamenti.*`): lotto 6, e adesso è
  collaudabile davvero, perché ci sono dati veri da filtrare;
* **le sistemazioni**: lotto 7.

#### 📮 Le code che il lotto lascia aperte

* **BE-1** (cumulativa) — rigenerare `error_policies_generated.py` per i tre
  codici nuovi;
* 📮 **BE** — allineare il ripiego di `E_RIGA_CONTABILE_DISTINTA_FINALE` in
  `error_messages_fallback.py`, che porta ancora la frase vecchia («non accetta
  altre righe»);
* 📮 **BE** — il verbo `POST /api/v1/pagamenti/contabili/<id>/registra/`:
  la madre è pronta e **nessuno la chiama**. ⚠️ Chi la cabla deve passare la
  **dichiarazione** (righe pronte e totale che l'operatore ha davanti), o il
  controllo di D13 resta un meccanismo che non scatta mai;
* 🔵 **decisione di dominio, ereditata dal lotto 3** — il rubinetto
  `E_PARAMETRO_INVALIDO` in `vendite` (coniare `E_VENDITE_CHIAMATA_NON_VALIDA` o
  allargare il 953);
* 🔵 **decisione di dominio, ereditata dal lotto 3** — togliere
  `ASSEGNATO → DISPONIBILE` dalla matrice del fondo, che ormai non percorre più
  nessuno.

---

### 6.12 ✅ Lotto 5 — CHIUSO: **l'incasso arriva alla rata**

**Nove changeSet** (`20260822-04` … `-12`, l'ultimo è una correzione in avanti),
un pgTAP nuovo da **18 asserzioni**, tre codici errore (964…966) e un messaggio
riscritto. ✅ **Applicati da Tid il 2026-08-22**, auto-gen rigenerata.

⭐ **Che cosa è cambiato, in una riga:** fino a ieri, nell'intero database, non
esisteva nessuna colonna `scadenza_id` — la guida dei pagamenti aveva una
sezione intitolata *«due metà che non si toccano ancora»*. Adesso si toccano, e
quella sezione è stata riscritta.

| Passo | File |
| --- | --- |
| **S2-1 + S2-5** | `00_schema/pagamenti/20260822-04-alter-vendite-contabili-righe-rata` — `scadenza_id`, `forzata`, `motivo_forzatura` |
| **S2-2** | `00_schema/pagamenti/20260822-05-alter-vendite-movimenti-scadenza` + `20_code/…-09-update-trgfn-movimenti-mirror-scadenza` |
| **S2-3** | `20_code/script/20260822-06-create-fn-check-scadenza-di-fattura` |
| **S2-6** | `20_code/pagamenti/20260822-07-create-fn-get-saldo-rata` |
| **S2-3/4/5** | `20_code/pagamenti/20260822-08-create-trgfn-righe-guard-rata` (+ `-12`, correzione) |
| **S2-7** | `20_code/pagamenti/20260822-10-create-vw-rate-fuori-capienza` |
| **S2-8** | `80_data/changelog/20260822-11-upsert-dbops-fk-index-policy-rata` + CSV |
| **P-6** | 3 codici nuovi: 964 `E_RIGA_CONTABILE_RATA_INCOERENTE`, 965 `E_RIGA_CONTABILE_CAPIENZA_SUPERATA`, 966 `E_RATA_NON_TROVATA` |
| test | `db/pgtap/pagamenti/test-abbinamento-rata.sql` (18) |
| doc | 3 `manual/` nuovi + 2 aggiornati, e la **riscrittura** della sezione «piano rate» della guida |

#### ⭐ Le decisioni prese scrivendo

1. ⭐ **L'abbinamento sta sulla riga, e la riga basta.** D1 lo prevedeva; il
   lotto lo conferma senza nessuna tabella in mezzo: chi paga due rate con un
   bonifico solo fa **due righe**, che è anche il modo in cui la banca lo
   racconta.
2. 🔴 **La coerenza si chiede FUORI dalla row security**, con una `SECURITY
   DEFINER` minuscola che risponde un booleano. Un guard che leggesse le
   scadenze sotto RLS non distinguerebbe *«non appartiene»* da *«non la vedo»*:
   due verità opposte che danno lo stesso `EXISTS` falso, e rifiutarle con lo
   stesso messaggio significa dirne una falsa.
   ⚠️ E il messaggio porta **l'id** della rata, non i suoi dati: quella rata è di
   un altro documento, e raccontarli disferebbe la ragione per cui la domanda si
   fa così.
3. 🔴 **Il caso che si sbaglia facile, e che il test 16 presidia.** La capienza
   si verifica **solo** quando la riga occupa spazio davvero. Se si guardasse a
   ogni cambio di stato, portare a `SCARTATA` una riga sospesa — cioè
   **toglierla di mezzo** — verrebbe rifiutato perché nel frattempo un'altra
   riga ha occupato lo spazio: *si rifiuterebbe un gesto che libera*.
4. ⭐ **Una rata senza fattura non è incoerente: è incompleta**, e a dirlo è il
   guard sui dati. Questo tace apposta — girando prima (i `BEFORE ROW` vanno in
   ordine alfabetico) coprirebbe il messaggio utile con uno vero e inutile.
5. ⭐ **`fn_get_saldo_rata` risponde tre numeri**, non uno: il **registrato**, il
   **dichiarato** e l'**incassato**. La terza colonna è §4 del brief madre — i
   centri interni non sono cassa — e senza di essa chi somma i movimenti misura
   un'altra cosa senza saperlo.
6. ⚠️ **La vista non si chiama come diceva il piano.** `vw_rate_sovra_incassate`
   avrebbe detto **meno** di ciò che l'elenco contiene: fuori capienza si esce in
   due versi, e il secondo — un rimborso dove non era entrato niente — è
   esattamente il caso che ha fatto cadere l'asimmetria di D1-bis. Si chiama
   `vw_rate_fuori_capienza`, e porta un `motivo` a vocabolario chiuso.
7. ⚠️ **S2-4 del piano era scaduto**, e va letto sapendolo: diceva «asimmetrico,
   il limite inferiore non è forzabile» citando D1-bis. **D14-e l'ha superato**:
   la regola è simmetrica, senza permessi, e non ha estremi fissi da invertire.

#### 🔴 Il difetto trovato dalla prova, e chi l'ha preso

Il ramo della **coerenza** chiamava `fn_log_and_raise_error` **senza valori**,
perché il messaggio non aveva segnaposti — ma `VARIADIC` senza default non
accetta la chiamata a cinque argomenti. ⚠️ **Il `CREATE FUNCTION` passava, il
guard funzionava, e l'unico caso rotto era proprio quello che il guard esiste
per gestire.**

L'hanno preso **due presidi**, e vale la pena sapere quali:

* `test-abbinamento-rata.sql` test 2, che asserisce con **`throws_like` sulla
  frase**. 📌 Con `throws_ok(..., 'P0001')` sarebbe stato **verde**: anche «la
  funzione non esiste» è un errore, e un `throws_ok` senza discriminante avrebbe
  fatto passare per rifiuto di dominio un errore di programmazione;
* `db/pgtap/dbops/test-riferimenti-morti-v1.sql`, il cancello statico che
  scandisce i corpi cercando chiamate che non risolvono — l'ha fatto girare Tid.

Correzione **in avanti** (`20260822-12`), come vuole la regola: un changeSet
mergiato non si modifica.

#### 📮 Le code che il lotto lascia aperte

* **BE-1** (cumulativa) — rigenerare `error_policies_generated.py` per i tre
  codici nuovi;
* 📮 **BE, e sono due verbi**: `POST …/righe/<id>/abbina/` (imputa una riga a una
  rata) e la **riproposta della forzatura** — ⚠️ il secondo tentativo deve
  passare `forzata = true`, o il meccanismo a due tempi non scatta mai e
  l'operatore vede solo un rifiuto;
* 📮 **BE/FE** — l'elenco di `vw_rate_fuori_capienza`: senza una schermata che lo
  guardi, la forzatura resta scritta e non letta;
* 🔵 le due decisioni di dominio ereditate dal lotto 3 (il rubinetto
  `E_PARAMETRO_INVALIDO` in `vendite`, e `ASSEGNATO → DISPONIBILE` che non
  percorre più nessuno);
* 🔵 **una nuova**: la stessa regola di capienza vale, con la stessa formula,
  anche a **livello di fattura** (D14-c lo dice). Qui è stata messa **solo sulla
  rata**, di proposito: al livello di fattura passerebbe il sync dei fondi, che
  gira dentro il ricalcolo della pipeline e non ha nessuno che possa
  «confermare». Estenderla è una decisione, non una rifinitura.

---

### ~~6.6 Il primo passo concreto~~ — ✅ **fatto** (storico)

> ~~Lotto 1, e comincia da P-0~~ → ✅ **P-0 è fatto** (2026-08-21): nessun altro
> vincolo evaporato, **la lista del lotto 1 non cambia**.
>
> ⭐ **Il primo passo è ora P-1**: i tre vincoli di `centri_riscossione` — i due
> indici unici **parziali** e il CHECK mai nato. SQL già scritto in §2.0.

Poi, nello stesso lotto e in quest'ordine: **P-2** (CSV + loader dei centri, con
il backfill delle due righe esistenti **prima** dei centri reali), **P-3**
(resync della sequenza), **P-4/P-5** (`stato_id` NOT NULL e il ramo morto che ne
segue), **P-6/P-7** (codici errore, poi la bonifica degli `E_GENERICO`), **P-8**
(il `manual/` di `sepa_mandati`).

⚠️ E prima di chiedere il migrate, il **passo 2 del ciclo**: provare il lotto in
`BEGIN … ROLLBACK`, col wrapper **dentro il file eseguito**.

---

## 7. Registro delle revisioni

| Data | Cosa |
| --- | --- |
| 2026-08-22 (notte, 2) | ✅ **LOTTO 5 CHIUSO E APPLICATO** — nove changeSet (`20260822-04` … `-12`), un pgTAP nuovo da 18 asserzioni, tre codici errore (964…966). ⭐ **L'INCASSO ARRIVA ALLA RATA**: fino a ieri nell'intero database non esisteva nessuna colonna `scadenza_id`, e la guida dei pagamenti aveva una sezione intitolata «due metà che non si toccano ancora» — riscritta. L'abbinamento vive **sulla riga contabile** e non in una tabella N:N (D1): chi paga due rate con un bonifico solo fa due righe, che è anche il modo in cui la banca lo racconta. 🔴 **La coerenza si chiede FUORI dalla row security**, con una SECURITY DEFINER minuscola che risponde un booleano: un guard che leggesse le scadenze sotto RLS non distinguerebbe «non appartiene» da «non la vedo» — due verità opposte che danno lo stesso EXISTS falso, e rifiutarle con lo stesso messaggio significa dirne una falsa. ⚠️ E il messaggio porta l'**id** della rata e non i suoi dati: quella rata è di un altro documento, e raccontarli disferebbe la ragione per cui la domanda si fa così. ⭐ **Sette decisioni prese scrivendo** (§6.12), e tre meritano di essere lette: (1) 🔴 **il caso che si sbaglia facile** — la capienza si verifica SOLO se la riga occupa spazio davvero, altrimenti portare a SCARTATA una riga sospesa, cioè *toglierla di mezzo*, verrebbe rifiutato perché un'altra riga ha nel frattempo occupato lo spazio: si rifiuterebbe un gesto che LIBERA (presidiato dal test 16); (2) una rata **senza fattura** non è incoerente ma incompleta, e il guard della rata **tace apposta** per non coprire il messaggio del guard sui dati, che parla dopo di lui nell'ordine alfabetico dei BEFORE ROW; (3) la vista **non si chiama come diceva il piano** — `vw_rate_sovra_incassate` avrebbe detto meno di ciò che contiene, perché fuori capienza si esce in due versi e il secondo (un rimborso dove non era entrato niente) è esattamente il caso che ha fatto cadere l'asimmetria di D1-bis. ⚠️ **S2-4 del piano era scaduto** e va letto sapendolo: diceva «asimmetrico, il limite inferiore non è forzabile» citando D1-bis, ma D14-e l'ha superato — la regola è simmetrica, senza permessi, e non ha estremi fissi da invertire. 🔴 **La prova ha trovato un difetto vero, ed era mio**: il ramo della coerenza chiamava `fn_log_and_raise_error` senza valori, ma il VARIADIC non ha default — il `CREATE FUNCTION` passava, il guard funzionava, e l'unico caso rotto era **proprio quello che il guard esiste per gestire**. 📌 L'hanno preso due presidi: il `throws_like` sulla FRASE del test 2 (con un `throws_ok` su P0001 sarebbe stato verde — anche «la funzione non esiste» è un errore) e il cancello statico `test-riferimenti-morti-v1.sql`, fatto girare da Tid. Correzione **in avanti** (`20260822-12`). 📮 Restano tre richieste BE (i due verbi dell'abbinamento e della forzatura, e la schermata dell'elenco), le due decisioni di dominio ereditate dal lotto 3, e una nuova: 🔵 la stessa regola di capienza vale anche a livello di FATTURA (D14-c), ma qui è stata messa solo sulla rata perché al livello di fattura passerebbe il sync dei fondi, che gira dentro il ricalcolo della pipeline e non ha nessuno che possa «confermare» |
| 2026-08-22 (notte) | ✅ **LOTTO 4 CHIUSO E APPLICATO** (01:29) — tre changeSet (`20260822-01` … `-03`), un pgTAP nuovo da 20 asserzioni, tre codici errore (961…963) e un messaggio allargato. ⭐ **NASCE IL PRIMO MOVIMENTO DEL PROGETTO**: fino a ieri nessuna funzione scriveva `vendite_movimenti`, quindi `fn_get_saldo_fattura` rispondeva «residuo = totale» **per costruzione** — non perché nessuno avesse pagato, ma perché non c'era modo di registrarlo. Il test 13 del nuovo pgTAP è la prova che la slice serviva: il saldo cala di quanto è stato registrato. Verifica: 20/20, baseline `pagamenti` 0 su 11, i sei file del perimetro fuori da `pagamenti/` verdi, `vw_fk_senza_indice` per `pagamenti` a **zero righe**, firma unica senza overload. 🔵→✅ **Chiusa da Tid la domanda che il brief lasciava aperta in §S1-10 punto 7: la chiusura della distinta è una CONSEGUENZA del registrare, non un gesto a parte.** ⭐ **E il prezzo si paga nello stesso lotto**: la **quarta mossa** del guard sulla distinta finale. Le tre esistenti (nascere, riattivare, spostare) non coprivano *«una riga che sta già lì e diventa pronta»* — caso che fino a ieri non era raggiungibile, perché a chiudere era una persona che sapeva che cosa ci lasciava dentro; con la chiusura automatica una riga `DA_ABBINARE` abbinata il giorno dopo sarebbe denaro pronto sotto una distinta che il posting rifiuta. ⛔ Senza quel guard la decisione avrebbe aperto la terza porta di C-5. ⭐ **Sette decisioni di forma** (§6.11), e tre meritano di essere lette: (1) il messaggio 958 si **allarga** invece di spezzarsi — il codice nasce quando cambia il *rimedio*, e il rimedio è lo stesso; (2) la dichiarazione di D13 è **facoltativa ma legata**, o tutti e due i parametri o nessuno, perché mezza dichiarazione non si può verificare e accettarla significherebbe registrare senza controllo *credendo* di averlo fatto; (3) i due statement imposti dalla RLS sono legati da un **array di id** e non dal ripetere il predicato — ripeterlo avrebbe portato a `POSTATA` anche una riga aggiunta nel frattempo, **senza il suo movimento**. ⭐ **S1-11 ha chiuso il registro delle FK, non solo aggiunto tre indici**: sei vincoli di `pagamenti` non avevano nessuna riga di policy (quattro nati col lotto 2) e `vw_fk_senza_indice` conta come «da coprire» tutto ciò che nessuno ha deciso. ⚠️ **L'unico rosso della prova era della prova**: `rls/test-role-batch-fatturazione-postura.sql` falliva l'asserzione «no over-grant» nella simulazione, che gira come **owner** perché il DDL lo pretende, e quel test legge `information_schema.role_table_grants` — filtrata per utente. Verificato come owner *senza* il lotto: stesso rosso. 📌 *Un rosso in una simulazione va attribuito prima di essere inseguito.* 📮 Restano **tre richieste BE** (rigenerare le policy, allineare il ripiego del 958, e il verbo che chiama la madre — che oggi è pronta e non la chiama nessuno: ⚠️ chi la cabla deve passare la dichiarazione, o il controllo di D13 è un meccanismo che non scatta mai) e le due decisioni di dominio ereditate dal lotto 3 |
| 2026-08-22 | ✅ **LOTTO 3 CHIUSO E APPLICATO** (00:36) — otto changeSet (`20260821-48` … `-55`), un pgTAP nuovo (13 asserzioni), uno riscritto (21 → 22), due codici `W_`. ⭐ **Il fondo fattura ha il suo quarto stato, `ESEGUITO`**, e con esso i difetti **C-2, C-3 e C-6 smettono di essere raggiungibili** invece di essere tamponati: i tre lettori dei fondi filtrano tutti sullo stato, quindi un atto che esce da `ASSEGNATO` esce da tutti e tre senza che nessuno di loro cambi. Il legame riga → atto è diventato una **colonna con FK** (`fondo_source_id`) e il reset **cancella** l'atto non eseguito invece di riaprirlo. Verifica: 13/13 e 22/22, gli **11 altri** pgTAP che nominano gli oggetti toccati tutti verdi, baseline `pagamenti` 0 su 10 e `vendite` 5 su 204 tutti già noti — **nessuna regressione** (riverificata da Tid). ⭐ **Il perimetro della prova è stato costruito col `grep` e non con l'`ls`**, che è la lezione pagata dal lotto 2. 🔵→✅ **La domanda di dominio del caso 14 è chiusa da Tid: si SDOPPIA** — la *contabilizzazione* (distinta chiusa, denaro mai registrato) resta in `test-fondi-fattura.sql` e lì `SOSPESA` smette di essere un rattoppo e diventa la fixture giusta; la *registrazione* (riga `POSTATA` col suo movimento, atto `ESEGUITO`, reset che non lo tocca) vive in `test-fondo-fattura-eseguito.sql`. ⭐ **Sette decisioni di forma prese scrivendo** (§6.10), e due meritano di essere lette: (1) la **rete di S1-8 interroga la matrice** delle transizioni invece di un elenco di stati, e per questo copre un caso che nessuno aveva visto — una riga `SCARTATA`, da cui `ABBINATA` non è raggiungibile, avrebbe fatto **cadere il ricalcolo della fattura**; (2) la frase del reset bloccato **diceva il falso** — «gia postato» dove il denaro *non* era stato registrato — e adesso i due casi hanno due frasi e due codici. ⚠️ **`%TYPE` esteso a firma e RETURNS su richiesta di Tid**, con l'anti-overload verificato eseguendo la forma nuova in una transazione annullata (un `%TYPE` in firma è una fotografia: se risolvesse a un tipo diverso affiancherebbe invece di sostituire). 📮 Restano **tre code**: BE-1 cumulativa (rigenerare `error_policies_generated.py`) e due decisioni di dominio — togliere `ASSEGNATO → DISPONIBILE`, che ormai non percorre più nessuno, e il **rubinetto `E_PARAMETRO_INVALIDO` in `vendite`**, dove le tre funzioni toccate passano ancora il nome del parametro come valore del messaggio |
| 2026-08-21 (dopo l'apply del lotto 2) | 🔴 **UN ROSSO LASCIATO IN `vendite` DA S1-20 — corretto, e da rivedere.** Dopo l'apply, `db/pgtap/vendite/test-fondi-fattura.sql` è rosso su `E_CONTABILE_CHIUSURA_CON_RIGHE_PRONTE`. ⚠️ **Non era in baseline: era verde**, quindi è un rosso nuovo. ⭐ **La paternità è stata verificata, non dedotta**: il guard è a `orderexecuted` 13257 e i due changeSet del cantiere *liste drawer lotto* (`-38`, `-39`) a 13273/13274 — dopo — e quel test non nomina nulla di ciò che toccano. È **il guard che funziona**, gemello esatto del caso già pagato *dentro* il lotto 2 (`test-vendite-contabili-stato-obbligatorio.sql`): la fixture portava la distinta a `CHIUSA` mentre la riga nata dal sync del fondo era ancora `ABBINATA`, l'**unico** stato con `is_postabile = true`. 📌 **La lezione è sul perimetro della prova, non sul guard**: quel caso stava in `pagamenti/` e la prova del lotto lo trovò; questo sta in `vendite/`, e la prova non ci è arrivata — *un guard nuovo su una tabella di `pagamenti` va grepato su TUTTA la suite, perché chi chiude una distinta a mano può vivere in un altro dominio*. Correzione: la riga passa a **`SOSPESA`** prima della chiusura (una delle due uscite che l'HINT del guard indica) e la distinta si sceglie **una volta** in una temp table invece che con una sotto-select ripetuta — **20/20 verdi**. ⭐ Non snatura il caso 14 perché `fn_reset_fondi_fattura` blocca su `c.stato_id = CHIUSA` e `cr.attivo IS TRUE` e **non guarda lo stato della riga**. 🔵 **Da rivedere, ed è una domanda di dominio**: se il caso 14 deve collaudare *una distinta chiusa dopo che il denaro è stato registrato*, la fixture giusta è `POSTATA` e `SOSPESA` è un rattoppo che tiene il verde senza dire la cosa giusta. ⛔ **Perimetro non chiuso**: gli altri file di `vendite/` che toccano `vendite_contabili` li verifica Tid (sua richiesta). Dettaglio in §6.9 |
| 2026-08-21 (notte, 2) | ✅ **LOTTO 2 CHIUSO E APPLICATO** (dalle 21:19) — undici changeSet (`20260821-24` … `-34`), quattro pgTAP nuovi, sette codici errore (954…960), **otto `manual/` nuovi e quattro aggiornati**. Prima del migrate: **31/31 verdi** in transazione annullata, i **sei** pgTAP esistenti di `pagamenti` restano verdi col lotto iniettato, database invariato, `liquibase validate` pulito, cancelli statici verdi, arità dei segnaposti 0 disallineamenti su 54 chiamate. 🔴 **La prova ha trovato una regressione, ed era il guard che funziona**: `test-vendite-contabili-stato-obbligatorio.sql` chiudeva una distinta con una riga ancora `ABBINATA`, cioè esattamente ciò che S1-20 ora vieta — fixture adeguata **nello stesso lotto** (§6.2 punto 6), e il test ci ha guadagnato in precisione perché `ANNULLATA` è il caso in cui il filtro su `is_final` ha davvero un mestiere. ⭐ **Quattro decisioni di forma prese scrivendo.** (1) La colonna «bagaglio» di D14-a diventa una **bandiera di catalogo** (`richiede_abbinamento`) invece di un elenco dentro il guard — stessa scelta di S1-5 per le transizioni, e ⚠️ **non era derivabile** da `is_final`, perché `ABBINATA` pretende l'abbinamento e non è finale. (2) 🔴 **`origine` è a TRE valori**: misurando *chi crea davvero le distinte* è emerso che l'unico creatore esistente — il sync dei fondi — **non è né manuale né automatica**, e con due soli valori il **100% delle distinte di oggi** porterebbe una parola falsa. Nasce **`GENERATA`** (Tid), e la decisione è scritta nel **brief madre, D12-b-bis** — non qui, perché le decisioni si aggiornano solo là. (3) Le matrici nascono `{"manuale": false}`: `check_i18n_keys.py` cerca le `label_key` dei seed `transizioni_stati_*` nei locales e **fallisce** se mancano, e il frontend di `pagamenti` è due `.gitkeep`. ⚠️ Non vuol dire «automatica», vuol dire «non ancora esposta come pulsante». (4) Il seed delle matrici è **SQL con lookup per `codice_interno`, non un CSV con gli id**: il CSV degli stati-riga non porta la colonna `id`, e inciderli in un CSV di transizioni li renderebbe un contratto **per sbaglio**. ⭐ **E una domanda si è chiusa da sola**: `fn_sync_contabili_fondo_fattura` crea già le sue distinte in `VALIDATA`, che è ciò che D14-a-bis prescrive — il codice era avanti al brief. ⚠️ **Verificato invece di dedotto**, su una domanda che poteva rompere il migrate: aggiungere colonne a un CSV condiviso **non rompe il mirror vecchio** — quindici CSV del progetto lo fanno già, fra cui `template_flussi.csv` con lo stesso `obsoleto_dal`. ⚠️ Il fail-open di C-6 **si sposta al lotto 3**, dove S1-8 riscrive comunque quella funzione — e il lotto 2 lo ha reso **peggiore**, perché una riga che ripiegasse su `IMPORTATA` sfuggirebbe anche al guard nuovo |
| 2026-08-21 (notte) | ✅ **LOTTO 1 CHIUSO — applicato in DUE migrate**, `-11`…`-20` alle 19:38 e `-21`…`-23` alle 20:07, entrambi eseguiti da Tid. Baseline riverificata: `pagamenti` **0 rossi su 6**, `vendite` 5 su 199 tutti già noti, `codici-errore-baseline` 0 accumuli / 0 ristretti. ⭐ **`pagamenti` non solleva più né `E_GENERICO` (erano 25) né `E_PARAMETRO_INVALIDO`.** 🔴 **Il secondo migrate esiste per una correzione che Tid ha imposto due volte, e la seconda è più profonda della prima.** Primo giro: il valore passato nel `VARIADIC` era un **nome di parametro PL/pgSQL**, cioè un messaggio di qualità `E_GENERICO` sotto un codice registrato — nasce `E_CONTABILE_DATI_OBBLIGATORI` (952) per i due dati che l'operatore compila. Secondo giro: **anche i sei guard rimasti su `E_PARAMETRO_INVALIDO` dovevano uscirne**, perché quel codice *«esiste ancora perché il BE deve gestire vecchie funzioni che non sono riuscito a correggere»* — ed è esattamente ciò che dicono la **D11** (*«denominatore sicuro + note, e cantiere suo»*: split **rimandato**) e la **§9.1** di `brief-db-be-classe-codici-errore` (*«rincorrere gli esistenti senza chiudere il rubinetto è la forma in cui questi registri non calano mai»*). Nasce `E_PAGAMENTI_CHIAMATA_NON_VALIDA` (953, **TECNICO** → 500), col precedente di `E_VENDITE_PRICING_ESITO_ASSENTE` (19/08, respinto dal rubinetto B-7 con *«lì non c'è nessun parametro invalido, c'è un'invariante rotta»*). ⭐ **La linea che divide non è «guard di parametro sì/no»: è CHI PUÒ RIMEDIARE** — dato che compila una persona → codice di dominio, 400, frase in italiano; dato che solo un chiamante rotto può produrre → codice di dominio, **500**, e la chiave `campo` **esce** dal contesto perché su un 500 non c'è nessun input da accendere. ⚠️ La correzione è stata **forward-only** (P-7-bis): il primo migrate era già girato, e il corpo è stato ripreso dagli YAML applicati **dopo averli verificati identici all'oggetto vivo** — `pg_get_functiondef` non era usabile perché scioglie i `%TYPE`. 📊 **E la misura ha ridimensionato la colpa**: 265 valori sospetti su 1469, in **157 funzioni** — è lo stile in cui il progetto è cresciuto, non una svista isolata; ⛔ per questo **non si è costruito un cancello** (l'euristica sbaglierebbe proprio sul caso legittimo, e vale *«un presidio spento è peggio di uno assente»*). La regola è scritta in tre sedi — `guide/Messaggi-di-Errore-e-Generazione-Log.md` §«I valori del messaggio» (sostanziale), `linee-guida-sql.md` §5/§5b e `.codex/AGENTS.md` (puntatori). 📮 Resta **BE-1**: rigenerare `error_policies_generated.py` per i 15 codici nuovi |
| 2026-08-21 (sera) | ⭐ **Lotto 1 SCRITTO e PROVATO.** Dieci changeSet (`20260821-11` … `-20`), due pgTAP nuovi, 13 codici errore appesi ai CSV. ⛔ Niente applicato: il migrate lo chiede Tid. **Provato in transazione annullata col wrapper dentro il file eseguito** e l'SQL **estratto dagli YAML, non ricopiato**: 20/20 verdi, i quattro pgTAP esistenti di `pagamenti` restano verdi col lotto iniettato nella loro transazione, database invariato, `liquibase validate` pulito, i due guardrail statici verdi. 🔴 **Tre misure di QUESTO brief erano sbagliate, e scriverle è servito a trovarle.** (1) Gli `E_GENERICO` non sono «quattro funzioni, una quindicina di punti»: sono **sette funzioni e venticinque punti**, nove dei quali dentro il solo punto d'ingresso della testata. (2) `test-enti-incasso-psp.sql` **è** transazionale — lo era già dal 18/08, tre giorni prima che il brief lo misurasse: tutti e quattro i file hanno il preambolo completo, e il presidio che lo dice (`guardrail_pgtap_preambolo.py`) esisteva già. (3) **P-3 non serve**: `90_end/20260818-72-resync-identity-sequences-globale` copre da solo tutti gli schemi, forward-only, `runAlways`. ⭐ Ma il resync non sparisce: **cambia sede** e va nel changeSet del seed (P-2), che è la forma idiomatica del progetto e il presidio primario — quella globale è dichiaratamente «una rete». Scritto forward-only anche lì, perché la forma corta `setval(seq, MAX(id))` riporterebbe indietro la sequenza su una tabella da cui si cancella. ⭐ **P-8 era già mezzo fatto**: il `manual/` di `sepa_mandati` esisteva (rev 2026-08-21, dalla passata di copertura documentale); mancava la seconda metà, la voce nella guida `gestione-dei-pagamenti.md`, aggiunta. ⭐ **Scelta di P-6 da scrivere**: **14** codici nuovi, non 25 — i guard su parametri che l'operatore non tocca riusano `E_PARAMETRO_INVALIDO` e la fattura inesistente riusa `E_FATTURA_NON_TROVATA`, perché il criterio del progetto è che un codice nasce quando cambia il **rimedio**, non la sfumatura. 🔴 **Ma la prima stesura sbagliava, e l'ha vista Tid**: mandava su `E_PARAMETRO_INVALIDO` anche i due dati che l'operatore fornisce (centro di riscossione, data contabile), passando come valore un **nome di parametro PL/pgSQL** — cioè un messaggio di qualità `E_GENERICO` sotto un codice registrato, esattamente il difetto che `correzione-e-generico.md` esisteva per togliere, rientrato dalla finestra nel **valore** invece che nel codice. ⭐ **La linea che divide non è «guard di parametro sì/no»: è chi può rimediare** — se il dato lo compila una persona, il messaggio lo legge una persona. Nasce `E_CONTABILE_DATI_OBBLIGATORI` (952) e i quattro guard che solo un chiamante rotto può far scattare restano dov'erano. ⚠️ Seconda ragione, misurata: `api.md` §Tassonomia dichiara `E_PARAMETRO_INVALIDO` **candidato allo split**, quindi aggiungergli punti evitabili va nella direzione opposta. Presidiato da un `throws_like` (test 9 di `test-fn-get-or-create-vendite-contabile.sql`), perché `P0001` dice «errore di dominio» e non *quale*: qui il discriminante è il testo; e per la stessa ragione i tre mismatch del mirror movimento↔riga prendono **un** codice con la colonna in un segnaposto, mentre `E_CONTABILE_COMPENSAZIONE_CON_LOTTO` è **uno solo per due porte** (la regola letta nei due versi). ⚠️ Da cui un vincolo di scrittura: il suo messaggio ha **un** segnaposto e non due, perché una delle due porte il lotto non lo conosce, e `format()` con meno valori dei segnaposti alza 22023 facendo **sparire** l'errore di dominio. ⭐ **Su richiesta di Tid, `%TYPE` esteso a firma e `RETURNS TABLE`** delle tre `fn_*` (i DECLARE lo usavano già): misurati prima tutti i tipi ancorati per escludere l'**overload** — un `%TYPE` in firma è una fotografia, e se risolvesse a un tipo diverso `CREATE OR REPLACE` affiancherebbe invece di sostituire — e per escludere il caso in cui il `RETURNS TABLE` cambierebbe, che `CREATE OR REPLACE` non sa fare. Tutti identici (`bigint`, `numeric` senza typmod), quindi sostituzione pulita: presidiato nella prova da un confronto su `pg_get_function_identity_arguments`. 📮 Restano BE-1 (rigenerare `error_policies_generated.py`) e il riallineamento di `codici-errore-baseline.sh` dopo il migrate, perché `E_GENERICO` perde 25 punti d'uso |
| 2026-08-21 | Stesura. Rimisurato il terreno contro la doc auto-generata e i changelog. ⭐ **Il cantiere fondi è atterrato** (Fasi A/B/C/E/F applicate, `fn_sync_pagamento_fondo_fattura` ritirata) e **la dipendenza si è invertita**: è la Fase D ad aspettare `pagamenti`. 🔴 **Corrette tre misure del brief madre**: B-2 è sbagliato a metà — il guard **c'è già** e il difetto vero è che sollevano tutti `E_GENERICO`; nessun pgTAP di `pagamenti` è in baseline (e uno non è transazionale); la scadenza della «metà fondi» non esiste più. 🔴 **Cinque difetti nuovi misurati, tre bloccanti**: `uq_centri_riscossione_compensazione` è un UNIQUE **totale** su un booleano — il `where:` scritto su `addUniqueConstraint` è stato **ignorato**, e la tabella non può contenere più di **due righe**, il che rende ineseguibile il prerequisito della slice 1; `fn_sync_contabili_fondo_fattura` **riscriverebbe righe già postate** perché il lookup non filtra lo stato; un fondo interamente postato **si auto-annulla** perché lo scorporo di `fn_saldo_sorgente_fondo` filtra `is_postabile`. Piano in **quattro** slice (la 0 e' nuova), otto domande aperte in §5. ⭐ **Aggiornato in giornata scrivendo il rimedio di C-1**: nello stesso file e' evaporato un **secondo** vincolo (**C-1-bis**, `chk_centri_riscossione_ruolo_esclusivo` — un `- sql:` annidato dentro `addColumn.columns:` non viene eseguito), quindi oggi un centro puo' essere compensazione **e** fondo fattura insieme. Due vincoli su tre persi nello stesso file spostano la lezione da «attenzione a quell'attributo» a *un'istruzione che lo strumento non capisce produce silenzio, e il file continua a dichiarare l'intenzione giusta* — da cui il passo **P-0**, una caccia mirata alle altre due forme silenziose nel raggio del cantiere . ⭐ **Secondo giro, su osservazione di Tid** (l'automatismo dei fondi gira solo sulle fatture *di minimo*, e il fondo vale il **residuo**, non il totale): verificato che entrambe le cose sono gia' cosi' nel codice — `f.minimo IS TRUE` in `fn_fondo_fattura_proponibile`, e il numero lo da' `fn_saldo_sorgente_fondo`, che sul caso «fattura 20, incasso 11» risponde **9**. ⭐ Ma la verifica ha chiuso **Q-5** e **corretto S1-8**: l'`importo` del fondo e' **immutabile** (`trgfn_lock_columns` + generazione create-only + atto unico), quindi non esiste lo scenario «l'importo cambia dopo il posting» su cui la domanda era costruita; e il rimedio che avevo scritto — *restringere il lookup alle righe non finali* — era **sbagliato**, perche' fa cadere nel ramo `INSERT` e crea una **seconda** riga. 🔴 Aggiunto che **C-2 e C-3 sono in fila, non affiancati**: oggi il ramo `ANNULLATO` di C-3 esce prima e nasconde C-2, quindi correggerne uno solo **scopre** l'altro. ✅ **Decisione D10 confermata da Tid** (*«altrimenti riparte la rincorsa»*): il fondo vale il residuo **alla nascita** e poi **non insegue** — scritta nel brief madre, §3-bis. 🔴 Con essa emerge la sua meta' mancante: il credito di chi paga *dopo* il fondo non torna nel fondo e **non compare da nessuna parte** (`vw_fondi_fattura_da_decidere` filtra `DISPONIBILE`, e la riga del fondo non e' attribuita a una rata) — **rafforza Q-9** invece di scioglierla . ⭐ **Terzo giro, e cambia il rimedio di due difetti su cinque.** Dal dubbio di Tid — *«un conto e' annullato perche' non si deve fare piu', un conto e' annullato perche' gia' eseguito»* — e' emerso che `ANNULLATO` porta **tre** significati, e che il ramo bloccante di `fn_reset_fondi_fattura` scrive oggi un record **autocontraddittorio** (`stato = ANNULLATO` con `fattura_figlia_id` ancora valorizzato). ✅ Decisione **D11**: quarto stato **`ESEGUITO`**, scritto da un **trigger** sulla riga contabile registrata, legame riga-fondo promosso da stringa JSON a **colonna con FK**, e **reset che cancella** l'atto non eseguito. ⭐ **Il guadagno e' strutturale**: i tre lettori dei fondi filtrano tutti su `stato`, quindi **C-2 e C-3 smettono di essere raggiungibili** invece di essere tamponati, e **Q-4 si chiude** — seconda domanda a cadere **senza essere decisa**, dopo Q-5. Nuovi passi **S1-14 … S1-17**, con tre trappole di scrittura: l'ordine obbligato colonna->stato->trigger, la FK che nel reset a CTE singola puo' scattare prima delle figlie, e il trigger che scrive **da `pagamenti` verso `vendite`**. ⚠️ Marcati superati **D-7** e **D-16** nel brief dei fondi: quel documento dichiarava «tre stati e non quattro» . ⭐ **Quarto giro, sul difetto C-4, e la prima stesura era sbagliata**: dicevo che il punto d'ingresso contraddice D3-a riusando la testata. Misurando le **colonne** si vede il contrario — la testata non ha ne' importo ne' riferimento bancario, e il riferimento della banca sta **sulla riga**: e' una **distinta di giornata per canale**, e il codice e' coerente. A contraddirsi e' il **brief madre**, che nell'intestazione dice «raccoglie N importi arrivati insieme» e in D3-a «e' il movimento bancario». ⭐ E la decisione D3-a **regge solo con la lettura distinta**: il suo «lascia li' il resto» richiede piu' righe. Corretta la frase nel brief madre, riformulata **Q-3** da tre strade a due conferme. ⚠️ Resta un rischio **operativo**, non di modello: su una distinta condivisa chi conferma conferma anche il lavoro altrui — il posting deve **dichiarare la propria portata** . ⭐ **Quinto giro: Tid chiede un lock e la richiesta si risolve togliendo il problema.** Portando in scena i **flussi esterni** e' emerso che le distinte sono di **due specie** — **D12**: manuale = il **lotto di lavoro di un operatore**, automatica = **il file**. Con quel raggruppamento la contesa **non esiste**, quindi il lock non si costruisce: niente colonne di blocco, scadenze, sblocco d'emergenza. *Il presidio piu' economico e' quello che il modello rende inutile.* Decisi anche `origine` + `importo_dichiarato` (obbligatorio sull'automatica, **facoltativo** sul manuale), la linea **fatti/decisioni dentro la riga** importata, e la quadratura che **la madre stabilisce e il guard conserva** — ⚠️ non un trigger di riga, perche' durante il caricamento la somma torna solo alla fine. **D13**: il posting porta **ricevuta + dichiarazione** in firma, e scrive `user_conferma`. ✅ **Q-3 chiusa**: restano **sei** domande, e la slice 1 ne aspetta **due**. ⭐ Chiusa anche la quarta riga di **Q-1**: `IMPORTATA` non e' piu' uno stato senza uscite — ma le sue transizioni **non si seminano** finche' l'import non esiste (la lezione appena pagata con `STORNATA`) . ⭐ **Sesto giro, sul difetto C-5: le porte sono due e avevo visto solo la prima.** Oltre all'«aggiungere una riga a una distinta chiusa» c'e' il caso naturale — **chiudere una distinta che ha ancora righe registrabili** — che fa sparire quelle righe da entrambi i conti. Nuovo passo **S1-20**: non si chiude una distinta con righe pronte. ⭐ E il guard **risponde in gran parte a Q-6**: la chiusura smette di essere una scelta e diventa una conseguenza. 🔴 Trovata sotto la stessa confusione di D11 un piano piu' giu': `is_final` appiattisce `CHIUSA` («e' fatta») e `ANNULLATA` («non e' mai successa»), che sono **opposti** — e nel caso `CHIUSA` quel filtro **non protegge niente**, perche' l'unica cosa che riesce a escludere e' proprio la riga anomala. *Un filtro che nasconde cio' che non sa gestire sembra un presidio finche' non si guarda che cosa esclude davvero.* ℹ️ Con S1-7 e S1-20 la confusione resta **innocua**: nessun attributo nuovo sul catalogo . ⭐ **Settimo giro: Q-1, Q-2 e Q-8 chiuse — le domande scendono da nove a TRE.** Su richiesta di Tid («spiegami Q-1 e Q-2 collegate») e' emerso che erano **la stessa domanda fatta due volte** — percorso e bagaglio — e si rispondono con una tabella sola (**D14**). ⭐ **Il passaggio che ha sciolto il nodo non e' stato rispondere**: e' stato accorgersi che le quattro situazioni portate da Tid (documento gia' saldato, pagamento oltre il totale, pagamento su un documento a credito, rimborso piu' grande del credito) **erano lo stesso caso** — *un movimento normale riduce il residuo e non lo supera*. 🔴 E quella forma **scioglie la trappola di §5**: il divieto di replicare la quadratura a livello fattura valeva per l'**intervallo a estremi fissi**, che su un documento a credito si inverte; una regola senza estremi passa accanto, e vale a entrambi i livelli senza filtri sul segno. ✅ Deciso anche che il DB **rifiuta la coerenza e segnala la capienza**, che la forzatura e' **flag + motivo facoltativo senza permesso** (cade l'azione di processo di D1-bis, e cade la sua **asimmetria**), e che **`SCARTATA` non e' piu' finale** (nuovo passo **S1-21**). ⭐ **Nessuna delle tre domande rimaste ferma lo sviluppo** . ⭐ **Ottavo e ultimo giro: le domande aperte vanno a ZERO.** **Q-6** — la matrice della distinta, cinque stati che vanno bene cosi'; ⭐ ne discende che **`VALIDATA` e' il gesto «ho finito di inserire»**, quindi la quadratura col totale dichiarato si sposta li' invece che nel posting (nuovo passo **S1-22**), e che `ANNULLATA` si raggiunge da **qualunque** stato non registrato. **Q-7** — opzione **B**: il posting **non solleva**, dichiara l'esito; il motivo concreto e' che il DB **scrive nel registro errori prima di sollevare**, quindi un pulsante premuto due volte avrebbe lasciato un errore che errore non e'. **Q-9** — chiusa **restringendosi**: le tre azioni **hanno gia' tutte il loro meccanismo**, mancano solo una **vista** e un **registro**. Il guscio `pagamenti.compensazioni` si allarga e si rinomina in **`pagamenti.sistemazioni`** (nome scelto da Tid; ⛔ scartato `regolazioni`, che in un ERP utilities vuol dire altro). Nuova **slice 4**, che **sblocca la Fase D** del cantiere fondi. ⭐ *Prima di dimensionare un lavoro, contare quanto ne e' gia' costruito da altri cantieri.* 🔵 Resta il solo **D15-e**, il verso del legame . ⭐ **E con le domande a zero il brief prende il §6: il piano operativo a LOTTI.** Le slice sono logiche, i lotti sono cio' che si scrive, si prova e si applica insieme — e si dimensionano su quanto si collauda in un colpo, non su quanto e' concettualmente affine. **Sette lotti**, con le scorciatoie che l'assenza di produzione consente scritte una per una (niente backfill, `DROP`+`CREATE` sulle firme, rinomina secca, il ramo morto tolto nello stesso lotto che lo rende morto, le fixture pgTAP adeguate subito). ⭐ Il perno e' il **passo 2 del ciclo**: provare in `BEGIN … ROLLBACK` prima di chiedere il migrate — e' cio' che permette lotti grossi e protegge dalla regola piu' rigida del progetto (*un changeSet mergiato non si modifica: si corregge in avanti*). 🔴 Il **lotto 3 non si spezza e non si salta**: applicare la madre senza la difesa creerebbe il primo movimento e contemporaneamente il primo modo di rovinarlo. Primo passo concreto: **P-0**, che non scrive niente e puo' cambiare la lista del lotto 1 . ✅ **E P-0 e' stato ESEGUITO in giornata: nessun altro vincolo evaporato.** Scansione **strutturale** di 2804 YAML (tutti parsati): `where:` compare **3 volte** in tutto il changelog e una sola e' su un change che non lo prevede (C-1); un change annidato dentro `columns:` **una sola** (C-1-bis). ⭐ **Due falsi allarmi scritti apposta**, perche' chi ripete la verifica li ritrovera': un change dichiarato **direttamente sotto `changeSet`** (7 casi) e `createIndex` con `columns: [ { name: x } ]` (54 casi) sono **forme valide** — verificato sull'oggetto vivo, non dedotto. ⭐ **La conclusione cambia la lettura del rischio**: non e' una malattia diffusa, sono **due sviste nello stesso schema, in due changeSet consecutivi, sulla stessa tabella, lo stesso giorno**. *Non «il changelog e' pieno di queste», ma «quella tabella e' stata costruita male, una volta».* 🔵 Due residui annotati e non lavorati: il rollback di `20260727-37` ricrea un indice **senza il `WHERE`** che aveva droppato, e non e' verificabile se `createIndex` onori `where:` (l'unico esemplare e' stato droppato) — da cui la regola prudenziale che P-1 gia' applica: **per un indice parziale, SQL esplicito** |
