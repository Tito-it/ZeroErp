## 📘 Documentazione Concettuale – Tabella `catalogo.articoli`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — l'unità principale dell'articolo
> * [catalogo.articoli_uom_operativa](/dbzero/catalogo/tabelle/articoli_uom_operativa) — le unità in cui l'articolo si muove, con la riga base che nasce qui
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — la distinta di un articolo composito
> * [config.nature_vendita](/dbzero/config/tabelle/nature_vendita) — dove va la riga venduta
> * [config.causali_onere](/dbzero/config/tabelle/causali_onere) — la causale che fa di un articolo un onere
> * [config.modi_approvvigionamento](/dbzero/config/tabelle/modi_approvvigionamento) — da dove arriva la merce
> * [dbops.lock_columns_conditional](/dbzero/dbops/tabelle/lock_columns_conditional) — le regole che spengono i campi nel form
>
> Approfondimento viste:
>
> * [catalogo.vw_articoli_dettaglio](/dbzero/catalogo/views/vw_articoli_dettaglio) — l'articolo con le decodifiche, per la lista e il drawer
>
> Approfondimento funzioni:
>
> * [catalogo.fn_articolo_usato](/dbzero/catalogo/funzioni/fn_articolo_usato) — il predicato «l'articolo è usato»
> * [catalogo.trgfn_articoli_guard_struttura_se_usato](/dbzero/catalogo/funzioni/trgfn_articoli_guard_struttura_se_usato) — un articolo usato non cambia struttura
> * [catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva](/dbzero/catalogo/funzioni/trgfn_articoli_guard_flags_struttura_bom_attiva) — i flag di struttura e la distinta
> * [catalogo.trgfn_articoli_guard_iva_bom_attiva](/dbzero/catalogo/funzioni/trgfn_articoli_guard_iva_bom_attiva) — l'IVA uguale fra kit e componenti
> * [catalogo.trgfn_articoli_guard_onere_natura](/dbzero/catalogo/funzioni/trgfn_articoli_guard_onere_natura) — un onere non è merce né un bene
> * [catalogo.trgfn_articoli_seed_uom_base](/dbzero/catalogo/funzioni/trgfn_articoli_seed_uom_base) — la riga base dell'unità operativa
> * [catalogo.fn_articolo_correggi_struttura](/dbzero/catalogo/funzioni/fn_articolo_correggi_struttura) — la porta amministratore per un errore di caricamento
> * [vendite.fn_resolve_iva_riga](/dbzero/vendite/funzioni/fn_resolve_iva_riga) — il risolutore IVA, che chiede prima all'articolo
>
> Guide:
>
> * [Uso di obsoleto](/guide/uso-di-obsoleto) — ritirare un articolo senza cancellarlo

---

### 🎯 Scopo Principale

Anagrafica unica di articoli, servizi e oneri, comune a tutte le aziende. Ogni riga di
documento, listino, commessa e movimento di magazzino punta a un articolo di questa tabella.

L'articolo dice come si vende (natura di vendita, IVA, tipologia di listino), come sta a
magazzino (gestito o no, a lotti, a matricola), se è un kit (`is_composito`) o solo un pezzo
di un kit (`is_solo_componente`), e se è un onere. Il catalogo non ha RLS: un articolo è lo
stesso per tutte le aziende, i documenti che lo usano no.

---

### ⭐ Il codice e l'unità principale non cambiano

* `codice` è univoco (`uq_articoli_codice`) ed è scritto sempre in maiuscolo da
  `script.trgfn_codice_maiuscolo`, all'inserimento e a ogni modifica.
* `codice` e `uom_id` non si cambiano dopo la creazione. Il lock lo genera l'automazione dal
  registro `dbops.automation_lock_columns`, con `script.trgfn_lock_columns`; il nome del trigger
  lo decide il template, e chi lo verifica lo cerca per funzione e argomenti.
* Una manutenzione può aprire il lock nella sola transazione con la GUC
  `zeroerp.allow_lock_columns_override`.
* Per cambiare l'unità principale si crea un articolo nuovo: il vecchio resta com'è, insieme ai
  documenti che lo usano.

---

### La riga base dell'unità operativa nasce con l'articolo

Dopo l'inserimento di un articolo, `catalogo.trgfn_articoli_seed_uom_base` scrive in
`catalogo.articoli_uom_operativa` la riga base: l'unità principale dell'articolo, con fattore
uno. Così l'unità principale è subito usabile nei documenti, senza un secondo passo. Se la coppia
articolo-unità esiste già, la scrittura non fa niente.

