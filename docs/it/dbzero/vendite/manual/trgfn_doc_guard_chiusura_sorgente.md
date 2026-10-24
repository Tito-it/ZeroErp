## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_doc_guard_chiusura_sorgente`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
> • [vendite.ordini](/dbzero/vendite/tabelle/ordini) · [vendite.ddt](/dbzero/vendite/tabelle/ddt) · [vendite.contratti](/dbzero/vendite/tabelle/contratti)  
>
**Approfondimento funzioni:**
>
• [script.fn_check_sorgente_chiudibile](/dbzero/script/funzioni/fn_check_sorgente_chiudibile)  
> • [vendite.trgfn_doc_guard_annullo_con_legami](/dbzero/vendite/funzioni/trgfn_doc_guard_annullo_con_legami) — l'avviso dell'annullo con legami  
> • [vendite.fn_documento_ritira_legami](/dbzero/vendite/funzioni/fn_documento_ritira_legami) — il ritiro, dopo la conferma  

---

### 🎯 Scopo Principale
(latest review 26-08-2026)

**Il freno.** Rifiuta la **chiusura** di un documento che ha spinto in commessa
righe già `EMESSA`. Trigger **generico**, fase `_a10_`, `BEFORE UPDATE OF` sulla
colonna di stato della testata.

> È **metà** della regola. L'altra metà — le righe `NON_EMESSA`, che il documento
> **ritira** — dal 2026-10-11 non è più un motore silenzioso in fase `_z90_`: le
> righe `NON_EMESSA` sono **legami**, l'annullo che le ha davanti chiede conferma
> (l'avviso [vendite.trgfn_doc_guard_annullo_con_legami](/dbzero/vendite/funzioni/trgfn_doc_guard_annullo_con_legami), fascia `_m10_`, che parla **dopo** questo freno) e le
> ritira il verbo di annullo del documento (brief-db-annullo-documento-con-legami, D-5).
> ⛔ **Non si fondono**: la cosa che *blocca* e la cosa che *agisce* sono due
> decisioni diverse, e tenerle separate è ciò che permette di cambiarne una senza
> toccare l'altra.

---

### Perché le righe emesse fermano

Sono **in volo verso una fattura**. Ritirarle lascerebbe un'attività fatturabile
orfana in viaggio — cioè esattamente il **residuo** che il cantiere esiste per
chiudere.

⭐ E dal verbo
[«Riporta da emettere»](/dbzero/vendite/funzioni/fn_riporta_attivita_da_emettere)
il rifiuto ha una **via d'uscita**, che il messaggio nomina. Prima non ce n'era
una, ed è precisamente ciò che `E_PREV_ANNULLA_COMMESSA_EMESSA` era: un vicolo
cieco.

---

### ⭐ Si aggancia al DATO, non a un codice cablato

Non confronta `codice_interno = 'ANNULLATO'`: legge **`is_abortito`** dal
vocabolario degli stati del documento.

Tutti e quattro i vocabolari ce l'hanno — `config.stati_doc_preventivi`,
`_ordini`, `_ddt`, `_contratti` — ed è la stessa scelta già fatta per la matrice
delle transizioni: **cosa significhi «chiuso» è una proprietà del dato**, non del
codice.

⚠️ Il giorno che nasce un secondo stato abortito, questo guard lo copre **da
solo**. Con un codice cablato non l'avrebbe coperto, e in silenzio.

ℹ️ Interessa **solo l'ingresso** in uno stato abortito: uscirne o restarci non è
una chiusura.

---

### Una funzione sola, parametrizzata

| Argomento | Cosa |
| --- | --- |
| `TG_ARGV[0]` | `codice_interno` della sorgente in `config.sorgenti` |
| `TG_ARGV[1]` | nome della colonna di stato sulla testata |
| `TG_ARGV[2]` | tabella del vocabolario degli stati (`schema.tabella`) |

Il progetto ha già l'idioma (`dbops.trgfn_child_requires_active_parent`).
⛔ Quattro copie divergerebbero.

⛔ **Fail-closed** su un trigger montato con un codice sorgente inesistente:
solleva, invece di restare silenziosamente inerte.

---

### Dov'è montato, e dove no

| Testata | Freno | Perché |
| --- | --- | --- |
| `vendite.ordini` · `vendite.ddt` · `vendite.contratti` | ✅ | non hanno un altro gate sulla chiusura |
| `vendite.preventivi` | ⛔ **no** | ha già il suo — `trgfn_preventivi_guard_annullamento` chiama `fn_check_preventivo_annullabile`, che **delega** alla stessa primitiva e rietichetta col codice deciso da Q-9. Montare anche questo farebbe uscire **due codici** per lo stesso rifiuto |
| `vendite.attivita_consumi` | ⛔ no | non ha una colonna di stato con vocabolario (`stato_calcolo` è un varchar senza `is_abortito`), ed è un flusso non ancora acceso |

⚠️ **L'ordine alfabetico dei `BEFORE ROW`**: `..._a10_guard_chiusura_sorgente_upd`
precede `..._a10_guard_transizione`. È innocuo, e vale la pena dire perché — i
due rifiutano **cose diverse** (uno il lavoro in volo, l'altro la transizione in
sé), quindi qualunque parli per primo dice una cosa vera. Non c'è un ordine
«giusto» da difendere, e infatti nessun test lo asserisce.

---

### ⛔ La chiave è `NEW.uid::text`

È ciò che le cinque `fn_list_*_da_pushare` scrivono in
`commesse_attivita.sorgente_uid`, per **ogni** sorgente.

⚠️ **Non** è la chiave di `vendite.commesse_sorgenti`, che varia (uid per il
preventivo, id per l'ordine): confonderle non darebbe errore, darebbe **zero
motivi** — cioè un freno che lascia passare tutto.

---

### ⚠️ Il limite, detto

Il conteggio gira sotto **ROW SECURITY** (`commesse_attivita` ha la RLS per
emittente). Chi chiude un documento **senza vedere** le righe di commessa che ne
sono nate **non viene fermato** da questo freno. Le righe `NON_EMESSA` invece le
conta l'avviso dell'annullo con un lettore `SECURITY DEFINER`
([`vendite.fn_documento_legami`](/dbzero/vendite/funzioni/fn_documento_legami)),
che la RLS non acceca (rev 2026-10-11).

⛔ È il comportamento di **oggi**, non un peggioramento — ma qui **non c'è
nessuna chiave esterna a fare da rete**, quindi va scritto invece che dedotto.
⭐ Il caso resta stretto: la commessa eredita l'emittente dal documento, quindi
chi vede l'uno vede normalmente le altre.

---

### Note operative

* Errore sollevato: **`E_SORGENTE_CON_RIGHE_EMESSE`** (classe
  `CONFLITTO_STATO`), col **conteggio** nella frase e non gli id.
* Test: `db/pgtap/vendite/test-ritiro-alla-chiusura-documento-v1.sql` (2, 3) e
  `test-ordini-guard-transizione-v1.sql` (7, 8).
* Cantiere: `brief-db-lavoro-che-non-torna-indietro.md`, lotto L7b / Q-5′ strada A.

---

{% include-markdown "signature-core.md" %}
