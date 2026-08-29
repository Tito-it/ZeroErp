# Brief DB — `fn_create_contratto` non whitelista i tre riferimenti dell'atto

> **Destinatario:** team DB (`dev/db-tid`). **Voce unica**, e sblocca la slice
> `S3-b` del piano
> [brief-be-fe-iva-risolutore-e-regime-cliente.md](brief-be-fe-iva-risolutore-e-regime-cliente.md).
>
> **Origine.** Trovato il 2026-08-29 costruendo `I8` lato BE/FE. La metà additiva
> di `I8` è **applicata** — `vendite.contratti` ha `codice_cig`, `codice_cup`,
> `codice_commessa` (changeSet `20260829-13`) — e il backend le scrive già in
> **PATCH**. In **CREATE** no, e non per una scelta: non può.
>
> **Stato.** 2026-08-29 — verificato sulla doc auto-generata
> ([fn_create_contratto](/dbzero/vendite/funzioni/fn_create_contratto)), non sui
> dati. Nessun file scritto lato DB.

---

## 1. Il fatto

`vendite.fn_create_contratto(p_testata jsonb, p_utility jsonb)` è la funzione
madre atomica della creazione contratto. Inserisce **le sole chiavi presenti in
una whitelist interna**:

```sql
v_testata_allowed text[] := ARRAY[
    'billing_account_id', 'emittente_fiscale_id', 'istanza_utility_id',
    'utility_id', 'ambito', 'valido_dal', 'valido_al',
    'parent_contratto_id', 'data', 'listino_id',
    'tipo_variazione_globale', 'valore_variazione_globale',
    'categoria_cliente_id_snapshot', 'valuta_id',
    'fatturazione_immediata', 'meta'
];
```

I tre riferimenti dell'atto non ci sono. Il filtro è sulla **presenza della
chiave**:

```sql
SELECT array_agg(quote_ident(key) ORDER BY key)
  INTO v_cols
  FROM jsonb_object_keys(COALESCE(p_testata, '{}'::jsonb)) AS key
 WHERE key = ANY(v_testata_allowed);
```

⛔ **Quindi una chiave non whitelisted non viene respinta: viene scartata.** Il
contratto nasce, la `INSERT` riesce, il backend risponde `200`, l'operatore non
vede nessun errore — e il CIG non va da nessuna parte.

---

## 2. ⭐ Perché è la voce da fare, e non una comodità

**È lo stesso difetto già costato un giro su questa stessa funzione**, ed è
scritto nel commento della funzione e in quello di `_CREATE_KEYS_TESTATA` nel
backend:

> *«rev 2026-07-27: `fatturazione_immediata` aggiunta a `v_testata_allowed` — la
> corsia di instradamento si decide PRIMA del push in commessa e la create è il
> momento naturale; **senza questa voce la chiave veniva scartata in silenzio**»*

Ripeterlo sarebbe la forma peggiore di regressione: quella già documentata
accanto al punto in cui si ripete.

⚠️ **E il caso non è di nicchia.** Un CIG nasce con la gara, cioè **prima** del
contratto: il momento naturale per digitarlo è proprio la creazione. Oggi
l'operatore dovrebbe creare il contratto e poi rientrarci per compilarli — e nel
frattempo il piano BE/FE tiene i tre campi **nascosti in CREATE** apposta, per
non offrire caselle che il DB butta via.

---

## 3. La richiesta

**Estendere `v_testata_allowed` con `'codice_cig'`, `'codice_cup'`,
`'codice_commessa'`.** Niente altro: la funzione non ha bisogno di altre
modifiche, e le tre colonne esistono già con i loro `COMMENT`.

⚠️ **Tre avvertenze per chi lo scriverà**, tutte già emerse su questa funzione:

1. **changeSet nuovo con numerazione successiva**, e il corpo si prende dalla
   **doc auto-generata**, non dallo YAML che definisce la funzione oggi: partire
   dallo YAML farebbe regredire le revisioni intermedie — fra cui proprio la
   `rev 2026-07-27` di `fatturazione_immediata`;
2. ⭐ **qui NON c'è la trappola «chiave assente vs chiave `null`»** che vale per
   `fatturazione_immediata`. Quella colonna è `NOT NULL` con `DEFAULT false`,
   quindi un `null` esplicito diventa un 23502 e il BE deve **omettere** la
   chiave. Le tre nuove sono **nullable**: un `null` è un valore legittimo e
   significa «non c'è un CIG». Il backend può mandarle sempre;
3. 📌 il `COMMENT ON FUNCTION` va aggiornato con la nuova rev, come è stato fatto
   per `fatturazione_immediata`: è lì che questa storia è rimasta leggibile.

---

## 4. Presidio atteso

⭐ **Il test che avrebbe risparmiato il giro del 2026-07-27**, e vale sia in
pgTAP sia lato Django: creare un contratto **con** i tre codici nel payload e
**rileggerlo** — ci devono essere.

⚠️ Non basta asserire che la `INSERT` riesce: riesce anche adesso. La funzione
**non solleva**, scarta — quindi l'unico test che discrimina è quello che rilegge
il valore. È la stessa forma della controprova che il team DB ha già usato su
`I10` e su `I9`: rilanciare l'asserzione contro la versione vecchia della
funzione e vederla diventare **rossa**.

---

## 5. Cosa succede lato BE/FE quando è applicato

Slice `S3-b` del piano, e sono tre righe:

* `_CREATE_KEYS_TESTATA` in `contratti_service.py` ← le tre chiavi;
* `_build_create_data_testata` ← la chiamata a `_apply_codici_atto`, che **esiste
  già** ed è condivisa con il mapper di update (oggi è cablata solo su
  quest'ultimo, con il perché scritto accanto);
* `ContrattoDrawer.vue` ← il `v-if="isEdit"` sulla sezione «Riferimenti
  dell'atto» cade, e i campi compaiono anche in creazione.

⭐ Il test `test_create_contratto_non_mappa_ancora_i_codici_atto`
(`apps/vendite/tests/services/test_contratti_service.py`) **si inverte** in quel
momento: oggi asserisce che le tre chiavi *non* sono in `_CREATE_KEYS_TESTATA`,
ed è il segnalibro che dice dove riprendere.

---

## 6. Diario

| Data | Cosa |
| --- | --- |
| 2026-08-29 | Brief nato costruendo `I8` lato BE/FE. La metà PATCH è stata fatta senza dipendenze (passa da `_UPDATE_WRITE_COLS`, che è Python); la metà CREATE si è fermata qui. ⭐ Il difetto è **identico** a quello di `fatturazione_immediata` del 2026-07-27, sulla stessa funzione, ed è documentato nel commento che gli sta accanto |
