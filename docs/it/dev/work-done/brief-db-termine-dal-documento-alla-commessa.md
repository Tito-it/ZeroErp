# Brief BE → DB — il termine di pagamento del documento non arriva alla commessa

> ✅ **CHIUSO il 2026-08-03.** Tutto applicato e verificato in giornata, dal
> difetto misurato alla validazione a video:
>
> - **DB**: T.1-T.4 applicati (`20260803-02` colonne esposte, `20260803-03`
>   livello 1 ripuntato sulla sorgente effettiva via `commessa_attivita_id`),
>   pgTAP `plan(9)` verde con prova di mutazione;
> - **BE**: giro reale end-to-end con lo smoke dedicato, **8/8** — la fattura
>   esce col piano rate del **documento**, due ordini con termini diversi
>   producono due commesse e due fatture;
> - **UI**: validazione a video di «Termine»/«Modalità» nel drawer fattura
>   **fatta da Tid** — era l'ultimo aperto (§10.4).
>
> ➡️ **Definizione di «fatto» (§7) chiusa 5/5.**
>
> **Resta fuori dal cantiere, e non lo blocca**: la fattura **2263** —
> EMESSA e non numerata — si corregge solo con la **Fase 6** del DB (ritorno a
> DRAFT), che questo caso ha motivato ed è il primo movente reale registrato
> (§6 e §8.5). Non va numerata nel frattempo.
>
> 💡 **Tre lezioni pagate qui**, tutte della stessa famiglia — *un livello si
> verifica dal percorso che lo attraversa, non dal codice che lo dichiara*:
> il livello 1 sembrava vivo ed era strutturalmente irraggiungibile; il primo
> test lo confermava perché costruiva l'attività con un valore che il pull non
> produce mai; e il «si accende da sé» di §3.1 era **falso** — la whitelist
> `_PUSHABLE_SHARED_COLS` era il cancello, e un mock fermo al contratto a 29
> colonne non poteva dirlo (§10.2, terza occorrenza nello stesso filone).
>
> ---
>
> **Chi scrive:** BE (`dev/backend-tid`), 2026-08-03.
> **A chi:** team DB (`dev/db-tid`).
> **Cos'è:** una fattura reale è uscita col piano rate **sbagliato**, in
> silenzio. La metà applicativa è già corretta e testata; restano **due
> colonne** nel contratto delle `fn_list_*_da_pushare` e **una decisione** sul
> livello 1 di `fn_resolve_termini_pagamento`.
> **Correlati:** [piano-db-satelliti-fattura.md](../work-in-progress/piano-db-satelliti-fattura.md) (D-R) ·
> [piano-be-fe-satelliti-fattura.md](../work-in-progress/piano-be-fe-satelliti-fattura.md)

---

## 1. Il fatto, misurato

Tid ha impostato `TP_30_60_EOM_2R` — **2 rate a 30/60 fine mese** — su
`PRV0000195` e sull'ordine `ORD0004786` che ne è nato. La fattura prodotta dal
giro reale, la **2263**, è uscita con **1 rata a 30 giorni**:

| | |
| --- | --- |
| ordine 4984 (`ORD0004786`) | `termine_pagamento_id = 3` → `TP_30_60_EOM_2R`, 2 rate |
| commessa 3941 | `termine_pagamento_id = **NULL**` |
| cliente del BA 155 | `termine_pagamento_id = 1` → `TP_30G_1R`, 1 rata |
| **fattura 2263** | **termine 1**, una rata al 2026-09-01 |

Ed è uscita **senza un errore**: `critical = false`, nessun log, le rate
quadrano al centesimo con `totale_a_pagare`. Il documento è internamente
**coerente** — passerebbe il guard D-K senza obiezioni, perché D-K presidia la
coerenza, non la correttezza della risoluzione. Sono due cose diverse ed è
giusto che lo siano, ma insieme fanno un difetto che non si vede.

⚠️ **Non è un caso isolato:** `0 commesse su 27` hanno un termine valorizzato.
Vale per ogni documento con condizioni diverse da quelle del cliente.

---

## 2. La catena, passo per passo

