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
