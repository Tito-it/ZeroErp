## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_doc_testata_lock_fuori_bozza`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.ddt](/dbzero/vendite/tabelle/ddt) · [vendite.resi](/dbzero/vendite/tabelle/resi) · [vendite.ordini](/dbzero/vendite/tabelle/ordini) · [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali) · [vendite.contratti](/dbzero/vendite/tabelle/contratti) · [vendite.preventivi](/dbzero/vendite/tabelle/preventivi) — gli adottanti
>
> Approfondimento funzioni:
>
> * [vendite.trgfn_doc_righe_lock_fuori_bozza](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza) — il gemello delle righe
> * [script.fn_get_stato_testata_documento](/dbzero/script/funzioni/fn_get_stato_testata_documento) — il lettore `SECURITY DEFINER` da cui prende lo stato
> * [script.fn_doc_lock_regola](/dbzero/script/funzioni/fn_doc_lock_regola) · [script.fn_doc_lock_colonna_bloccata](/dbzero/script/funzioni/fn_doc_lock_colonna_bloccata) — la grammatica degli argomenti e la decisione
> * [script.fn_doc_lock_montaggi](/dbzero/script/funzioni/fn_doc_lock_montaggi) — il lettore del montaggio
> * [script.fn_doc_testata_in_stato](/dbzero/script/funzioni/fn_doc_testata_in_stato) — la stessa informazione per le capability
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — il blocco **assoluto** di colonna, che non guarda lo stato

---

### 🎯 Scopo Principale

**Alcune colonne della testata di un documento si scelgono solo finché il documento è in bozza.**

Fuori dalla bozza il documento è stampato, consegnato o ha già prodotto un fatto: merce uscita o
rientrata, un cliente a cui si fattura, un numero sul registro di un'azienda. Cambiare dopo la
causale, il cliente, il magazzino, l'azienda che emette o il documento da cui nasce vorrebbe dire che
il foglio dice una cosa e il database un'altra. Se il dato è sbagliato, si annulla il documento e se
ne fa uno nuovo.

È un **building block**: una sola funzione, montata `BEFORE UPDATE` su ogni testata con la lista
delle colonne da bloccare.

