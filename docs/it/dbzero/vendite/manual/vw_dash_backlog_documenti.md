## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_backlog_documenti`

> 👀 **Vedi anche**
>
[config.motivi_fermo](/dbzero/config/tabelle/motivi_fermo)
> [vw_dash_fatturazione_documenti](vw_dash_fatturazione_documenti.md)
> [vw_dash_backlog_riepilogo](vw_dash_backlog_riepilogo.md)
>
Rami resi (dal 2026-07-18):
>
[vw_resi_da_riconsegnare](/dbzero/vendite/views/vw_resi_da_riconsegnare) ·
> [vw_resi_da_accreditare](vw_resi_da_accreditare.md)

---
### 🎯 Scopo Principale
> **Ultimo aggiornamento**: 31 ottobre 2026

**Lente 2 Backlog** (cruscotti fatturazione a due lenti): la lista dei
**non-collegati azionabili** — cosa è fermo prima della commessa, da quanto, e
cosa serve per sbloccarlo. L'asse **non è la competenza** (i fermi non ce
l'hanno): è l'**anzianità** (`data_riferimento`/`anzianita_giorni`) e
l'**azionabilità** (`classe` dalla lookup `config.motivi_fermo`).

> ⚠️ **Cambio di forma (2026-07-18)**: la vista **è diventata una `UNION`** — non è
> più costruita solo sopra `vw_dash_fatturazione_documenti`. Ai documenti si
> affiancano **due rami resi**, che in quella union non possono stare (i resi sono
> flusso inverso, `REVERSE_FLOW`) ma nel backlog sì: hanno lavoro arretrato vero.

---

### Semantica

| Aspetto | Regola |
|---------|--------|
| **Popolazione** | **Tre rami** uniti: (1) `vw_dash_fatturazione_documenti` con `motivo_fermo IS NOT NULL`; (2) `vw_resi_da_riconsegnare` → `RICONSEGNA_NON_ESEGUITA`; (3) `vw_resi_da_accreditare` con etichetta `DOVUTA` → `MERCE_RESA_GIA_FATTURATA`. Su **tutti** si applica poi la stessa regola unica DL-7: classe **non** `FISIOLOGICO`, nessun caso speciale per area |
| **`classe`** | Da `config.motivi_fermo` per `codice_interno = motivo_fermo`: `RECUPERABILE` 🟠 (lavoro interno, il numero che conta) · `ANOMALIA` 🔴 (da rivedere) · `SOLLECITO_CLIENTE` 🔵 (palla al cliente, filtro dedicato) |
| **Fail-visible (DB-3)** | LEFT JOIN + `COALESCE(classe, 'ANOMALIA')`: un motivo non mappato (o con lookup disattivata) **compare come anomalia**, non sparisce in silenzio |
| **Conseguenze DL-7** | Contratti: dal 2026-10-31 `CANONE_NON_GENERATO` 🟠 e `CANONE_NON_GENERABILE` 🔴 (prima fuori: giudizio sospeso) · Offerte: solo `FIGLIO_ABORTITO` 🔴 e `IN_ATTESA_ACCETTAZIONE` 🔵 · Preventivi/Ordini/Commesse: il loro 🟠 |
| **Anzianità (v1 proxy)** | `data_riferimento`: data documento (preventivi/ordini), emissione con fallback (offerte), l'addebito più vecchio che aspetta (contratti, mai dopo oggi), mese della riga (commesse), **data del reso** (area RESI). `anzianita_giorni = CURRENT_DATE - data_riferimento` |
| `valore_fermo` / `unita_ferme` | `totale - transitato` (valore NULL per le aree a conteggi) |
| **Area `RESI` — grana** | Una riga per **(reso × motivo)**, non per riga di reso né per documento. Un **reso misto** (parte da ri-spedire, parte a credito) ha davvero due cose in corso e compare **due volte**, ciascuna con la sua azione e la sua classe: è una **deroga dichiarata**, unica area in cui accade — non un doppione da de-duplicare |
| **Area `RESI` — misura** | **A conteggi** (i resi non hanno importi): `valore_fermo` **NULL**, mai `0` — zero direbbe «valore nullo», NULL dice «non misurabile in euro». `unita_ferme` = numero di righe reso del motivo |

