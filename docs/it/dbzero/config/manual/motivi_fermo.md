## 📘 Documentazione Concettuale – Tabella `config.motivi_fermo`

> 👀 **Vedi anche**
>
[vendite.vw_dash_backlog_documenti](/dbzero/vendite/views/vw_dash_backlog_documenti)
> [vendite.vw_dash_fatturazione_documenti](/dbzero/vendite/views/vw_dash_fatturazione_documenti)

---
### 🎯 Scopo Principale
(latest review 06-07-2026)
Vocabolario dei **motivi di fermo** della dashboard fatturazione (cruscotti a
due lenti) con la **classe di azionabilità**: la gravità di un fermo non si
deriva dallo stato grezzo del documento ma dal `motivo_fermo` che i resolver
`vw_dash_fatturazione_*` già producono; la classe è una **mappatura statica**
decisa dal dominio (decisione DL-6, Tid 2026-07-04), collocata qui DB-first.

---

### Le 4 classi (CHECK, contratto semantico del design)

| `classe` | Colore | Significato | Azione |
|----------|--------|-------------|--------|
| `FISIOLOGICO` | 🟢 | Nessun ritardo: lavorazione interna o limite strutturale noto | nessuna |
| `RECUPERABILE` | 🟠 | Ritardo recuperabile **da noi** — il numero che conta per il lavoro quotidiano | vedi colonna `azione` |
| `ANOMALIA` | 🔴 | Non un semplice ritardo: serve revisione | vedi colonna `azione` |
| `SOLLECITO_CLIENTE` | 🔵 | Palla al cliente (non lavoro interno): filtro dedicato | sollecito |

### Whitelist operativa (seed, 14 codici)

`RIGA_RESIDUA`, `PUSH_NON_ESEGUITO`, `PUSH_PARZIALE`, `ATTIVITA_NON_APPROVATA`,
`ATTIVITA_NON_EMESSA`, **`RICONSEGNA_NON_ESEGUITA`** → 🟠 · `FIGLIO_ABORTITO` → 🔴 ·
`IN_ATTESA_ACCETTAZIONE` → 🔵 · `DOC_BOZZA`, `CANONE_NON_GENERATO`, `SENZA_FIGLIO`,
**`IN_TRANSITO`**, **`IN_ATTESA_DDT`**, **`MERCE_RESA_GIA_FATTURATA`** → 🟢.

#### I quattro codici aggiunti dalla slice DDT/resi (2026-07-18)

| `codice_interno` | Classe | Emesso da | Perché quella classe |
|---|---|---|---|
| `IN_TRANSITO` | 🟢 | `vw_dash_fatturazione_ddt` | Merce spedita che non ha ancora raggiunto lo stato che fattura: **è in viaggio, non in ritardo** |
| `IN_ATTESA_DDT` | 🟢 | `vw_dash_fatturazione_ordini` | Ordine con trigger `SPEDITO`/`CONSEGNATO`: **non è lui a pushare**, lo faranno i suoi DDT. Resta nel serbatoio, esce dal backlog |
| `RICONSEGNA_NON_ESEGUITA` | 🟠 | ramo resi del backlog | L'azione **esiste** (`fn_genera_ddt_riconsegna`) e la sua mancata esecuzione **blocca la fatturazione**: il residuo dell'ordine resta riaperto |
| `MERCE_RESA_GIA_FATTURATA` | 🟢 **oggi** | ramo resi del backlog | Merce resa che risulta già fatturata → accredito dovuto. Fisiologico **perché nessuna azione esiste**: la nota di credito non c'è ancora, e correggere la quantità a mano è vietato dall'immutabilità |

> **`MERCE_RESA_GIA_FATTURATA` diventerà 🟠 cambiando questa sola cella di seed.**
> Il ramo che lo emette è già costruito e la classe si risolve a valle della union:
> quando esisterà la slice NC, il backlog si popolerà **senza toccare una vista né
> rilasciare BE/FE**. Il nome nomina **il fatto** («fatturata per 10, tenuta 7»), non
> il rimedio: un `NC_DOVUTA` pre-deciderebbe la risposta e mentirebbe se il rimedio
> scelto fosse un altro.

---

### Regole

* **`codice_interno`** = chiave naturale immutabile (lock auto-provisionato):
  è il valore emesso dalle viste e usato in logica/join/i18n FE. `codice` è
  solo display.
* **Nessuna FK possibile** dalle viste (emettono letterali). La coerenza è
  garantita **fail-visible**: `vw_dash_backlog_documenti` fa LEFT JOIN e un
  motivo non mappato compare con classe `ANOMALIA` (mai perso in silenzio) +
  pgTAP di coerenza (`test-vw-dash-backlog-v1.sql`).
* **Nuovo motivo** = append al CSV seed
  (`db/changelog/migrations_v2/80_data/sql/config/motivi_fermo.csv`) con la
  sua classe, **prima** di emetterlo da una vista. Mai un nuovo loader: il
  changeset `runOnChange` esistente ripesca il CSV.
* Le classi sono **chiuse** (CHECK): aggiungerne una è una modifica di design,
  non di configurazione.

---

{% include-markdown "signature-core.md" %}
