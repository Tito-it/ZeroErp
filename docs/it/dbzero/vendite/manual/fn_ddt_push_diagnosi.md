## Documentazione Concettuale – Funzione `vendite.fn_ddt_push_diagnosi(p_ddt_id)`

> **Ultimo aggiornamento**: 3 novembre 2026

> **Vedi anche**
>
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)
> [vendite.fn_list_ddt_da_pushare](/dbzero/vendite/funzioni/fn_list_ddt_da_pushare) — **deriva** da questa funzione
> [script.fn_available_actions_ddt](/dbzero/script/funzioni/fn_available_actions_ddt) — la legge una volta
> [script.fn_get_stato_push_segment](/dbzero/script/funzioni/fn_get_stato_push_segment)
> [vendite.fn_partite_merce](/dbzero/vendite/funzioni/fn_partite_merce) — la partita, per documento

---
### 🎯 Scopo Principale

`vendite.fn_ddt_push_diagnosi(...)` è la **fonte unica dell'eleggibilità al push
a commessa**. Per ogni riga attiva di un DDT risponde a *perché questa riga non
è inviabile a commessa?* — `motivo = NULL` se è eleggibile, altrimenti **il**
motivo di esclusione, per precedenza — ed espone i quattro fatti che servono a
chi agisce su quella risposta: il billing account, la riga d'ordine sorgente, lo
stato-push del segmento e la **dose** da spingere.

Nasce per sciogliere un catch-all: un DDT non inviabile riceveva sempre lo
stesso messaggio — «dev'essere spedito o consegnato» — vero per una causa e
falso per le altre. Oggi è anche il posto **dove l'eleggibilità sta scritta**:
il lister che alimenta il push non ripete i predicati, li legge da qui.

⛔ **Un predicato di eleggibilità nuovo si aggiunge qui, come rank.** Nel lister
non c'è più un posto dove metterlo.

---

### Le cause, con precedenza

`motivo_rank` è la precedenza: più basso = più forte. Quando una riga ricadrebbe
in più cause, vince quella di rank minore; quando le righe di uno stesso DDT
ricadono in cause diverse, chi consuma la funzione prende il **minimo** rank.

La precedenza è a **due livelli**: prima le cause di **documento** (valgono per
tutto il DDT), poi le cause di **riga**. I motivi della partita (7–10) stanno
apposta **prima** del contatore: una partita senza conto ha dose zero, e il
contatore scatterebbe per primo mascherando la ragione vera.

| rank | `motivo` | tipo | significato |
| --- | --- | --- | --- |
| 1 | `DDT_ANNULLATO` | documento | il DDT è annullato (documento morto) |
| 1 | `DDT_RESO` | documento | la merce è tutta tornata indietro |
| 2 | `DDT_SOLO_TRASPORTO` | documento | causale non fatturabile **o assente**: accompagna la merce senza fatturare (DL-28) |
| 3 | `DDT_SENZA_BA` | documento | nessun billing account risolvibile — né in testata né dall'ordine sorgente — **o non visibile** a chi legge (la tabella ha RLS) |
| 4 | `DDT_ROUTED` | riga | riga già instradata: `segment` è `ALLOCATA` o `EMESSA` |
| 5 | `DDT_MERCE_IN_VIAGGIO` | riga | lo stato è precedente al trigger dell'ordine (o, senza ordine, non è spedito/consegnato) |
| 6 | `DDT_FATTURA_DA_ORDINE` | riga | l'ordine sorgente fattura alla conferma (regola XOR): il DDT non transita mai in commessa |
| 7 | `DDT_RICONSEGNA` | riga | riga di ri-consegna: la merce è già contata sulla partita d'origine |
| 8 | `DDT_NON_FATTURABILE` | riga | la partita non conta ai fini della fatturazione |
| 9 | `DDT_NON_MISURABILE` | riga | kit di cui non si ricostruisce la quantità del padre |
| 10 | `DDT_SENZA_PARTITA` | riga | nessuna partita (DDT sotto `EMESSO`): fallback, perché una riga non spingibile non deve **mai** uscire con `motivo = NULL` |
| 11 | `DDT_CONTATORE` | riga | c'è un conto ed è ≤ 0: quantità già coperta per altra via |

