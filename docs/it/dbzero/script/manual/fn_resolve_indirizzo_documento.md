## 📘 Documentazione Concettuale – Funzione `script.fn_resolve_indirizzo_documento`

> 👀 **Vedi anche**
>
> **Tabelle:**
>
> • [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)
> • [config.tipi_ruolo_tipi_indirizzo](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo) — la matrice dei tipi ammessi per ruolo
>
> **Funzioni:**
>
> • [script.fn_snapshot_indirizzo](/dbzero/script/funzioni/fn_snapshot_indirizzo) — layer RUOLO
> • [script.fn_snapshot_indirizzo_soggetto](/dbzero/script/funzioni/fn_snapshot_indirizzo_soggetto) — layer SOGGETTO
> • [vendite.fn_snapshot_indirizzi_fattura](/dbzero/vendite/funzioni/fn_snapshot_indirizzi_fattura) — primo consumatore

---
### 🎯 Scopo Principale
(latest review 02-08-2026)

`script.fn_resolve_indirizzo_documento` risponde alla domanda «qual è
l'indirizzo di tipo X da stampare su un documento per questo soggetto?».

È la **catena unica** di risoluzione degli indirizzi documentali, estratta perché
la stessa regola serve alla fattura e ai documenti fratelli — e una regola scritta
due volte è una regola che diverge.

---

### 🪜 Due layer, non uno

```text
layer RUOLO      →  se c'è, vince
   ├─ indirizzo dell'ISTANZA specifica   ← ha la precedenza
   └─ indirizzo generico del ruolo
layer SOGGETTO   →  fallback
```

**Il layer non è uno solo, ed è l'errore più comune su quest'area.** Una vista che
legge il solo layer RUOLO (`WHERE scope = 'RUOLO'`) risponde «nessun indirizzo»
per un soggetto che ce l'ha eccome — sul proprio layer. È il difetto che ha
prodotto la sede legale vuota sulla stampa, e vale **identico** sulla riga del
cliente: un cliente con l'indirizzo sul solo layer SOGGETTO farebbe fallire la
fattura pur avendone uno.

---

### 🎯 Precedenza per istanza, e perché è deterministica

Dentro il layer RUOLO, l'indirizzo legato all'**istanza utility** del documento
batte quello generico.

Il determinismo non viene da un `LIMIT 1` messo lì per sicurezza: viene da **due
unique parziali** che garantiscono al massimo due candidati — uno per istanza e
uno generico. L'`ORDER BY (istanza IS NULL)` sceglie fra quei due, e non fra un
insieme di dimensione ignota.

> ⚠️ La differenza è sostanziale: un `LIMIT 1` su un insieme non vincolato
> restituisce **una** riga, non **la** riga. Qui il vincolo è nel modello.

---

### Assenza = zero righe

Come le due funzioni di snapshot che invoca, non solleva su assenza. Decidere se
un indirizzo mancante sia un problema spetta al chiamante — ed è quello che fa il
guard di uscita da DRAFT, sulla base della **matrice** dei tipi obbligatori e non
su un tipo cablato nel codice.

---

### ⚠️ Due trappole per chi scrive fixture

Misurate collaudando, e non ovvie:

- **`CON` non è inseribile sul ruolo cliente**: è ammesso al solo `tipo_ruolo = 8`,
  quindi il guard `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo` respinge. Per
  esercitare quel tipo serve il layer SOGGETTO;
- un indirizzo **non normalizzato** deve avere la forma che il suo stato
  vuole (guard `trgfn_indirizzi_guard_forma_libera`): per l'Italia la coppia
  comune/CAP del catalogo, per uno stato senza catalogo la `locality`. Nelle
  fixture la dà `dbops.fn_pgtap_indirizzo_libero_forma`.

---
{% include-markdown "signature-core.md" %}
