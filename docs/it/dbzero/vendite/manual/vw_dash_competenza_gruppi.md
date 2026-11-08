## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_competenza_gruppi`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — `apribile`, `target_table`, `label_selector` del tipo
>
> Approfondimento viste:
>
> * [vendite.vw_dash_competenza_attivita](/dbzero/vendite/views/vw_dash_competenza_attivita) — la base da cui deriva
>
> Approfondimento funzioni:
>
> * [vendite.fn_build_gruppo_fatturabile_key](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key) — la forma della chiave di gruppo
> * [vendite.fn_get_sorgente_documento_ref](/dbzero/vendite/funzioni/fn_get_sorgente_documento_ref) — **da qui** vengono `riferimento` e `documento_id`
> * [script.fn_sorgente_documento_da_chiave](/dbzero/script/funzioni/fn_sorgente_documento_da_chiave) — il ponte delle chiavi in testo, su cui quella è scritta
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — §5, le chiavi in testo

---

### 🎯 Scopo Principale

L'**elenco dei gruppi fatturabili** che alimenta la card «Da emettere» della
Lente Competenza. Prima di agire, l'operatore deve vedere cosa può fatturare,
raggruppato nelle unità su cui può decidere, con **quante righe** e **quanto
valore** ciascuna pesa.

```text
Card «Da emettere» (29 attività)
 ├─ PRV-0012              Rossi    5 righe   1.000 €   [Fattura]
 ├─ CTR-0007              Rossi    3 righe     500 €   [Fattura]
 ├─ ORD-0033              Bianchi  8 righe   2.300 €   [Fattura]
 └─ Oneri · commessa #42  Rossi    1 riga      500 €   [Fattura]
```

---

### Perché è *derivata* e non una query autonoma

Costruita su `vw_dash_competenza_attivita` per due ragioni che sarebbero
altrimenti da riscrivere e mantenere:

1. **Scope emittente gratis.** La base è `security_invoker=on` e filtra su
   `script.fn_get_emittenti_scope_sr_ids`: un operatore non può vedere né
   selezionare gruppi fuori dal suo perimetro. Non perché la regola sia ripetuta
   qui, ma perché è **la stessa sorgente**.
2. **Conteggi coerenti con la card per costruzione.** Il numero della card nasce
   dallo stesso `stadio` e dallo stesso `valore`. Una query parallela partirebbe
   identica e divergerebbe alla prima modifica di una delle due — è la lezione
   già pagata con le viste del riepilogo IVA.

---

### `stadio` è nel `GROUP BY`, non filtrato

La vista resta generale: è il **consumatore** a filtrare `DA_EMETTERE` per la
lista del cockpit.

Conseguenza: un gruppo parzialmente fatturato compare su **due righe**, una per
stadio. Non è un difetto — è l'informazione vera: dice all'operatore che di quel
documento una parte è già passata.

---

### ⭐ Il riferimento leggibile viene dal resolver di catalogo

`riferimento` e `documento_id` arrivano da
`vendite.fn_get_sorgente_documento_ref(sorgente_tipo_id, sorgente_uid)`, in
`LEFT JOIN LATERAL` **dopo** l'aggregazione — quindi l'etichetta non può toccare
`n_attivita` e `valore`, che devono coincidere con la card.

⚠️ `sorgente_uid` qui è l'**uid del documento in testo**, per ogni tipo, come
sta nella chiave del gruppo (lo porta la base): non è la colonna uuid della
provenienza. `fn_get_sorgente_documento_ref` lo passa al ponte delle chiavi in
testo, [`script.fn_sorgente_documento_da_chiave`](/dbzero/script/funzioni/fn_sorgente_documento_da_chiave),
che risolve col BB che risolve: legge **una** tabella, quella dichiarata da
`config.sorgenti.target_table`, e ne prende il numero da `label_selector`. Lo
stesso BB lo usa `fn_list_commessa_attivita`, la lente gemella, che lo chiama
direttamente con le colonne tipizzate della riga di commessa.

#### ⛔ Perché non si passa da `vw_dash_fatturazione_documenti`

Prima questa vista risolveva il documento attraverso quella —
cioè attraverso una `UNION ALL` dei **sei resolver** della fatturazione, che
ricalcolano valori, righe, transitato e motivo di fermo — per tenerne due
colonne. Due ragioni indipendenti, **nessuna delle due è la velocità**:

1. ⛔ **Il predicato non era indicizzabile sotto RLS, e non poteva diventarlo.**
   Il confronto era `(uid)::text = sorgente_uid`. Il cast `uuid → text` non ha
   una entry in `pg_cast`: è un `CoerceViaIO`, e `uuid_out`/`textin` non sono
   `leakproof`. Un quale *leaky* **non può essere valutato prima del security
   qual** della RLS, quindi non diventa mai un `Index Cond`.
   ⚠️ **Chi trovasse `ix_preventivi_uid_text` inutilizzato e pensasse di
   aggiungere lo stesso indice funzionale agli altri cinque rami costruirebbe
   cinque indici morti.** L'indice funziona solo dove la RLS non c'è, cioè da
   owner — mai sul percorso applicativo.
2. ⛔ **Il documento cadeva fuori quando il resolver lo escludeva.** I sei
   resolver hanno filtri loro — `WHERE p.is_attiva` sui preventivi,
   `caus.fatturabile IS TRUE` sui DDT — che sono giusti *per le lenti backlog e
   aperto*, ma non per una lookup. Un preventivo **superato da una revisione**
   ha `is_attiva = false`: il suo gruppo perdeva il nome del documento pur
   avendo attività ancora da fatturare.

⭐ **E sparisce il `LIMIT 1`.** Non era una scelta: `vw_dash_fatturazione_documenti`
non è unica per documento (il ramo commesse raggruppa per `competenza_mese`,
quindi una commessa emette una riga per mese), e quell'`ORDER BY … LIMIT 1` era
de-duplicazione forzata dalla sorgente sbagliata. Col resolver il documento è
unico **per costruzione**, e il presidio anti-fan-out non dipende più da un
«prendine una».

⚠️ `vw_dash_fatturazione_documenti` **resta** ed è intatta: è la sorgente di
`vw_dash_backlog_documenti` e `vw_dash_aperto_documenti`, che il motore intero
lo vogliono davvero. È cambiato solo chi la usava come tabella di lookup.

---

### ⚠️ Tutti i join sono `LEFT`, mai `INNER`

Un gruppo il cui documento non è risolvibile — un tipo che non ha una pagina
(`apribile` falso), gli oneri di commessa — deve **comunque comparire**. Sparire dall'elenco significherebbe
lavoro non azionabile: lo stesso difetto che il concetto di gruppo esiste per
evitare.

Il fallback del riferimento è a cascata: `numero del documento` → `codice della
commessa` → `chiave del gruppo`. Non si resta mai senza etichetta.

⚠️ **Ma il terzo anello è irraggiungibile per un gruppo documento**, e conviene
saperlo: `vendite.commesse.codice` è `NOT NULL` e
`vendite.commesse_attivita.commessa_id` pure, quindi il secondo anello c'è
sempre. Quando il documento non si risolve, a video esce il **codice commessa**.
⭐ È la forma **peggiore** del difetto, non la più lieve: una chiave grezza si
vede che è rotta, un codice commessa sembra un valore legittimo — e la riga
**nomina un oggetto diverso** da quello di cui parla. È lo stesso difetto che il
frontend ha già corretto sull'azione «Apri commessa», che *«portava a un oggetto
DIVERSO da quello scritto nella riga»*. Col resolver di catalogo il caso non si
produce per un documento che esiste.

---

### Colonne principali

| Colonna | Note |
| --- | --- |
| `gruppo_key` | **esattamente** la stringa che i filtri `p_gruppi` accettano: il FE passa ciò che legge |
| `tipo_gruppo` | `codice_interno` della sorgente, oppure `ONERI_COMMESSA`. È un **codice**, non un'etichetta: la traduzione a video la fa il frontend (i18n) |
| `documento_apribile` | `config.sorgenti.apribile` del tipo: vero se il documento ha una sua pagina, vuoto per i gruppi senza documento |
| `riferimento` | numero del documento (da `fn_get_sorgente_documento_ref`), o codice commessa. ⚠️ È colonna di **ricerca libera** e di **ordinamento** lato BE: non è solo un'etichetta |
| `n_attivita` · `valore` | il **peso** di ciò che si sta per fatturare, *prima* di agire |
| `ha_oneri` | difensivo: un gruppo dovrebbe essere interamente ONERE o interamente NORMALE |
| `stadio` | nel GROUP BY, vedi sopra |

---

### ⚠️ `security_invoker=on` va ri-specificato

La reloption **non compare** in `pg_get_viewdef` e PostgreSQL la **azzera** a
ogni `CREATE OR REPLACE` che non la ripete. Perderla trasformerebbe la vista in
`security_definer` di fatto, aprendo un buco nello scope emittente. Un pgTAP la
verifica (`test-vw-dash-competenza-gruppi-v1.sql`, caso 9).

---

### Display già decodificato: `commessa_stato_descrizione` e `documento_id`

Due colonne che tolgono al repository una **seconda risoluzione della
stessa cosa**, e nessuna delle due costa un JOIN nuovo.

