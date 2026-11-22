## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_indirizzo_soggetto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — la riga che la funzione scrive
> * [config.tipi_soggetto_dettaglio_tipi_indirizzo](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo) — i tipi che la natura ammette
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_indirizzo_elemento](/dbzero/anagrafiche/funzioni/fn_indirizzo_elemento) — la grammatica dell'indirizzo
> * [anagrafiche.fn_indirizzo_elemento_dettaglio](/dbzero/anagrafiche/funzioni/fn_indirizzo_elemento_dettaglio) — il dettaglio, se l'indirizzo non è libero
> * [anagrafiche.fn_check_tipo_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_check_tipo_indirizzo_soggetto) — il giudizio sul tipo
> * [anagrafiche.trgfn_indirizzi_guard_forma_libera](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_forma_libera) — le due forme dell'indirizzo libero
> * [anagrafiche.fn_crea_indirizzi_soggetto](/dbzero/anagrafiche/funzioni/fn_crea_indirizzi_soggetto) — la plurale, che scrive da questa
> * [anagrafiche.fn_crea_indirizzo_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_indirizzo_ruolo) — la gemella del ruolo
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — le tre forme e i tipi

---

### 🎯 Scopo Principale

`anagrafiche.fn_crea_indirizzo_soggetto` scrive un indirizzo di un soggetto e restituisce l'id della riga. È la sede
unica dell'inserimento in `anagrafiche.indirizzi_soggetti`: ci passano la plurale, la copia di un indirizzo, la
creazione dell'operatore, il provisioning dei dati di sviluppo e l'applicazione.

---

### L'indirizzo, in una di tre forme

L'indirizzo è un oggetto con la grammatica di `anagrafiche.fn_indirizzo_elemento`, la stessa della gemella del ruolo:

| Forma | Che cosa si indica |
| --- | --- |
| **libero** | il testo, lo stato e, secondo lo stato, comune e CAP del catalogo oppure la località, con codice postale, regione e sotto-località facoltativi |
| **dettaglio già risolto** | il dettaglio (`indirizzo_dettaglio_id`) |
| **via da risolvere** | la via del catalogo, oppure una via nuova (tipo strada, nome, comune, CAP), più il civico |

Il tipo si indica per id (`tipo_indirizzo_id`) o per codice interno (`tipo_indirizzo_codice_interno`, per esempio
`RES`). La chiave `tipo_indirizzo_codice` non si accetta: `*_codice` è il nome che le viste usano per il display.

⚠️ Se l'elemento porta insieme un testo libero e un dettaglio, **vale il libero**: il dettaglio si scarta e la riga
nasce libera. Un dettaglio insieme ai campi di una via vale invece il dettaglio.

---

### ⭐ Il tipo lo giudica la check, prima di scrivere

Prima dell'inserimento la madre chiede a `anagrafiche.fn_check_tipo_indirizzo_soggetto` i motivi per cui quel tipo
non si può scrivere sul soggetto, e solleva il primo, col campo `tipo_indirizzo_codice_interno`. I motivi, in
quest'ordine: il soggetto ha già un indirizzo di quel tipo; la natura del soggetto non lo ammette, il giorno operativo.

La stessa check la leggono il picker dei tipi (`anagrafiche.fn_tipi_indirizzo_proponibili_soggetto`) e la copia di un
indirizzo: ciò che il picker propone e ciò che la madre accetta sono la stessa regola. Sulla tabella restano, per ogni
altra strada di scrittura e contro due scritture concorrenti, il guard `anagrafiche.trgfn_indirizzi_soggetti_guard_tipo_indirizzo`
e il vincolo `uq_indirizzi_soggetti_soggetto_tipo`: da questa madre non parlano, perché la check arriva prima.

---

### Che cosa lascia alla tabella

* **La forma dell'indirizzo libero** (i campi che mancano, quelli dell'altra forma, comune e CAP coerenti con lo
  stato) la dice il guard `anagrafiche.trgfn_indirizzi_guard_forma_libera`: la madre non la ripete.
* **Lo stato non indicato** di un indirizzo libero lo propone il normalize della tabella.
* **Gli indirizzi obbligatori** del soggetto li pretendono i guard differiti, al COMMIT: la madre scrive una riga
  e non guarda gli altri tipi. La copia del primo indirizzo negli obbligatori è della plurale.
* **Il permesso** lo decide l'applicazione.

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — manca il soggetto, o l'indirizzo non è un oggetto.
* `E_CAMPO_NON_AMMESSO` — una chiave che un indirizzo non ha, col suo nome.
* `E_TIPO_INDIRIZZO_NON_TROVATO` — il codice del tipo manca o non esiste.
* `E_SOGGETTO_NOT_FOUND` — il soggetto non esiste.
* `E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE` — il soggetto ha già quel tipo.
* `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO` — la natura del soggetto non ammette quel tipo.
* Dal guard della forma: `E_INDIRIZZO_LIBERO_INCOMPLETO`, `E_INDIRIZZO_CAMPO_ALTRA_FORMA`,
  `E_INDIRIZZO_COMUNE_ALTRO_STATO`, `E_INDIRIZZO_CAP_ALTRO_COMUNE`.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-indirizzo-soggetto.sql` — il dettaglio, il secondo tipo, il tipo già presente,
  le chiavi estranee e quella ritirata, il tipo vuoto o inesistente, il soggetto mancante.
* `db/pgtap/anagrafiche/test-indirizzo-libero-due-forme-v1.sql` — le due forme dell'indirizzo libero, anche passando
  dalla madre.
* `db/pgtap/anagrafiche/test-check-tipo-indirizzo-v1.sql` — la check chiamata dalla madre, prima del vincolo.

---

### Note di migrazione

* 2026-10-18 — l'indirizzo passa in jsonb, con la grammatica della gemella del ruolo, al posto di sette parametri
  posizionali. La firma vecchia non aveva i campi della forma estera e pretendeva comune e CAP per ogni indirizzo libero;
  è stata tolta.
* 2026-11-01 — il tipo per codice si chiama `tipo_indirizzo_codice_interno`; `tipo_indirizzo_codice` si rifiuta.

---

{% include-markdown "signature-core.md" %}
