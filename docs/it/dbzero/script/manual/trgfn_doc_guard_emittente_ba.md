## 📘 Documentazione Concettuale – Trigger function `script.trgfn_doc_guard_emittente_ba`

> 👀 **Vedi anche**
>
> [anagrafiche.fn_get_emittente_fiscale_pk](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk) · [anagrafiche.fn_get_emittente_fiscale_id](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_id) — i due risolutori: dal billing account all'azienda che emette
> [script.trgfn_default_emittente_fiscale](/dbzero/script/funzioni/trgfn_default_emittente_fiscale) · [vendite.trgfn_commesse_default_emittente](/dbzero/vendite/manual/trgfn_commesse_default_emittente) — chi riempie l'emittente quando il chiamante non lo dice, prima di questo controllo
> [anagrafiche.fn_guard_ba_cambio_emittente](/dbzero/anagrafiche/manual/fn_guard_ba_cambio_emittente) — l'altra metà: un cliente che ha già documenti non cambia azienda
> [vendite.trgfn_doc_testata_lock_fuori_bozza](/dbzero/vendite/manual/trgfn_doc_testata_lock_fuori_bozza) — fuori bozza l'emittente non si cambia proprio; su preventivo, offerta e contratto nemmeno in bozza (e quel rifiuto parla prima di questo controllo)

---

### 🎯 Scopo Principale

**Un documento di vendita è emesso dall'azienda del suo cliente.**

Ogni cliente, attraverso il suo billing account, appartiene a un'azienda: quella
che lo serve, che numera i suoi documenti sul proprio registro e gli fattura.
Un preventivo, un'offerta, un contratto, un ordine, una bolla, un reso o una
commessa intestati a quel cliente devono essere emessi da **quella** azienda.

Il controllo è un **building block**: una sola funzione, montata sulle sette
tabelle.

| `TG_ARGV` | Cosa | Esempio |
| --- | --- | --- |
| `[0]` | come chiamare il documento nella frase | `'Ordine'` |
| `[1]` | la colonna che lo identifica | `'numero'` (`'codice'` su offerta e commessa) |
| `[2]` | la colonna dell'emittente | `'emittente_fiscale_id'` (`'emittente_soggetto_ruolo_id'` sulla commessa) |
| `[3]` | il codice d'errore | `'E_DOC_EMITTENTE_BA_INCOERENTE'` |

```sql
CREATE TRIGGER trg_ordini_a10_guard_emittente_ba_ins_upd
  BEFORE INSERT OR UPDATE OF billing_account_id, emittente_fiscale_id ON vendite.ordini
  FOR EACH ROW
  EXECUTE FUNCTION script.trgfn_doc_guard_emittente_ba(
    'Ordine', 'numero', 'emittente_fiscale_id', 'E_DOC_EMITTENTE_BA_INCOERENTE');
```

Se l'azienda non è quella del cliente, l'errore dice:

> «Ordine ORD2026-0000012: l'azienda che emette (Rossi Srl) non è quella del
> cliente (Bianchi Spa, billing account BAC/0000023).»

I nomi sono la ragione sociale completa del soggetto; un'azienda che chi
scrive non può vedere esce col suo numero interno.

---

### ⭐ Da dove nasce: sette copie

Fino al 10 ottobre 2026 la regola era scritta sette volte, una funzione per
tabella (brief `brief-db-guard-emittente-ba-unico`). Sei erano identiche nel
testo e cambiavano solo il codice d'errore; la settima, la commessa, diceva la
stessa cosa su un'altra colonna. Le frasi mostravano nomi di colonna
all'utente («emittente_fiscale_id non corrisponde…») e il log perdeva il
riferimento alla transazione.

Ora la regola sta qui. I sei documenti rispondono con un codice solo,
`E_DOC_EMITTENTE_BA_INCOERENTE`; i sei codici di prima sono ritirati.

---

### 🏢 La commessa: stessa regola, un altro errore

La commessa non la scrive una persona: nasce dal push della fatturazione, e la
sua azienda si deriva sempre dal billing account. Un valore diverso può
arrivare solo da un programma che sbaglia, mai da un utente. Per questo il suo
codice resta `E_COMMESSA_EMITTENTE_BA_INCOERENTE`, di classe **tecnica**: un
errore 500, senza un campo del form da evidenziare (il contesto non porta
`campo`).

E per la commessa il controllo conta più che altrove: la sua azienda è **la
chiave con cui il sistema decide chi può vederla** (visibilità della tabella,
cruscotti, giornale degli eventi). Una commessa con l'azienda sbagliata non dà
errore e non compare sbagliata a video: **sparisce**, e il lavoro non viene
mai fatturato.

---

### 🔀 Quando gira, e perché solo su due colonne

Il controllo scatta alla creazione e quando si toccano **il cliente o
l'azienda**, non a ogni modifica. È quello che tiene i documenti modificabili:
se girasse a ogni modifica, il giorno in cui un cliente cambiasse azienda tutti
i suoi documenti diventerebbero intoccabili, con un errore su una colonna che
nessuno stava cambiando. Quel caso ha il suo presidio altrove: si impedisce di
spostare il cliente, non si congela il lavoro.

**Su bolla e reso gira dopo la normalizzazione** (fascia `_z10_`; sugli altri
documenti `_a10_`). Lì il billing account spesso non arriva da chi scrive: lo
eredita il normalize, dall'ordine o dalla bolla d'origine. Un controllo
anticipato vedrebbe il campo vuoto proprio nei casi da guardare, e
lascerebbe passare.

**Senza billing account non controlla niente.** Dove il billing account è
obbligatorio, è il vincolo della colonna a parlare (si controlla dopo i
trigger); su bolla e reso un documento senza cliente non ha un'azienda con cui
confrontarsi.

---

### 🧪 Test

`db/pgtap/vendite/test-guard-emittente-ba-unico-v1.sql` (montaggio sulle sette
tabelle, ordine e commessa con l'azienda sbagliata, frase, bolla senza cliente,
montaggio errato); `db/pgtap/vendite/test-commesse-emittente-invariante-v1.sql`
(la commessa).