I motivi 7–9 non ri-derivano niente: sono la colonna `stato` della partita,
che è già la decomposizione di «differenza vuota» nelle sue cause.

---

### Il ramo della riga-onere (rev 2026-11-03)

Dal `20261103-39` (brief-db-addebito-trasporto-ordine §8.1, §8.3) la riga-onere
(`script.fn_natura_e_merce` falso sulla natura congelata) non ha partita di merce:

* le rank 7–11 (ri-consegna, non fatturabile, non misurabile, senza partita, contatore) non la
  guardano, e la dose è la quantità della riga (l'anti doppione resta il segmento, rank 4);
* le rank 1–6 valgono come per la merce. Per l'onere **senza legame** (scritto a mano) il trigger di
  fatturazione si legge dall'ordine sorgente della **testata**: sulla bolla di un ordine che fattura
  alla conferma è `DDT_FATTURA_DA_ORDINE` (prima risultava pushabile). Con il legame (copiato
  dall'ordine) il trigger resta quello del legame.
  Quel trigger di testata lo dà il building block `vendite.fn_ddt_trigger_ordine_testata`
  (`20261103-43`/`-44`), lo stesso che usa la check di emissione: una sede sola.

Sulle righe di merce nulla cambia (prova pre-apply: diagnosi e lister identici prima e dopo, su una
popolazione costruita di bolle di sola merce).

### I quattro fatti esposti

Oltre a `ddt_id`, `riga_id`, `motivo_rank` e `motivo`, ogni riga porta ciò che
la funzione ha già dovuto calcolare per giudicare — e che chi agisce non deve
ricalcolare:

| colonna | cos'è | chi la usa |
| --- | --- | --- |
| `billing_account_id` | il BA della riga: testata, altrimenti l'ordine sorgente; letto attraverso `anagrafiche.billing_account`, quindi `NULL` anche quando esiste ma chi legge non lo vede | il lister (proiezione, filtro per BA) |
| `ordine_riga_id` | la riga d'ordine sorgente: il **primo fulfillment per id**. È l'unica sede di questa regola | il lister (ordine, prezzo e valuta sorgente, per chiave) |
| `segment` | `LIBERA` / `ALLOCATA` / `EMESSA` da [`fn_get_stato_push_segment`](/dbzero/script/funzioni/fn_get_stato_push_segment) | la capability (precedenza *già inviato* / *già fatturato*) |
| `quantita_push` | la **dose**: `GREATEST(0, LEAST(quantita della riga, differenza della partita))` — calcolata una volta, giudicata dal rank 11 e proiettata dal lister | il lister (`quantita`, e `qta_operativa` in proporzione) |

---

### Chi ne deriva, chi la legge

- [`vendite.fn_list_ddt_da_pushare`](/dbzero/vendite/funzioni/fn_list_ddt_da_pushare)
  **deriva** da qui: `FROM fn_ddt_push_diagnosi(p_ddt_id) WHERE motivo IS NULL`,
  più i suoi filtri di chiamata (competenza, BA, limit) e la proiezione dei
  campi per la pipeline. Le righe che il push alimenta e quelle che questa
  funzione dichiara eleggibili sono la **stessa query**: non c'è un'equivalenza
  da tenere, c'è una derivazione.
- [`script.fn_available_actions_ddt`](/dbzero/script/funzioni/fn_available_actions_ddt)
  la legge **una volta**, con una `SELECT` aggregata: `can_push_commessa` =
  esiste una riga con `motivo NULL` (vero per costruzione, perché il push legge
  la stessa cosa); altrimenti, **prima** del motivo, la precedenza sul segmento
  (`ALLOCATA` → `DDT_GIA_INVIATO`, `EMESSA` → `DDT_GIA_FATTURATO`); altrimenti
  il motivo a rank minimo, mappato per **stringa** — rinumerare non la rompe, e
  il suo `CASE` ha un `ELSE` che fa cadere i motivi nuovi nel generico. Dà un
  ramo proprio a `SOLO_TRASPORTO`, `MERCE_IN_VIAGGIO`, `FATTURA_DA_ORDINE`;
  gli altri finiscono in `DDT_NON_PUSHABILE`.

---

### Come è costruita

Il corpo è `BEGIN ATOMIC`: le dipendenze — `fn_partite_merce`,
`fn_get_stato_push_segment`, le tabelle e i cataloghi — stanno in `pg_depend`,
quindi una rinomina a monte viene **rifiutata** dal catalogo invece di lasciare
una funzione morta (il presidio dei riferimenti morti compila solo il plpgsql).
`SECURITY INVOKER`: la RLS resta di chi legge.

Il documento chiesto è un **seme a due rami** (`d.id = p_ddt_id` in `UNION ALL`
con `p_ddt_id IS NULL`), mai `p IS NULL OR …`: in piano generico — ed è il caso,
perché lister e capability sono plpgsql — quell'`OR` sarebbe una scansione
intera di `vendite.ddt` sotto policy, mentre il ramo «tutti» con un predicato
senza colonne diventa un *One-Time Filter* e non viene nemmeno eseguito. La
partita si legge da [`fn_partite_merce`](/dbzero/vendite/funzioni/fn_partite_merce)
con il DDT come seme: la **chiusura** del documento, non le partite di tutti.

Ciò che esclude è un `LEFT JOIN` con una rank sotto: la funzione deve
**spiegare** l'esclusione, non ripeterla. Il perimetro sono le righe **attive**
del documento: una riga disattivata non è una riga del documento, per questa
funzione come per la partita e per il lister.

---

### Input / Output

- **Input**: `p_ddt_id` (opzionale). Se valorizzato, il solo DDT chiesto (uso
  della capability e del lister per documento). Se `NULL`, tutte le righe
  attive dei DDT del sistema (lista push, cockpit).
- **Output**: una riga per ogni riga attiva considerata — `ddt_id`, `riga_id`,
  `motivo_rank` (`NULL` se eleggibile), `motivo` (`NULL` se eleggibile),
  `billing_account_id`, `ordine_riga_id`, `segment`, `quantita_push`.

⚠️ Una colonna nuova nel `RETURNS TABLE` è `DROP FUNCTION` + rigenera
(`CREATE OR REPLACE` non cambia il tipo di ritorno): oggi nessuna vista dipende
da questa funzione, e i chiamanti sono plpgsql.

---

### Presidio

`db/pgtap/script/test-fn-available-actions-ddt-reason-catch-all-v1.sql` (16),
a casi **costruiti** — non confronta la popolazione: l'eleggibile letto a tre
voci (diagnosi, lister, capability), `ALLOCATA` ed `EMESSA` sul segmento, la
precedenza del segmento sul documento annullato, le cause del catch-all, la
coerenza rank ↔ motivo e delle quattro colonne esposte, il pin di **forma**
(il lister nomina questa funzione e nessun predicato suo; la capability legge
solo questa; il corpo è `BEGIN ATOMIC` e non `DEFINER`), lo scope sotto RLS.

---

> **Brief**: `brief-db-ddt-reason-push-catch-all.md` §3 (Decisione A) — la
> nascita; `brief-db-partita-merce-per-documento.md` §2-bis.8 e §10 — la
> fonte unica (D4, forma B2) e la partita per documento (D14).
> **Changeset**: `20260719-15` (nascita), `20260818-20` (riallineata alla
> partita), `20260921-24` (la partita come seme), `20260921-32` (fonte unica:
> `BEGIN ATOMIC`, le quattro colonne, il seme in `UNION ALL`).