| Argomento | Cosa |
| --- | --- |
| `[0]` | il tipo di documento, col codice di `config.sorgenti` (`DDT_VENDITA`, `RESO_VENDITA`, `ORDINE_VENDITA`, `CONTRATTO`, `PREVENTIVO`, `OFFERTA_COMMERCIALE`): lo usa il lettore di stato |
| `[1]` | `codice_interno` dello stato «bozza» (`DRAFT`; `BOZZA` sull'offerta) |
| `[2..]` | terne *(colonna, codice d'errore, stati in cui resta aperta fuori bozza)* |

---

### 🔍 Come decide

* Confronta il valore vecchio e quello nuovo di ogni colonna della lista. Se nessuna cambia, non
  legge nemmeno lo stato.
* Se una cambia, guarda lo stato **di prima**. Così il passaggio dalla bozza all'emissione, che
  sceglie per esempio il cliente nello stesso momento, è legittimo: in quell'istante il documento
  era ancora in bozza.
* Il terzo elemento della terna dice dove la colonna resta aperta: **vuoto**, la colonna è ferma
  appena il documento esce dalla bozza; **una lista di stati**, la colonna si cambia ancora in quegli
  stati e si ferma negli altri (il documento chiuso); **`-`**, la colonna è ferma **sempre**,
  anche in bozza.
* Parla per la **prima** colonna della lista che cambia, nell'ordine del montaggio, col suo codice;
  nella frase c'è lo stato del documento.
* Si monta in fascia `_a05_`: «non si tocca» deve parlare prima dei guard che giudicano il valore
  nuovo, che proporrebbero un rimedio sbagliato.

Il trigger non interpreta gli argomenti da sé: la grammatica sta in `script.fn_doc_lock_regola`, la
decisione in `script.fn_doc_lock_colonna_bloccata`, e le usa anche il lettore del montaggio.

Un montaggio sbagliato (evento diverso da `UPDATE`, argomenti spaiati, una colonna che la testata
non ha) è un errore di configurazione, non di dato: `E_DOC_RIGHE_LOCK_MONTAGGIO`, lo stesso codice
del gemello delle righe, con la frase che dice che cosa si aspetta. Il nome parla di righe per
storia; la frase vale per tutti e due.

---

### Che cosa ferma, documento per documento

| Documento | Ferme fuori bozza | Aperte, e dove |
| --- | --- | --- |
| bolla | data, valuta, anno, serie, registro; causale; cliente; magazzini; emittente; documento d'origine | vettore, mittente, aspetto, porto, colli, pesi, volume, targa, autista, partenza, consegna prevista, tracciamento, note — in `EMESSO`, `SPEDITO`, `CONSEGNATO` |
| reso | data, valuta, anno, registro; magazzino; emittente; documento d'origine | note — in `CONFERMATO` |
| ordine | data, valuta, cambio, anno, serie, registro; utility; emittente; pagamento, agente, condizioni di fatturazione; documento d'origine | note — da `CONFERMATO` a `EVASO` |
| preventivo | data, valuta, revisione; cliente; termine, validità | competenza (si sceglie accettando) e note — in `EMESSO`, `ACCETTATO` |
| offerta | valuta; cliente; listino, versione, variazioni, validità | note e motivazione del rifiuto — in `EMESSA`, `ACCETTATA` |
| contratto | data, valuta; cliente; listino, versione, variazioni, ambito, decorrenza, canone, contratto padre, categoria cliente; documento d'origine | fine validità, CIG, CUP, codice commessa, note — in `ATTIVO` |

Il **documento d'origine** è la provenienza della testata, nelle tre colonne del modello
(`sorgente_tipo_id`, `sorgente_id`, `sorgente_uid`), tutte ferme insieme
(`E_DOC_SORGENTE_FUORI_BOZZA`): per il contratto è l'offerta da cui nasce, per l'ordine il
preventivo o l'offerta, per il reso la bolla, per la bolla l'ordine o il reso.

Su preventivo, offerta e contratto la **utility** e l'**emittente** non si cambiano nemmeno in
bozza: in bozza si cambia il cliente, dentro la stessa utility. I codici sono propri, perché la frase
«si sceglie solo in bozza» lì sarebbe falsa:

| Colonna | Codice |
| --- | --- |
| `utility_id` | `E_DOC_UTILITY_IMMUTABILE` |
| `emittente_fiscale_id` | `E_DOC_EMITTENTE_IMMUTABILE` |

Codici per famiglia, sulle altre colonne: `E_DOC_IDENTITA_FUORI_BOZZA`,
`E_DOC_CONDIZIONI_FUORI_BOZZA`, `E_DOC_CLIENTE_FUORI_BOZZA`, `E_DOC_SORGENTE_FUORI_BOZZA`,
`E_DOC_EMITTENTE_FUORI_BOZZA`, e `E_DOC_CHIUSO` per le colonne aperte a documento chiuso. Bolla e
reso tengono i loro codici di causale, cliente e magazzino.

Non si nominano le colonne generate (in un trigger `BEFORE` valgono `NULL` e sembrerebbero cambiate
sempre) né `fatturazione_immediata`, che ha il suo guard (si ferma quando il documento entra in
commessa). Sul contratto il lock parla prima del guard del listino.

⚠️ È un blocco **per fase**. Il blocco **assoluto** (una colonna che non cambia mai, come il cliente
dell'ordine) resta a `script.trgfn_lock_columns`, generato dal registro
`dbops.automation_lock_columns`.

---

### 🧪 Test

* `db/pgtap/vendite/test-esecutivi-ba-coppia-v1.sql` — cliente e causale della bolla, emittente di
  bolla e ordine, montaggio sugli adottanti.
* `db/pgtap/script/test-doc-lock-montaggio-v1.sql` — la grammatica e il lettore del montaggio.
* `db/pgtap/vendite/test-testata-dopo-emissione-v1.sql` — la matrice colonna × stato.
* `db/pgtap/vendite/test-doc-emittente-utility-fermi-v1.sql` — utility ed emittente fermi sempre.

---

### Note di migrazione

* 2026-10-09 — nasce dalle tre copie scritte a mano della regola «si cambia solo in bozza» (causale
  e magazzino della bolla, magazzino del reso), ritirate nello stesso giro; lo adottano subito il
  cliente della bolla e l'emittente di sei documenti (brief-db-esecutivi-ba-coppia).
* 2026-10-10 — la grammatica e la decisione passano in una sede condivisa, e gli argomenti
  diventano terne con gli stati in cui la colonna resta aperta; sul contratto assorbe
  `trgfn_contratti_lock_post_attivazione`, ritirato (brief-db-testata-dopo-emissione).
* 2026-10-18 — utility ed emittente fermi sempre su preventivo, offerta e contratto
  (brief-db-indirizzi-documento-seguono-il-cliente §8.7).
* 2026-11-06 — su bolla e reso si ferma anche `sorgente_id` (brief-db-sorgente-documento-e-riga).
* 2026-11-07 — su ordine e contratto si ferma anche `sorgente_id`; il documento d'origine
  dell'ordine (`documento_origine_*`) e l'offerta del contratto (`offerta_id`) escono dalle tabelle,
  e la loro provenienza è la sorgente.

---

{% include-markdown "signature-core.md" %}
