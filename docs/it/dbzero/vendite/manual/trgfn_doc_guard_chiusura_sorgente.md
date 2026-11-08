## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_doc_guard_chiusura_sorgente`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — le righe che il documento ha spinto in commessa
> * [vendite.ordini](/dbzero/vendite/tabelle/ordini) · [vendite.ddt](/dbzero/vendite/tabelle/ddt) · [vendite.contratti](/dbzero/vendite/tabelle/contratti) — le testate su cui è montato
>
> Approfondimento funzioni:
>
> * [script.fn_check_sorgente_chiudibile](/dbzero/script/funzioni/fn_check_sorgente_chiudibile) — la regola
> * [vendite.trgfn_doc_guard_annullo_con_legami](/dbzero/vendite/funzioni/trgfn_doc_guard_annullo_con_legami) — l'avviso dell'annullo con legami
> * [vendite.fn_documento_ritira_legami](/dbzero/vendite/funzioni/fn_documento_ritira_legami) — il ritiro, dopo la conferma
> * [vendite.fn_riporta_attivita_da_emettere](/dbzero/vendite/funzioni/fn_riporta_attivita_da_emettere) — la via d'uscita
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

**Il freno.** Rifiuta la **chiusura** di un documento che ha spinto in commessa righe già `EMESSA`. Trigger **generico**, fase `_a10_`, `BEFORE UPDATE OF` sulla colonna di stato della testata.

È **metà** della regola. L'altra metà — le righe `NON_EMESSA` — non la fa questo trigger: quelle
righe sono **legami**, l'annullo che le ha davanti chiede conferma (l'avviso
[vendite.trgfn_doc_guard_annullo_con_legami](/dbzero/vendite/funzioni/trgfn_doc_guard_annullo_con_legami),
fascia `_m10_`, che parla **dopo** questo freno) e le ritira il verbo di annullo del documento.
⛔ **Non si fondono**: la cosa che *blocca* e la cosa che *agisce* sono due decisioni diverse, e
tenerle separate è ciò che permette di cambiarne una senza toccare l'altra.

---

### Perché le righe emesse fermano

Sono **in volo verso una fattura**. Ritirarle lascerebbe un'attività fatturabile orfana in viaggio.

⭐ Il rifiuto ha una **via d'uscita**, che il messaggio nomina: il verbo
[«Riporta da emettere»](/dbzero/vendite/funzioni/fn_riporta_attivita_da_emettere) riporta le righe a
`NON_EMESSA`, e da lì il ritiro le prende.

---

### ⭐ Si aggancia al DATO, non a un codice cablato

Non confronta il codice `ANNULLATO`: legge **`is_abortito`** dal vocabolario degli stati del
documento. Tutti i vocabolari delle testate su cui è montato ce l'hanno, ed è la stessa scelta già
fatta per la matrice delle transizioni: **che cosa significhi «chiuso» è una proprietà del dato**,
non del codice.

⚠️ Il giorno che nasce un secondo stato abortito, questo guard lo copre **da solo**.

ℹ️ Interessa **solo l'ingresso** in uno stato abortito: uscirne o restarci non è una chiusura.

---

### Una funzione sola, parametrizzata

| Argomento | Cosa |
| --- | --- |
| `TG_ARGV[0]` | `codice_interno` del tipo del documento in `config.sorgenti` |
| `TG_ARGV[1]` | nome della colonna di stato sulla testata |
| `TG_ARGV[2]` | tabella del vocabolario degli stati (`schema.tabella`) |

Il progetto ha già l'idioma (`dbops.trgfn_child_requires_active_parent`). ⛔ Tre copie
divergerebbero.

⛔ **Fail-closed** su un trigger montato con un codice di tipo inesistente: solleva
(`E_RITIRO_SORGENTE_PARAMETRO_MANCANTE`), invece di restare silenziosamente inerte.

---

### Dov'è montato, e dove no

| Testata | Freno | Perché |
| --- | --- | --- |
| `vendite.ordini` · `vendite.ddt` · `vendite.contratti` | ✅ | non hanno un altro gate sulla chiusura |
| `vendite.preventivi` | ⛔ **no** | ha già il suo — `trgfn_preventivi_guard_annullamento` chiama `fn_check_preventivo_annullabile`, che **delega** alla stessa primitiva e rietichetta col suo codice. Montare anche questo farebbe uscire **due codici** per lo stesso rifiuto |
| `vendite.attivita_consumi` | ⛔ no | non ha una colonna di stato con vocabolario (`stato_calcolo` è un testo senza `is_abortito`) |

⚠️ **L'ordine alfabetico dei `BEFORE ROW`**: `..._a10_guard_chiusura_sorgente_upd` precede
`..._a10_guard_transizione`. È innocuo: i due rifiutano **cose diverse** (uno il lavoro in volo,
l'altro la transizione in sé), quindi qualunque parli per primo dice una cosa vera. Non c'è un
ordine «giusto» da difendere, e infatti nessun test lo asserisce.

---

### ⛔ La chiave è quella del modello

Le righe di commessa dichiarano il documento con la provenienza comune: il tipo, e la chiave del
documento in `sorgente_id` o in `sorgente_uid` secondo il `key_selector` del tipo (`id` per ordine,
bolla e contratto). Il trigger ha in mano il documento, e passa alla regola il tipo con il suo
**id** e il suo **uid**; la regola conta le righe con la regola d'incontro, senza leggere il
`key_selector`.

⚠️ Sbagliare la chiave non darebbe un errore: darebbe **zero motivi**, cioè un freno che lascia
passare tutto.

---

### ⚠️ Il limite, detto

Il conteggio gira sotto **ROW SECURITY** (`commesse_attivita` ha la RLS per emittente). Chi chiude
un documento **senza vedere** le righe di commessa che ne sono nate **non viene fermato** da questo
freno. Le righe `NON_EMESSA` invece le conta l'avviso dell'annullo con un lettore
`SECURITY DEFINER` ([`vendite.fn_documento_legami`](/dbzero/vendite/funzioni/fn_documento_legami)),
che la RLS non acceca.

Qui **non c'è nessuna chiave esterna a fare da rete**, quindi il limite va scritto invece che
dedotto. ⭐ Il caso resta stretto: la commessa eredita l'emittente dal documento, quindi chi vede
l'uno vede normalmente le altre.

---

### Codici errore

* `E_SORGENTE_CON_RIGHE_EMESSE` (classe `CONFLITTO_STATO`) — il documento ha righe di commessa già
  emesse; nella frase c'è il **conteggio**, non gli id.
* `E_RITIRO_SORGENTE_PARAMETRO_MANCANTE` — il trigger è montato con un tipo che non esiste.

---

### Test

* `db/pgtap/vendite/test-ritiro-alla-chiusura-documento-v1.sql` (2, 3)
* `db/pgtap/vendite/test-ordini-guard-transizione-v1.sql` (7, 8)

---

### Note di migrazione

* 2026-08-26 — nasce come metà «freno» della regola del lavoro che non torna indietro
  (brief-db-lavoro-che-non-torna-indietro, lotto L7b).
* 2026-10-11 — il ritiro silenzioso delle righe `NON_EMESSA` in fascia `_z90_` si ritira: le ritira
  il verbo di annullo, dopo l'avviso (brief-db-annullo-documento-con-legami, D-5).
* 2026-11-07 — la chiave passa alle colonne tipizzate del modello: prima il trigger cercava le righe
  con l'uid del documento in testo (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
