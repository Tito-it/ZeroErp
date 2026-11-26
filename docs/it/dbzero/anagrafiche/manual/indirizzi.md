## 📘 Documentazione Concettuale – Tabella `anagrafiche.indirizzi`

> **Ultimo aggiornamento**: 24 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo a cui l'indirizzo appartiene
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza di servizio, per l'indirizzo che vale solo lì
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — gli indirizzi del soggetto, l'ultimo livello del ripiego
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — il civico, nella forma col dettaglio
> * [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi) — il tipo dell'indirizzo
> * [config.stati](/dbzero/config/tabelle/stati) — lo stato, che decide la forma dell'indirizzo libero
> * [storico.indirizzi](/dbzero/storico/tabelle/indirizzi) — le versioni conservate
>
> Approfondimento viste:
>
> * [anagrafiche.vw_indirizzi_resolved_base](/dbzero/anagrafiche/views/vw_indirizzi_resolved_base) — la lettura risolta degli indirizzi
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_indirizzi_base_normalize](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_base_normalize) — mette in ordine la riga secondo la forma
> * [anagrafiche.trgfn_indirizzi_guard_forma_libera](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_forma_libera) — giudica l'indirizzo libero
> * [anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo) — il tipo ammesso per il ruolo
> * [anagrafiche.trgfn_guard_istanza_del_ruolo](/dbzero/anagrafiche/funzioni/trgfn_guard_istanza_del_ruolo) — l'istanza è dello stesso soggetto
> * [anagrafiche.trgfn_indirizzi_guard_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_obbligatori_ruolo) — gli indirizzi obbligatori del ruolo
> * [anagrafiche.fn_crea_indirizzo_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_indirizzo_ruolo) — il verbo che crea un indirizzo del ruolo
> * [script.fn_get_indirizzo](/dbzero/script/funzioni/fn_get_indirizzo) — il risolutore che scende per i livelli
> * [script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic) — lo storico
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — il quadro degli indirizzi, dei tipi e dei ripieghi

---

### 🎯 Scopo Principale

`anagrafiche.indirizzi` tiene gli indirizzi di un ruolo di un soggetto (il cliente, il fornitore, il
gestore…): uno per tipo, più, quando serve, uno per tipo specifico di un'istanza di servizio.

L'indirizzo ha una delle due forme descritte in fondo alla pagina, col dettaglio o libera; questa pagina dice
ciò che è proprio degli indirizzi del ruolo.

---

### ⭐ Tre livelli, dal più specifico al più generale

* **Dell'istanza** (`istanza_utility_id` valorizzato): l'indirizzo vale solo per quella fornitura, per esempio
  la fatturazione di un contratto del gas diversa da quella degli altri. Uno per tipo per istanza
  (`uq_indirizzi_ruolo_istanza_tipo`).
* **Del ruolo** (`istanza_utility_id` vuoto): vale per tutte le istanze del ruolo che non ne hanno uno loro.
  Uno per tipo per ruolo (`uq_indirizzi_ruolo_tipo_no_istanza`).
* **Del soggetto**, in `anagrafiche.indirizzi_soggetti`: vale per tutti i ruoli.

Chi cerca l'indirizzo da usare scende i livelli in quest'ordine, e sui due livelli del ruolo prova anche il
tipo di ripiego che la matrice dei ruoli prevede (per esempio la sede operativa che, se manca, è la sede legale). La
discesa la fa `script.fn_get_indirizzo`, non la tabella: qui ogni riga è un indirizzo scritto davvero.

---

### Chi può stare sulla riga

Le regole che seguono hanno ciascuna la sua scheda; qui se ne dice il significato.

* **Il titolare non cambia**: `soggetto_ruolo_id` è bloccato dopo la nascita (`E_INDIRIZZO_RUOLO_TITOLARE_IMMUTABILE`).
  Un indirizzo di un altro ruolo si crea, o si copia, non si sposta.
* **Il tipo è ammesso per il tipo di ruolo** (`anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`):
  la matrice dei ruoli dice quali tipi d'indirizzo un ruolo può avere.
* **L'istanza è dello stesso soggetto** (`anagrafiche.trgfn_guard_istanza_del_ruolo`, `E_ISTANZA_ALTRO_SOGGETTO`):
  un indirizzo di istanza non può puntare la fornitura di un altro.
* **Il civico è attivo**: alla conferma dell'operazione, un indirizzo col dettaglio deve puntare un civico
  attivo.
