# Brief DB — La suite pgTAP non è confrontabile con la sua baseline (utente ≠ utente)

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` ·
> **Data**: 2026-07-29 · **Owner**: Tid · **Stato**: 🔴 **APERTO** ·
> **Priorità**: 🔴 **ALTA** — non per un difetto di prodotto, ma perché
> **`scripts/pgtap-baseline.sh` oggi non può fare il suo mestiere**: distinguere
> un rosso nuovo da uno noto. Finché non è risolto, ogni «zero regressioni»
> dichiarato dalla suite vale poco.
>
> **Origine**: verifica del 2026-07-29 sul residuo **P6** del
> [brief-db-emissione-fattura-per-documento-sorgente](../work-done/brief-db-emissione-fattura-per-documento-sorgente.md).
> Controllando se i 9 rossi `E_SORG_FORMATO` fossero rientrati è emerso che il
> conto non torna: **105 rossi su 155 in `vendite`, di cui solo 38 in baseline**.
>
> **Contesto**: non siamo in produzione
> ([[project_no_produzione_solo_sviluppo]]).
>
> **Assorbe**: il residuo **P6** del brief sopra, che come voce a sé non ha più
> senso — va ricontato dopo aver sistemato quanto segue.

---

## 1. Il sintomo

```
$ scripts/pgtap-baseline.sh vendite
Rossi ora: 105 su 155   |   noti in baseline (perimetro): 38
❌ REGRESSIONI — rossi NUOVI, non erano in baseline:  (~60 file)
exit 1
```

La baseline è stata aggiornata il **2026-07-28 alle 23:42** (commit del brief di
ritiro). Se fosse stata registrata con lo stesso runner, i conti tornerebbero.
Non tornano.

## 2. La causa, verificata

**Il runner e la baseline non girano come lo stesso utente PostgreSQL.**

`scripts/testpgtap.sh` legge `backend/.env` e mappa `DB_USER` → `PGUSER`: si
connette come **`zeroerp_app`**. Ma:

| Ruolo | `BYPASSRLS` | È owner di `vendite` | Vede le tabelle RLS |
|---|---|---|---|
| `titodb` | ❌ no | ✅ **sì** | ✅ — perché `relforcerowsecurity` è `false`, e l'owner salta la RLS |
| `zeroerp_app` | ❌ no | ❌ no | ❌ **no**, senza le GUC operatore |
| `zeroerp_batch_fatturazione` | ✅ **sì** | ❌ no | ✅ |

Quindi lo stesso file `.sql` **passa o fallisce a seconda di chi lo lancia**, e
non c'è nulla nel test che lo dichiari.

### 2.1 Le due forme in cui si manifesta

Campionati sei test falliti, la causa è una sola in due vesti:

| Test | Errore |
|---|---|
| `test-fatture-righe-importo-e-kit-v1` | `la nuova riga viola la regola di sicurezza per riga per la tabella "fatture"` |
| `test-commesse-schema-v1` | idem su `"commesse"` |
| `test-ddt-read-side-v1` | idem su `"ordini"` |
| `test-emissione-mirata-gruppi-fatturabili-v1` | idem su `"preventivi"` |
| `test-annulla-commessa-attivita-v1` | `Parametro non valido: p_billing_account_id obbligatorio e > 0` |
| `test-fn-batch-upsert-commessa-attivita-v1` | idem |

- **Scrittura bloccata**: la policy `rls_fatture_ef_whitelist` (e sorelle) è
  `cmd=ALL` con un `WITH CHECK` che pretende
  `app.ruolo_applicativo='OPERATORE'` + `app.current_user_id`. Il fixture non le
  imposta → l'`INSERT` viene respinto.
- **Lettura vuota**: `anagrafiche.billing_account` è **anch'essa RLS** e senza
  GUC restituisce **0 righe** (verificato). Il fixture cerca un billing account,
  non lo trova, passa `NULL` alla funzione, e il guard di dominio solleva. Stesso
  difetto, sintomo diverso — e più insidioso, perché l'errore parla di un
  parametro e non di sicurezza.

Controprova coerente: i test che **passano** sono quelli che o impostano la GUC
(`test-porta-oneri-giro-completo-v1`, 1 occorrenza di `set_config`) o non
scrivono su tabelle RLS (`test-articolo-regole-fatturazione`). Il test nuovo che
fallisce ha **zero** `set_config`.

## 3. Perché è cresciuto adesso

Le tabelle con RLS in `vendite` + `anagrafiche` sono ormai **quattordici**:

```
anagrafiche.billing_account   vendite.fatture              vendite.offerte_commerciali
vendite.commesse              vendite.fatture_riepiloghi_iva   vendite.ordini
vendite.commesse_attivita     vendite.fatture_righe        vendite.preventivi
vendite.contratti             vendite.fatture_scadenze     vendite.resi
vendite.ddt                   vendite.fatturazione_lotti
```

⚠️ **`fatture_righe` e `fatture_riepiloghi_iva` sono state protette da poco** —
è l'applicazione di
[brief-db-rls-satelliti-fattura-portale](../work-done/brief-db-rls-satelliti-fattura-portale.md),
che risulta ancora `⬜ DA FARE` nella sua intestazione: **da allineare**. Ogni
tabella che entra nella RLS aggiunge fixture che smettono di funzionare, quindi
il fenomeno è destinato a peggiorare a ogni ondata.

> ✅ **Nessun impatto sui percorsi applicativi**, verificato: il worker di
> stampa gira dentro `system_process_context` come `zeroerp_batch_fatturazione`,
> che ha `BYPASSRLS`; il percorso web porta le GUC dal middleware; i due smoke
> di fatturazione (`smoke-fatturazione-aggregazione-righe`,
> `smoke-fatturazione-render-stampa`) sono **verdi** perché impostano il
> contesto operatore. Il problema è **solo** della suite pgTAP.

## 4. Cosa si chiede di decidere

Non propongo un'implementazione — è terreno del team DB — ma la scelta è fra
tre strade, e conviene farla esplicita perché condiziona ogni test futuro.

| | Strada | Conseguenze |
|---|---|---|
| **(a)** | Il runner si connette come **owner** (`titodb`) | Un cambio a `scripts/testpgtap.sh`. Ma i test **non esercitano mai la RLS**: continuerebbero a non accorgersi di una policy sbagliata, che è già un limite noto (cfr. `brief-db-emissione-fattura-per-documento-sorgente` §RLS) |
| **(b)** | Ogni fixture imposta le **GUC operatore** in testa | I test girano come l'applicazione e la RLS viene esercitata davvero. Costo: toccare ~60 file, o meglio estrarre un **helper di fixture** condiviso (`SELECT script.pgtap_set_contesto_operatore()`) e chiamarlo da ognuno |
| **(c)** | Il runner usa un ruolo **`BYPASSRLS`** dedicato ai test | Come (a) ma senza dipendere dall'ownership. Stesso limite: RLS non esercitata |

**Raccomandazione: (b)**, con l'helper condiviso. È l'unica che rende i test
rappresentativi di come gira l'applicazione, ed è coerente con la lezione di
questi giorni — un test che passa in una condizione che in esercizio non esiste
mai è verde senza dire nulla. (a) e (c) risolvono il conteggio nascondendo il
problema.

Se si sceglie (b), i test che devono verificare **il canale batch** useranno
esplicitamente il contesto di sistema: la differenza fra i due diventa parte di
ciò che si collauda, invece di un incidente.

## 5. Dopo la scelta

1. Applicare la strada scelta ai file del perimetro `vendite` (~60).
2. **Ricontare** e rigenerare la baseline: `scripts/pgtap-baseline.sh --update vendite`.
3. Solo allora ha senso riprendere **P6** (i 9 rossi `E_SORG_FORMATO`): oggi non
   sono nemmeno distinguibili dal rumore — la baseline non riporta più quella
   causa, ha solo `ERRORE_FIXTURE` (75) e `ASSERZIONE` (33).
4. Togliere dalla baseline i **5 rientrati** che il runner già segnala:
   `test-bozza-non-operativa-e-preview-contratto-v1`, `test-colonne-lineage-liste-v1`,
   `test-contratti-modalita-pricing-v1`, `test-contratti-schema-step21-v1`,
   `test-guard-esclusione-figlio-bundle-v1`.
5. Allineare l'intestazione di
   [brief-db-rls-satelliti-fattura-portale](../work-done/brief-db-rls-satelliti-fattura-portale.md),
   che si dichiara `DA FARE` mentre le due policy risultano applicate.

## 6. Fuori perimetro

- **`FORCE ROW LEVEL SECURITY`**: resta l'ondata coordinata futura. Nota però
  che il giorno in cui verrà attivata, la strada **(a)** smetterà di funzionare —
  l'owner non salterebbe più la RLS. È un argomento in più per **(b)**.
- **Il rosso di `test-contratti-overlap-draft-escluso-v1`**: fallisce per
  **asserzione**, non per fixture. È l'unico del campione con una causa diversa,
  e va guardato a parte.

---

## 7. Registro

| Data | Cosa | Esito |
|---|---|---|
| 2026-07-29 | Verifica del residuo P6 | Trovato lo scarto baseline/runner. Causa isolata su un campione di 6 test: RLS in scrittura (4) e `billing_account` invisibile in lettura (2). Confermato che i percorsi applicativi **non** sono coinvolti |
