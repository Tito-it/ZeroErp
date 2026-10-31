## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_fatturazione_documenti`

> 👀 **Vedi anche**
>
Resolver di area (rami della union):
>
[vw_dash_fatturazione_preventivi](vw_dash_fatturazione_preventivi.md)
> [vw_dash_fatturazione_ordini](vw_dash_fatturazione_ordini.md)
> [vw_dash_fatturazione_offerte](vw_dash_fatturazione_offerte.md)
> [vw_dash_fatturazione_contratti](vw_dash_fatturazione_contratti.md)
> [vw_dash_fatturazione_commesse](vw_dash_fatturazione_commesse.md)
>
Aggregata e brief:
>
[vw_dash_aperto_documenti](vw_dash_aperto_documenti.md)
> Brief autorevole: `docs/it/dev/work-in-progress/brief-design-dashboard-fatturazione.md`

---
### 🎯 Scopo Principale
> **Ultimo aggiornamento**: 31 ottobre 2026

`vendite.vw_dash_fatturazione_documenti` è la fonte dati del **drill-down della
Dashboard Fatturazione**: una riga per **documento × mese di competenza** su tutte
e **6** le aree che portano alla fatturazione (`PREVENTIVI`, `ORDINI`, `OFFERTE`,
`CONTRATTI`, `COMMESSE`, **`DDT`**), con valore/unità **totali** vs **transitati**
verso l'area successiva e il **motivo** per cui un documento è fermo.

È una **proiezione read-only**: nessuno stato nuovo sui documenti — il transito è
derivato dai link che i push scrivono già (FK, `segment_key`, `stato_emissione`,
`sorgente_*`). `UNION ALL` dei 6 resolver di area (stesso layering della proiezione
stato dominio). Il backend consuma **solo** questa vista (drill-down fermi) e
l'aggregata mensile — mai i resolver singoli.

