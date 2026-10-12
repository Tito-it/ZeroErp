## 📘 Documentazione Concettuale – Funzione `script.fn_get_stato_push_segment`

> 👀 **Vedi anche**
>
**Consumatori (push-list, eleggibile ⇔ LIBERA):**
>
• [vendite.fn_list_ordini_da_pushare](/dbzero/vendite/funzioni/fn_list_ordini_da_pushare)
> • [vendite.fn_ddt_push_diagnosi](/dbzero/vendite/funzioni/fn_ddt_push_diagnosi) — per il DDT lo legge lei (rank 4 e colonna `segment`), e il lister ne deriva
> • [vendite.fn_list_ddt_da_pushare](/dbzero/vendite/funzioni/fn_list_ddt_da_pushare)
> • [vendite.fn_list_contratti_da_pushare](/dbzero/vendite/funzioni/fn_list_contratti_da_pushare)
>
**Consumatori (rami reason delle capability):**
>
• [script.fn_available_actions_ordine](/dbzero/script/funzioni/fn_available_actions_ordine)
> • [script.fn_available_actions_ddt](/dbzero/script/funzioni/fn_available_actions_ddt)

### 🎯 Scopo Principale

(creata 2026-07-19 — brief-db-push-commessa-gia-inviato §4b, rilievo ORD0000227)

**Classificatore condiviso dello stato-push di una riga documento** rispetto a
`vendite.commesse_attivita`. Prende la `segment_key` della riga (quella emessa
dalle push-list) e ritorna:

| valore | significato |
|---|---|
| `LIBERA` | nessuna attività **viva**: riga mai instradata in commessa, o instradata e ritirata (`ANNULLATA`) |
| `ALLOCATA` | attività vive presenti, non tutte fatturate — pushata, in attesa di billing |

⭐ **rev 2026-10-12 (`20261012-08`, brief-db-annullo-a-valle-riapre-a-monte, D-5 di
Tid): una riga `ANNULLATA` non occupa più il segmento.** Fino a quel giorno contava
come allocata (decisione del 2026-06-28: «instradata = esclusa; il ri-push è un
flusso da progettare a parte»). Il ri-push è quello di D30: annullata la commessa,
il documento a monte deve tornare spingibile. Sicuro sul modello: una riga
`ANNULLATA` con sorgente nasce dal ritiro all'annullo del documento a monte (morto,
escluso dai lister per stato) o della commessa; `ANNULLATA` è irreversibile. Il
predicato è scritto «diverso da `ANNULLATA`»: uno stato nuovo occupa, solo il ritiro
libera. Da quel giorno leggono questa funzione, invece di un predicato proprio, anche
`vendite.vw_preventivi_righe_smistabili_commessa`,
`vendite.vw_preventivi_smistamento_righe` e `vendite.fn_list_consumi_da_pushare`.
| `EMESSA` | attività presenti e **tutte** fatturate |

Il match è «la chiave esatta, o la chiave con un suffisso `#CMP:` / `#RET:`»:
vede anche le attività dei **componenti BoM**, il cui suffisso `#CMP:<componente_id>`
è appeso dal BE esattamente alla segment_key della riga
(`commesse_source_handlers.py`), e le **rettifiche** (`#RET:<n>`, rev 2026-08-18).
Dal 2026-09-21 il predicato non è più scritto con `LIKE` ma come **range a byte**
sugli operatori del pattern — vedi la revisione in fondo: sotto la policy RLS un
`LIKE` non usa mai l'indice.

### Perché esiste

Prima il predicato «già inviato» viveva in **due forme divergenti** — nelle
`fn_list_*_da_pushare` e nella query inline del ramo reason della capability
ordine — entrambe ancorate alla *fatturazione* (`stato_emissione = 'EMESSA'`)
e cieche sui `#CMP`. Effetto (ORD0000227): righe già pushate ri-elencate a ogni
giro del batch e azione «Invia a commessa» ri-offerta dopo il consumo. Ora
liste e capability leggono **lo stesso verdetto**: al prossimo cambio di
semantica si tocca un posto solo.

### Regole

- **Pura**, `LANGUAGE sql STABLE`: nessun raise, nessuna scrittura.
- Il parametro è la segment_key **completa** emessa dalla lista: per i
  contratti include `:M:<YYYY-MM>` (il push contratti è ricorrente mensile by
  design — il mese successivo ha chiave diversa e resta `LIBERA`).
- `fn_list_consumi_da_pushare` NON la usa: la sua chiave è un prefisso
  per-documento (`CONS:<uid>:%`), già corretto; lì il fix è stato solo
  rimuovere il filtro su `stato_emissione`.
- ⚠️ Performance: fino al 2026-09-21 i due rami `LIKE '...#CMP:%'` / `'...#RET:%'`
  erano una scansione intera di `commesse_attivita` **sotto la policy RLS**, a
  ogni chiamata — e la diagnosi del DDT la chiama per ogni riga attiva. La cura
  non era «solo» l'indice `varchar_pattern_ops` che questa riga prometteva:
  vedi la revisione del 2026-09-21.
- `BEGIN ATOMIC` (dal 2026-09-21): le dipendenze stanno in `pg_depend`; una
  rinomina di `commesse_attivita` viene rifiutata.

### Dipendenze DB

`vendite.commesse_attivita` (`segment_key`, `stato_emissione`).

---

### 🔄 rev 2026-08-18 — riconosce il suffisso `#RET:` delle rettifiche

Brief: `brief-design-note-credito-resi` (slice **N11**).

L'avvertenza era già scritta, nel commento vivo di
`vendite.fn_list_ddt_da_pushare`:

> *«È l'unica cintura che impedirà di ri-spingere una riga la cui differenza
> torna positiva per una RETTIFICA (nota di credito): chi introdurrà un
> segment_key nuovo per la rettifica deve insegnarglielo.»*

Il predicato guadagna quindi:

```sql
OR ca.segment_key LIKE p_segment_key || '#RET:%'
```

che copre **entrambe** le forme, perché il suffisso `#CMP:` di un kit viene DOPO
`#RET:<n>`:

```text
DDT:<uid>:R:<id>#RET:1
DDT:<uid>:R:<id>#RET:1#CMP:<componente>
```

⚠️ Ed è anche il motivo per cui la madre scrive `#RET` **prima** di `#CMP` e non
il contrario: così `split_part(segment_key, '#CMP:', 1)` continua a dare il
`kit_key` e `vw_af_merce_per_riga` legge la rettifica senza modifiche.

#### ⚠️ Non è cosmesi

Su una partita fatturata dalla corsia **DDT** il segmento porta già l'attività
`NORMALE`, quindi risulta `EMESSA` comunque: lì non cambia nulla. Su una partita
fatturata dalla corsia **ORD**, invece, il segmento DDT non ha alcuna attività —
e resterebbe `LIBERA` anche dopo la nota di credito. A impedire una ri-spinta ci
sarebbe **solo** la cintura XOR sullo stato del documento d'ordine.

⭐ **Due cinture sono una; una è zero.** Con il suffisso riconosciuto, la partita
è protetta dalla propria storia e non da una condizione che vive altrove.

⚠️ **Nessun cambio di comportamento all'applicazione**: al 2026-08-18 le righe
`RETTIFICA` erano zero, quindi nessun segmento conteneva `#RET:` e il
classificatore rispondeva esattamente come prima su ogni riga esistente. È una
cintura che entra in funzione il giorno in cui serve.

---

### 🔄 rev 2026-09-21 — il range leakproof: l'indice serve solo se la clausola sale sopra la policy

Brief: `brief-db-partita-merce-per-documento` §11 (**D14 giro 4, D8**).

Il classificatore è chiamato **per ogni riga attiva** di un DDT dalla diagnosi
(`fn_ddt_push_diagnosi`, colonna `segment`), e dal giro 3 la lista del push
senza documento eredita quel costo: 54 righe × 7,6 ms erano 400 dei 663 ms del
cockpit (fatto datato, dbdev come app, 21-09 sera). La causa sul modello:
`commesse_attivita` è sotto RLS, e con i due `LIKE` la lettura era la tabella
intera con la policy valutata **riga per riga**.

⛔ **E l'indice da solo non l'avrebbe curata.** Provato come `zeroerp_app` su una
tabella con `FORCE ROW LEVEL SECURITY` e una policy non leakproof: sotto una
policy PostgreSQL mette in un indice **solo clausole leakproof** — una clausola
valutata prima della policy potrebbe far trapelare righe invisibili — e `LIKE`
(`textlike`) non lo è. Nemmeno a costante diventa `Index Cond`; senza policy il
planner lo riscrive nel range e usa l'indice, ed è per questo che la prova da
owner mente.

La forma che regge è quella che il planner farebbe da solo se potesse, **scritta a
mano** con gli operatori del pattern, che confrontano i byte e sono leakproof:

```text
segment_key = k
OR (segment_key ~>=~ k || '#CMP:'  AND  segment_key ~<~ k || '#CMP;')
OR (segment_key ~>=~ k || '#RET:'  AND  segment_key ~<~ k || '#RET;')
```

`;` è il byte dopo `:`, quindi `[k#CMP:, k#CMP;)` è **esattamente** «comincia per
`k#CMP:`». Con l'indice `ix_commesse_attivita_segment_key` in `varchar_pattern_ops`
(ricreato nello stesso giro) è un `BitmapOr` di tre `Index Cond` sopra la policy,
in piano generico e custom.

**Semantica identica** per le chiavi che il classificatore riceve (uuid, cifre,
`:`): il range è un prefisso a byte, il `LIKE` un prefisso a caratteri con `_`/`%`
jolly, e nessuna chiave li contiene. Il vicino numerico (`:R:1` non vede `:R:12`)
e il suffisso ignoto (`#FOO` → `LIBERA`, come prima) sono i casi costruiti dal
presidio.

⛔ **Un `LIKE` qui dentro non deve tornare**: il presidio
`db/pgtap/script/test-fn-get-stato-push-segment-v1.sql` pinna la forma (il corpo
deparsato non contiene `LIKE` né `~~`) oltre ai tre valori con e senza suffissi.

⚠️ Resta aperta **D8(b)** del brief: una forma set-based (una scansione per
documento invece di una chiamata per riga, con questa scalare come proiezione)
per la lista senza documento — si decide sulla misura dopo l'apply.

### 🔄 rev 2026-10-10 — si entra dalla base del segmento

Il range qui sopra sale nell'indice, ma quando la chiave arriva come
**parametro** (piano generico: le liste del push, la diagnosi, le capability) il
pianificatore non conosce i bordi e stima ogni ramo a circa l'11 % della
tabella: la scansione intera vinceva. Da `20261010-82` la funzione entra
dall'**uguaglianza** `segment_base = split_part(p_segment_key, '#', 1)` sulla
colonna generata di `20261010-80`, indicizzata; i tre rami di prima restano come
filtro residuo e la implicano (una chiave che vale `k` o comincia per
`k#CMP:`/`k#RET:` ha la base di `k`), quindi i tre valori non cambiano: il
vicino numerico e il suffisso ignoto `#FOO` restano quelli del presidio.
`split_part` sta sul **parametro**, non sulla colonna: la clausola resta
leakproof per la tabella. Brief: `brief-db-segment-base-commesse-attivita`.

