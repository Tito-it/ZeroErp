## 📘 Documentazione Concettuale – Tabella `config.sorgenti`

> 👀 **Vedi anche**
>
Approfondimenti tabelle/domìni collegati:
>
[config.note_stili](/dbzero/config/tabelle/note_stili)
> [config.note_stili](/dbzero/config/tabelle/note_stili)
>
Approfondimenti funzioni/trigger:
>
[config.trgfn_sorgenti_norm](/dbzero/config/funzioni/trgfn_sorgenti_normalize)

---

La tabella **`config.sorgenti`** definisce il **dizionario centralizzato delle sorgenti applicative**.

È pensata per:

* identificare in modo **standard e normalizzato** la “sorgente” di un collegamento (es. *ATTIVITA*, *PREVENTIVO_RIGA*, *DDT_VENDITA*);
* supportare meccanismi di **idempotenza** e **validazione polimorfa** (tramite `target_table` e `key_selector`), cioè controlli che possono agire su tabelle diverse con la stessa logica;
* fungere da perno per collegare record di tabelle eterogenee a **note**, **log**, **attività**, **job**, ecc.

---
### 🎯 Scopo Principale
(latest update 24-01-2026)
* Fornire un **catalogo univoco** delle sorgenti applicative utilizzate in:

  * tabelle di collegamento (es. note collegate a entità diverse),
  * funzioni di validazione polimorfa su tabelle target,
  * sistemi di idempotenza/lock (es. registrazione eventi, attività, job).
* Normalizzare i riferimenti alle sorgenti per evitare codifiche testuali sparse e non controllate nel database.
* Permettere a trigger generici di **individuare automaticamente**:

  * quale tabella target leggere/validare (`target_table`),
  * quale chiave usare (`key_selector`: `id` o `uid`).

---

### Vincoli e Regole Aziendali

* **Chiave primaria** (`id`):

  * identificatore tecnico `bigint` con identity.

* **Codici sorgente**:

  * `codice_interno`:

    * codice **funzionale interno**, univoco (`uq_sorgenti_codice_interno`),
    * non vuoto (`chk_sorgenti_codice_interno_non_vuoto`),
    * normalmente gestito in **UPPER** (come da commento),
    * dovrebbe essere considerato **immutabile** a livello di regole applicative.
  * `codice`:

    * codice esposto o operativo, anch’esso univoco (`uq_sorgenti_codice`),
    * usato da UI, integrazioni, configurazioni leggibili.

* **Categoria** (`categoria`):

  * classificazione opzionale ma consigliata della sorgente (es. `ANAGRAFICA`, `DOCUMENTO`, `PROCESSO`);
  * utilizzata per raggruppare e filtrare sorgenti in base al tipo di entità collegata;
  * **non modificabile** dopo la creazione (vedi trigger `trg_sorgenti_a10_upd_lock_columns`).

* **Area documentale** (`area`) — *aggiunta 27-07-2026*:

  * area corrispondente alla sorgente: `PREVENTIVI`, `ORDINI`, `CONTRATTI`, `DDT`, `OFFERTE`, `COMMESSE`;
  * è la chiave con cui `vendite.vw_dash_fatturazione_documenti` — e le sei viste per-sorgente che la compongono — etichetta i documenti. Serve a tradurre un riferimento tecnico nel **numero leggibile** che l'operatore riconosce;
  * **`NULL` = la sorgente non è un documento sfogliabile** (`ATTIVITA`, `ATTIVITA_CONSUMI`, `FATTURA`, `RESO_VENDITA`): non hanno una scheda nel cockpit di fatturazione. I consumatori usano `LEFT JOIN`, così un riferimento senza area non sparisce dagli elenchi;
  * `CHECK` non-vuota: `''` sarebbe indistinguibile da `NULL` a occhio ma si comporterebbe diversamente nel join (matcherebbe nulla invece di saltare);
  * ⚠️ **non è fra le colonne lock**, a differenza di `categoria`. La categoria è strutturale — classifica il tipo di entità e cambia il comportamento; l'area è una mappa di **presentazione** verso un altro vocabolario, che può legittimamente aver bisogno di correzione se una vista di dashboard cambia etichetta.

  > **Perché questa colonna esiste.** Prima del 27-07-2026 il vocabolario «area» **non esisteva come dato**: la stringa era scritta a mano dentro ciascuna delle sei viste per-sorgente (`'PREVENTIVI'::varchar AS area` in `vw_dash_fatturazione_preventivi`, e così via). Alla sesta occorrenza è stato estratto qui, accanto agli altri attributi che descrivono la sorgente. La bonifica delle sei viste, che possono leggerla da qui, è una rifinitura separata.
  >
  > Riferimento: `brief-db-emissione-fattura-per-documento-sorgente` decisione D-5.

