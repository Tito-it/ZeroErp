## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_doc_testata_lock_fuori_bozza`

> 👀 **Vedi anche**
>
> [vendite.trgfn_doc_righe_lock_fuori_bozza](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza) — il gemello delle righe
> [script.fn_get_stato_testata_documento](/dbzero/script/funzioni/fn_get_stato_testata_documento) — il lettore `SECURITY DEFINER` da cui prende lo stato
> [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — il blocco **assoluto** di colonna, che non guarda lo stato
> [vendite.ddt](/dbzero/vendite/tabelle/ddt) · [vendite.resi](/dbzero/vendite/tabelle/resi) · [vendite.ordini](/dbzero/vendite/tabelle/ordini) · [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali) · [vendite.contratti](/dbzero/vendite/tabelle/contratti) · [vendite.preventivi](/dbzero/vendite/tabelle/preventivi) — gli adottanti

---

### 🎯 Scopo Principale

**Alcune colonne della testata di un documento si scelgono solo finché il
documento è in bozza.**

Fuori dalla bozza il documento è stampato, consegnato o ha già prodotto un
fatto: merce uscita o rientrata, un cliente a cui si fattura, un numero sul
registro di un'azienda. Cambiare dopo la causale, il cliente, il magazzino o
l'azienda che emette vorrebbe dire che il foglio dice una cosa e il database
un'altra. Se il dato è sbagliato, si annulla il documento e se ne fa uno
nuovo.

È un **building block**: una sola funzione, montata su ogni testata con la
lista delle colonne da bloccare e il codice d'errore di ciascuna.

| `TG_ARGV` | Cosa | Esempio |
| --- | --- | --- |
| `[0]` | tipo di documento, per il lettore di stato | `'DDT'` |
| `[1]` | `codice_interno` dello stato «bozza» | `'DRAFT'` (`'BOZZA'` sull'offerta) |
| `[2..]` | coppie *(colonna, codice d'errore)* | `'billing_account_id', 'E_DDT_CLIENTE_IMMUTABILE'` |

```sql
CREATE TRIGGER trg_ddt_a05_lock_fuori_bozza_upd
  BEFORE UPDATE ON vendite.ddt
  FOR EACH ROW
  EXECUTE FUNCTION vendite.trgfn_doc_testata_lock_fuori_bozza(
    'DDT', 'DRAFT',
    'causale_trasporto_id', 'E_DDT_CAUSALE_IMMUTABILE',
    'billing_account_id',   'E_DDT_CLIENTE_IMMUTABILE',
    ...);
```

---

### 🔍 Come decide

* Confronta il valore vecchio e quello nuovo di ogni colonna della lista. Se
  nessuna cambia, non legge nemmeno lo stato.
* Se una cambia, guarda lo stato **di prima**. Così il passaggio dalla bozza
  all'emissione, che sceglie per esempio il cliente nello stesso momento, è
  legittimo: in quell'istante il documento era ancora in bozza.
* Parla per la **prima** colonna della lista che cambia, col suo codice; nella
  frase c'è lo stato del documento.
* Si monta in fascia `_a05_`: «non si tocca» deve parlare prima dei guard che
  giudicano il valore nuovo.

Un montaggio sbagliato (evento diverso da `UPDATE`, argomenti spaiati, una
colonna che la testata non ha) è un errore di configurazione, non di dato:
`E_DOC_RIGHE_LOCK_MONTAGGIO`, lo stesso codice del gemello delle righe. Il nome
parla di righe per storia; la frase vale per tutti e due.

---

### ⭐ Da dove nasce

La regola «questa colonna si cambia solo in bozza» era scritta a mano tre
volte: la causale del DDT, il suo magazzino, il magazzino del reso. Il 9
ottobre 2026 (brief `brief-db-esecutivi-ba-coppia`) ne serviva una quarta, il
cliente della bolla: è nato il building block, e le tre copie sono state
ritirate nello stesso giro. Lo stesso giorno lo ha adottato l'**azienda che
emette** su sei documenti, che fino ad allora si poteva cambiare in qualunque
stato.

| Documento | Colonne bloccate fuori bozza |
| --- | --- |
| DDT | causale, billing account, utility, destinatario, magazzino di partenza e di arrivo, emittente |
| reso | magazzino di rientro, emittente |
| ordine, offerta, contratto, preventivo | emittente |

⚠️ È un blocco **per fase**. Il blocco **assoluto** (una colonna che non
cambia mai, nemmeno in bozza, come il cliente dell'ordine) resta a
`script.trgfn_lock_columns`, generato dal registro
`dbops.automation_lock_columns`.

---

### 🧪 Test

`db/pgtap/vendite/test-esecutivi-ba-coppia-v1.sql`: test 15 e 16 (cliente e
causale del DDT), 28 e 29 (emittente di DDT e ordine), 30 e 38 (montaggio su
preventivo, offerte, contratti e resi).

---

### 🔄 rev 2026-10-10 — gli argomenti e la decisione in una sede condivisa (brief-db-testata-dopo-emissione, fase 1)

Come il gemello delle righe, il trigger non interpreta più gli argomenti da sé: la
grammatica sta in [`script.fn_doc_lock_regola`](/dbzero/script/funzioni/fn_doc_lock_regola),
la decisione in [`script.fn_doc_lock_colonna_bloccata`](/dbzero/script/funzioni/fn_doc_lock_colonna_bloccata),
e le usa anche il lettore del montaggio,
[`script.fn_doc_lock_montaggi`](/dbzero/script/funzioni/fn_doc_lock_montaggi).

Il comportamento resta quello descritto sopra: se nessuna colonna nominata cambia lo stato
non si legge; altrimenti parla la prima colonna nominata, nell'ordine del montaggio, col
suo codice. Montato su un evento diverso da `UPDATE`, la frase dice «si monta BEFORE
UPDATE»; con argomenti sbagliati dice quali si aspetta.

⭐ È anche il punto in cui arriverà la **forma per stato** della testata (decisione D-8 del
brief: le colonne che restano aperte dopo l'emissione si chiudono quando il documento si
chiude). Si aggiunge alla grammatica, e trigger e lettore la seguono insieme.

> 📎 changeSet `20261010-60`, `-61`, `-65`. Presidio:
> `db/pgtap/script/test-doc-lock-montaggio-v1.sql` (18-21).

---

### 🔄 rev 2026-10-10 — terne e famiglie (brief-db-testata-dopo-emissione, fase 2)

Gli argomenti sono **terne** *(colonna, codice, stati in cui resta aperta fuori bozza)*. Stati
vuoti: la colonna è ferma appena il documento esce dalla bozza. Una lista: la colonna si cambia
ancora in quegli stati, e si ferma negli altri (il documento chiuso: decisioni D-8 e D-10).

| Documento | Ferme fuori bozza | Aperte, e dove |
| --- | --- | --- |
| bolla | data, valuta, anno, serie, registro; causale; cliente; magazzini; emittente; sorgente | vettore, mittente, aspetto, porto, colli, pesi, volume, targa, autista, partenza, consegna prevista, tracciamento, note — in `EMESSO`, `SPEDITO`, `CONSEGNATO` |
| reso | data, valuta, anno, registro; magazzino; emittente; sorgente | note — in `CONFERMATO` |
| ordine | data, valuta, cambio, anno, serie, registro; utility; emittente; pagamento, agente, condizioni di fatturazione; sorgente e documento d'origine | note — da `CONFERMATO` a `EVASO` |
| preventivo | data, valuta, revisione; cliente; emittente; termine, validità | competenza (si sceglie accettando, D-9) e note — in `EMESSO`, `ACCETTATO` |
| offerta | valuta; cliente; emittente; listino, versione, variazioni, validità | note e motivazione del rifiuto — in `EMESSA`, `ACCETTATA` |
| contratto | data, valuta; cliente; emittente; listino, versione, variazioni, ambito, decorrenza, contratto padre, categoria cliente; offerta e sorgente | fine validità, CIG, CUP, codice commessa, note — in `ATTIVO` |

Codici per famiglia: `E_DOC_IDENTITA_FUORI_BOZZA`, `E_DOC_CONDIZIONI_FUORI_BOZZA`,
`E_DOC_CLIENTE_FUORI_BOZZA`, `E_DOC_SORGENTE_FUORI_BOZZA`, `E_DOC_EMITTENTE_FUORI_BOZZA`, e
`E_DOC_CHIUSO` per le colonne aperte a documento chiuso. Bolla e reso tengono i loro codici di
causale, cliente e magazzino.

Non si nominano le colonne generate (in un trigger `BEFORE` valgono `NULL` e sembrerebbero
cambiate sempre) né `fatturazione_immediata`, che ha il suo guard (si ferma quando il documento
entra in commessa). Sul contratto il lock ha assorbito `trgfn_contratti_lock_post_attivazione`
(ritirato), e parla prima del guard del listino. Le capability leggono le stesse informazioni
con [`script.fn_doc_testata_in_stato`](/dbzero/script/funzioni/fn_doc_testata_in_stato).

> 📎 changeSet `20261010-68`, `-69`. Presidio: `db/pgtap/vendite/test-testata-dopo-emissione-v1.sql`
> (la matrice colonna × stato, test 3).

### 🔄 rev 2026-10-18 — emittente e utility fermi sempre (brief-db-indirizzi-documento-seguono-il-cliente §8.7)

Su preventivo, offerta e contratto la **utility** e l'**emittente** non si cambiano più nemmeno
in bozza: in bozza si cambia il cliente, dentro la stessa utility (decisioni B-4 ed E-3 di Tid).
Prima la regola la diceva solo il backend, e in tre modi diversi. Nel montaggio la terna ha `-` al
posto degli stati; i codici sono nuovi, perché la frase di prima («si sceglie solo in bozza») qui
sarebbe falsa:

| Colonna | Codice |
| --- | --- |
| `utility_id` | `E_DOC_UTILITY_IMMUTABILE` |
| `emittente_fiscale_id` | `E_DOC_EMITTENTE_IMMUTABILE` |

Bolla, reso e ordine non cambiano. Il lock è in fascia `_a05_`: il rifiuto parla prima dei guard
che giudicano il valore nuovo (emittente e billing account, perimetro dell'emittente), che
proporrebbero un rimedio sbagliato. Il corpo della funzione non cambia.

> 📎 changeSet `20261018-67`. Presidio: `db/pgtap/vendite/test-doc-emittente-utility-fermi-v1.sql`;
> la matrice colonna × stato di `test-testata-dopo-emissione-v1.sql` dice `-` per queste sei colonne.