1. **La commessa nasce senza termine.** `commesse_source_handlers.py:452`
   chiamava `get_or_create_commessa` **senza** i due parametri, e la firma del
   repository BE non li aveva — benché `fn_get_or_create_commessa` li accettasse
   già (`p_termine_pagamento_id`, `p_modalita_pagamento_id`). **Difetto nostro,
   già corretto** — §4.
2. **Il pull ristampa la sorgente.** `fn_emit_attivita_fatturabili_da_commessa`
   scrive `sorgente COMMESSA` sull'attività generata (per disegno, documentato
   rev 2026-06-28); il tipo originale resta in `sorgente_origine_tipo_id`.
   Misurato: `commesse_attivita 6735` ha `sorgente_tipo_id = 6`
   (`ORDINE_VENDITA`) e l'uid dell'ordine, mentre `attivita_fatturabili 2265`
   ha `sorgente_tipo_id = 13` (`COMMESSA`) e un uid diverso.
3. **Quindi il livello 1 del resolver non può scattare.**
   `fn_resolve_termini_pagamento` legge `a.sorgente_tipo_id`, trova `COMMESSA`,
   non matcha né `ordini` né `preventivi` → salta. Livello 2 (commessa): NULL.
   Vince il livello 3, il cliente. Verificato sull'attività vera:

   ```
   fn_resolve_termini_pagamento(2265) -> (1, 5)
   ```

> 💡 **Nota di metodo, perché non si ripeta.** Leggendo il corpo della funzione
> il livello 1 sembra vivo, e il nostro primo test in rollback lo ha
> **confermato** — perché costruiva l'attività a mano con `sorgente_tipo_id = 6`,
> cioè con un valore che il pull vero non produce **mai**. È la lezione di
> `feedback_whitelist_dal_percorso_reale`: un livello si verifica dal percorso
> che lo attraversa, non dal codice che lo dichiara.

---

## 3. Cosa chiediamo — due colonne e una decisione

### 3.1 🔴 Le `fn_list_*_da_pushare` espongano le condizioni del documento

Oggi il contratto ha **29 colonne** e nessuna è il termine (verificato su
`fn_list_ordini_da_pushare` e `fn_list_preventivi_da_pushare`). Chiediamo due
colonne aggiuntive, dallo stesso documento che la funzione già legge:

| Colonna | Tipo | Da |
| --- | --- | --- |
| `termine_pagamento_id` | `bigint` | `<sorgente>.termine_pagamento_id` |
| `modalita_pagamento_id` | `integer` | `<sorgente>.modalita_pagamento_id` |

Per le sorgenti che non hanno quelle colonne (`contratti` non ha nessuna delle
due, i `preventivi` non hanno la modalità) → `NULL`: il BE lo tratta già come
«non specificato» e la cascata scende al livello successivo.

**Il BE è pronto e la sua metà è inerte fino a quel momento**: le legge con
`col_map.get`, esattamente come `riga_id`, quindi **si accende da sé** appena
le colonne compaiono, senza altre modifiche applicative. È lo stesso criterio
del seed in due tempi che abbiamo già usato per i task.

### 3.2 🟠 Decisione sul livello 1 di `fn_resolve_termini_pagamento`

Il livello «documento sorgente» **non può scattare** sulle attività prodotte dal
pull, che sono la totalità di quelle che arrivano in fattura. O si toglie, o si
ripunta su `sorgente_origine_tipo_id` + l'uid del documento originale.

Noi propendiamo per **ripuntarlo**, per un motivo che va oltre l'eleganza: con
3.1 applicato il livello 2 (commessa) copre il caso normale, ma il livello 1
resta l'unico presidio per le attività **inserite direttamente** con sorgente
documento — e soprattutto è ciò che rende vera la frase «documento → commessa →
cliente → default» che sta scritta in D-R e nel brief scadenze. Tenerlo com'è
significa avere una catena a quattro livelli di cui uno è decorativo, e la
prossima persona che la legge concluderà, come abbiamo concluso noi, che
l'ordine vince.

Se invece la decisione è che **la commessa è l'unica proprietaria** delle
condizioni (lettura ortodossa di D-R), allora il livello 1 va **rimosso** e la
sua assenza documentata: è comunque meglio di un ramo morto.

