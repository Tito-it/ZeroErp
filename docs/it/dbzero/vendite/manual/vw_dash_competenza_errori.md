## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_competenza_errori`

> 👀 **Vedi anche**
>
[vendite.fatturazione_lotti_task_runs](/dbzero/vendite/tabelle/fatturazione_lotti_task_runs)
> [vendite.fatture_log](/dbzero/vendite/tabelle/fatture_log)
> [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)
> [vw_dash_competenza_attivita](vw_dash_competenza_attivita.md)

---
### 🎯 Scopo Principale
(latest review 06-07-2026)
Blocco **errori** della Lente 1 Competenza (blocco 4 del design, assorbe §12.3
del brief pre-fatturazione): gli eventi di errore **vivi** della pipeline di
fatturazione, per mese di competenza — dal cruscotto si vede subito se c'è un
lotto o una fattura inceppati, senza andare a caccia nei log.

---

### Semantica

| `tipo_evento` | Popolazione | Competenza |
|---------------|-------------|------------|
| `TASK_ERRORE` | Run di `fatturazione_lotti_task_runs` con `task_stato = 'ERRORE'` e `attivo`, **non superato** da un run `COMPLETATO` successivo sulla stessa chiave (lotto, step, task): un retry riuscito spegne l'errore | `fatturazione_lotti.competenza_mese` |
| `FATTURA_CRITICA` | `fatture.critical IS TRUE` (flag sincronizzato dai trigger su `fatture_log`); `messaggio` = ultimo log non disabilitato | Regola DB-7 in cascata: mese del **lotto** collegato → mesi **distinti** delle AF collegate (una riga per mese) → fallback mese della **data fattura** |

Scope emittente in-vista da GUC (fail-closed), `security_invoker = on`.

---

### Esempio d'uso

```sql
-- C'e' qualcosa di inceppato che tocca la competenza di maggio?
SELECT tipo_evento, lotto_codice, fattura_id, error_code, messaggio, data_evento
FROM vendite.vw_dash_competenza_errori
WHERE competenza_mese = DATE '2026-05-01'
ORDER BY data_evento DESC;
```

---

### Note operative

* Un errore si "spegne" da solo: retry `COMPLETATO` per i task,
  `critical = false` (risoluzione/disabilitazione log) per le fatture.
* Una fattura critica multi-mese (AF di competenze diverse, senza lotto)
  produce **una riga per mese**: ogni mese interessato vede il suo problema.
* ⚠️ Fail-closed: senza GUC operatore restituisce 0 righe.
* Test: `db/pgtap/vendite/test-vw-dash-competenza-v1.sql`.

---


---

### 🆕 `emittente_ragione_sociale` *(R-4, 18-08-2026)*

Il nome dell'emittente arriva in coda alla proiezione. La union dei due rami
(`TASK_ERRORE` dal **lotto**, `FATTURA_CRITICA` dalla **fattura**) viene avvolta
in una CTE e il nome si risolve una volta all'esterno: entrambi i rami portano
già la chiave, quindi non c'è niente da normalizzare — solo da leggere.

⚠️ **Il filtro di scope NON è stato accorpato fuori dalla union**, e non è una
svista: i due rami filtrano su **sorgenti diverse** (l'emittente del lotto e
quello della fattura), e unificarli significherebbe sceglierne una. Il filtro
sta dove sta la ragione.

⚠️ **Il flag `multi_emittente` della lista NON si accende insieme alla colonna.**
Si guadagna dopo, quando la colonna mostra un nome su dati veri (brief
perimetro-emittente §7, decisione 3). Il controllo automatico
`dbops.vw_liste_multi_emittente_non_certificate` deve restare a zero righe.

* Test: `db/pgtap/vendite/test-viste-dash-emittente-v1.sql`.

---

### 🆕 `commesse_fallite` e `n_commesse_fallite` *(D3, 04-09-2026)*

Un `TASK_ERRORE` del pull dice «una su tre è fallita» e non diceva **quale**.
Queste due colonne portano l'elenco delle commesse respinte da **quel** giro,
ognuna con il suo motivo:

```json
[{"commessa_id": 34137, "commessa_codice": "CMM-…-000000004",
  "error_code": "E_PULL_COMMESSA",
  "messaggio": "Errore emissione commessa 34137",
  "dettaglio":  "ROOT source mancante per commessa 34137 …"}]
```

⭐ **In coda, e la grana NON cambia**: una riga resta un **evento**. È una
decisione, non una comodità — il badge del calendario conta le righe di questa
vista, e farne una per commessa respinta l'avrebbe fatto passare da «quante
volte devo aprire un lotto» a «quanto lavoro è rimasto indietro»: due domande
buone, ma diverse.
⚠️ E la vista somma **già** due unità (`TASK_ERRORE` per (lotto × task),
`FATTURA_CRITICA` per fattura). Una terza avrebbe reso il totale la somma di tre
cose diverse: «4» avrebbe voluto dire «2 task + 1 fattura + 1 commessa».
⇒ Il conteggio resta sugli eventi; l'elenco per commessa vive nel **dettaglio**,
e in forma di lista in [vw_dash_commesse_respinte](vw_dash_commesse_respinte.md).

⛔ **La sorgente non è `task_run.meta -> 'commesse_fallite'`**, che il backend
scrive **troncato a cinque** dichiarandolo una traccia per il cockpit: con sei
respinte la sesta sparirebbe in silenzio. Si legge il **log di lotto**, che è
completo e porta il `commessa_id` in un campo strutturato.

⚠️ Tre filtri portanti, che sembrano dettagli: **stesso task** (il log di un
lotto contiene le righe di tutti gli step), **stesso tentativo**
(`data_ora >= data_evento`, o un lotto rilanciato si porterebbe dietro le
respinte del giro precedente) e **cast protetto** da un test di forma, perché
una sola riga di log sporca non deve poter spegnere il cruscotto.

* Test: `db/pgtap/vendite/test-vw-dash-commesse-respinte-v1.sql`.

---

{% include-markdown "signature-core.md" %}