| Colonna | Da dove viene | Perché in vista |
| --- | --- | --- |
| `commessa_stato_descrizione` | `stati_commessa`, `COALESCE(descrizione, codice)` | A video va la descrizione. Un codice interno dentro una frase — *«The job order is in state BOZZA»* — è il sintomo che la decodifica è finita lato client. Il JOIN la vista lo faceva già per `emittibile` e `codice_interno` |
| `documento_id` | la **stessa** LATERAL da cui esce `riferimento` (`fn_get_sorgente_documento_ref`) | I drawer di dominio si aprono per **id**, e la vista esponeva solo codice e uid |

⭐ **Il punto che rende `documento_id` non cosmetico.** Finché l'id lo risolveva
il repository con una LATERAL sua, `riferimento` (il codice, dalla vista) e
`documento_id` (l'id, dal repository) potevano in linea di principio descrivere
**due documenti diversi**, se un giorno l'`ORDER BY` fosse cambiato da una parte
sola. Ora arrivano dalla stessa riga per costruzione: non è più una convenzione
da mantenere a mano.

ℹ️ `documento_id` è `NULL` per i gruppi **sourceless** (oneri di commessa,
`documento_apribile` vuoto). È corretto: quei gruppi un documento non ce l'hanno, e
il frontend offre la sola commessa.

⚠️ **Il guard che lo tiene `NULL` è `apribile` nella `ON` del `LATERAL`, ed è
semantico, non difensivo.** Il resolver, chiamato su un tipo che non ha una
pagina (un consumo, `ATTIVITA_CONSUMI`), risponderebbe
con l'id della sua `target_table` — un valore **vero** dentro una colonna che
afferma *«l'id del documento sorgente»*. Non è un documento che il cruscotto
sappia aprire, e la colonna direbbe una cosa per un'altra.

⭐ **Quale revisione apre `documento_id`**: la **revisione spinta**, non la
corrente: l'uid nella chiave del gruppo è quello della revisione mandata in
commessa. È quella da cui vengono quantità e prezzi che si stanno per fatturare;
aprire la corrente mostrerebbe righe diverse da quelle che finiranno in fattura,
senza dirlo. ⚠️ Il numero a video **non distingue** le revisioni
(`label_selector = numero`, condiviso), quindi la scelta si vede solo nell'id — e
per questo è presidiata da un test dedicato.

ℹ️ `COALESCE` e non `descrizione` nuda: la colonna è nullable a catalogo, e un
campo di **display** vuoto si legge come «non lo so» invece che come «manca il
dato».

---

### Nota per chi scrive test

La vista base è **fail-closed senza GUC**:
`script.fn_get_emittenti_scope_sr_ids(NULL)` restituisce l'array **vuoto** (non
`NULL`), quindi senza `app.current_user_id` **nessuna riga passa**. Un test che
non imposta la sessione misurerebbe zero *per il motivo sbagliato*.

Le due colonne nuove sono presidiate dai casi 14-15 di
`test-vw-dash-competenza-v1.sql`.

⭐ **`riferimento` e `documento_id` hanno un file loro**:
`db/pgtap/vendite/test-vw-dash-competenza-gruppi-riferimento-sorgente-v1.sql`.
Si **fabbrica** il caso — preventivo spinto, poi revisionato — invece di
cercarlo: al 2026-09-01 le righe nel caso rotto sono **zero** su tutta la
popolazione di sviluppo, quindi un test che confrontasse i dati esistenti
sarebbe verde per sottrazione, e in CI (database ricostruito da zero)
passerebbe a vuoto sempre.

---

### Note di migrazione

* 2026-07-27 — nasce l'elenco dei gruppi fatturabili: prima la discovery lavorava a livello di terna
  del lotto (brief-db-emissione-fattura-per-documento-sorgente, parte A, A8).
* 2026-08-15 — arrivano `commessa_stato_descrizione` e `documento_id` (brief-db-emittibilita-visibile-e-sbloccabile §8.3, §9 F3).
* 2026-09-01 — il riferimento viene dal resolver di catalogo e non più da
  `vw_dash_fatturazione_documenti`; la revisione aperta è quella spinta (brief-db-riferimento-gruppi-lateral-costosa, D-1).
* 2026-10-20 — `area_documento` lascia il posto a `documento_apribile`, da `config.sorgenti.apribile`
  (brief-db-grammatica-unica-documenti).
* 2026-11-06 — il resolver passa dal ponte delle chiavi in testo del modello della provenienza; i
  tipi `*_RIGA` escono dal catalogo dei tipi (brief-db-sorgente-documento-e-riga).
* 2026-11-07 — la base porta l'uid del documento in testo dal `segment_key`; il tipo `ATTIVITA` esce
  dal catalogo dei tipi.

---

{% include-markdown "signature-core.md" %}