### 3.3 🟢 Conferma che serve al BE, non una richiesta

Il termine è **dimensione della chiave** della commessa (D-R)? Ce lo aspettiamo,
e abbiamo già allineato la cache locale del push (§4) perché due documenti con
termini diversi aprano **due** commesse. Se non lo fosse, quella scelta va
rivista: ci basta un sì o un no.

---

## 4. Cosa abbiamo già fatto noi (2026-08-03)

| Dove | Cosa |
| --- | --- |
| `db/commesse_repository.py` | `PushableRow` porta i due campi (default `None`, letti con `col_map.get` → inerti finché il DB non li espone); `get_or_create_commessa` ha i due parametri e li passa alla fn |
| `services/commesse_source_handlers.py` | i due valori passati alla creazione commessa **e inseriti nella `cache_key`** |
| test | 5 nuovi, di cui uno con **prova di mutazione** |

⚠️ **La `cache_key` è la metà che si dimentica.** Propagare il termine senza
metterlo nella chiave della cache locale fa collassare in **una** commessa due
ordini dello stesso cliente con termini **diversi**: la seconda riga riusa l'id
della prima e ne eredita il termine. È un difetto peggiore di quello che si
voleva togliere, perché la commessa esiste, è popolata e sembra giusta. Il test
`test_cache_commessa_separa_per_termine_di_pagamento` lo blocca, e la prova di
mutazione (rimuovendo i due campi dalla chiave) lo rende rosso — e rosso **solo
lui**.

✅ **Binding provato con chiamata reale** in transazione con rollback: i due
parametri arrivano a destinazione (`commessa 4005: termine=3 modalita=5`). I
3457 test verdi non lo avrebbero visto — mockano il repository.

---

## 5. Cosa NON chiediamo

| Cosa | Perché no |
| --- | --- |
| Risolvere le condizioni in Python | Sarebbe il secondo risolutore che il brief scadenze §8 vieta. Noi **copiamo** il valore del documento, non percorriamo la cascata |
| Bonificare le 27 commesse esistenti | Le loro attività sono già emesse o annullate; e il termine è in chiave, quindi riscriverlo su una commessa aperta è una modifica di chiave, non un aggiornamento |
| Toccare la fattura 2263 | È un dato, non codice. Vedi §6 |

---

## 6. Un vicolo cieco che vale la pena segnalare

La fattura 2263 è **EMESSA e non numerata**, e non si può disfare:

```
matrice: EMESSA -> DRAFT  AMMESSA (solo_lotto, tipo_lotto MASSIVO)
fn_elimina_fattura_da_lotto_draft(1200, 2263) -> RIFIUTATO: "solo se il lotto e DRAFT"
fn_annulla_lotto_da_draft(1200)               -> RIFIUTATO: "rollback solo se DRAFT"
```

**La matrice ammette il ritorno a bozza, ma non esiste la funzione che lo
esegue** — è la vostra Fase 6, non ancora aperta. Non è una richiesta di
anticiparla: è la conferma sul campo che quella fase serve, e il primo caso
d'uso reale che la motiva. Nel frattempo il documento non va numerato: una volta
DEFINITIVA i satelliti si congelano e il piano rate si corregge solo con una
nota di variazione.

---

## 7. Definizione di «fatto»

1. `fn_list_ordini_da_pushare` e sorelle espongono le due colonne;
2. un ordine con termine non-default apre una commessa **che lo porta**;
3. la fattura che ne nasce ha il piano rate **del documento**, non del cliente —
   il caso di `ORD0004786`: 2 rate a 30/60 fine mese;
4. due ordini dello stesso cliente con termini diversi producono **due**
   commesse e **due** fatture (D-7 + D-R insieme);
5. il livello 1 del resolver o presidia davvero, o non c'è più.

---

## 8. 📎 Risposta DB (2026-08-03)

> Rilievi verificati uno per uno sul DB prima di rispondere. **Tutti confermati**,
> e uno è più forte di come lo avevate scritto.

### 8.1 Le vostre misure, ricontrollate

