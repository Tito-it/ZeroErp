## 📘 Documentazione Concettuale – Tabella `vendite.tipi_doc_fiscale_registri`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale)  
> • [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)  
>
**Approfondimento funzioni:**
>
• [`vendite.fn_get_registro_id`](/dbzero/vendite/funzioni/fn_get_registro_id)
>
### 🎯 Scopo Principale
(latest review 27-01-2026)
La tabella **`vendite.tipi_doc_fiscale_registri`** definisce il mapping
**tipo documento fiscale → registro di fatturazione**, necessario per la
numerazione e la contabilizzazione dei documenti.

---

### Campi chiave

* `tipo_doc_fiscale_id` → tipo documento fiscale (FK).
* `registro_id` → registro di fatturazione associato (FK).
* `codice_interno` → codice di servizio del mapping (opzionale).

---

### Regole principali

* mapping **multiplo** per `tipo_doc_fiscale_id` verso registri diversi.
* la selezione del registro e` determinata da `vendite.fn_get_registro_id`.


---


---

### 🔄 rev 2026-08-18 — il mapping diventa `(tipo_doc, natura) → (registro, serie)`

Brief: `brief-design-note-credito-resi` (slice **N2**, §12.4-bis.3).

```text
PRIMA    (tipo_doc)          →  registro
ORA      (tipo_doc, natura)  →  (registro, serie)
```

Questa tabella **era già** la sede della domanda *«dato un tipo di documento, su
quale registro va?»*. La natura è la seconda metà della stessa domanda, non una
domanda nuova: per questo entra qui e non in una gerarchia a parte.

| Colonna nuova | Ruolo |
|---|---|
| `natura_doc_id` | `NOT NULL DEFAULT FATTURA` → le righe esistenti restano quelle che erano |
| `serie` | nullable: **override** del `serie_default` del registro. `NULL` = vale il default |

⚠️ **La `UNIQUE` è cambiata**, da `(tipo_doc_fiscale_id, registro_id)` a
`(tipo_doc_fiscale_id, natura_doc_id, registro_id)`. Senza, mappare fattura e
nota di credito sullo **stesso** registro con due serie diverse — che è l'altra
metà della scelta — sarebbe stato vietato da un vincolo che non sa della natura.
Il vincolo va allargato **prima** del seed, o il seed non entra.

#### ⭐ È qui che «registro proprio o serie dedicata?» diventa una riga di seed

| Se il seed dice… | Effetto |
|---|---|
| stesso `registro_id`, `serie = 'NC'` | serie a parte **dentro** il registro vendite |
| `registro_id` diverso | **sezionale proprio**, progressivo e `reset_policy` indipendenti |

Entrambe funzionano senza una riga di codice diversa, ed entrambe restano
cambiabili dopo. È la forma che il progetto usa per le scelte che appartengono
all'azienda e non allo sviluppatore — `tipi_reso.riapre_residuo`,
`causali_trasporto.fatturabile`: nessun `IF` cablato, si legge il flag.

#### ⭐ Ogni emittente nasce con le sue righe (dal 18-10-2026)

Prima nessun emittente nasceva col registro delle fatture, e il primo documento
fiscale si fermava su `fn_get_registro_id` con «registro non risolto». Da oggi
(R-BE-14, decisioni D-14a … D-14d di Tid) il provisioning
[`vendite.fn_provision_registri`](/dbzero/vendite/manual/fn_provision_registri)
fa nascere con l'emittente un **registro delle fatture standard** e una riga di
questa tabella per **ogni coppia** (tipo documento attivo, natura attiva) che
non ha ancora un registro. Quali coppie mancano lo dice
[`vendite.fn_coppie_fattura_scoperte`](/dbzero/vendite/manual/fn_coppie_fattura_scoperte).

* uno standard solo per tutte le coppie: chi vuole sezionali separati li divide
  dal CRUD dei registri;
* un emittente configurato a mano riceve lo standard solo per le coppie che non
  ha;
* un tipo documento o una natura che nasce, o si riaccende, si collega da sé
  allo standard di ogni emittente (trigger sui due cataloghi).

⭐ **La nota di debito** (fino al 18-10-2026 senza riga, «nessuno ha deciso su
quale registro numerarla») va sul registro standard, come le altre nature:
deciso da Tid il 18-10-2026. Per un emittente nuovo è numerata insieme alle
fatture; agli emittenti già configurati a mano lo standard nasce apposta.

#### ⛔ Una coppia, un registro, per emittente e utility

Due registri dello **stesso emittente** e della **stessa utility** sulla stessa
coppia (tipo documento, natura) non sono ammessi:
`E_REGISTRO_COPPIA_GIA_COPERTA`. Prima `fn_lookup_registro_id` sceglieva il
primo per id, cioè una scelta decisa da un numero. L'emittente e l'utility stanno
sul registro, non su questa riga, quindi un indice unico non basta: lo controllano
due guard, qui (all'inserimento o al cambio di tipo, natura o registro) e sul
registro (al cambio di emittente o utility). Un registro di **una** utility
accanto a quello di tutte resta ammesso: il lookup preferisce il più specifico.

---

{% include-markdown "signature-core.md" %}