* **Descrizione** (`descrizione`):

  * testo leggibile che descrive in modo chiaro cosa rappresenta la sorgente (es. “Riga preventivo vendita”, “DDT di vendita”, “Attività di fatturazione”).

* **Stato di attivazione** (`attivo`):

  * indica se la sorgente è utilizzabile nelle nuove configurazioni;
  * le sorgenti utilizzate storicamente non dovrebbero essere cancellate, ma eventualmente rese non attive.

* **Metadati estensibili** (`meta`):

  * campo `jsonb` obbligatorio con default `{}`;
  * utilizzabile per:

    * parametri di comportamento specifici della sorgente,
    * indicazioni su tabelle correlate,
    * regole speciali per trigger o job;
  * la struttura del JSON deve seguire linee guida condivise per evitare incoerenze.

* **Target polimorfo** (`target_table`):

  * campo di tipo `regclass` che identifica la **tabella target** associata alla sorgente (schema + tabella);
  * utilizzato da trigger/funzioni polimorfe per:

    * verificare l’esistenza di una riga sorgente;
    * applicare controlli consistenti su entità diverse.

* **Selettore chiave** (`key_selector`):

  * indica quale tipo di chiave utilizzare per identificare la riga nella tabella target;
  * vincolato dal check `chk_sorgenti_key_selector_values` ai soli valori ammessi:

    * `id` → chiave intera/bigint,
    * `uid` → chiave UUID.
  * guida la logica dei trigger polimorfi su come costruire le query di validazione.

* **Selettore etichetta** (`label_selector`) — *aggiunta 20-08-2026*:

  * la **gemella** di `key_selector`: quella dichiara la colonna con cui la riga
    si **trova**, questa la colonna con cui il documento si **nomina** — il
    numero che l'operatore riconosce (`DDT0010839`, `ORD0000227`, `RESO0005122`);
  * non è uniforme, ed è per questo che è un **dato** e non un `CASE` dentro una
    funzione: `numero` su preventivi, contratti, ordini, DDT, resi e fatture;
    `codice` su offerte commerciali e commesse;
  * **`NULL` = la sorgente non ha un numero leggibile** (`ATTIVITA`,
    `ATTIVITA_CONSUMI` e le cinque `*_RIGA`). Non è un errore, e **non spegne**
    la risoluzione dell'id;
  * la legge [`vendite.fn_get_sorgente_documento_ref`](/dbzero/vendite/funzioni/fn_get_sorgente_documento_ref)
    con `format(%I)`;
  * vincolata dal check `chk_sorgenti_label_selector_identificatore`: o `NULL`, o
    un identificatore PostgreSQL minuscolo non quotato.

  > ⚠️ **Il CHECK è igiene contro il REFUSO, non contro l'injection** — quella la
  > copre `%I`. Un nome sbagliato non darebbe nessun errore: il resolver cattura
  > `undefined_column` e risponde `NULL`, e l'unico sintomo sarebbe una **colonna
  > vuota a video**. Il cancello che verifica l'esistenza reale della colonna sta
  > nel pgTAP (`test-fn-list-commessa-attivita-provenienza-v1`, test 10), perché
  > un `CHECK` non può interrogare `pg_attribute`.
  >
  > ⭐ E un secondo invariante (test 11) tiene la coerenza con `area`: una
  > sorgente **sfogliabile** deve avere anche un numero. Senza, la colonna
  > «Origine» della lista attività resterebbe vuota per sempre su quel dominio.
  >
  > ⚠️ **Le cinque `*_RIGA` non sono nel CSV di seed.** Misurato il 20-08-2026:
  > `config.sorgenti` ha **15 righe nel database e 10 nel CSV** — gli id 3, 5, 7,
  > 9, 11 esistono solo nel DB. `loadUpdateData` non tocca chi non trova, quindi
  > restano a `NULL`, che per loro è il valore giusto. È una divergenza
  > preesistente, non una dimenticanza di questa colonna.
  >
  > ✅ **Superata.** Al 20-10-2026 il CSV porta **tutte** le righe del database
  > (29), confrontate colonna per colonna: la divergenza non c'è più, e il
  > `NOT NULL` di `etichetta` (sotto) la presuppone.