| Vostra affermazione | Verifica DB |
|---|---|
| Le `fn_list_*_da_pushare` non espongono il termine | ✅ **5 funzioni**, 32-34 colonne ciascuna, **zero** con `termine_pagamento` |
| Il pull scrive `sorgente COMMESSA` | ✅ **35 attività su 35**. Non è «il livello 1 è dormiente»: è **strutturalmente irraggiungibile** |
| Il tipo originale sopravvive | ✅ 23 `ORDINE_VENDITA`, 10 `PREVENTIVO`, 1 `DDT_VENDITA`, 1 nullo |
| `0 commesse su 27` con termine | ✅ confermato |

🔴 **Una correzione che ci riguarda.** Il manuale di
`fn_resolve_termini_pagamento`, scritto il 2026-08-02, motivava il livello 1
dormiente con «ordini e preventivi hanno zero righe». **Il motivo era sbagliato**:
quel livello non scatterebbe nemmeno con le tabelle piene, perché il pull
riscrive la sorgente. La vostra nota di metodo — *un livello si verifica dal
percorso che lo attraversa, non dal codice che lo dichiara* — coglie esattamente
l'errore. Manuale corretto.

### 8.2 Decisioni

| # | Decisione |
|---|---|
| **3.2** | ✅ **RIPUNTARE** (Tid, 2026-08-03). Una catena a quattro livelli di cui uno decorativo è peggio di una a tre: chi la legge conclude che il documento vince, ed è ciò che è appena successo |
| **3.3** | ✅ **SÌ**: il termine **è** dimensione della chiave — verificato in `fn_get_or_create_commessa`. La vostra `cache_key` è allineata al modello, tenetela |

### 8.3 🔴 La vostra proposta di ripuntamento non è applicabile così

Scrivete «ripuntarlo su `sorgente_origine_tipo_id` + l'uid del documento
originale». **Quell'uid non esiste**: `vendite.attivita_fatturabili` ha
`sorgente_tipo_id`, `sorgente_uid`, `sorgente_riga` e `sorgente_origine_tipo_id`
— si conserva il **tipo**, non l'**uid**. Sapremmo che viene da un ordine, non da
*quale* ordine.

Il percorso però c'è, ed è migliore perché non richiede colonne nuove:

```text
attivita_fatturabili.commessa_attivita_id
        └──► commesse_attivita.sorgente_tipo_id   (ORDINE_VENDITA / PREVENTIVO)
             commesse_attivita.sorgente_uid       (l'uid del documento VERO)
```

✅ Verificato: **35 attività su 35** hanno `commessa_attivita_id` valorizzato, la
JOIN è totale. È la riga che avete misurato voi (`commesse_attivita 6735`).

Il livello 1 riscritto copre quindi **due strade**, non una:

1. attività **inserita direttamente** con sorgente documento → `a.sorgente_uid`
   (comportamento attuale, resta);
2. attività **prodotta dal pull** (`sorgente = COMMESSA`) → si risale via
   `commessa_attivita_id` e si legge la sorgente vera.

### 8.4 Piano

| # | Cosa | Stato |
|---|---|---|
| **T.1** | Le 5 `fn_list_*_da_pushare` espongono `termine_pagamento_id` e `modalita_pagamento_id` | ✅ **applicato** `20260803-02` |
| **T.2** | Ripuntamento del livello 1 di `fn_resolve_termini_pagamento` (§8.3) | ✅ **applicato** `20260803-03` |
| **T.3** | pgTAP dal percorso reale | ✅ **9/9**, mutazione provata |
| **T.4** | Doc: manuale del resolver | ✅ **fatto**, con la rettifica di §8.1 |

⚠️ **Trappola nota su T.1**: aggiungere colonne a un `RETURNS TABLE` **non** si
fa con `CREATE OR REPLACE` — PostgreSQL rifiuta. Serve `DROP FUNCTION` esplicita
prima, e con essa la verifica dei chiamanti: una `SELECT *` posizionale a valle
si romperebbe in silenzio.