---

### Esempio d'uso

```sql
-- Il lavoro di oggi: gli arretrati interni piu' vecchi.
SELECT area, codice, cliente_display, motivo_fermo, azione, anzianita_giorni
FROM vendite.vw_dash_backlog_documenti
WHERE classe = 'RECUPERABILE'
ORDER BY anzianita_giorni DESC;
```

---

### Note operative

* L'**ordinamento** per anzianità è responsabilità del BE (le viste non
  garantiscono ORDER).
* Scope ereditato dalla union: aree documentali via RLS, commesse via GUC
  fail-closed (senza GUC il ramo commesse è vuoto).
* **Nuovo `motivo_fermo`** = append al CSV seed della lookup **prima** di
  emetterlo da una vista; il pgTAP di coerenza (`test-vw-dash-backlog-v1.sql`
  test 4) diventa rosso se un codice emesso non è mappato.
* **La classe si risolve una volta sola, a valle della union**: i rami emettono
  soltanto il *motivo*. Conseguenza pratica: promuovere un motivo da
  `FISIOLOGICO` a `RECUPERABILE` **cambia il backlog senza toccare la vista**. È
  esattamente ciò che accadrà a `MERCE_RESA_GIA_FATTURATA` quando esisterà la nota
  di credito — oggi il ramo lo emette e il filtro di classe lo esclude, perché
  nessuna azione è possibile (niente NC, quantità immutabile).
* Il timestamp di transito (DL-5) **non serve qui**: gli elementi del backlog
  non sono ancora transitati — l'anzianità v1 resta sulla data documento.
* Test: `db/pgtap/vendite/test-vw-dash-backlog-v1.sql`.

---


---

### 🆕 `emittente_ragione_sociale` *(R-4, 18-08-2026)*

Il nome dell'emittente arriva in coda alla proiezione, su **tutti e tre** i rami.

⚠️ **Qui il problema era doppio**, e la seconda metà è la più insidiosa:

1. come per la Situazione aperta, la proiezione è a colonne **esplicite** e non
   eredita dalla vista a monte;
2. i due rami **RESI** non hanno `emittente_soggetto_ruolo_id` (lì è `NULL`) ma
   hanno `emittente_fiscale_id`. Risolvere il nome solo dal soggetto-ruolo
   avrebbe lasciato muto **l'intero blocco resi** — e siccome i resi sono una
   minoranza delle righe, sarebbe passato per «qualche riga senza emittente»
   invece che per un ramo mai risolto.

⭐ **La cura è una sola catena di JOIN, non due.**
`emittenti_fiscali.soggetto_ruolo_id` è `NOT NULL` con `UNIQUE`: fra emittente
fiscale e soggetto-ruolo c'è una corrispondenza uno-a-uno. Basta un `COALESCE`
sulla **chiave** — prima il soggetto-ruolo se c'è, altrimenti quello dedotto
dall'id fiscale — e la risoluzione del nome resta scritta una volta.

⚠️ `emittente_soggetto_ruolo_id` sui rami resi **resta `NULL`** come prima.
Valorizzarla sarebbe un miglioramento vero, ma è un cambio di semantica di una
colonna esistente e va deciso a parte.

⚠️ **Il flag `multi_emittente` della lista NON si accende insieme alla colonna.**
Si guadagna dopo, quando la colonna mostra un nome su dati veri (brief
perimetro-emittente §7, decisione 3). Il controllo automatico
`dbops.vw_liste_multi_emittente_non_certificate` deve restare a zero righe.

* Test: `db/pgtap/vendite/test-viste-dash-emittente-v1.sql`.

---

{% include-markdown "signature-core.md" %}
