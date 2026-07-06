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

### Whitelist operativa (seed, 10 codici)

`RIGA_RESIDUA`, `PUSH_NON_ESEGUITO`, `PUSH_PARZIALE`, `ATTIVITA_NON_APPROVATA`,
`ATTIVITA_NON_EMESSA` → 🟠 · `FIGLIO_ABORTITO` → 🔴 · `IN_ATTESA_ACCETTAZIONE`
→ 🔵 · `DOC_BOZZA`, `CANONE_NON_GENERATO`, `SENZA_FIGLIO` → 🟢.

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
