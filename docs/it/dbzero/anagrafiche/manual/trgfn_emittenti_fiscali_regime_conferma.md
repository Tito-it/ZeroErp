## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_emittenti_fiscali_regime_conferma`

> 👀 **Vedi anche**
>
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [anagrafiche.trgfn_emittenti_fiscali_guard_regime_conferma](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_guard_regime_conferma)
> [dbops.vw_emittenti_regime_non_confermato](/dbzero/dbops/views/vw_emittenti_regime_non_confermato)

### 🎯 Scopo

(02-10-2026 — brief `brief-db-esigibilita-iva-per-cassa-emittente`, sezione 10, revisione di D-11)

**Chi scrive il regime fiscale lo dichiara; data e autore della conferma li scrive il
database.** È la forma delle code (`dbops.trgfn_coda_archiviazione`): il chiamante
scrive il fatto, il trigger ne deriva data e autore.

Prima (D-11, 01-10-2026) la conferma la scriveva il form dell'emittente insieme al
regime, e questa funzione la azzerava se il regime cambiava senza. La regola restava
fuori dal database: ogni altro scrittore del regime (un import, un batch, un altro
endpoint) doveva ricordarsi di scrivere anche la conferma.

### Regole

* Trigger `trg_emittenti_fiscali_a20_regime_conferma_upd`, `BEFORE UPDATE OF
  regime_fiscale_rf`. Fascia `a20`: non è un guard, scrive un valore.
* Un `UPDATE` che nomina `regime_fiscale_rf`, **anche con lo stesso valore**, è una
  dichiarazione: `regime_fiscale_confermato_il = now()` e
  `regime_fiscale_confermato_da` = la GUC `app.jwt_user`, o `CURRENT_USER` se manca.
  Lo stesso valore conta perché è così che si conferma un RF01 che nessuno aveva
  dichiarato.
* Un `UPDATE` che non nomina il regime non fa scattare il trigger: la conferma resta.
* La `INSERT` non conferma mai: un RF01 scelto e un RF01 di default sono la stessa
  riga nuova. Un regime dichiarato in creazione si conferma con un `UPDATE` del
  regime nella stessa transazione.
* ⭐ **Riempire un regime vuoto non è una dichiarazione.** È il default RF01 (D-1)
  applicato dopo, cioè il backfill `80_data/20261001-16`. Su un database ricostruito
  da zero l'`80_data` gira dopo tutto il `20_code`, quindi il backfill passa da questa
  funzione: senza questa regola «confermerebbe» col nome del migratore ogni RF01
  messo dal default, e il presidio resterebbe vuoto proprio sul caso per cui esiste.
  Dopo il `-17` (`NOT NULL` + FK al catalogo) un regime vuoto non esiste più.
* Non solleva. Chi scrive le due colonne da fuori lo ferma prima il guard `a10`
  [trgfn_emittenti_fiscali_guard_regime_conferma](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_guard_regime_conferma),
  che vede i valori del chiamante prima che questa funzione li scriva.
* Non esiste più un regime cambiato e non confermato: ogni cambio è una
  dichiarazione. Il presidio mostra solo i regimi che nessuno ha mai dichiarato.

### Test

`db/pgtap/vendite/test-esigibilita-iva-per-cassa-v1.sql` (casi 22-33). Il ramo del
backfill non è nel pgTAP: per costruire una riga col regime vuoto bisogna togliere il
`NOT NULL` e spegnere i trigger, cosa che il runner come app non può fare. È provato
una volta sullo scratch, con una mutazione (brief, sezione 10.4).

---

{% include-markdown "signature-core.md" %}
