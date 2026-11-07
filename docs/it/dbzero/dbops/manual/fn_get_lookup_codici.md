## 📘 Documentazione Concettuale – Funzione `dbops.fn_get_lookup_codici`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_overrides_cols](/dbzero/dbops/tabelle/automation_overrides_cols) — gli override per le tabelle con la chiave naturale sotto un altro nome
> * [config.lingue](/dbzero/config/tabelle/lingue) — il caso che gli override servono: la chiave è `codice_iso`
>
> Approfondimento funzioni:
>
> * [dbops.trgfn_child_requires_non_obsolete_parent](/dbzero/dbops/funzioni/trgfn_child_requires_non_obsolete_parent) — la difesa che vieta davvero un'istanza nuova su un catalogo obsoleto
> * [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa) — il «oggi» con cui si giudica l'obsolescenza

---

### 🎯 Scopo Principale

Il lookup generico dei cataloghi: restituisce, per una tabella di configurazione qualunque, la
stessa forma a cinque campi (`id`, `codice`, `codice_interno`, `descrizione`, `attivo`), con
ordinamento, paginazione e due filtri facoltativi su `attivo` e su `obsoleto_dal`.

È la sede unica delle tendine dei cataloghi: il backend la chiama per ogni lookup e non scrive
una query per tabella.

---

### ⭐ La struttura si legge dalla tabella, non da un elenco

La funzione non sa in anticipo che tabella riceverà: ne legge le colonne dal catalogo di
PostgreSQL e decide da lì.

* `id` è obbligatorio e deve essere un intero (`smallint`, `integer`, `bigint`): una tabella con
  `id` `uuid` è rifiutata;
* serve almeno uno fra `codice` e `codice_interno`, reale o dichiarato da un override;
* `descrizione` è obbligatoria;
* `attivo` e `obsoleto_dal` sono facoltativi: se ci sono, devono essere uno booleano e l'altro
  una data. Se mancano, il relativo filtro semplicemente non si applica e la lista esce intera.

Il campo `codice` del risultato è la colonna `codice`; se la tabella non l'ha, è il
`codice_interno`, e in mancanza anche di quello l'`id` scritto come testo. `codice_interno` è
vuoto quando la tabella non lo ha; `attivo` è vuoto quando la tabella non ha la colonna.

---

### ⭐ La chiave con un altro nome si dichiara, non si programma

Una tabella con una chiave naturale stabile ma con un altro nome (`config.lingue` ha
`codice_iso`) non obbliga a rinominare la colonna né a scrivere un ramo apposta: basta una riga
in `dbops.automation_overrides_cols` con ruolo `CODICE_COL` (la colonna da esporre come `codice`)
o `CODICE_INTERNO_COL` (quella da esporre come `codice_interno`).

L'override ha la precedenza su ciò che la funzione trova da sola, e vale anche per l'ordinamento:
ordinare per codice ordina sulla colonna dichiarata.

---

### Due filtri, due domande diverse

| Filtro | La domanda | Il default |
| --- | --- | --- |
| `p_attivo_only` | il riferimento è ancora valido? | **restringe**: solo le righe attive |
| `p_includi_obsoleti` | si può ancora scegliere per una cosa nuova? | **non restringe**: mostra anche gli obsoleti |

Con `p_includi_obsoleti` spento sono escluse le righe la cui data di obsolescenza è già arrivata,
cioè non successiva alla **data operativa** del giorno. Una riga senza data è sempre
selezionabile; una riga con la data nel futuro è un **ritiro programmato**, ed è selezionabile
fino a quel giorno.

⚠️ **L'asimmetria dei default è voluta.** Un default che nascondesse gli obsoleti cambierebbe in
silenzio il comportamento di tutti i chiamanti, compresi i filtri delle liste, dove un tipo
ritirato deve restare cercabile. Nascondere gli obsoleti nella tendina di creazione è una scelta
del chiamante.

⛔ Nascondere non è vietare: la difesa che impedisce davvero di creare un'istanza nuova su un
catalogo obsoleto è il guard `dbops.trgfn_child_requires_non_obsolete_parent`.

---

### Ordinamento e pagine

Si ordina per `descrizione` o per `codice`, in un verso o nell'altro; i vuoti vanno in fondo.
Ordinare per codice su una tabella che non ha né la colonna né un override ordina per
descrizione.

⭐ A parità di valore decide l'`id`, **nello stesso verso** della colonna: l'ordine è totale, e
chi sfoglia con `p_limit` e `p_offset` vede ogni riga una volta sola, senza ripetizioni né buchi.
È la stessa regola dello spareggio che il backend usa per le sue liste.

Senza `p_limit` la funzione restituisce tutte le righe che passano i filtri. Il backend la chiama
così, da zero e senza tetto, e cerca, ordina e pagina fuori, con il suo spareggio sull'`id`: un
tetto applicato prima della ricerca deciderebbe quali righe la ricerca può trovare.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — tabella non indicata, colonna o verso di ordinamento non ammessi,
  limite non positivo, offset negativo.
* `E_LOOKUP_STRUTTURA_TABELLA_INVALIDA` — la tabella non ha la forma richiesta: `id` mancante,
  `uuid` o di un tipo non intero; nessuna colonna di codice né override; `descrizione` mancante;
  `attivo` non booleano; `obsoleto_dal` non data.

---

### Test

* `db/pgtap/dbops/test-fn-get-lookup-codici.sql` — ordinamento nei due versi su tabelle reali, il
  filtro `attivo`, i rifiuti di parametro e dell'`id` `uuid`, lo spareggio sull'`id` nei due versi e
  le pagine che, concatenate, danno la lista intera.
* `db/pgtap/dbops/test-fn-get-lookup-codici-obsoleto-v1.sql` — il filtro dell'obsolescenza: il
  default che mostra tutto, l'esclusione, il ritiro programmato, la tabella senza la colonna e la
  colonna del tipo sbagliato.
* `db/pgtap/script/test-giornale-registri-catalogo-v1.sql` — il catalogo dei registri del giornale
  si legge da qui.

---

### Note di migrazione

* 2026-05-20 — nascono gli override in `dbops.automation_overrides_cols`, con la riga per
  `config.lingue`.
* 2026-06-30 — nasce il filtro su `obsoleto_dal` (`brief-db-obsoleto-dal-filtro-lookup-e-guard`).
* 2026-10-09 — la data di riferimento del filtro passa da quella di sistema alla data operativa
  (`script.fn_data_operativa`), il «oggi» del fuso aziendale.
* 2026-11-07 — l'ordinamento prende lo spareggio sull'`id`. Prima, a parità di valore, l'ordine
  lo sceglieva il piano; e il backend chiamava con un tetto di diecimila righe e cercava dopo il
  taglio, così su una tabella più lunga la ricerca non vedeva le righe oltre il tetto.

---

{% include-markdown "signature-core.md" %}
