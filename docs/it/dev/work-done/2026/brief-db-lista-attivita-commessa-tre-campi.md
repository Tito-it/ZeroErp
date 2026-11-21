# Lista attività di commessa — tre informazioni che si fermavano al database

> **Cos'è.** La sede DB della richiesta che il BE ha mandato il **2026-08-16**:
> la riga della lista attività di commessa deve portare a valle **quando** è
> stata portata in fattura, **quale** fattura, e **quale** documento di origine.
> Tutte e tre nascono da `vendite.fn_list_commessa_attivita`, quindi un
> intervento solo — come chiedeva la richiesta.
>
> 🟢 **CHIUSO — 2026-08-16.** Applicato e **validato in app da Tid**: nella
> commessa `CMM-20260803100729415-ee7090` si vedono la colonna «Fatturata il»,
> l'azione verso l'ordine di origine e quella verso la fattura.
>
> **Cinque changeSet, in due giri.** Primo: `20260816-03` (risoluzione della
> sorgente polimorfa) e `-04` (le sette colonne). Secondo, dopo i due rilievi
> del BE al §7: `-05` (`NULLS LAST`) più il seed della colonna a catalogo
> (`ui.lista_colonna` + `lista_preset_colonna`).
>
> 📌 **Documento unico dei due lati**, come da regola già pagata su questo
> progetto: qui cambiava il lato che lavorava, non il soggetto. Il §8 porta la
> parte BE/FE, il §7 i due rilievi che hanno generato il secondo giro.

---

## 1. Cosa esce dalla funzione adesso

Sette colonne nuove, la firma **invariata** (nessun overload: verificato che
resti una sola definizione).

| Colonna | Da dove | Nota |
| --- | --- | --- |
| `fatturata_il` | `vendite.fatture_righe.data_insert` | il momento in cui la riga è stata **portata** in fattura |
| `fattura_id`, `fattura_numero`, `fattura_stato` | `fatture_righe → fatture → stati_doc_fiscale` | su cosa navigare, e cosa dire all'operatore prima di aprirlo |
| `sorgente_uid` | `commesse_attivita.sorgente_uid` | c'era già in tabella, **non usciva** |
| `sorgente_area` | `config.sorgenti.area` | quello che il BB del frontend chiama «area» |
| `sorgente_documento_id` | `vendite.fn_get_sorgente_documento_id` | l'id numerico, risolto |

Ordinamento: la whitelist accetta due nomi nuovi, **`fatturata_il`** — che è la
domanda da cui nasce la richiesta, «fatturata ieri o tre mesi fa» — e
`fattura_numero`.

---

## 2. ⭐ «Fatturata il»: il dato vero esiste, e non è `data_update`

La richiesta metteva le mani avanti: *«se esiste il dato vero è quello che
vogliamo, altrimenti prendiamo l'approssimazione e l'etichetta lo dirà»*.

**Esiste**: `vendite.fatture_righe.data_insert`, la nascita della riga di
fattura. È un fatto che nessuna modifica successiva all'attività può spostare.

✅ **E la differenza è già visibile.** Sulle 37 righe di commessa già fatturate,
**10 hanno `ca.data_update` diverso da `fr.data_insert`**. Oggi lo scarto è di
**0,4 secondi** — stesso giro di fatturazione, statement diversi — quindi
nessuno se ne accorgerebbe; ma è la prova che le due colonne non sono la stessa
cosa. Basta un riallineamento di prezzo dopo la fatturazione e `data_update`
diventa quella data, mentre l'etichetta continuerebbe a dire «fatturata il».

---

## 3. 🔴 Il documento di origine: **nessuna** riga ha un id numerico

La richiesta diceva: *«l'area è derivabile da `config.sorgenti.area`, l'id no —
la riga porta solo `sorgente_uid`»*. La misura dice che è peggio, e in un modo
che cambia la soluzione.

```text
vendite.commesse_attivita, 2026-08-16

  88 righe con sorgente   →   88 hanno un UUID in `sorgente_uid`
  di cui: 44 PREVENTIVO (key_selector = uid)   ← atteso
          43 ORDINE_VENDITA + 1 DDT (key_selector = id)   ← NON atteso
```

La normalizzazione a `id::text` che fa `fn_link_commessa_sorgente` vale per la
tabella dei **legami** (`commesse_sorgenti`), non per questa colonna: qui il
documento è identificato dal suo uid, sempre.

