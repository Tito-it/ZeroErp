## 📘 Documentazione Concettuale – Funzione `vendite.fn_crea_revisione_offerta(...)`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
> [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> [vendite.offerte_commerciali_eccezioni](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni)
> [vendite.offerte_commerciali_eccezioni_componenti](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni_componenti)
> [vendite.offerte_commerciali_utilities](/dbzero/vendite/tabelle/offerte_commerciali_utilities)
> [config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte)
>
> Trigger correlati:
> [vendite.trgfn_offerte_commerciali_revisione](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_revisione)
> [vendite.trgfn_offerte_commerciali_guard_transizione](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_guard_transizione)
> [vendite.trgfn_offerte_commerciali_gen_codice](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_gen_codice)
>
> Funzioni correlate:
> [vendite.fn_push_offerta_a_contratto](/dbzero/vendite/funzioni/fn_push_offerta_a_contratto)
>
> Contesto di sviluppo:
> [Brief DB offerte commerciali — Step 7](/dev/work-done/analisi-offerta-commerciale-db)

---

### 🎯 Scopo Principale

(rev 2026-05-25; ultima revisione 2026-10-26)

`vendite.fn_crea_revisione_offerta(p_offerta_id, p_user)` crea una **nuova
revisione** (rev.N+1) di un'offerta commerciale, copiando testata, eccezioni
attive coi loro componenti e utility (1:1). Il pattern riusa concettualmente
`fn_crea_revisione_preventivo` (§6.3 analisi offerta).

---

### Regole principali

- **Stato ammesso**: solo offerte in stato `EMESSA`. BOZZA si modifica
  direttamente; ACCETTATA/RIFIUTATA/SUPERATA/ANNULLATA sono terminali
  immutabili e non revisionabili.
- **`uid` e codice** generati ex novo: `uid` da default `uuidv7()`, codice
  `OFC-NNNNNNN` dal trigger `trgfn_offerte_commerciali_gen_codice` (BEFORE
  INSERT, Step 5). Non vengono ereditati dalla rev.N.
- **`revisione_numero`** = rev.N.`revisione_numero` + 1.
- **`revisione_padre_id`** = `p_offerta_id` (FK self alla rev.N).
- **Stato iniziale rev.N+1**: `BOZZA`.
- **Timestamp di transizione** (`data_emissione`, `data_accettazione`,
  `data_rifiuto`, `data_annullamento`) restano `NULL` sulla rev.N+1: vengono
  valorizzati al momento delle proprie future transizioni.
- **Eccezioni copiate**: solo righe con `attivo IS TRUE` (1:1, senza
  reinterpretazione).
- **Componenti copiati** (dal 2026-10-05): per ogni eccezione copiata, **tutti**
  i suoi componenti — anche gli opzionali spenti, che sono una scelta
  dell'offerta — agganciati alla riga nuova, con stato e pratica di
  approvazione 1:1, salvo lo spento in attesa, che arriva senza marca (dal
  2026-10-08, sotto). Vedi la revisione del 2026-10-05 qui sotto.
- **Stato approvazione prezzo carry-forward** (rev2, 2026-06-01): le colonne
  `stato_approvazione_prezzo` e `pratica_approvazione_prezzo_id` delle eccezioni
  (aggiunte da `20260601-01`) sono copiate **1:1** nella nuova revisione, **non**
  azzerate. Razionale: i gate L1/L2/L3 scattano solo sull'edit BE della riga (non
  all'emissione/push), quindi lo stato approvazione è l'unico marcatore persistente
  che un prezzo fuori-soglia è autorizzato/in attesa; azzerarlo lascerebbe un prezzo
  fuori-policy non marcato, che potrebbe arrivare al contratto senza controllo. Il
  carry-forward preserva l'invariante "prezzo fuori-policy sempre marcato". L'edit
  successivo sulla nuova revisione resta governato dal guard
  [`script.trgfn_righe_guard_pending`](/dbzero/script/funzioni/trgfn_righe_guard_pending)
  (blocco struttura mentre `PENDING`). *Caveat lifecycle pratica su `PENDING` in
  revisione SUPERATA: di competenza del dominio approvazioni (livello applicativo).*
- **Utility copiata**: 1:1, un solo record per offerta (UNIQUE `offerta_id`).
- **Marcatura padre SUPERATA**: gestita automaticamente dal trigger
  `trg_offerte_commerciali_z90_revisione_ins` (AFTER INSERT), non da questa
  funzione. Dal 2026-10-26 il trigger chiama la proiezione
  [`vendite.fn_offerta_proietta_stato_revisione`](/dbzero/vendite/funzioni/fn_offerta_proietta_stato_revisione),
  che scrive lo stato del padre attraverso la porta (lo stato si cambia solo dai
  verbi). La transizione `EMESSA → SUPERATA` è di processo nella matrice.

---

### Parametri

| Parametro     | Tipo                                      | Note                                        |
| ------------- | ----------------------------------------- | ------------------------------------------- |
| `p_offerta_id` | `vendite.offerte_commerciali.id%TYPE`    | ID offerta da revisionare. Obbligatorio, > 0. |
| `p_user`      | `vendite.offerte_commerciali.user_update%TYPE` | Utente che esegue l'operazione (audit).     |

---

### 📦 Output

| Campo        | Tipo     | Descrizione                     |
| ------------ | -------- | ------------------------------- |
| `RETURNS BIGINT` | bigint | ID della nuova revisione (rev.N+1). |

---

### Codici errore

| Codice                                  | Quando                                                          |
| --------------------------------------- | --------------------------------------------------------------- |
| `E_PARAMETRO_INVALIDO`                  | `p_offerta_id` NULL o <= 0; offerta non trovata.                |
| `E_OFFERTA_REVISIONE_STATO_NON_AMMESSO` | Stato corrente diverso da `EMESSA`.                             |
| `E_CONFIG_MANCANTE`                     | Stato `BOZZA` non trovato in `config.stati_doc_offerte`.        |

---

### Interazione con i trigger

La catena al momento dell'INSERT della rev.N+1:

```text
fn_crea_revisione_offerta
  └─ INSERT testata rev.N+1 (BOZZA)
       ├─ BEFORE INSERT: trgfn_offerte_commerciali_gen_codice → assegna OFC-*
       └─ AFTER INSERT:  trg_offerte_commerciali_z90_revisione_ins
                           └─ fn_offerta_proietta_stato_revisione(rev.N)
                                └─ fn_doc_scrivi_stato: rev.N → SUPERATA, attraverso la porta
                                     └─ BEFORE UPDATE: trgfn_offerte_commerciali_guard_transizione
                                                         └─ controlla EMESSA→SUPERATA → ammessa ✓
```

---

### Esempio d'uso

```sql
-- Crea rev.2 dell'offerta 42 (deve essere in stato EMESSA)
SELECT vendite.fn_crea_revisione_offerta(42, 'operatore1');
-- Restituisce: 99  (id della nuova rev.2 in stato BOZZA)
-- L'offerta 42 passa automaticamente a SUPERATA.
```

---

### Rev 2026-09-24 — nessuna revisione con un prezzo in attesa

(`20260924-35`, decisione di Tid.) Dopo il controllo sullo stato, la funzione rifiuta la
revisione se l'offerta ha eccezioni o loro componenti attivi con un prezzo **in attesa**:
solleva il primo motivo di
[script.fn_check_prezzi_in_attesa](/dbzero/script/funzioni/fn_check_prezzi_in_attesa)
(`E_DOC_PREZZO_PENDENTE`). Stessa ragione della gemella del preventivo: un'eccezione in attesa
ricopiata restava legata alla pratica della versione vecchia. La copia di approvato e
rifiutato resta (`20260601-05`). Nello stesso changeSet firma e risultato sono ancorati con
`%TYPE` e `SECURITY INVOKER` è esplicito.

---

### Rev 2026-10-05 — la revisione porta con sé i componenti

(`20261005-19`, decisione di Tid; brief `brief-db-righe-esclusione-solo-non-si-vende`
§8.2 B1.) Fino a questa data la funzione copiava le righe ma non i loro
**componenti**, e un suo commento diceva che le righe dell'offerta «non hanno
tabelle figlie». Le hanno: i componenti di una riga composita (un bundle, un
kit) stanno in `vendite.offerte_commerciali_eccezioni_componenti`. Una
revisione di un'offerta con un bundle nasceva quindi con la riga e senza i suoi
pezzi, e il push verso il contratto — che i componenti li copia — la portava
così nel contratto.

Ora le righe si copiano **una alla volta**, e per ciascuna i suoi componenti
sulla riga appena nata. È la stessa forma del push: la corrispondenza fra riga
vecchia e riga nuova la dà l'inserimento stesso, non l'ordine in cui il database
assegna i numeri.

* Si copiano **tutti** i componenti, anche quelli spenti: spegnere un
  componente opzionale è una scelta di chi ha fatto l'offerta (quelli
  obbligatori non si possono spegnere), e la revisione è la stessa offerta.