---

### Le relazioni

* Quasi tutte le FK sono `ON UPDATE CASCADE` e senza azione alla cancellazione. Fanno eccezione
  `uom_id` e `causale_onere_id`, senza `CASCADE`.
* La nota dell'articolo è la coppia `note_target_tipo`, `note_id`, che punta a `catalogo.note`.
  `note_target_tipo` vale `ARTICOLO` o è vuoto. Se la nota si cancella, la coppia si svuota.
* I vocabolari puntati devono essere attivi: unità, IVA, natura, causale, tipologia di
  listino, modo di approvvigionamento, tipologia, gruppo e spesa (i conti contabili no). Il
  controllo è un trigger differito, quindi l'errore arriva al COMMIT.

---

### ⛔ `iva_id` vuota vuol dire «l'articolo non ha un'opinione sull'IVA»

L'articolo è il primo gradino del risolutore IVA (`vendite.fn_resolve_iva_riga`). Se
l'articolo ha un'aliquota, è quella che compete alla merce, e l'uso della fornitura non la
scavalca; un titolo IVA del cliente la può sostituire sulla riga. Se `iva_id` è vuota, il
risolutore passa al gradino dopo, il tipo d'uso della fornitura.

Per questo la colonna è nullabile e deve restarlo. Renderla obbligatoria «per igiene»
spegnerebbe il secondo gradino.

---

### La natura di vendita dice dove va la riga venduta

`natura_vendita_id` è obbligatoria, e un articolo creato senza dirla nasce merce. La
destinazione della natura instrada la riga dopo l'accettazione: `ORDINE_VENDITA` per la merce,
`COMMESSA` per il servizio una tantum, `CONTRATTO` per il servizio ricorrente. La natura è
copiata sulla riga del documento quando la riga nasce: cambiarla qui non tocca le righe
esistenti.

---

### La tipologia di listino

Un articolo senza `listino_tipologia_id` non entra in un listino tipizzato
(`E_ARTICOLO_TIPOLOGIA_MANCANTE`), e un articolo di un'altra tipologia nemmeno
(`E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE`). Lo decide la check delle righe di listino, non questa
tabella.

---

### Matricola e lotto sono due domande diverse

* `requires_serial`: ogni pezzo ha una matricola, una riga per pezzo in `magazzino.assets`.
* `requires_lotto`: ogni carico appartiene a una partita di `magazzino.lotti`, con data d'arrivo
  e scadenza.

Un articolo può volere l'una, l'altra, tutte e due o nessuna. La primitiva di scrittura del
magazzino le fa rispettare: un movimento senza il lotto o la matricola che l'articolo pretende
è rifiutato (`E_MAG_LOTTO_OBBLIGATORIO`, `E_MAG_LOTTO_NON_AMMESSO`).

I due flag non sono simmetrici. `requires_serial` è anche un flag di struttura della distinta:
non cambia su un articolo padre di una distinta in vigore. `requires_lotto` non entra nella
distinta. Tutti e due, però, non cambiano più quando l'articolo è usato (sezione sotto), e il
form li spegne con la stessa regola.

---

### Da dove arriva l'articolo: tre domande separate

* `modo_approvvigionamento_id`: acquisto, produzione, stock o non applicabile. Obbligatorio;
  un articolo nuovo nasce «acquisto».
* `gestito_a_magazzino`: l'articolo movimenta giacenza. Obbligatorio; un articolo nuovo nasce
  «non a magazzino». È la prima cosa che la primitiva di magazzino guarda
  (`E_MAG_ARTICOLO_NON_GESTITO`).
* `lead_time_giorni`: i giorni fra «lo chiedo» e «ce l'ho». Può restare vuoto, perché per una
  prestazione non significa niente, e `0` non vuol dire «non si applica». Non è mai negativo.

⭐ Sono tre domande perché le risposte non si deducono l'una dall'altra: una merce acquistata
può arrivare direttamente dal fornitore, senza passare dal magazzino, e la natura di vendita
dice dove va la riga venduta, non da dove arriva.

⚠️ Il default prudente ha un costo: finché nessuno marca la merce, il magazzino si comporta come
se non ci fosse merce, senza errori. La spia `dbops.vw_articoli_a_magazzino_prontezza` dice se
almeno un articolo attivo è marcato.

---

### 🔒 Un articolo usato non cambia la sua struttura