⚠️ **T.1 prima di T.2**: con le colonne esposte il livello 2 copre il caso
normale, e T.2 diventa il presidio del caso residuo invece che l'unica difesa.
L'ordine inverso lascerebbe il livello 1 a reggere tutto il traffico.

### 8.5 Sul vicolo cieco di §6

Confermato e utile: la matrice ammette `EMESSA → DRAFT` ma **la funzione che lo
esegue non esiste**. È la Fase 6, e il vostro caso è il primo movente reale che
abbiamo — lo registriamo nel piano come tale. Nel frattempo concordiamo: la 2263
non va numerata.

---

## 9. ✅ Consuntivo DB (2026-08-03) — tutto applicato

### 9.1 La prova sul vostro caso

```
attivita 2265 (quella della fattura 2263):
   PRIMA -> termine 1   TP_30G_1R        1 rata   ← il CLIENTE
   DOPO  -> termine 3   TP_30_60_EOM_2R  2 rate   ← l'ORDINE
```

Distribuzione su tutte le 35 attività: **una sola si sposta**, le altre 34
restano dov'erano. Il cambio è quindi mirato, non un effetto di massa.

### 9.2 Cosa è stato applicato

| changeSet | Cosa |
|---|---|
| `20260803-02` | Le 5 `fn_list_*_da_pushare` con le due colonne. `DROP` esplicita: la `RETURNS TABLE` cambia |
| `20260803-03` | Livello 1 del resolver sulla sorgente effettiva, via `commessa_attivita_id` |

pgTAP `test-resolve-termini-livello-sorgente-v1.sql`, **plan(9)**, verde.
Baseline `vendite`: 168 file, 36 rossi noti, **nessuna regressione**.

**Prova di mutazione**: rimuovendo il blocco della sorgente effettiva diventano
rossi **solo** i test 2, 4 e 5 — i tre che esercitano il livello 1. Gli altri sei
restano verdi.

### 9.3 🔴 Un difetto evitato, che vi riguarda se toccherete quel codice

`commesse_attivita.sorgente_uid` è **TEXT**, `attivita_fatturabili.sorgente_uid`
è **UUID**, e la sorgente è **polimorfa**: per convenzione preventivo e offerta
usano l'uid, gli altri `id::text`.

La prima stesura assegnava senza filtrare. **Il test passava** — oggi i valori in
`commesse_attivita` sono tutti uuid validi (39 ORDINE, 44 PREVENTIVO, 1 DDT) — ma
il primo CONTRATTO o CONSUMO che arrivasse lì avrebbe fatto **esplodere il cast**.

L'assegnazione è ora ristretta a `ORDINE_VENDITA` e `PREVENTIVO`, che sono anche
gli unici due tipi che il livello 1 gestisce e gli unici documentati come
portatori di uid. Per contratti e DDT non avrebbe comunque nulla da leggere.
Il **test 7** presidia che un tipo non gestito non sollevi.

### 9.4 La vostra §7, punto per punto

| # | Criterio | Stato |
|---|---|---|
| 1 | Le `fn_list_*` espongono le due colonne | ✅ **fatto** — verificato che la colonna porta il valore del documento e non un NULL fisso (test 9) |
| 2 | Un ordine con termine non-default apre una commessa che lo porta | 🟡 **sbloccato, da provare con un giro vero**: la vostra metà era inerte e questo changeSet la accende |
| 3 | La fattura che ne nasce ha il piano rate del documento | 🟡 idem — serve il giro end-to-end |
| 4 | Due ordini con termini diversi → due commesse e due fatture | 🟡 idem. La conferma DB che serviva è in §8.2: il termine **è** dimensione della chiave |
| 5 | Il livello 1 o presidia davvero, o non c'è più | ✅ **presidia**, ed è coperto dal percorso reale |

➡️ **1 e 5 sono chiusi lato DB. 2, 3 e 4 sono ora possibili e vanno confermati da
un giro reale**: è lavoro di smoke, non di modello. Quando lo girate, l'ordine
`ORD0004786` è il caso di riferimento — ha già il termine a 2 rate.

### 9.5 Nota di metodo, ricambiata

