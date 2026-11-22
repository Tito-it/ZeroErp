## 📘 Documentazione Concettuale – Tabella `anagrafiche.indirizzi_soggetti`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — il soggetto a cui l'indirizzo appartiene
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — gli indirizzi dei ruoli, che ripiegano su questi
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — il civico, nella forma col dettaglio
> * [config.tipi_soggetto_dettaglio_tipi_indirizzo](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo) — i tipi ammessi e obbligatori per natura
> * [config.storico_set_storicizza](/dbzero/config/tabelle/storico_set_storicizza) — le tabelle con lo storico continuo, fra cui questa
> * [storico.indirizzi_soggetti](/dbzero/storico/tabelle/indirizzi_soggetti) — le versioni conservate
>
> Approfondimento viste:
>
> * [anagrafiche.vw_indirizzi_resolved_soggetto](/dbzero/anagrafiche/views/vw_indirizzi_resolved_soggetto) — la lettura risolta di questi indirizzi
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_indirizzi_soggetti_guard_tipo_indirizzo](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_soggetti_guard_tipo_indirizzo) — il tipo ammesso per la natura
> * [anagrafiche.trgfn_indirizzi_soggetti_guard_obbligatori_soggetto](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_soggetti_guard_obbligatori_soggetto) — gli indirizzi obbligatori del soggetto
> * [anagrafiche.trgfn_indirizzi_base_normalize](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_base_normalize) — mette in ordine la riga secondo la forma
> * [anagrafiche.trgfn_indirizzi_guard_forma_libera](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_forma_libera) — giudica l'indirizzo libero
> * [anagrafiche.trgfn_indirizzi_sync_geoloc](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_sync_geoloc) — la posizione copiata dal civico
> * [anagrafiche.fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_crea_indirizzo_soggetto) — il verbo che crea un indirizzo del soggetto
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — il quadro degli indirizzi, dei tipi e dei ripieghi

---

### 🎯 Scopo Principale

`anagrafiche.indirizzi_soggetti` tiene gli indirizzi che appartengono al soggetto in sé, qualunque ruolo
abbia: la residenza, il domicilio fiscale, la sede legale. Uno per tipo (`uq_indirizzi_soggetti_soggetto_tipo`).

L'indirizzo ha una delle due forme descritte in fondo alla pagina, col dettaglio o libera; questa pagina dice
ciò che è proprio degli indirizzi del soggetto.

---

### ⭐ L'indirizzo di tutti i ruoli

Un indirizzo del soggetto vale per ogni suo ruolo che non ne ha uno proprio dello stesso tipo: è l'ultimo
livello del ripiego che parte dall'istanza e passa dal ruolo (vedi `anagrafiche.indirizzi`). Chi ha bisogno di
un indirizzo diverso per un ruolo lo scrive sul ruolo, eventualmente copiandolo da qui; questa riga non cambia.

---

### Le regole della riga

Le regole che seguono hanno ciascuna la sua scheda; qui se ne dice il significato.

* **Il tipo è ammesso per la natura del soggetto** (`anagrafiche.trgfn_indirizzi_soggetti_guard_tipo_indirizzo`,
  `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO`): la matrice per natura, letta nel giorno operativo, dice quali
  tipi una persona fisica o una società possono avere. Si giudica alla nascita e al cambio di tipo.
* **Il titolare non cambia**: `soggetto_id` è bloccato dopo la nascita (`E_INDIRIZZO_SOGGETTO_TITOLARE_IMMUTABILE`).
* **Le madri sono attive**: alla conferma dell'operazione, il soggetto e, nella forma col dettaglio, il civico
  devono essere attivi. Un soggetto spento non riceve indirizzi nuovi.
* **Gli obbligatori restano**: alla conferma dell'operazione, togliere un indirizzo o cambiargli tipo non può
  lasciare il soggetto senza un tipo che la sua natura rende obbligatorio
  (`anagrafiche.trgfn_indirizzi_soggetti_guard_obbligatori_soggetto`).

Le righe le scrive `anagrafiche.fn_crea_indirizzo_soggetto` (e, per più tipi insieme,
`anagrafiche.fn_crea_indirizzi_soggetto`).

---

### Lo storico è continuo

A differenza degli indirizzi del ruolo, qui `storicizza` nasce `true` e la tabella è in
`config.storico_set_storicizza`: il trigger dello storico non rimette il flag a `false`. Ogni modifica e ogni
cancellazione lasciano la loro versione in `storico.indirizzi_soggetti`, salvo una scrittura che passi
esplicitamente `storicizza = false`.

---

### ⚠️ Che cosa oggi non copre

* **La posizione è una copia**: `geoloc` prende la posizione del civico quando la riga si scrive. Se poi cambia
  la posizione del civico, la riga la riprende solo alla sua prossima scrittura.
* **Le FK verso comune, CAP e stato non hanno azione alla cancellazione**, mentre le gemelle di
  `anagrafiche.indirizzi` sono `ON DELETE SET NULL`: le due tabelle, che hanno le stesse colonne e le stesse
  regole, rispondono in modo diverso alla stessa cancellazione nel catalogo.

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-indirizzi-required.sql` — gli obbligatori per natura (residenza e
  domicilio fiscale per la persona fisica, sede legale per la società), al COMMIT.
* `db/pgtap/anagrafiche/test-fn-crea-indirizzo-soggetto.sql` — la creazione dal verbo, il secondo indirizzo
  dello stesso tipo rifiutato.
* `db/pgtap/anagrafiche/test-indirizzo-libero-due-forme-v1.sql` — le due forme dell'indirizzo libero, sulle due
  tabelle.

---

### Note di migrazione

* 2026-10-18 — `postal_box` diventa `postal_code`, e l'indirizzo libero prende le due forme decise dallo stato,
  con il giudizio in un guard che dice il campo.

---

{% include-markdown "it/dbzero/anagrafiche/_indirizzo-libero-o-dettaglio.md" %}

---

{% include-markdown "signature-core.md" %}
