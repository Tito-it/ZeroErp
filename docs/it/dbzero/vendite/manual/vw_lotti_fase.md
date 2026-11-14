## 🔍 Documentazione Concettuale – Vista `vendite.vw_lotti_fase`

> **Versione**: 2026-09-09 — nata con
> [brief-db-il-trattenuto-passa-lo-stesso](/dev/work-done/brief-db-il-trattenuto-passa-lo-stesso)
> (lotto L1 · migration `20260909-51`)

> **Vedi anche**
>
> [config.stati_doc_fiscale](/dbzero/config/tabelle/stati_doc_fiscale) — i tre assi, a catalogo
> [vendite.vw_documenti_trattenuti_da_lotto](/dbzero/vendite/views/vw_documenti_trattenuti_da_lotto) — chi chiede «questo lotto tiene ancora il documento?»
> [script.fn_check_documento_escludibile_da_giro](/dbzero/script/funzioni/fn_check_documento_escludibile_da_giro) — la **porta d'uscita**, che usa lo stesso flag
> [script.fn_check_lotto_riportabile_a_draft](/dbzero/script/funzioni/fn_check_lotto_riportabile_a_draft) · [script.fn_check_fattura_eliminabile_da_lotto](/dbzero/script/funzioni/fn_check_fattura_eliminabile_da_lotto) · [script.fn_check_lotto_annullabile](/dbzero/script/funzioni/fn_check_lotto_annullabile)

---

### 🎯 Scopo Principale

**In che fase è questo lotto**, e in un posto solo.

Una riga per lotto: i tre assi che il catalogo degli stati porta con sé, più il
derivato che li interpreta. Non decide niente — dice un fatto, e lo dice sempre,
anche quando lo stato non si risolve.

---

### Perché esiste

La stessa lettura era scritta in **cinque** punti, e ognuno rifaceva da capo lo
stesso `LEFT JOIN` a `config.stati_doc_fiscale` con la propria difesa.

⛔ **E non era duplicazione innocua.** La quinta lettura aveva scritto «vivo»
implementandolo come *«non annullato»*. Ma un lotto **DEFINITIVA** non è
annullato: è **chiuso**. Ne discendeva che un documento fatturato in un lotto
regolarmente chiuso risultava trattenuto **per sempre**, e il verbo «Riporta da
emettere» smetteva di avere effetto senza che niente segnalasse nulla.

⭐ Il precedente è in casa: il commento di `fn_check_lotto_riportabile_a_draft`
racconta che `NOT IN ('DRAFT','EMESSA')` erano **otto copie della stessa frase**,
e che `congela_fiscale` nacque proprio per toglierle. Il flag aveva già ucciso
l'elenco di stati; restava duplicato **il modo di leggerlo**.

---

### Il derivato è **uno solo**, e si chiama `pre_fiscale`

| Colonna | Che cos'è |
| --- | --- |
| `is_abortito` · `congela_fiscale` · `chiude_lotto` | **il fatto**, come sta a catalogo — nullabili, perché un fatto ignoto si dice ignoto |
| `pre_fiscale` | **la decisione**: `NOT congela_fiscale`, mai nulla |

| stato | `is_abortito` | `congela_fiscale` | `chiude_lotto` | **`pre_fiscale`** |
| --- | :---: | :---: | :---: | :---: |
| DRAFT | f | f | f | **t** |
| EMESSA | f | f | f | **t** |
| DEFINITIVA | f | t | **t** | f |
| INVIATA | f | t | f | f |
| REGISTRATA | f | t | f | f |
| ANNULLATA | **t** | t | f | f |
| *(non risolvibile)* | — | — | — | **f** |

`pre_fiscale` risponde a due domande che sono la stessa cosa: *«il giro può
ancora agire su questo documento?»* e *«il documento si può ancora togliere dal
giro?»*.

---

### ⛔ Perché **non** si deriva da `chiude_lotto`

È l'errore che la prima stesura di questa vista conteneva, ed è istruttivo.

Sembra naturale scrivere «il giro non ha finito» come
`NOT is_abortito AND NOT chiude_lotto`. Non regge, e lo dice il catalogo delle
transizioni: **`DEFINITIVA → INVIATA` è ammessa** per il lotto, e INVIATA ha
`chiude_lotto = f`.

> `chiude_lotto` marca la **transizione che chiude**, non la **proprietà di
> essere chiuso**: gli stati che vengono *dopo* non la portano.

⇒ Un lotto chiuso e poi inviato sarebbe tornato «aperto», e i suoi documenti
sarebbero risultati trattenuti di nuovo. È la stessa forma di difetto che questa
vista nasce per chiudere, un piano più in là.

---

### ⭐ E coincide con la porta d'uscita — che è la ragione, non una fortuna

`script.fn_check_documento_escludibile_da_giro` ammette di togliere un documento
dal giro **solo se il lotto è pre-fiscale**. La vista dei trattenuti usa lo
stesso flag per dire «trattenuto».

> **Trattenuto ⇔ si può ancora uscire.**

⛔ Se i due predicati divergessero, esisterebbe un documento **trattenuto senza
via d'uscita**: un cancello senza chiave. È esattamente il difetto che il
cantiere ha trovato, e tenerli sullo stesso flag è ciò che impedisce che
ricompaia.

---

### ⚠️ Le due assenze, e non sono la stessa cosa

| Cosa manca | Che cosa significa | Come risponde la vista |
| --- | --- | --- |
| lo **stato** non si risolve | non succede: lo stato del lotto è obbligatorio e nasce dal vocabolario | la vista lo difende lo stesso: `pre_fiscale` è `false` (fail-closed) e i tre assi restano `NULL` |
| la **riga** non c'è | il lotto non esiste, oppure è fuori dal perimetro RLS | è un'altra domanda: i quattro `fn_check_*` la trattano come errore (`E_LOTTO_NON_TROVATO`) |

⚠️ **Il fail-closed sta nel derivato, non nei grezzi.** Se anche i tre assi
fossero già difesi, la stessa colonna direbbe «fatto» e «difesa» insieme — per
giunta con default in direzioni opposte.

---

### Sicurezza

`security_invoker = true`: la vista legge `vendite.fatturazione_lotti`, che ha la
RLS. Il perimetro resta quello di chi interroga, esattamente come quando i
cinque lettori facevano il join per conto proprio. ⚠️ Va **ri-specificato** a
ogni `CREATE OR REPLACE VIEW`: non è visibile in `pg_get_viewdef` e PostgreSQL
lo azzera in silenzio.

---

### Verifica

`db/pgtap/vendite/test-vw-lotti-fase-v1.sql` (plan 6) — i sette casi sono
**costruiti**, non cercati fra i lotti di oggi. Il test 6 non guarda la vista:
guarda il **catalogo**, e tiene in vita la ragione per cui il flag non è
`chiude_lotto`.

⭐ E la prova che l'adozione non ha cambiato nessuna decisione sono i pgTAP dei
quattro `fn_check_*`, che restano verdi **senza essere stati toccati**.
