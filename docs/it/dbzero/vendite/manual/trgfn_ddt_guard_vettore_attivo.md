## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_ddt_guard_vettore_attivo`

> **Ultimo aggiornamento**: 27 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.ddt](/dbzero/vendite/tabelle/ddt) — la tabella su cui il guard è montato
> * [anagrafiche.vettori](/dbzero/anagrafiche/tabelle/vettori) — il vettore, con il suo stato
> * [dbops.automazione_attivo_eccezioni](/dbzero/dbops/tabelle/automazione_attivo_eccezioni) — perché il guard sta al posto del require dell'automazione
>
> Guide:
>
> * [Gestione DDT](/guide/gestione-ddt) — la bolla e il suo vettore
> * [Framework di automazione DB](/guide/automazione-db) — §4.2, le eccezioni

---

### 🎯 Scopo Principale

La bolla che sceglie un vettore lo vuole acceso: quando nasce con un vettore, o quando il vettore cambia.

---

### Come decide

È montata `BEFORE INSERT OR UPDATE OF vettore_soggetto_ruolo_id` su `vendite.ddt`
(`trg_ddt_a10_guard_vettore_attivo_ins_upd`). Non dice niente quando il vettore manca, e niente quando una modifica
lascia il vettore com'era.

⭐ **La bolla è storia.** Un vettore spento dopo resta sulle bolle che lo hanno già, e quelle bolle si modificano
come prima. È il motivo per cui la chiave esterna della bolla verso `anagrafiche.vettori` è un'eccezione
dell'automazione dello spegnimento: il suo require rigiudicherebbe il vettore a ogni modifica, e il suo block non
lascerebbe mai spegnere un vettore che ha portato una bolla. Questo guard tiene la sola metà che serve.

Che il valore sia davvero un vettore lo dice la chiave esterna, a fine istruzione: un ruolo che non è un vettore
il guard lo lascia passare, e lo rifiuta il vincolo. Dopo l'emissione il vettore non si cambia, e parla prima il
lucchetto della testata.

La bolla di riconsegna eredita il vettore della bolla d'origine solo se è acceso
(`vendite.fn_genera_ddt_riconsegna`): spento, nasce col vettore vuoto, e questo guard non ha niente da rifiutare.

---

### Codici errore

* `E_DDT_VETTORE_NON_ATTIVO` (`CONFLITTO_STATO`) — il vettore scelto è spento.

---

### Test

* `db/pgtap/anagrafiche/test-ruoli-impresa-psp-vettore-gestore-v1.sql` — il vettore che ha portato una bolla si
  spegne, la bolla si modifica ancora, una bolla non sceglie un vettore spento, un ruolo che non è un vettore lo
  rifiuta la chiave esterna.

---

{% include-markdown "signature-core.md" %}