* **Etichetta** (`etichetta`) — *aggiunta 20-10-2026*, brief
  `brief-db-grammatica-unica-documenti` §12.9:

  * il **nome del tipo di documento come lo legge una persona**, sulla carta:
    «Preventivo», «Offerta», «Ordine», «DDT», «Reso». Diversa da `descrizione`,
    che resta la **nota tecnica** della sorgente («Offerta commerciale
    (testata)»);
  * la legge la stampa: la provenienza di un ordine è `ordine.origine.etichetta`
    nel modello standard «Ordine di vendita» (versione 2, forma dei dati 3);
  * **`NOT NULL` per ogni riga**, anche le `*_RIGA`: una sorgente nuova entra
    col suo nome. Il valore sta nel CSV, e il vincolo si accende in `90_end`
    (`20261020-23`), dopo il mirror; `chk_sorgenti_etichetta_non_vuota`
    rifiuta la stringa vuota;
  * una sola lingua, l'italiano, come le altre parole di stampa del catalogo.

  > ⭐ **Perché nel DB e non nelle traduzioni.** Le etichette c'erano già, ma
  > solo nel frontend: il backend di stampa non le legge, e una mappa in Python
  > sarebbe stata la seconda copia delle stesse parole. La stampa prende le
  > parole dal catalogo, come la fattura fa con `tipo_doc_fiscale.descrizione`.

* **Audit**:

  * `data_insert`, `user_insert`, `data_update`, `user_update` tracciano le modifiche al catalogo sorgenti;
  * la gestione può essere uniformata in futuro tramite trigger generici di audit.