⚠️ **Ne discende che la traduzione via tabella di destinazione non è il ramo
raro: è l'unico ramo che il dato percorre.** La prima stesura di
`fn_get_sorgente_documento_id` trattava «id numerico» come caso principale e
sarebbe tornata `NULL` su tutte e 88 le righe — cioè un'azione «apri documento»
che non si accende mai, **senza nessun errore**. L'ha scoperta il dry-run, non
il ragionamento.

### Perché una funzione e non una join

La tabella di destinazione cambia con la sorgente (`config.sorgenti.target_table`,
un `regclass`): in una query set-based servirebbe un `LEFT JOIN` per ogni dominio
possibile — quindici, di cui tre usati — e ognuno diventerebbe una riga da
mantenere quando nasce un dominio nuovo. La funzione legge la destinazione dal
catalogo, come fa già `fn_link_commessa_sorgente`.

⚠️ **E non solleva**, al contrario di quella: lì un legame irrisolvibile è un
errore perché si sta **scrivendo**; qui si sta rispondendo a una **lista**, e una
sorgente non risolta deve solo far sparire l'azione — come per le voci manuali,
che un documento a monte non ce l'hanno. *Fail-closed dove si scrive, silenzioso
ma visibile dove si guarda.*

✅ Verificato dopo la correzione: **88 su 88** risolvono.

---

## 4. ⚠️ Due scelte che non si vedono dal risultato

**1. Il booleano `fatturata` NON deriva dalla join.** Resta l'`EXISTS` su
`vendite.attivita_fatturabili`, che **non ha RLS**, mentre `vendite.fatture` e
`fatture_righe` ce l'hanno. Derivarlo dalla join lo renderebbe **falso** per chi
non vede la fattura: una riga fatturata si presenterebbe come da fatturare.

Così invece chi non vede la fattura legge `fatturata = true` con le colonne del
documento a `NULL`: **sa che è fatturata e sa di non poterci navigare**. Il flag
resta dov'era, il link no.

**2. Il legame con la fattura si prende con un `LATERAL` ordinato + `LIMIT 1`.**
Oggi il rapporto attività → riga di fattura è 1:1 (misurato: nessuna riga con più
di una `attivita_fatturabili`), ma *«oggi è 1:1»* è una fotografia, non un
vincolo. Con una join nuda, il giorno di una fatturazione parziale la lista
**raddoppierebbe le righe** — un difetto che si manifesta come dati sbagliati e
non come errore.

---

## 5. Verificato

In transazione annullata, sulla commessa che ha righe già fatturate:

```text
FIRME: 1                          ← nessun overload, la firma è identica
fatturata=true  il=2026-06-20 00:31:09  fattura=210/1/DEFINITIVA
sorgente=ORDINE_VENDITA  area=ORDINI  doc_id=100
RISOLTI: 88 su 88 righe con sorgente
ORDER BY fatturata_il: ammesso
```

---

## 6. 📮 Per il BE

* la firma **non cambia**: le chiamate esistenti continuano a funzionare, le
  sette colonne sono additive;
* `sorgente_documento_id` è `NULL` quando la sorgente non si risolve **o quando
  il documento non è visibile a chi chiede** (RLS): in entrambi i casi l'azione
  «apri» va nascosta, che è il comportamento già previsto per le voci manuali;
* se al frontend serve anche l'`uid` — per esempio per una rotta che usa la
  chiave nativa — c'è: esce grezzo in `sorgente_uid`.

---

## 7. Il secondo giro — due cose che il dato giusto non bastava a dare

Collegando il backend è emerso che le sette colonne erano corrette **e
comunque invisibili all'operatore**. Due difetti diversi, entrambi fuori dal
perimetro del §1 e nessuno dei due visibile guardando il risultato della
funzione.

### 7.1 La colonna non era a catalogo — il dato c'era, a video no

La lista attività è **catalogo-driven**: `<ListaConfigurabile>` disegna le
colonne dichiarate in `ui.lista_colonna`, e per la lista 38 erano otto, senza
`fatturata_il`. La colonna usciva quindi dall'API a ogni chiamata e non
compariva da nessuna parte.

⚠️ **È il caso peggiore da diagnosticare**: nessun errore, nessuna colonna
vuota — semplicemente una colonna che non esiste. Chi avesse controllato la
risposta dell'endpoint l'avrebbe trovata al suo posto e avrebbe concluso che
funzionava.

✅ Chiuso con il seed (`ui.lista_colonna` id 475 + `lista_preset_colonna`):
ottava posizione, formato `datetime_short`, e una descrizione che mette in
chiaro il merito — *«la nascita della riga di fattura, non l'ultimo
aggiornamento»*.

### 7.2 `ORDER BY fatturata_il` metteva in cima le righe mai fatturate

