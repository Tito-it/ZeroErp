## 📘 Documentazione Concettuale – Tabella `anagrafiche.contatti`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — il titolare di ogni contatto, che punta al suo predefinito
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo del soggetto, quando è il contesto del contatto
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza del soggetto, quando è il contesto del contatto
> * [config.tipi_contatti](/dbzero/config/tabelle/tipi_contatti) — la categoria del contatto
> * [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative) — il reparto del referente
> * [config.titoli_cortesia](/dbzero/config/tabelle/titoli_cortesia) — l'appellativo del nominativo
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_contatto](/dbzero/anagrafiche/funzioni/fn_crea_contatto) — il verbo che fa nascere un contatto
> * [anagrafiche.trgfn_contatti_set_default_contatto](/dbzero/anagrafiche/funzioni/trgfn_contatti_set_default_contatto) — il predefinito di ogni contesto
> * [anagrafiche.trgfn_contatti_guard_contesto_soggetto](/dbzero/anagrafiche/funzioni/trgfn_contatti_guard_contesto_soggetto) — ruolo e istanza sono del soggetto del contatto
> * [anagrafiche.trgfn_soggetti_guard_soggetto_contatti](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_soggetto_contatti) — il soggetto ha almeno un contatto, al COMMIT
> * [script.fn_get_contatti](/dbzero/script/funzioni/fn_get_contatti) — il contatto migliore per tipo, dal più specifico al soggetto
> * [script.fn_get_contatto_default](/dbzero/script/funzioni/fn_get_contatto_default) — il predefinito fra quei contatti
>
> Guide:
>
> * [Gestione dei Contatti](/guide/gestione-dei-contatti) — il modello raccontato per intero

---

### 🎯 Scopo Principale

`anagrafiche.contatti` raccoglie i contatti delle anagrafiche: ogni contatto è una persona di riferimento di un
soggetto, con i suoi recapiti, e può avere come contesto un ruolo del soggetto, una sua istanza o tutti e due.

È l'unica sede dei contatti: un contatto del cliente o del fornitore è un contatto del soggetto col ruolo come
contesto, non una riga di un'altra tabella.

---

### Il contatto è del soggetto; ruolo e istanza sono il contesto

Il soggetto è obbligatorio. Ruolo e istanza sono facoltativi, e dicono **per che cosa** il contatto vale: il
referente del soggetto in generale, quello del suo ruolo di cliente, quello di una sua fornitura. Il ruolo e
l'istanza devono essere **del soggetto del contatto**: lo pretende
`anagrafiche.trgfn_contatti_guard_contesto_soggetto`, anche quando una modifica sposta il contatto su un altro
soggetto.

---

### Nominativo e tipo, il resto facoltativo

Ogni contatto ha un **nominativo** e un **tipo** (`tipo_contatto_id`, la categoria: il referente, l'ufficio
acquisti, …). I recapiti (email, telefono, cellulare, PEC) sono colonne della riga, e un contatto può averne
più d'uno o nessuno: il tipo non è il canale. Il **reparto** del referente è un'altra cosa ancora, e sta in
`unita_organizzativa_id`, facoltativa; il titolo di cortesia dà l'appellativo al nominativo.

---

### Un contatto per tipo in ogni contesto

Tre indici unici parziali, uno per livello, impediscono due contatti dello stesso tipo nello stesso posto:

* sul soggetto, senza ruolo né istanza: uno per tipo (`uq_contatti_soggetto_tipo`);
* sul ruolo, senza istanza: uno per tipo e per ruolo (`uq_contatti_ruolo_tipo_no_istanza`);
* sul ruolo e sull'istanza: uno per tipo, ruolo e istanza (`uq_contatti_ruolo_istanza_tipo`).

---

### Nasce con un verbo

Un contatto nasce con `anagrafiche.fn_crea_contatto`, che pretende nominativo e tipo e accetta un elenco chiuso
di campi. Lo usano i verbi di nascita del soggetto (che creano il suo primo contatto), quelli del cliente e del
fornitore, la creazione degli utenti tecnici e l'applicazione.

