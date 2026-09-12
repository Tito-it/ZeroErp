## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_competenza_mensile`

> 👀 **Vedi anche**
>
[vw_dash_competenza_attivita](vw_dash_competenza_attivita.md)
> [vw_dash_competenza_errori](vw_dash_competenza_errori.md)
> [config.stati_doc_fiscale](/dbzero/config/tabelle/stati_doc_fiscale)

---
### 🎯 Scopo Principale
(latest review 26-08-2026)
Aggregata mensile della **Lente 1 Competenza** in **formato lungo**: una riga
per `competenza_mese × stadio × stato_fattura_codice_interno × tipo_movimento ×
motivo_non_fatturata`.
Gli stati fattura sono **dati** (`config.stati_doc_fiscale`), non colonne: il
formato lungo regge il breakdown per stato (blocco 3a del design) senza
rincorrere il vocabolario; il **BE pivota**.

---

### Semantica

| Colonna | Regola |
|---------|--------|
| `stato_fattura_codice_interno` | Valorizzato solo per lo stadio `FATTURATA` (NULL per gli altri stadi e per le rare fatture senza stato) |
| `n_attivita`, `valore_tot` | Conteggio e somma `prezzo_snapshot × quantita` del gruppo |
| `valore_fatturato_tot` | Somma `imponibile_riga` (riconciliazione col fatturato reale) |
| `n_in_ritardo`, `valore_in_ritardo` | Recuperi tardivi del gruppo (`emessa_in_ritardo`) |
| `tipo_movimento` | `NORMALE` / `RETTIFICA` / `ONERE` — dimensione del raggruppamento dal 20-08-2026 |
| `motivo_non_fatturata` | `GIRO_IN_CORSO` / `RESIDUO` / `SENZA_ATTIVITA_FATTURABILE`, `NULL` fuori dallo stadio `EMESSA_NON_FATTURATA` — dimensione del raggruppamento dal 26-08-2026. ⚠️ `IN_ATTESA_LOTTO` è **ritirato** dal 12-09-2026 (`20260912-36`): nessun caso lo produce, vedi il manuale del dettaglio |

Eredita dal dettaglio perimetro computabile e scope emittente fail-closed.

---

### ⭐ `tipo_movimento` nel raggruppamento (20-08-2026)

**Perché.** Il residuo del mese è una somma **con segno**, quindi senza questa
dimensione le rettifiche si **compensano** con le fatture ancora da emettere.
Misurato: agosto 2026 segnava **101% di copertura** perché il residuo era
−29,50 — due note di credito da emettere.

⚠️ **Non è estetica.** Con una sola fattura da 29,50 in sospeso, il residuo
sarebbe andato a **zero** e la dashboard avrebbe detto *«100%, niente da fare»*
con **tre documenti da produrre**. La compensazione **nasconde lavoro**.

⭐ E non riguarda solo le rettifiche: a luglio 2026 ci sono **5.000 € di oneri**
nello stesso totale. La somma mescolava **tre** cose di natura diversa, non due
— ed è la ragione per cui si è aggiunta la **dimensione** e non una colonna
`valore_rettifiche`, che avrebbe messo i valori dell'enum dentro la vista e
avrebbe ignorato il quarto movimento che nascerà.

🔴 **Cambia la cardinalità, ed è un contratto rotto in un punto solo.** Sul dato
del 20-08-2026 le righe passano da **7 a 8**; l'unico bucket che si spezza è
`2026-07 · FATTURATA · EMESSA` (`NORMALE` + `ONERE`). Il pivot del BE
**accumula** per `(mese, stadio)`, quindi i **totali reggono**; il breakdown per
stato documento fiscale invece elenca **una voce per riga**, e senza adeguamento
mostra **EMESSA due volte**.

⚠️ E si vede **solo su luglio**: su agosto la cardinalità non cambia affatto (le
rettifiche stanno in `DA_EMETTERE`, i normali in `FATTURATA`). Chi provasse il
solo mese del rilievo concluderebbe che non si è rotto niente.

---

### ⭐ `motivo_non_fatturata` nel raggruppamento (26-08-2026)

