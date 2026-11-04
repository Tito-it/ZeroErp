## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_commessa_attivita`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — la riga che la fixture fa scrivere
>
> Approfondimento funzioni:
>
> * [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita) — la madre che scrive l'attività
> * [script.fn_segment_key](/dbzero/script/funzioni/fn_segment_key) — il solo costruttore della chiave del segmento
> * [script.fn_segment_key_sorgente](/dbzero/script/funzioni/fn_segment_key_sorgente) — chi legge il documento dalla chiave
> * [vendite.trgfn_attivita_guard_listino_riga](/dbzero/vendite/funzioni/trgfn_attivita_guard_listino_riga) — la coerenza fra articolo, riga e versione di listino
> * [dbops.fn_pgtap_crea_commessa](/dbzero/dbops/funzioni/fn_pgtap_crea_commessa) — la commessa su cui scriverla
> * [dbops.fn_pgtap_crea_articolo](/dbzero/dbops/funzioni/fn_pgtap_crea_articolo) — l'articolo, quando il test non lo dà
> * [vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa) — l'emissione, che resta al test
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — dove si sceglie una fixture

---

### 🎯 Scopo Principale

Fixture pgTAP: **un'attività su una commessa già costruita**, scritta dalla madre del dominio. Di
default è approvata e non emessa, quantità 1, prezzo fisso 10, con la commessa come sorgente: la
forma da cui l'emissione delle attività fatturabili la prende.

Un'attività di commessa si scriveva a mano in molti pgTAP, con articolo, unità di misura e istanza
pescati dal database; altri chiamavano la madre ricopiando una ventina di argomenti. Ora ha una
sede.

---

### ⭐ Il confine: la fixture decide il contesto, il chiamante l'oggetto

La fixture decide l'**istanza di utility** (quella del conto di fatturazione della commessa) e il
**periodo** di default (quello della commessa, o il mese corrente). Il chiamante sceglie il
**prezzo**, l'**articolo**, la **provenienza del prezzo** (versione e riga di listino), la
**sorgente**, la **quantità**, gli **stati** di approvazione ed emissione e, se vuole, il periodo.
Tutto il resto (tipo movimento, rettifiche, oneri, contratto, promo) resta alla madre: una
fixture con tutti i parametri della madre sarebbe una seconda madre.

---

### L'articolo e il listino

* **Senza articolo** la fixture ne costruisce uno, non gestito a magazzino: su un database
  ricostruito il catalogo è vuoto. Un articolo con certi flag (la tipologia di un listino, una
  natura) il chiamante lo costruisce **prima** e lo passa: un articolo usato non cambia più la
  struttura, e quello costruito qui è già usato quando il test lo riceve.
* **Con una riga di listino**, l'unità di misura è la sua, e articolo e versione, se mancano, si
  prendono da lei.
* **Con la sola versione** l'attività è registrata sotto quella versione, senza riga di listino.
* ⚠️ Una riga di listino **invisibile** a chi agisce (di un'altra azienda) non ferma la fixture se
  il chiamante dà anche articolo e versione: l'unità di misura viene dall'articolo e giudica il
  guard, come nel percorso del backend.
* ⛔ La **coerenza** fra articolo, riga e versione non la controlla la fixture: la tiene la
  tabella, per tutti.

Una commessa, un articolo o una riga di listino che non esistono fermano la fixture con un errore
che li nomina, invece di far morire la madre su un valore vuoto.

---

### La sorgente e la chiave del segmento

* **Con una sorgente** (codice del documento, sua chiave, riga) l'attività è quella che la push di
  una riga di quel documento avrebbe scritto. La chiave del segmento la compone **il dominio**, con
  `script.fn_segment_key`: ricopiarne il formato a mano si rompe quando la grammatica dei documenti
  cambia. Una sorgente che non esiste, o senza la chiave del documento, ferma la fixture.
* ⚠️ **Senza sorgente** la sorgente è la commessa stessa, e la chiave del segmento è una sigla
  casuale con prefisso `PGT-SEG-`, scritta dalla fixture e **fuori dalla grammatica** delle chiavi:
  chi legge il documento dalla chiave (`script.fn_segment_key_sorgente`) vi legge la sigla intera,
  non `COMMESSA` né `MAN`.

---

### Che cosa non fa

* **non emette** e non lega l'attività a una fattura: lo stato di emissione lo dichiara il test,
  il lavoro della pipeline resta fuori. La catena dell'applicazione è commessa pronta per la
  fatturazione, poi `vendite.fn_emit_attivita_fatturabili_da_commessa`;
* nessuna promo, contratto o variazione: il prezzo è uno snapshot fisso.

Esce con i vincoli richiusi (`IMMEDIATE`).

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-crea-commessa-attivita-v1.sql` — l'attività è sulla commessa,
  approvata e non emessa, con l'istanza del conto e la competenza della commessa; il prezzo è
  quello chiesto; l'emissione la prende; una commessa inesistente parla; l'articolo passato arriva
  coi suoi flag; la riga di listino dà la sua unità di misura, articolo e versione; la sola
  versione registra l'attività senza riga; con la sorgente la chiave è quella del costruttore del
  dominio, e quantità, stati e periodo sono quelli dichiarati; una sorgente senza chiave parla.

---

### Note di migrazione

* 2026-10-07 — nasce con il terzo giro delle fixture che costruiscono documenti
  (`brief-db-fixture-rls-documenti-costruiti`).
* 2026-10-15 — articolo, versione e riga di listino li sceglie il chiamante (richiesta del team BE).
* 2026-10-16 — una riga di listino invisibile non ferma più la fixture se il chiamante dà articolo e
  versione: prima il guard non veniva mai raggiunto, e un test era verde da owner e rosso come
  applicazione.
* 2026-10-24 — sorgente, quantità, stati e periodo in coda; la chiave la compone il dominio invece
  della chiave scritta a mano che dieci pgTAP ricopiavano (`brief-modello-documento-vendita`,
  §4-octies).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
