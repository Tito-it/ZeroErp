## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_aperto_documenti`

> 👀 **Vedi anche**
>
[vw_dash_fatturazione_documenti](vw_dash_fatturazione_documenti.md)
> [vw_dash_aperto_riepilogo](vw_dash_aperto_riepilogo.md)
> [vw_dash_competenza_attivita](vw_dash_competenza_attivita.md) (Lente 1)
> [vw_dash_backlog_documenti](vw_dash_backlog_documenti.md) (Lente 2)

---
### 🎯 Scopo Principale
(latest review 08-07-2026 — v2 serbatoio pre-commessa, DL-14..18)
Vista dettaglio della **Situazione aperta v2 — serbatoio pre-commessa**: lo
**stock dei documenti aperti e non conclusi** delle 4 aree documento
(PREVENTIVI, ORDINI, OFFERTE, CONTRATTI), **senza asse temporale**. Risponde a:
*"quali documenti aperti, se conclusi, andrebbero in commessa/fatturazione ma
non ci sono ancora arrivati, e in che fase sono?"*. Il concetto **"transitato"**
è **eliminato** (DL-14): in una vista senza asse temporale totalizzava *dalla
notte dei tempi* documenti già passati avanti, informazione non azionabile.

---

### Semantica

| Aspetto | Regola |
|---------|--------|
| **Perimetro (DL-15 — 4 predicati)** | `area <> 'COMMESSE' AND NOT is_abortito AND is_transitato IS DISTINCT FROM true AND fase <> 'CHIUSO'`. Le COMMESSE sono coperte dalla Lente 1; gli abortiti (esito NEGATIVO) sono marcati dai resolver ed esclusi qui |
| **I due filtri servono entrambi** | `is_transitato IS DISTINCT FROM true` toglie i **transitati-non-chiusi** (es. preventivo ACCETTATO già completamente smistato, resta IN_CORSO); `fase <> 'CHIUSO'` toglie i **chiusi-non-transitati** (es. preventivo EVASO con riga residua: POSITIVO → non abortito, non transitato). ⚠️ Un'offerta SUPERATA **non** è un chiuso-non-transitato: SUPERATA ha esito NEGATIVO → è già abortita |
| **Contratti (DL-18)** | Giudizio sospeso (`is_transitato NULL` → aperto): compaiono DRAFT + ATTIVO; CESSATO escono con `fase<>CHIUSO`, ANNULLATO sono abortiti. Un ATTIVO figura come IN_CORSO (astrazione fase normalizzata, accettata) |
| Valori | Da resolver: € per PREVENTIVI/ORDINI, `NULL` per OFFERTE/CONTRATTI (aree a conteggi, DL-11) |
| Scope | `security_invoker = on` → RLS emittente delle 4 aree sul chiamante |

Colonne **rimosse** rispetto alla v1 (DL-14): `is_transitato`, `is_aperto`,
`valore_transitato`, `unita_transitate` (`is_transitato` resta usato solo nel
WHERE, dalla union). `motivo_fermo` **tenuto** come hint informativo di riga.

---

### Esempio d'uso

```sql
-- Drill-down di una card: i preventivi aperti in fase IN_ATTESA. Il filtro
-- "aperti da oltre N giorni" è BE-side su data_riferimento (solo sulla lista).
SELECT codice, cliente_display, stato_codice, motivo_fermo, data_riferimento
FROM vendite.vw_dash_aperto_documenti
WHERE area = 'PREVENTIVI' AND fase = 'IN_ATTESA';
```

---

### Note operative

* È il **perimetro unico** di card (`vw_dash_aperto_riepilogo`) e drill-down:
  il BE non deve replicare filtri (aggiunge solo il ritardo su `data_riferimento`).
* Ricreata con **DROP + CREATE** (`20260708-03`): rimuovere colonne da una vista
  non è possibile con `CREATE OR REPLACE`; il riepilogo dipendente è droppato
  prima (ordine di dipendenza, no CASCADE) e ricreato dal `20260708-04`.
* `fase` è sempre valorizzata sulle 4 aree (join `config.stati_doc_*`).
* Test: `db/pgtap/vendite/test-vw-dash-aperto-v1.sql`.

---


---

### 🆕 `emittente_ragione_sociale` *(R-4, 18-08-2026)*

Il nome dell'emittente arriva in coda alla proiezione, già risolto da
[vw_dash_fatturazione_documenti](vw_dash_fatturazione_documenti.md).

⚠️ **Andava ELENCATA.** La proiezione di questa vista è a colonne esplicite:
non eredita niente dalla vista a monte. È il tranello che ha reso cinque i
changeSet di R-4 invece dei tre previsti — e il modo in cui si scopre è
guardare *cosa legge il backend*, non il grafo delle viste.

⚠️ **Il flag `multi_emittente` della lista NON si accende insieme alla colonna.**
Si guadagna dopo, quando la colonna mostra un nome su dati veri (brief
perimetro-emittente §7, decisione 3). Il controllo automatico
`dbops.vw_liste_multi_emittente_non_certificate` deve restare a zero righe.

* Test: `db/pgtap/vendite/test-viste-dash-emittente-v1.sql`.

---

{% include-markdown "signature-core.md" %}
