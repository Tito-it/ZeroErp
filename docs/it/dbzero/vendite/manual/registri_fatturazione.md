## 📘 Documentazione Concettuale – Tabella `vendite.registri_fatturazione`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.registri_fatturazione_progressivi](/dbzero/vendite/tabelle/registri_fatturazione_progressivi)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale)  
> • [vendite.tipi_doc_fiscale_registri](/dbzero/vendite/manual/tipi_doc_fiscale_registri)  
> • [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)  
>
### 🎯 Scopo Principale
(latest review 26-01-2026)
`vendite.registri_fatturazione` definisce i **registri fiscali di emissione**:
serie, regole di reset e collegamento all’emittente fiscale. Ogni fattura
si aggancia a un registro, che governa numerazione e perimetro fiscale.

---

### Campi chiave (semantica)

* **Identita`**: `id`, `uid`, `codice`.
* **Emittente**: `emittente_soggetto_ruolo_id` (ruolo fiscale che emette).
* **Utility**: `utility_id` (opzionale, per registri specifici di utility).
* **Numerazione**: `serie_default`, `reset_policy` (es. ANNUALE).
* **Stato**: `attivo`.
* **Governance**: `meta`, `storicizza`, `tx_id`, audit.

---

### Relazioni principali

* `vendite.fatture.registro_id` → determina la numerazione.
* `vendite.registri_fatturazione_progressivi` mantiene i contatori per anno/mese/serie.
* `vendite.tipi_doc_fiscale_registri` associa il registro al tipo documento fiscale.

---

### Nota sulla FK emittente

La FK su `emittente_soggetto_ruolo_id` e` **coerente** con un modello multi‑emittente:
ogni registro appartiene a un emittente fiscale specifico. In presenza di piu`
aziende abilitate, la separazione dei registri evita collisioni di numerazione.

---

### 🔄 rev 2026-08-25 — il registro dice anche CHE DATA porta il documento

Brief: `brief-db-numerazione-data-documento-e-sequenza` (**DB-3**, **DB-12**).

#### Nuova colonna `politica_data_documento`

| valore | data del documento |
| --- | --- |
| `OGGI` (default) | `script.fn_data_operativa()` — fattura immediata |
| `FINE_MESE_COMPETENZA` | ultimo giorno di `fatturazione_lotti.competenza_mese` — fattura differita |

⭐ **Perché sul registro e non sul lotto.** Il registro **è** il sezionale: è lì
che vive la sequenza, e la regola della data deve stare accanto alla regola del
numero — altrimenti si può configurare un registro la cui data litiga con la sua
numerazione.

E c'è un guadagno che una colonna sul lotto non darebbe: **un lotto può contenere
documenti di registri diversi** (la natura instrada la nota di credito su un
sezionale suo). Con la regola sul registro, ogni documento prende la data giusta
**da sé**.

⚠️ Una data valorizzata su `fatturazione_lotti.data_documento` **scavalca** questa
politica, per tutti i documenti di quel lotto.

⚠️ **`FINE_MESE_COMPETENZA` e il cancello di monotonia collidono per
costruzione**, e non è un difetto: è il comportamento normale della differita in
ritardo. Un lotto di competenza arretrata lavorato oggi prende la data di fine di
quel mese, che è anteriore all'ultimo numero emesso, e viene rifiutato —
l'operatore ridichiara la data dal dialog. 📌 Misurato il 2026-08-25: 4 lotti
hanno competenza giugno e fatture datate luglio/agosto, e uno di essi porta una
fattura **già numerata**. ⭐ Per questo la `minDate` esposta al frontend
([`fn_get_data_minima_numerabile_lotto`](/dbzero/vendite/funzioni/fn_get_data_minima_numerabile_lotto))
non è un abbellimento: è ciò che rende vivibile la politica.

#### `reset_policy` scende a **una voce sola**

Il `CHECK` ammette ora solo `ANNUALE`. Prima accettava anche `NESSUNA` e
`MENSILE`, che erano **dichiarate e non implementate**: la chiave del contatore
porta `mese = 0` fisso e `uq_fatture_numero` il mese non lo contiene, quindi
`NESSUNA` si comportava come `ANNUALE` e `MENSILE` pure.

⛔ Un catalogo che promette tre comportamenti e ne fa uno è **peggio** di un
catalogo con una voce sola: prima o poi qualcuno sceglie `MENSILE`, e
un'implementazione a metà finisce in violazione di `UNIQUE`.

⚠️ Se un giorno `MENSILE` servisse davvero non basta riaprire il `CHECK`: serve
il mese **nel contatore** (c'è già) **e in `uq_fatture_numero`** (non c'è), più un
`fn_get_anno_registro` che riceva il registro.

⚠️ **Il `serie_default` è portante, non un'etichetta.** È da lì che
`fn_assign_numero_fattura` risolve la serie di un documento che non ne dichiara
una (`COALESCE(f.serie, r.serie_default, '')`), quindi **rinominarlo sposta il
sezionale**: le righe di `registri_fatturazione_progressivi` restano sulla serie
vecchia e vanno spostate a mano, o il contatore riparte da zero e il cancello
resta senza pavimento.

---

{% include-markdown "signature-core.md" %}