* **Tipo documento fiscale** (`tipo_doc_fiscale_id`):

  * opzionale, usato per sorgenti **RIGA** nella generazione di `attivita_fatturabili`;
  * se valorizzato, ha priorita` sul tipo documento di default della utility.

---

### 🔑 Convenzione chiave sorgente (`id` vs `uid`) — mappa e trappole

> **Leggere prima di costruire qualsiasi grafo/join tra documenti** (lineage,
> genealogia, proiezione stato). Questa convenzione è **voluta e portante**: non
> va "ripulita".
>
> 📖 Per il **funzionamento completo** del meccanismo (a cosa serve, come si usa, il
> guard, e le query per lo **stato d'uso vivo**) vedi la guida
> [Sorgente polimorfa](/guide/sorgente-polimorfa). Questa sezione ne è la mappa-chiave.

**Mappa attuale `key_selector` per tipo** (verificata sul seed):

| Sorgente | `key_selector` |
|---|---|
| `PREVENTIVO`, `OFFERTA_COMMERCIALE` | **`uid`** (UUID) |
| `ORDINE_VENDITA`, `CONTRATTO`, `DDT_VENDITA`, `FATTURA`, `COMMESSA`, `ATTIVITA`, `ATTIVITA_CONSUMI` | **`id`** (bigint, `::text`) |

Cioè: nelle tabelle di collegamento polimorfe (`pratiche.pratiche_sorgenti`,
`vendite.commesse_sorgenti`) e nelle viste `vw_stato_sorgente_*`, la colonna
`sorgente_uid` (di tipo `text`) contiene **l'uid per preventivo/offerta** e
**l'id (::text) per gli altri**. Dal 2026-07-18 la convenzione è **blindata**
(brief-db-guard-sorgente-polimorfa) da due livelli:

* **rubinetto**: `vendite.fn_link_commessa_sorgente` normalizza la chiave prima
  di scrivere (traduce l'uuid dei chiamanti storici in `id::text` per i tipi a
  chiave `id`; formato non conforme → `E_SORG_FORMATO`, uuid non risolvibile →
  `E_SORG_NORM_NON_RISOLTA`);
* **guard**: `script.trgfn_guard_sorgente_polimorfa_testuale` (modello B) valida
  formato ed esistenza su INSERT/UPDATE di `pratiche_sorgenti` e
  `commesse_sorgenti`.

⭐ **Dal 2026-10-05 «formato» vuol dire forma canonica**: la chiave si salva esattamente
come la scrive il database (`id::text`, `uid::text` minuscolo con i trattini), perché è
in quella forma che la cercano i lettori. Una sola regola per chi scrive e per chi legge:
`script.fn_sorgente_chiave_id` / `script.fn_sorgente_chiave_uuid`.

> Nota COMMESSA: `target_table` del tipo è `vendite.commesse` (fix 2026-07-18:
> il seed storico puntava a `vendite.commesse_attivita`, il marker di pipeline —
> ma i link di collegamento usano l'id della **commessa**, ed è contro
> `vendite.commesse` che il guard risolve).

**⚠️ Due meccanismi diversi — non confonderli:**

1. **Sorgente polimorfa** (questa tabella + `pratiche_sorgenti` /
   `commesse_sorgenti` / `vw_stato_sorgente_*`): chiave nodo =
   `(sorgente_tipo_id, sorgente_uid)`, con `sorgente_uid` **secondo
   `key_selector`**. Guard attivo: `trgfn_guard_sorgente_polimorfa_testuale`
   (modello B — chiave testuale; la sorella `_tipizzata` per il modello A a
   colonne tipizzate esiste ma oggi non è agganciata).
2. **Colonne tipizzate dirette** (fuori dal meccanismo polimorfo): es.
   `vendite.ddt.sorgente_uid` e `vendite.resi.sorgente_uid` sono **`uuid`** (puntano
   a `ordini.uid` / `ddt.uid`); `vendite.ordini.documento_origine_id` e
   `vendite.contratti.offerta_id` sono **`bigint`** (puntano per `id`). Ognuna è
   corretta per sé, ma **non** passa per `key_selector`.

**Regola pratica per chi unisce documenti (es. lineage):** usare la **chiave
nativa polimorfa** `(sorgente_tipo_id, sorgente_uid)` come identità del nodo (per
la commessa → `id::text`, coerente con `key_selector='id'`). Le colonne tipizzate
dirette del punto 2 vanno **tradotte** su quella chiave con un join alla tabella
target (es. `ddt.sorgente_uid` uuid → `ordini.id::text`). **Non** standardizzare i
due meccanismi a un'unica chiave "al volo": è un refactor del motore polimorfo
(guard + resolver + `vw_stato_sorgente_*` + writer), non un ritocco.

> Nota storica: le tabelle **più vecchie** referenziano per `id`, quelle **più
> recenti** (ddt, resi) per `uid`. La disomogeneità è incapsulata da `key_selector`
> e dai tipi di colonna; si vede solo unendo tutto in un grafo unico.

---

### Relazioni

`config.sorgenti` è una tabella **di dominio/i18n logico** usata tipicamente da:

* **Tabelle di note collegate a entità diverse**:

  * una nota può salvare `sorgente_id` + chiave della riga (id/uid) cui si riferisce;
  * tramite `target_table` e `key_selector` è possibile verificare la coerenza del collegamento.

* **Tabelle di attività / job / log applicativo**:

  * per tracciare da quale sorgente logica (documento, processo, evento) nasce una certa attività o un certo log.

* **Meccanismi di idempotenza**:

  * utilizzando `codice_interno` e la chiave della riga sorgente, è possibile evitare esecuzioni duplicate di processi.

> In generale, dove serve un **collegamento generico e riusabile** a “qualcosa nel sistema”, `config.sorgenti` diventa il punto di partenza per identificare *cosa* sia quel “qualcosa”.

---

### Vantaggi Operativi

* **Centralizzazione**: tutte le sorgenti logiche del sistema sono censite in un unico punto.
* **Riutilizzo**: le stesse definizioni di sorgente possono essere impiegate in note, log, attività, job, idempotenza, ecc.
* **Polimorfismo controllato**: grazie a `target_table` e `key_selector` è possibile scrivere **trigger e funzioni generiche** che lavorano su entità diverse senza perdere sicurezza.
* **Governance**: categorie, descrizioni e metadati permettono di documentare e governare l’uso delle sorgenti nel tempo.
* **Evolutività**: l’uso di `meta` consente di arricchire il comportamento associato alle sorgenti senza modificare la struttura fisica della tabella.

---

> **“`config.sorgenti` è il dizionario centrale che dà un nome e una struttura alle ‘origini’ dei dati e dei processi in Zero ERP, abilitando controlli polimorfi e collegamenti robusti tra moduli diversi.”**
