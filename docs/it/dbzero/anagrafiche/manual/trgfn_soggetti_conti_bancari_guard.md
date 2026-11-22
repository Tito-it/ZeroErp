## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_conti_bancari_guard`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_conti_bancari) — il legame del soggetto, su cui è montata
> * [anagrafiche.conti_bancari](/dbzero/anagrafiche/tabelle/conti_bancari) — il registro, da cui legge lo stato del conto
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_soggetti_ruoli_conti_bancari_guard](/dbzero/anagrafiche/funzioni/trgfn_soggetti_ruoli_conti_bancari_guard) — la gemella, sul legame del ruolo
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — lo stesso controllo, al COMMIT
> * [script.trgfn_guard_date_validita](/dbzero/script/funzioni/trgfn_guard_date_validita) — il controllo delle date del legame
>
> Guide:
>
> * [Gestione dei conti bancari](/guide/gestione-conti-bancari) — i due legami e la scelta del conto

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_conti_bancari_guard` rifiuta un legame fra un soggetto e un conto spento: un conto tolto
dall'uso non si lega a nessuno.

---

### Il conto è attivo

Prima di ogni nascita e di ogni modifica del legame, qualunque colonna cambi, il trigger legge lo stato del conto nel
registro. Un conto spento, o che non esiste, è rifiutato (`E_CONTO_BANCARIO`, sul campo `conto_bancario_id`): per il
conto inesistente il rifiuto arriva prima di quello della chiave esterna.

Il verso opposto non è suo: un conto legato non si spegne, e lo impedisce il trigger sullo spegnimento del conto.
Così un legame su un conto spento non esiste mai, e la modifica di un legame non trova mai il conto spento.

Il trigger fa solo questo. Le date del legame (la fine che non precede l'inizio) le controlla
`script.trgfn_guard_date_validita`, che il legame ha montato a parte; il soggetto attivo lo controlla un trigger
differito, al COMMIT.

---

### ⚠️ Che cosa oggi non copre

* **Lo stesso controllo sta in due sedi.** Il legame ha anche un controllo differito che pretende il conto attivo al
  COMMIT: il guard parla prima della scrittura, e quello differito non parla mai per primo.

---

### Codici errore

* `E_CONTO_BANCARIO` — il conto del legame è spento o non esiste.

---

### Test

* `db/pgtap/dbops/test-punti-canale-campo-v1.sql` — il rifiuto dichiara il campo `conto_bancario_id`. Nessun test prova
  il rifiuto su un conto spento.

---

### Note di migrazione

* 2026-09-23 — il controllo delle date passa a `script.trgfn_guard_date_validita`, la sede comune per le tabelle con
  validità: qui resta il solo conto attivo.

---

{% include-markdown "signature-core.md" %}