Changeset `20260826-55`, brief `brief-db-residui-competenza-dimensione-e-chiave`
(D-2, richiesta del backend).

**Perché, ed è la stessa forma del 20-08.** Lo stadio `EMESSA_NON_FATTURATA`
guarda **solo** `fattura_riga_id`, e dentro quel valore convivono situazioni con
**rimedi opposti**: due non chiedono nessuna azione — l'attività che aspetta il
suo lotto, quella dentro un giro vivo — e una sì, il **residuo**, l'unica su cui
«Riporta da emettere» ha effetto.

⚠️ **Un numero solo per rimedi opposti dice il falso in due versi**: manda
l'operatore a cercare un guasto dove sta passando lavoro sano, oppure nasconde il
lavoro perso dentro un transito legittimo. È la stessa ambiguità che il cantiere
«il lavoro che non torna indietro» ha chiuso un livello più in giù, e a video
produce il difetto peggiore — la card diventa illeggibile proprio quando conta.

⛔ **Dimensione e non una colonna `n_residui`.** Quella avrebbe costretto
l'aggregata a **conoscere** il valore `RESIDUO`, cioè a cablare un elemento del
vocabolario dentro una somma: lo stesso errore che si evitò rifiutando
`valore_rettifiche`. La dimensione non conosce nessun valore — li porta.

🔴 **E cambia di nuovo la cardinalità.** Un bucket `EMESSA_NON_FATTURATA` che
contiene più situazioni si spezza in **una riga per situazione**. I totali del
consumatore reggono perché il pivot accumula; il **breakdown** elenca una voce
per riga, quindi senza adeguamento il frontend mostrerebbe
`EMESSA_NON_FATTURATA` due volte. È lavoro BE/FE e va fatto **nello stesso
giro** — identico a quanto dichiarato il 20-08 per `tipo_movimento`.

⚠️ Il vocabolario e il criterio che lo decide vivono sul **dettaglio**, non qui:
vedi [`vw_dash_competenza_attivita`](vw_dash_competenza_attivita.md) §«La chiave
del verbo e la dimensione». Questa vista lo **raggruppa** e basta.

---

### Esempio d'uso

```sql
-- Funnel del mese (il BE genera i mesi mancanti con generate_series).
SELECT stadio, stato_fattura_codice_interno, n_attivita, valore_tot
FROM vendite.vw_dash_competenza_mensile
WHERE competenza_mese = DATE '2026-05-01'
ORDER BY stadio, stato_fattura_codice_interno NULLS FIRST;
```

---

### Note operative

* Contratto **stabile per tutti i 4 blocchi** del design DL-8 (funnel,
  breakdown stato, ritardi; gli errori hanno la loro vista dedicata).
  ⚠️ La revisione del 20-08-2026 lo **estende** (una dimensione in più): è
  l'unica volta in cui la grana è cambiata, e il §40.2 di
  `brief-design-note-credito-resi` dice cosa deve fare il BE.
* Materializzabile in futuro (snapshot notturno) **senza cambiare il
  contratto** verso il BE.
* ⚠️ Fail-closed: senza GUC operatore restituisce 0 righe (vedi dettaglio).
* Test: `db/pgtap/vendite/test-vw-dash-competenza-v1.sql`,
  `db/pgtap/vendite/test-fn-list-commessa-attivita-provenienza-v1.sql`
  (test 20-22: la colonna, `security_invoker` preservato, e la **grana** — una
  riga per **tutte** le dimensioni, così una ri-aggregazione a valle «per non
  rompere il backend» diventerebbe rossa) e
  `db/pgtap/vendite/test-motivo-non-fatturata-v1.sql` (test 14-15: la grana con
  la dimensione nuova, e `security_invoker` su **entrambe** le viste toccate).
  ⚠️ Il test 22 è un presidio **di grana**: quando la grana cambia va **portato
  sulla regola nuova, mai spento** — è lo stesso meccanismo che rese rossi due
  test quando L7b *allargò* un guard. Un presidio cade allo stesso modo nelle
  due direzioni.

---

{% include-markdown "signature-core.md" %}
