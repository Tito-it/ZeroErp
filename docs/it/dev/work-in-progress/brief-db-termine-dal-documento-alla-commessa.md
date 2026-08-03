# Brief BE → DB — il termine di pagamento del documento non arriva alla commessa

> **Chi scrive:** BE (`dev/backend-tid`), 2026-08-03.
> **A chi:** team DB (`dev/db-tid`).
> **Cos'è:** una fattura reale è uscita col piano rate **sbagliato**, in
> silenzio. La metà applicativa è già corretta e testata; restano **due
> colonne** nel contratto delle `fn_list_*_da_pushare` e **una decisione** sul
> livello 1 di `fn_resolve_termini_pagamento`.
> **Correlati:** [piano-db-satelliti-fattura.md](piano-db-satelliti-fattura.md) (D-R) ·
> [piano-be-fe-satelliti-fattura.md](piano-be-fe-satelliti-fattura.md)

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