* Lo stato di approvazione del prezzo viaggia 1:1, come sulle righe. Un
  componente in attesa non arriva fin qui: la revisione si rifiuta prima
  (revisione del 2026-09-24).
* I trigger del componente lavorano come alla nascita: la quantità si ricalcola
  dalla riga madre, e il prezzo della madre dai componenti attivi — lo stesso
  della versione precedente.

⚠️ La gemella del preventivo (`fn_crea_revisione_preventivo`) copiava solo i
componenti **attivi**: asimmetria chiusa il 2026-10-08 (`20261008-35`), ora le
due copiano tutti i componenti.

Presidio: `db/pgtap/vendite/test-righe-gemelle-secondo-giro-v1.sql` (test 12-14,
19).

---

### Rev 2026-10-08 — un componente spento in attesa si copia senza marca

Il controllo «prima l'esito, poi la revisione» guarda i soli componenti **attivi**, ed è
giusto: un componente spento non deve bloccare la revisione per sempre. Ma lo spento si
copia, e copiato con la sua marca `PENDING` portava nella nuova revisione un prezzo in
attesa legato alla pratica della revisione vecchia — riacceso, il caso che il controllo
aveva chiuso per le righe.

Dal `20261008-88` (D-3 di Tid, `brief-db-righe-e-componenti-debiti-residui` §3) un componente
**spento in attesa** arriva sulla nuova revisione **senza marca né pratica**. Approvato e
rifiutato si copiano come prima; un componente attivo in attesa continua a fermare la
revisione. Le altre due strade bloccavano per sempre: sui componenti nessun verbo dà un
esito, e i componenti di un documento fuori bozza sono chiusi.

⚠️ Debito dichiarato: quando si riaccende, quel prezzo dovrebbe tornare a chiedere
l'approvazione. È del ciclo di approvazione dei componenti, che oggi non esiste. La
gemella è [fn_crea_revisione_preventivo](/dbzero/vendite/funzioni/fn_crea_revisione_preventivo).

Presidio: `db/pgtap/vendite/test-righe-e-componenti-debiti-residui-v1.sql` (test 21-24).

---

{% include-markdown "signature-core.md" %}