`NULLS FIRST` è il default di PostgreSQL sul `DESC`, quindi ordinando per data
decrescente arrivavano prima tutte le righe **senza** data. Misurato sulla
commessa di prova:

```text
prima:   desc → 7304 None · 7305 None · 7306 None · 7307 2026-08-16
adesso:  desc → 7307 2026-08-16 · 7304 None · 7305 None · 7306 None
```

Su quattro righe si nota appena; su una commessa con cento righe di cui dieci
fatturate, le dieci che interessano finiscono in fondo e l'ordinamento diventa
inservibile — proprio sulla domanda da cui è nata la colonna, «fatturata ieri o
tre mesi fa».

✅ Chiuso con `20260816-05` (`NULLS LAST`).

⭐ **La lezione delle due**: una colonna nuova non è finita quando il dato è
giusto. Deve anche **arrivare a chi guarda** e **ordinare nel verso in cui la
domanda è posta**. Nessuno dei due difetti si vedeva dal risultato della
funzione, ed entrambi sono emersi solo collegando il consumatore.

---

## 8. Lato BE/FE (2026-08-16)

**Backend.** Le sette colonne passano dalla lista (`_ATTIVITA_COLS` in
`commesse_repository`), `fatturata_il` serializzata come le altre date, e
`fatturata_il`/`fattura_numero` aggiunte alla whitelist di ordinamento —
specchio di quella chiusa dentro la funzione.

⚠️ **Provato contro il database vero, non solo coi mock**: il test a mock aveva
la tupla della vecchia forma e falliva con `IndexError`, che è il modo giusto
di accorgersene; ma un nome di colonna sbagliato i mock non l'avrebbero visto.
La chiamata reale su `CMM-20260803100729415-ee7090` restituisce
`fatturata_il = 2026-08-16T15:39:49` — l'istante esatto del giro di
fatturazione — `fattura_id` 9691, `fattura_numero` NULL perché non ancora
numerata, e i due ordini di origine (5387 per le tre righe non emesse, 5388 per
quella emessa).

**Frontend.** Due voci di navigazione nel kebab di riga: «Apri documento di
origine» (stesso BB dei cruscotti, tipo di drawer derivato da `sorgente_area`)
e «Apri la fattura», con il numero nell'etichetta quando c'è.

Tre scelte che non si leggono dal codice:

* le due azioni valgono **anche in sola lettura** e su riga già fatturata:
  guardare un documento non è un'azione di governo, e nasconderle in readonly
  toglieva la strada al documento proprio a chi sta ispezionando;
* l'apertura della fattura è condizionata a `fattura_id`, **non** al flag
  `fatturata` — che come dice il §4 resta `true` anche per chi la fattura non
  la vede. Proporre un'apertura che non può funzionare è peggio che non
  proporla;
* la colonna «Fatturata il» **non ha uno slot**: `datetime_short` è già gestito
  dal formatter di serie e i valori nulli rendono stringa vuota. Aggiunte le
  sole chiavi i18n (it/en), altrimenti in inglese sarebbe rimasta l'etichetta
  italiana del catalogo.

**Validazione in app (Tid, 2026-08-16)**: colonna, filtro di stato e le due
azioni funzionano sulla commessa reale.

---

## 9. Registro

| Data | Cosa |
| --- | --- |
| 2026-08-16 (2° giro) | ⭐ **Chiuso**, con `-05` e il seed di catalogo dopo i due rilievi del BE (§7): il dato c'era ma **non si vedeva** (colonna non a catalogo) e **non si ordinava utilmente** (`NULLS FIRST` metteva in cima le righe mai fatturate). Poi BE/FE collegati e **validato in app da Tid** (§8) |
| 2026-08-16 | ⭐ **Scritti i due changeSet** (`-03` la risoluzione della sorgente polimorfa, `-04` la lista). **«Fatturata il» ha un dato vero** — `fatture_righe.data_insert` — e non è `data_update`: 10 righe su 37 già divergono. 🔴 **La misura ha smentito l'ipotesi sul documento di origine**: non «metà delle righe non ha un id» ma **nessuna** — 88 su 88 hanno un UUID, ordini e DDT compresi, perché la normalizzazione a `id::text` vale per `commesse_sorgenti` e non per `commesse_attivita`. La prima stesura sarebbe tornata NULL su tutto senza dare errore. ⚠️ Due scelte non visibili dal risultato: `fatturata` resta calcolato sulla tabella **senza RLS** (altrimenti chi non vede la fattura leggerebbe «da fatturare» una riga fatturata) e il legame passa da un `LATERAL` ordinato, perché l'1:1 di oggi è una fotografia |