* **Gli obbligatori restano**: alla conferma dell'operazione, togliere un indirizzo o cambiargli tipo non può
  lasciare il ruolo senza un indirizzo che la matrice dice obbligatorio
  (`anagrafiche.trgfn_indirizzi_guard_obbligatori_ruolo`). Si giudica solo ciò che l'indirizzo che esce dava:
  un obbligatorio nato dopo, che il ruolo non ha mai avuto, non ferma la cancellazione di un altro indirizzo.
  La nascita non si giudica qui: la giudica il ruolo.

Le righe le scrivono i verbi del dominio, `anagrafiche.fn_crea_indirizzo_ruolo` e `anagrafiche.fn_crea_indirizzi_ruolo`
per la creazione, e i verbi della copia per portare qui un indirizzo del soggetto.

---

### Lo storico è continuo

`storicizza` nasce `true`, e la tabella è fra quelle che tengono il flag acceso
(`config.storico_set_storicizza`): ogni modifica lascia in `storico.indirizzi` la versione nuova (la prima
anche quella di partenza), e ogni cancellazione la sua. Lo garantisce il database, qualunque sia la strada
della scrittura: il pannello, le madri, i verbi di copia. Come su `anagrafiche.indirizzi_soggetti`, una
scrittura che porta il flag a `false` non lascia traccia, e la riga resta senza storico finché qualcuno non lo
riaccende: il flag è il modo di chi scrive di dire «questa no».

---

### Un comune, un CAP o uno stato in uso non si cancellano

Le FK verso comune, CAP e stato non hanno azione alla cancellazione, come le gemelle di
`anagrafiche.indirizzi_soggetti`: finché un indirizzo li usa, la cancellazione si ferma sulla FK. Una voce del
catalogo che non serve più si spegne. Un cambio d'id, invece, segue sulla riga.

---

### Col dettaglio, la posizione la dice il civico

Un indirizzo col dettaglio non tiene una posizione sua: `geoloc` resta vuota, come comune e CAP, e chi legge
prende quella del civico, che segue ogni correzione. Solo l'indirizzo libero tiene la posizione scritta da chi
lo salva.

---

### Test

* `db/pgtap/anagrafiche/test_indirizzi_unique_res.sql` — un solo indirizzo dello stesso tipo per il ruolo,
  fuori da un'istanza.
* `db/pgtap/anagrafiche/test-indirizzi-istanza-cascata.sql` — i due indici unici, la discesa istanza → ruolo →
  soggetto, le viste risolte che espongono l'istanza.
* `db/pgtap/anagrafiche/test-indirizzi-fallback.sql` — il tipo rifiutato per il ruolo, il ripiego del tipo.
* `db/pgtap/anagrafiche/test-indirizzo-libero-due-forme-v1.sql` — le due forme dell'indirizzo libero.
* `db/pgtap/anagrafiche/test-soggetti-ruoli-indirizzi-required.sql` — gli indirizzi obbligatori del ruolo, al
  COMMIT.
* `db/pgtap/anagrafiche/test-indirizzi-viste-forma-e-vincoli-v1.sql` (6, 15, 21, 22) — le FK senza azione, come
  quelle di `anagrafiche.indirizzi_soggetti`; lo stato e il CAP in uso che non si cancellano; l'indirizzo col
  dettaglio che nasce senza una posizione sua.
* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-requisito-nuovo-v1.sql` (6, 7) — sul ruolo a cui un
  obbligatorio nato dopo chiede un indirizzo che non ha, cancellare un indirizzo che nessuno chiede passa.
* `db/pgtap/anagrafiche/test-storico-indirizzi-continuo-v1.sql` — lo storico continuo: la riga nasce col flag
  acceso, due modifiche lasciano due versioni, il flag resta acceso, una scrittura che lo spegne non lascia traccia.

---

### Note di migrazione

* 2026-10-18 — `postal_box` diventa `postal_code`, e l'indirizzo libero prende le due forme decise dallo stato,
  con il giudizio in un guard che dice il campo.
* 2026-11-24 — le FK verso comune, CAP e stato perdono `ON DELETE SET NULL`; si ritira la copia della posizione
  del civico nella riga (le righe col dettaglio la perdono una volta); il guard degli obbligatori giudica solo
  ciò che l'indirizzo che esce dava.

---

{% include-markdown "it/dbzero/anagrafiche/_indirizzo-libero-o-dettaglio.md" %}

---

{% include-markdown "signature-core.md" %}
