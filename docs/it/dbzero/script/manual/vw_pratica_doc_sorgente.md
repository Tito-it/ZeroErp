## 📘 Documentazione Concettuale – Vista `script.vw_pratica_doc_sorgente`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche_sorgenti](/dbzero/pratiche/tabelle/pratiche_sorgenti) — i collegamenti fra cui sceglie
>
> Approfondimento viste:
>
> * [script.vw_stato_sorgente](/dbzero/script/views/vw_stato_sorgente) — il descrittore dello stato di ogni documento
> * [script.vw_flusso_doc_sorgente](/dbzero/script/views/vw_flusso_doc_sorgente) — la gemella, una riga per milestone
>
> Approfondimento funzioni:
>
> * [pratiche.fn_stato_sorgente](/dbzero/pratiche/funzioni/fn_stato_sorgente) — lo stesso descrittore per un documento solo, con la sentinella
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza: tipo, documento, riga

---

### 🎯 Scopo Principale

Per ogni pratica, il documento che ne rappresenta lo stato vivo, con il suo descrittore normalizzato:
una riga per pratica, il documento **più vivo** fra tutti i suoi collegamenti (`ROOT` e `COLLEGATO`)
in `pratiche.pratiche_sorgenti`, con fase, esito e flag terminale letti da `script.vw_stato_sorgente`.

È la sede unica della regola d'ancora a livello di pratica (dettaglio e lista), e la legge il
backend. Il percorso e la coda di lavoro, che ragionano per milestone, leggono la gemella
`script.vw_flusso_doc_sorgente`.

---

### La regola d'ancora

Fra i collegamenti della pratica vince il primo in quest'ordine:

1. il documento **risolto** batte quello non risolto;
2. il documento **vivo** (non terminale) batte quello terminale;
3. il collegamento **`ROOT`** batte il `COLLEGATO`;
4. il collegamento **più recente** batte il più vecchio.

Perché non basta «il vivo prima»:

* una pratica evoluta da preventivo a ordine ha spesso il preventivo `ROOT` già terminale (evaso):
  con la sola ancora `ROOT` non si vedrebbe mai l'ordine `COLLEGATO` vivo. Il secondo criterio fa
  vincere l'ordine;
* una pratica evoluta da preventivo a commessa ha la commessa `COLLEGATO` **non risolta** (la
  commessa non ha un resolver di stato): il suo flag terminale è vuoto, e in un ordinamento
  decrescente i vuoti vengono per primi. Senza il primo criterio, e senza trattare il vuoto come
  «falso», vincerebbe la commessa e la pratica perderebbe il suo stato.

---

### Che cosa espone

* **La pratica**: `pratica_id`.
* **Il collegamento scelto**: il tipo, la chiave del documento nelle colonne del modello
  (`sorgente_id` oppure `sorgente_uid`, una sola, quella del `key_selector` del tipo), il ruolo e la
  descrizione del tipo.
* **Il descrittore**: `risolto`, e fase, esito, terminale e stato del documento.

Il ripiego è quello che il backend si aspetta, non la sentinella `UNKNOWN` di
`pratiche.fn_stato_sorgente`: se il collegamento scelto non è risolto, `risolto` è falso e i campi di
stato sono vuoti. Una pratica **senza collegamenti** non ha righe: chi legge la vista in join esterno
da `pratiche.pratiche` ottiene vuoto.

---

### ⭐ Come si trova il documento

Il documento di ogni collegamento si cerca nella vista dello stato sulle **chiavi native**, un ramo
per chiave: l'uid del collegamento su `sorgente_chiave_uuid`, l'id su `sorgente_chiave_id`. La
ricerca sta dentro una `LATERAL`.

⚠️ Né l'una né l'altra cosa sono di stile. Dentro la `LATERAL` la chiave del collegamento arriva come
valore esterno, e sotto RLS il database può usare l'indice di ogni ramo della union (i confronti fra
uuid e fra interi sono `leakproof`); scritta come join allo stesso livello, o con un OR sulle due
chiavi in un ramo solo, la ricerca tornerebbe a leggere tutti i documenti di tutti i tipi.

---

### 🔴 La vista gira con il perimetro di chi legge

La vista è `security_invoker`. Senza, girerebbe come il proprietario, che possiede anche le tabelle
dei documenti e, senza `FORCE ROW LEVEL SECURITY`, è esente dalla RLS: lo scope dell'emittente non
si applicherebbe.

⚠️ **Gli anelli sotto non bastano.** `script.vw_stato_sorgente` e le `vendite.vw_stato_sorgente_*`
hanno tutte il flag, ma `security_invoker` **non si propaga**: da dentro una vista che gira come il
proprietario, il «chiamante» che gli anelli interni onorano è il proprietario della vista esterna.
Basta un anello spento per spegnere la catena.

Che cosa vuol dire per chi legge:

* le colonne che vengono da `pratiche_sorgenti` e da `config.sorgenti` non dipendono dal perimetro;
* `risolto`, il flag terminale e i campi di stato sono vuoti quando il documento è **fuori dal
  perimetro di chi legge**;
* ⭐ **e può cambiare il collegamento scelto**: la regola d'ancora ordina proprio su `risolto` e
  terminale, e su una pratica con più documenti può vincerne un altro. È corretto (non si sceglie
  un'ancora guardando dati che non si possono vedere), ma è un cambio di scelta, non solo un
  nascondimento.

⚠️ Su dati coerenti non si vede niente: `pratiche.pratiche` ha la stessa regola di perimetro delle
tabelle dei documenti. ⛔ Ma il modello ammette la divergenza: il guard della provenienza verifica che
il documento esista e sia visibile **a chi scrive** il collegamento, e niente confronta l'emittente
del documento con quello della pratica. Una pratica di un emittente può citare il documento di un
altro, ed è il caso per cui il flag esiste.

---

### Test

* `db/pgtap/pratiche/test-proiezione-stato-sorgente.sql` — la regola d'ancora: il documento solo, il
  `COLLEGATO` vivo che batte il `ROOT` terminale, il `ROOT` risolto che batte la commessa non
  risolta, il solo collegamento non risolto.
* `db/pgtap/pratiche/test-sorgente-pratiche-sorgenti-v1.sql` — il documento più vivo, con la chiave
  nelle colonne del modello.
* `db/pgtap/vendite/test-vw-stato-sorgente-ddt-reso-v1.sql` — un collegamento a chiave id.
* `db/pgtap/rls/test-rls-viste-security-invoker.sql` — ogni vista che tocca dati protetti, anche
  attraverso altre viste, ha il flag.

---

### Note di migrazione

* 2026-07-02 — nasce, portando nel database la regola d'ancora che viveva nel repository Python delle
  pratiche (`brief-db-proiezione-stato-dominio`).
* 2026-09-07 — prende `security_invoker`, che fino ad allora mancava: lo scope dell'emittente non si
  applicava (`brief-db-viste-security-invoker-criterio`).
* 2026-10-05 — il documento si cerca sulle chiavi native della vista dello stato, non più sulla
  chiave in testo.
* 2026-11-08 — il collegamento scelto espone la chiave nelle colonne del modello (`sorgente_id`,
  `sorgente_uid` uuid), e la ricerca va per ramo di chiave (`brief-db-sorgente-documento-e-riga`).

---
{% include-markdown "signature-core.md" %}