La vostra osservazione — *un livello si verifica dal percorso che lo attraversa,
non dal codice che lo dichiara* — è finita nel **test 1** come asserzione
permanente sulla **forma** che il pull produce: se un domani cambiasse, è il primo
a diventare rosso.

E ci è servita due volte: il nostro test 9, alla prima stesura, usava l'ordine
dietro un'attività esistente — **già pushato**, quindi giustamente escluso dalla
`fn_list_*`. Stessa famiglia: una riga in uno stato che il percorso reale non ha.


---

## 10. ✅ Consuntivo BE (2026-08-03) — giro reale fatto, §7 chiusa 5/5

### 10.1 Il giro reale che la vostra §9.4 chiedeva

Nuovo smoke **`smoke-push-termine-documento-commessa.py`** (idempotente, tutto
in rollback): clona un ordine vero in CONFERMATO col termine `TP_30_60_EOM_2R`
e da lì in poi è **solo codice di produzione** — `pr_run_commesse_push_one`,
`fn_emit_attivita_fatturabili_da_commessa`, `fn_select_attivita_fatturabili`
con lock, `FattureRigheService`, task IVA e scadenze. Il termine non viene mai
scritto a mano su commessa o testata: o lo porta la catena, o è rosso.

**8/8 verdi.** In particolare:

| §7 | Esito |
|---|---|
| 2 | ✅ la commessa del push porta termine **e** modalità dell'ordine |
| 3 | ✅ la fattura esce col piano rate del **documento**: 2 rate, Σ = `totale_a_pagare` al centesimo — il caso 2263 alla rovescia, con **controprova discriminante** (commessa senza termine → la catena dà il termine del cliente, quindi il valore osservato viene dal documento e non dal default ambientale) |
| 4 | ✅ due ordini stesso cliente con termini diversi → **due** commesse e **due** fatture |

Con i vostri 1 e 5 (§9.4), la **definizione di fatto è chiusa 5/5**.

### 10.2 🔴 Ma il giro ha trovato un difetto — NOSTRO, e il «si accende da sé» era falso

Alla prima esecuzione il test 0 era rosso: `PushableRow.termine_pagamento_id`
**None** con la colonna esposta e il valore giusto a DB. La causa non era vostra:
`fetch_pushable_rows` costruisce la `col_map` filtrando i nomi sulla whitelist
`_PUSHABLE_SHARED_COLS` — e le due colonne nuove **non c'erano**. Il
`col_map.get` difensivo di §4 leggeva da una mappa che non le avrebbe contenute
mai: la frase «si accende da sé appena le colonne compaiono» (§3.1) era
**sbagliata**, e i 5 test di `ad1151da9` non potevano dirlo perché il mock del
cursore era fermo al contratto a 29 colonne — un fixture che riproduce la forma
sbagliata conferma un comportamento inesistente, **terza occorrenza** della
lezione `feedback_whitelist_dal_percorso_reale` in questo stesso filone.

Fix: le due colonne in `_PUSHABLE_SHARED_COLS` (con commento-sentinella: la
whitelist È il cancello del binding), mock dei test allineato al contratto a 31
colonne, asserzioni sul passaggio dei valori con **prova di mutazione eseguita**
(togliendo i due nomi dalla whitelist diventa rosso SOLO
`test_fetch_pushable_rows_maps_shared_columns`).

### 10.3 Non-regressione

- suite `apps.vendite`: **1436 verdi**;
- `smoke-fattura-aggregazione-termini.py` **7/7** e `smoke-fattura-scadenze.py`
  **10/10** rieseguiti col resolver ripuntato (`20260803-03`) sotto: verdi
  entrambi, nessun cambiamento osservabile sul loro perimetro — coerente con la
  vostra distribuzione «una sola attività si sposta su 35».

### 10.4 Cosa resta

- La **fattura 2263** resta com'è: EMESSA, non numerata, si corregge solo con
  la vostra Fase 6 (ritorno a DRAFT) — invariato da §6/§8.5.
- Validazione **a video** di «Termine»/«Modalità» nel drawer fattura su una
  fattura nuova (era già l'unico aperto del cantiere satelliti, e ora una
  fattura nuova porta davvero il termine del suo documento).