---

### La vita del contatto segue quella del soggetto

* Il contatto si scrive solo su un soggetto **attivo**, e con un'unità organizzativa attiva: lo controllano al
  COMMIT due trigger differiti, quando nasce o cambia soggetto o reparto.
* Il soggetto, finché ha contatti, **non si disattiva**; l'unità organizzativa nemmeno, finché un contatto la
  nomina.
* Cancellare il soggetto cancella i suoi contatti. Un ruolo o un'istanza che un contatto nomina, invece, non si
  cancellano finché il contatto c'è.
* Il soggetto deve avere almeno un contatto al COMMIT di ogni sua scrittura
  (`anagrafiche.trgfn_soggetti_guard_soggetto_contatti`).

La tabella non ha row security.

---

### La lettura: dal più specifico al soggetto

Chi cerca il contatto da usare non legge la tabella: `script.fn_get_contatti` dà un contatto per tipo, preferendo
quello dell'istanza e del ruolo chiesti, poi quello del ruolo, poi quello del soggetto; a parità, quello del
reparto chiesto, poi il predefinito, poi l'id più basso. `script.fn_get_contatto_default` sceglie il predefinito
fra quei contatti.

---

{% include-markdown "it/dbzero/anagrafiche/_contatto-predefinito.md" %}

---

### ⚠️ Che cosa oggi non copre

* **Il predefinito di un ruolo o di un'istanza.** La chiave del predefinito è soggetto più contesto: due ruoli,
  o due istanze, dello stesso soggetto ne condividono uno, e chi cerca il predefinito del suo ruolo può trovarlo
  vuoto perché il segno l'ha preso un contatto di un altro ruolo.
* **Il contatto di un'istanza senza ruolo.** È ammesso, e nessuno dei tre indici lo copre: sullo stesso soggetto
  e sulla stessa istanza possono stare due contatti dello stesso tipo.
* **Il predefinito che perde il segno o sparisce.** Nessuno ne promuove un altro, e il soggetto continua a
  puntare il contatto di prima.
* **Il soggetto che si spegne.** I contatti, che non hanno un loro `attivo`, ne bloccano la disattivazione
  finché esistono; tolti tutti, è la disattivazione stessa a non passare il controllo del contatto obbligatorio.
  Un soggetto con contatti oggi non si disattiva.
* **La lettura senza reparto.** Senza unità organizzativa fra i parametri, `script.fn_get_contatti` scarta i
  contatti che ne hanno una, invece di considerarli; `script.fn_get_contatto_default`, quando i predefiniti sono
  di tipi diversi, sceglie quello con l'id più basso.
* **I COMMENT.** Quello di `default_context` elenca i valori `soggetto`, `ruolo`, `utility` (il terzo è
  `istanza`); quello di `is_default` parla di un predefinito «per il soggetto».

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-contatto-v1.sql` — il verbo: il contatto di soggetto e quello di ruolo, i
  campi incompleti o fuori elenco, i quattro verbi che non scrivono più la tabella a mano.
* `db/pgtap/anagrafiche/test-contatti-soggetto-cliente.sql` — il contesto `ruolo` del contatto di un cliente, e la
  lettura per ruolo, per tipo e per reparto.
* `db/pgtap/anagrafiche/test-istanza-dello-stesso-soggetto-v1.sql` (test 13-16) — ruolo e istanza di un altro
  soggetto rifiutati.
* `db/pgtap/anagrafiche/soggetti-con-contatti.sql` — un soggetto costruito ha almeno un contatto con un recapito.

---

### Note di migrazione

* 2026-10-17 — nasce `anagrafiche.fn_crea_contatto`, e prende il posto degli inserimenti diretti dei verbi di
  nascita del soggetto, degli utenti tecnici, delle fixture e dell'applicazione.
* 2026-10-19 — nasce il controllo che ruolo e istanza siano del soggetto del contatto.

---

{% include-markdown "signature-core.md" %}