Un articolo usato non cambia più le otto colonne che decidono come si vende e come sta a
magazzino: `is_composito`, `is_solo_componente`, `natura_vendita_id`, `causale_onere_id`,
`listino_tipologia_id`, `gestito_a_magazzino`, `requires_lotto`, `requires_serial`. A valle ci
sono listini, ordini, bolle e giacenze costruiti su quelle caratteristiche, e non le rincorrono.

* **Usato** vuol dire che l'articolo compare in una tabella che lo punta con una FK, in
  qualunque stato, anche chiusa o annullata (`catalogo.fn_articolo_usato`). Non contano le
  tabelle che sono anagrafica dell'articolo: distinta, unità operative, descrizioni, note,
  regole di fatturazione, ambiti IVA.
* L'uso conta in tutte le aziende, anche in un documento che chi modifica non vede. Il messaggio
  non dice dove.
* Lo fa rispettare `catalogo.trgfn_articoli_guard_struttura_se_usato`
  (`E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE`). Nel form le regole gemelle di
  `dbops.lock_columns_conditional` spengono il campo con lo stesso predicato.
* La via d'uscita è un articolo nuovo. Un errore di caricamento lo corregge il SUPER_ADMIN con
  `catalogo.fn_articolo_correggi_struttura`.

Descrizioni, gruppi, conti, tempi di consegna e modo di approvvigionamento restano liberi.
Anche `iva_id` resta fuori da questa regola, ma su un articolo che sta in una distinta la blocca
il guard dell'IVA (sezione sotto).

---

### Le regole della distinta sull'articolo

Valgono anche per un articolo non ancora usato.

* `catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva`: `is_composito`,
  `requires_serial` e `is_solo_componente` non cambiano mentre l'articolo è padre o componente
  di una distinta in vigore, e un componente non diventa composito (la distinta ha un livello).
* `catalogo.trgfn_articoli_guard_iva_bom_attiva`: un kit e i suoi componenti hanno la stessa
  IVA.
* `catalogo.trgfn_articoli_guard_listino_se_composito`: un articolo con righe di listino attive
  non diventa composito.

---

### Un articolo è un onere quando ha una causale

Un articolo con `causale_onere_id` è un onere: trasferta, urgenza, spese, penale. Il legame con
la causale è uno a uno (`uq_articoli_causale_onere`). Così ogni onere porta la sua IVA, quella
dell'articolo, e la causale ne è la classificazione. La porta oneri della commessa
(`vendite.fn_aggiungi_onere_commessa`) riceve l'articolo-onere e ne prende causale, unità e
IVA.

Un onere è un addebito, non un bene (`catalogo.trgfn_articoli_guard_onere_natura`): la sua
natura non ha destinazione `ORDINE_VENDITA`, e non è gestito a magazzino, composito, a lotti o
a matricola.

---

### Ritirare un articolo senza cancellarlo: `obsoleto_dal`

Un articolo usato non si cancella e non si spegne: `attivo` vuol dire «riferimento valido», e i
trigger generati `block_deact` impediscono di spegnerlo finché qualcuno lo usa. Per dire «non si
sceglie più per il nuovo» c'è `obsoleto_dal`:

* vuota: si sceglie;
* data passata o di oggi: ritirato;
* data futura: ritiro programmato.

Il confronto è alla data operativa, con `script.fn_e_obsoleto`.

* Una **riga nuova** su un articolo ritirato è respinta (`E_ARTICOLO_OBSOLETO`). È il primo
  motivo della check delle righe, che legge anche il picker `catalogo.fn_articoli_ammessi`.
* Una **riga derivata** da un'altra passa. Una **riga esistente** si modifica; solo il cambio di
  articolo è una scelta nuova.
* Il **magazzino** non è mai bloccato. La **copia di un listino** salta l'articolo ritirato.

La regola completa, coi casi, è nella guida dell'obsoleto.

---

### Disattivare e riattivare

Spegnere un articolo (`attivo = false`) è un UPDATE diretto. I trigger `block_deact` lo
rifiutano finché una tabella figlia ha righe attive che lo puntano. Riaccenderlo è il verbo
`catalogo.fn_riattiva_articolo`, che non riaccende i figli.

---

### ⚠️ Che cosa oggi non copre

* **Un articolo creato non attivo non si salva.** La riga base dell'unità operativa nasce
  sempre attiva, e le unità operative pretendono un articolo attivo. Il controllo è differito:
  l'inserimento di un articolo con `attivo = false` fallisce al COMMIT con
  `E_ATTIVO_PADRE_NON_ATTIVO`.