> **Area `DDT` aggiunta il 2026-07-18** (slice fatturazione DDT/resi, §4a). Due cose
> da sapere per chi consuma:
>
> * la popolazione DDT è **selettiva**: entrano solo i DDT con un ruolo di
>   fatturazione — fuori quelli di ordini a trigger `CONFERMATO` (fattura l'ordine)
>   e quelli con causale di trasporto non fatturabile (solo trasporto). Dettaglio in
>   [vw_dash_fatturazione_ddt](vw_dash_fatturazione_ddt.md);
> * **i RESI non sono qui e non ci saranno**: sono flusso inverso (`REVERSE_FLOW`),
>   quindi non appartengono al funnel pre-commessa. Compaiono solo nel
>   [backlog](vw_dash_backlog_documenti.md), con rami propri.

---

### 📑 Contratto colonne

| Campo | Significato |
|-------|-------------|
| `area` | `PREVENTIVI` / `ORDINI` / `OFFERTE` / `CONTRATTI` / `COMMESSE` / `DDT` |
| `competenza_mese` | 1° del mese; derivazione per area documentata nel resolver |
| `documento_id` / `documento_uid` / `codice` | Identità del documento (`uid::text` dove esiste, altrimenti `id::text`) |
| `emittente_fiscale_id` | Scope emittente (NULL per COMMESSE) |
| `emittente_soggetto_ruolo_id` | Solo COMMESSE (non in RLS: eventuale filtro applicativo a carico del BE) |
| `valore_totale` / `valore_transitato` | Euro **imponibile** (decisione D-4). **NULL** per le aree a conteggi v1: OFFERTE e CONTRATTI (decisioni D-2/D-3) |
| `unita_totali` / `unita_transitate` | Righe (preventivi/ordini), attività (commesse), 1/0 (offerte, contratti×mese) |
| `is_transitato` | Transito **completo** del documento nel mese |
| `is_abortito` | `esito = 'NEGATIVO'` (proiezione stato dominio D1) — fuori dal confronto totale/transitato |
| `motivo_fermo` | Vocabolario chiuso (sotto); NULL se transitato o abortito |
| `stato_codice_interno` / `stato_codice` / `fase` | Stato nativo (alias fedeli §6c) + fase D1 (NULL per COMMESSE) |
| `cliente_display` | Ragione sociale del cliente (nullable). Path **per-area** riusato dalle rispettive `vw_*_lista`: preventivi/offerte da `istanze_utilities → soggetti`; ordini da `soggetto_ruolo_id`; contratti/commesse da `billing_account → soggetto_ruolo → soggetti` |

---

### Vocabolario `motivo_fermo` (decodifica i18n lato FE)

| Codice | Area | Significato |
|--------|------|-------------|
| `DOC_BOZZA` | preventivi, ordini, offerte | Documento ancora in bozza (il contratto in bozza ha il giudizio sospeso: motivo NULL) |
| `IN_ATTESA_ACCETTAZIONE` | preventivi, offerte | Emesso, in attesa del cliente |
| `RIGA_RESIDUA` | preventivi | Accettato con righe non ancora smistate (residuo bi-ramo) |
| `PUSH_NON_ESEGUITO` / `PUSH_PARZIALE` | ordini | Confermato, push a commessa assente/parziale |
| `SENZA_FIGLIO` | offerte | Accettata, né contratto né ordine generato |
| `FIGLIO_ABORTITO` | offerte | Figlio generato ma annullato: la XOR permanente impedisce di rigenerarlo — serve una **revisione** dell'offerta |
| `CANONE_NON_GENERATO` | contratti | Un addebito maturato (canone, una tantum, storno) non ancora in commessa (dal 2026-10-31, da `vendite.fn_contratti_addebiti_maturati`) |
| `CANONE_NON_GENERABILE` | contratti | Un canone che il push salta: senza periodicità, durata senza calendario, prezzo che manca alla data (dal 2026-10-31) |
| `ATTIVITA_NON_APPROVATA` / `ATTIVITA_NON_EMESSA` | commesse | Collo di bottiglia: approvazione vs emissione |

---

### Esempio d'uso

```sql
-- Elementi fermi di maggio 2026 nell'area preventivi (drill-down).
SELECT codice, valore_totale, valore_transitato, motivo_fermo, stato_codice
FROM vendite.vw_dash_fatturazione_documenti
WHERE area = 'PREVENTIVI'
  AND competenza_mese = DATE '2026-05-01'
  AND NOT is_abortito
  AND NOT is_transitato
ORDER BY valore_totale DESC NULLS LAST;
```

---

### Note operative

* **Predicato canonico del transito**: lo stesso delle funzioni di eligibilità al
  push (`fn_list_*_da_pushare`) — un'attività di commessa conta solo se
  `stato_emissione = 'EMESSA'`; una riga presente ma `NON_EMESSA` è ancora
  residua/ri-pushabile (upsert idempotente su `segment_key`) e risulta ferma sia
  nell'area sorgente sia in COMMESSE.
* **Regola-cardine abortiti**: i documenti con esito `NEGATIVO` escono dal confronto
  — se restassero nel totale, `totale = transitato` non tornerebbe mai (brief §3.3).
* **RLS**: la vista gira come invoker — lo scope emittente degli operatori su
  preventivi/ordini/offerte/contratti si applica automaticamente. L'area
  **COMMESSE è fuori RLS by design** (tabella di pipeline): lo scope è applicato
  **dentro** il resolver `vw_dash_fatturazione_commesse` via GUC, così che
  aggregata mensile e drill-down concordino (vedi quella scheda per il caveat
  fail-closed).
* Test: `db/pgtap/vendite/test-vw-dash-fatturazione-v1.sql`.

---


---

### 🆕 `emittente_ragione_sociale` *(R-4, 18-08-2026)*

Il nome dell'emittente arriva in coda alla proiezione.

⭐ **La JOIN è scritta una volta sola.** I sei resolver di ramo portano tutti
`emittente_soggetto_ruolo_id`: la union viene avvolta e il nome si risolve
all'esterno. Aggiungere la colonna ai sei rami avrebbe dato lo stesso risultato
al prezzo di sei modifiche e di sei occasioni di divergere.

⚠️ **Le due lenti NON ereditano la colonna.**
[vw_dash_aperto_documenti](vw_dash_aperto_documenti.md) e
[vw_dash_backlog_documenti](vw_dash_backlog_documenti.md) hanno proiezione a
colonne **esplicite**, e sono loro che il backend legge. «Eredita» è vero del
*dato* — nasce qui — ma falso della *proiezione*: va ri-elencata. Fermarsi a
questa vista avrebbe prodotto migrazione verde, catalogo verde e colonna vuota a
video, senza nessun errore a spiegarlo.

⚠️ **Il flag `multi_emittente` della lista NON si accende insieme alla colonna.**
Si guadagna dopo, quando la colonna mostra un nome su dati veri (brief
perimetro-emittente §7, decisione 3). Il controllo automatico
`dbops.vw_liste_multi_emittente_non_certificate` deve restare a zero righe.

* Test: `db/pgtap/vendite/test-viste-dash-emittente-v1.sql`.

---

{% include-markdown "signature-core.md" %}
