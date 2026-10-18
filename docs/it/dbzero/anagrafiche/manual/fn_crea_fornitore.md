## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_fornitore()`

> 👀 **Vedi anche**
>
> [anagrafiche.fornitori](/dbzero/anagrafiche/manual/fornitori) ·
> [anagrafiche.fn_crea_contatto](/dbzero/anagrafiche/manual/fn_crea_contatto) ·
> [anagrafiche.fn_crea_indirizzi_ruolo](/dbzero/anagrafiche/manual/fn_crea_indirizzi_ruolo)

### 🎯 Scopo
(18-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, 2b-1 lotto 4)

**Fare di un soggetto un fornitore**, in un'operazione sola: il ruolo
fornitore del soggetto (creato se manca), la scheda del fornitore, il suo
contatto e i suoi indirizzi.

È la sede unica della creazione: la usano il backend (dal drawer dei
fornitori), i pgTAP e il provisioning dei dati di sviluppo.

### I campi

* **La scheda**: facoltativi `codice`, valuta, modalità e termine di
  pagamento, giorni, fine mese, split payment, ritenuta d'acconto e aliquota,
  regime fiscale, bollo, canale e PEC della fatturazione elettronica, rating,
  scadenza della qualifica, note. Quelli assenti (o vuoti) prendono il
  default; senza codice lo genera il sistema dei codici. Un campo diverso è
  rifiutato col suo nome (`E_CAMPO_NON_AMMESSO`).
* **Lo stato non è un campo**: un fornitore nasce sempre **in verifica**
  (`VE`). Qualificarlo è un passaggio di stato successivo.
* **Il contatto**: facoltativo. Se c'è, valgono le regole del contatto
  (nominativo e tipo obbligatori).
* **Gli indirizzi**: un elenco, anche vuoto. Basta il primo: gli altri tipi
  obbligatori per un fornitore (sede legale, fatturazione) si copiano da lui.
  Se il ruolo esisteva già, i tipi che ha non si riscrivono.

### Quando si controlla la completezza

Un fornitore senza gli indirizzi obbligatori è rifiutato **al commit**, non
subito: il ruolo e i suoi indirizzi nascono nella stessa transazione.

### Che cosa non controlla

* **Il permesso**: nel dominio anagrafiche lo decide il backend.
* I **duplicati** (un secondo fornitore sullo stesso soggetto, un codice già
  usato) escono dai vincoli della tabella, col loro nome.

### Test

`db/pgtap/anagrafiche/test-fn-crea-fornitore-v1.sql`.

---

{% include-markdown "signature-core.md" %}