* **La riga base dell'unità operativa non è protetta.** Nessun vincolo impone fattore 1 sulla
  riga base, né impedisce di cambiarne l'unità o di cancellarla.
* **Un articolo può essere composito e solo componente insieme.** Nessun vincolo lo esclude, e
  un articolo così non fa da padre né da componente.
* **Una nota impedisce di spegnere l'articolo.** La partizione delle note di articolo non ha
  `attivo`, quindi per il trigger `block_deact` ogni nota è un figlio vivo
  (`E_ATTIVO_BLOCK_CHILDREN_EXIST`).
* **L'IVA di un kit non si cambia più**, se il kit ha legami attivi: vedi
  `catalogo.trgfn_articoli_guard_iva_bom_attiva`.

---

### Codici errore

* `E_CODICE_NON_MODIFICABILE`: UPDATE di `codice` o di `uom_id`. Lo stesso codice vale per
  tutte e due le colonne.
* `E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE`: una delle otto colonne strutturali cambia su un
  articolo usato.
* `E_BOM_MODIFICA_VIETATA`, `E_BOM_COMPONENTE_DIVENTA_COMPOSITO`: i flag di struttura contro la
  distinta.
* `E_BOM_IVA_DISCORDANTE`: l'IVA del kit e quella di un componente divergono.
* `E_LISTINO_RIGA_COMPOSITO_VIETATO`: un articolo con righe di listino attive diventa
  composito.
* `E_ARTICOLO_ONERE_NATURA_MERCE`, `E_ARTICOLO_ONERE_STRUTTURA`: un onere con natura di merce o
  con una caratteristica da bene.
* `E_ATTIVO_PADRE_NON_ATTIVO`: un vocabolario puntato è spento (al COMMIT).
* `E_ATTIVO_BLOCK_CHILDREN_ACTIVE`, `E_ATTIVO_BLOCK_CHILDREN_EXIST`: l'articolo si spegne mentre
  una tabella figlia lo usa.

---

### Test

* `db/pgtap/catalogo/test-articoli-seed-uom-base-lock.sql` — la riga base nasce, è una sola, e
  il lock su `codice` e `uom_id` c'è (cercato per funzione e argomenti) e si apre solo con la
  GUC di manutenzione.
* `db/pgtap/catalogo/test-articoli-approvvigionamento-v1.sql` — i default delle tre colonne di
  approvvigionamento, il `lead_time_giorni` negativo rifiutato e lo zero ammesso, il modo spento
  rifiutato.
* `db/pgtap/catalogo/test-articoli-natura-vendita-notnull-default-v1.sql` — un articolo senza
  natura nasce merce.
* `db/pgtap/catalogo/test-articolo-usato-struttura-v1.sql` — un articolo usato non cambia
  struttura, anche se l'uso è di un'altra azienda; `iva_id` e descrizione restano libere.
* `db/pgtap/catalogo/test-articolo-onere-struttura-v1.sql` — un onere non nasce né diventa un
  bene.
* `db/pgtap/vendite/test-articolo-ritirato-v1.sql` — l'articolo ritirato sulla riga nuova, sulla
  copia di listino e sugli oneri.

---

### Note di migrazione

* 2026-04-07 — `uom_id` diventa obbligatoria, e nasce la riga base automatica dell'unità
  operativa (senza recupero sugli articoli che c'erano già).
* 2026-04-14 — nasce `listino_tipologia_id`; gli articoli non utility di allora sono stati
  mappati a `PRODOTTI`.
* 2026-09-13 — nascono `modo_approvvigionamento_id`, `gestito_a_magazzino` e `lead_time_giorni`
  (brief-db-modifiche-certe-ciclo-vendita-e-articolo).
* 2026-09-14 — nasce `requires_lotto`.
* 2026-09-23 — i due trigger di lock scritti a mano su `codice` e `uom_id` sono sostituiti da
  quello generato dall'automazione (brief-db-codici-ritirati-negli-argomenti-dei-trigger).
* 2026-10-13 — un articolo usato non cambia struttura, e un onere non è merce
  (brief-db-articoli-ammessi-per-documento).
* 2026-10-19 — la destinazione della merce si chiama `ORDINE_VENDITA` (prima `ORDINE`).
* 2026-10-25 — `note_target_tipo` vale `ARTICOLO` (prima `ARTICOLI`).
* 2026-11-03 — un onere non è nemmeno un bene (brief-db-addebito-trasporto-ordine).
* 2026-11-05 — nasce `obsoleto_dal` (brief-db-articoli-obsoleto-dal).

---

{% include-markdown "signature-core.md" %}
