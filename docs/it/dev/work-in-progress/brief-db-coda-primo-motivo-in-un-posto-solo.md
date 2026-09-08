# Brief DB — la coda che si ripete: sollevare il primo motivo in un posto solo

> **Destinatario:** team DB (`dev/db-tid`). Aperto il 2026-09-08.
>
> **In una riga:** dieci punti del database sollevano il **primo motivo** di una
> `fn_check_*` con le stesse cinque righe copiate. Le righe non sono il problema:
> dentro ci stanno **tre convenzioni che, sbagliate, non fanno fallire niente**.
>
> **Origine.** Non da un difetto in campo: dalla domanda di Tid del 2026-09-08,
> durante il cantiere della chiave del contatore — *«queste funzioni ormai sono
> molto simili, possono essere unificate in una sola?»*. La risposta sulle due
> guard di `registri_fatturazione` è **no** (§3), ma la misura fatta per
> rispondere ha trovato la duplicazione vera, che sta **altrove e su cinque
> tabelle**. Perimetro suo, per decisione di Tid nella stessa conversazione.
>
> ⛔ **Nessuna misura decide niente qui.** I conteggi sono **fatti datati** e
> servono a un uso solo: dire quanto è largo il perimetro. A decidere è la
> struttura.
>
> **Correlati:**
> [brief-db-registri-numerazione-chiave-del-contatore](../work-done/brief-db-registri-numerazione-chiave-del-contatore.md) — il cantiere in cui la domanda è nata ·
> [linee-guida-sql §12.5](../../linee-guida-sql.md) — le azioni per riga, dove la regola «la madre CHIAMA la check» è scritta

---

## 1. ⭐ Cosa si estrae davvero — non le righe, le convenzioni

La coda è questa, identica in dieci punti:

```sql
v_primo := v_motivi -> 0;
PERFORM script.fn_log_and_raise_error(
    'area', 'funzione', v_primo ->> 'codice',
    COALESCE(v_primo -> 'dettaglio', '{}'::jsonb)
        || jsonb_build_object('campo', 'nome_colonna'),
    NULL::uuid,
    VARIADIC ARRAY(SELECT jsonb_array_elements_text(v_primo -> 'valori')));
```

⛔ **Quattro righe risparmiate per sito non valgono un building block.** Il
motivo per farlo sono le **tre cose che ci stanno dentro e che sbagliano in
silenzio** — nessuna delle tre fa fallire qualcosa, tutte e tre producono un
messaggio o un log sbagliato:

| Cosa | Se si sbaglia | Chi se ne accorge |
| --- | --- | --- |
| **`-> 0`** — si solleva il **primo** motivo | il tooltip della maschera dice una cosa e l'errore un'altra: l'ordine dell'array **è il contratto** (§12.5.2) | nessuno, finché un utente non li legge entrambi |
| **il `tx_id`** — dipende dalla **fase** del trigger (§5) | l'errore finisce nel log **senza** la transazione che l'ha prodotto, o con una che non è la sua | nessuno: `dbops.error_log` si riempie lo stesso |
| **lo spacchettamento del `VARIADIC`** | passando il `jsonb` invece dell'array di testo, i `%s` del messaggio si riempiono male — arità giusta, **frase falsa** | solo chi **legge la frase resa** |

⚠️ E la terza ha già morso: il 2026-09-01, su
`E_REGISTRO_SERIE_NON_AMMESSA`, a video usciva *«Registro X1»* dove `X1` era la
**serie**. Due segnaposto, due valori, nessun cancello rosso.
⚠️ La seconda ha un precedente registrato pure lei: **`fn_log_and_raise_error`
chiamata con cinque argomenti non risolve** — il `VARIADIC` va passato sempre,
anche vuoto.

⇒ **Un posto solo, con un test suo.** È la ragione dell'estrazione; le righe in
meno sono un effetto collaterale.

---

## 2. Il censimento — fatto datato, 2026-09-08

**Dieci punti di chiamata in dieci funzioni** (uno ciascuna), su **cinque**
tabelle e **due** schemi:

| Funzione | Natura | Passa `campo` | `tx_id` |
| --- | --- | :---: | --- |
| `anagrafiche.trgfn_soggetti_titoli_iva_ambiti_guard` | trigger `_z90_` | ✅ | `NEW.tx_id` |
| `anagrafiche.trgfn_soggetti_titoli_iva_guard_ambito` | trigger `_z90_` | ✅ | `NEW.tx_id` |
| `anagrafiche.trgfn_stiva_movimenti_guard_annullo` | trigger `_a10_` | ⛔ | `NEW.tx_id` ⚠️ |
| `vendite.trgfn_famiglie_documento_guard_disattivazione` | trigger `_a10_` | ⛔ | `NULL::uuid` |
| `vendite.trgfn_famiglie_documento_guard_struttura` | trigger `_a10_` | ✅ | `NULL::uuid` |
| `vendite.trgfn_registri_fatturazione_guard_forma_numero` | trigger `_a10_` | ✅ | `NULL::uuid` |
| `vendite.trgfn_registri_fatturazione_guard_serie_ammessa` | trigger `_a10_` | ✅ | `NULL::uuid` |
| `anagrafiche.fn_annulla_movimento_titolo_iva` | madre | ⛔ | `NULL::uuid` |
| `anagrafiche.fn_guard_ba_cambio_emittente` | madre | ⛔ | `NULL::uuid` |
| `vendite.fn_annulla_accredito_riga_reso` | madre | ⛔ | `NULL::uuid` |

⚠️ **Si conta per PUNTO DI CHIAMATA, non per funzione**: tre di queste
sollevano in più rami (fino a sei volte), e solo **uno** per funzione è la coda
del primo motivo. Il resto sono rifiuti con codice fisso, che **non entrano** in
questo cantiere.

⚠️ **E il perimetro cresce da sé**: il cantiere della chiave del contatore ne ha
aggiunto uno il 2026-09-01 e ne stava aggiungendo un altro il 2026-09-08. Chi
scrive una `fn_check_*` copia la coda dalla guard accanto — è così che si arriva
a dieci senza che nessuno abbia deciso niente.

---

## 3. ⛔ Cosa NON si unisce, ed è la domanda da cui si è partiti

Le due guard di `registri_fatturazione` **sembrano** gemelle e non lo sono:

| | `guard_serie_ammessa` | `guard_forma_numero` |
| --- | --- | --- |
| evento | `INSERT` + `UPDATE OF (serie_default, famiglia_documento)` | `UPDATE OF (prefisso, suffisso, lunghezza_numero, anno_nel_numero)` |
| `campo` nel contesto | `serie_default` | il campo della forma |
| domanda | «questa famiglia registra la serie?» | «questo sezionale ha già numerato?» |

⛔ **La clausola `UPDATE OF` è portante, non decorativa**: è ciò che tiene il
guard fuori dai piedi del mirror CSV che riscrive quelle righe a ogni migrate.
Unendole, il trigger si sveglierebbe sull'**unione** delle colonne e ogni regola
dovrebbe ricontrollare da sé se la riguarda — più codice, non meno, e due
confronti di no-op invece di uno.
⛔ **E il `campo` è uno per regola**: è il canale che accende l'input giusto nel
form. Un campo solo per due regole accende quello sbagliato.

⭐ **La lezione generale, che è il motivo per cui questo §3 sta qui**: *due
funzioni che finiscono uguali non sono due funzioni da unire — sono due funzioni
che chiamano la stessa cosa.* Si estrae la coda, non si fondono le teste.

---

## 4. La forma dell'helper

```sql
script.fn_raise_primo_motivo(
    p_area     text,
    p_funzione text,
    p_motivi   jsonb,
    p_campo    text DEFAULT NULL,
    p_tx_id    uuid DEFAULT NULL) RETURNS void
```

* ⭐ **Tace su un array vuoto.** `[]` o `NULL` ⇒ non fa niente. Così il sito
  chiamante perde anche l'`IF`, e diventa una riga sola. ⛔ E non è fail-open:
  «nessun motivo» è esattamente la risposta che dice *passa*;
* **`p_campo` NULL ⇒ la chiave `campo` non entra nel contesto**, perché cinque
  dei dieci non la passano e su un errore `TECNICO` non c'è nessun campo da
  accendere;
* `SECURITY INVOKER`, `VOLATILE` (scrive nel log attraverso la madre);
* ⛔ **Non normalizza né inventa niente**: prende il primo elemento e lo passa.
  Se un giorno servisse sollevarne un altro, la regola da cambiare è **l'ordine
  dell'array nella check**, che è dove il contratto vive.

⚠️ **Cosa NON entra nell'helper**: l'`IF` di uscita anticipata del guard
(`RETURN NEW`), i confronti di no-op sui valori e la scelta di quale check
chiamare. Sono la **testa**, e la testa è diversa in ognuno dei dieci.

---

## 5. ⚠️ La variante del `tx_id`, e la regola che la scioglie

Sette punti passano `NULL::uuid`, tre passano `NEW.tx_id`. Non è disordine: **la
fase del trigger decide**, e la regola si deriva.

| Fase | Quando scatta | `tx_id` |
| --- | --- | --- |
| `_a10_` | **prima** di `trg_*_gen_tx_id_ins_upd` (ordine alfabetico: `a10` < `gen`) | ⇒ `NEW.tx_id` è **NULL**: si passa `NULL::uuid` e lo si dichiara |
| `_z90_` | **dopo** quel trigger | ⇒ `NEW.tx_id` **c'è**, e passarlo è giusto |

✅ I due `_z90_` di `anagrafiche` fanno la cosa giusta.
🟠 **`trgfn_stiva_movimenti_guard_annullo` è `_a10_` e passa `NEW.tx_id`.** Non
è un difetto di comportamento — lì quel valore è NULL, quindi il log riceve NULL
in entrambi i casi — ma è **una riga che afferma una cosa falsa**: sembra portare
la transazione e non la porta. Il giorno che quel guard passasse a `_z90_`, o che
qualcuno copiasse quella riga in una madre, la differenza diventerebbe vera.
⇒ Si sana passando l'helper, che il parametro ce l'ha esplicito.

---

## 6. Il piano

| Passo | Cosa | Dove |
| --- | --- | --- |
| **H-1** | `script.fn_raise_primo_motivo` | `20_code/script` |
| **H-2** | I sette **trigger** riscritti per chiamarla — uno per changeSet, e i pgTAP della tabella rilanciati a ogni passo | `20_code/<schema>` |
| **H-3** | Le tre **madri**, stessa forma | `20_code/<schema>` |
| **P-1** | Il pgTAP dell'helper: primo motivo, array vuoto, `campo` assente, `VARIADIC` con zero e con più valori | `db/pgtap/script` |
| **P-2** | ⭐ Il presidio che tiene chiuso il rubinetto (§7) | `db/pgtap/script` |

⚠️ **Uno per changeSet e non un giro solo.** Sono dieci funzioni vive su cinque
tabelle: un changeSet unico che le riscrive tutte è un rosso che non dice quale.
⛔ E il corpo di ognuna si prende dalla **funzione viva**, non dagli YAML.

---

## 7. ⭐ I presidi — e il rubinetto conta più della bonifica

1. **L'helper fa quel che dice**: il pgTAP di `P-1`, coi casi limite.
2. ⭐⭐ **Il rubinetto**: un presidio che conta i punti di chiamata rimasti con
   la coda copiata e **pretende zero**, derivato da `pg_proc` come già fa il
   guardrail dei codici errore. Senza, la bonifica di oggi si riempie di nuovo —
   *«rincorrere gli esistenti senza chiudere il rubinetto è la forma in cui
   questi registri non calano mai»*.
   ⚠️ A soglia decrescente finché H-2/H-3 non sono finiti: **può solo calare**,
   come il debito dei `throws_ok` senza SQLSTATE.

⛔ **Cosa NON si prova con un test**: che il messaggio rendine bene. Quello si
guarda **leggendo la frase resa**, ed è la ragione per cui questo cantiere
esiste — un cancello sull'arità non lo vedrebbe.

---

## 8. ⛔ Cosa non si tocca

* **Le teste dei dieci guard**: quale check chiamare, su quali colonne, con quale
  no-op. Restano dove sono, ed è il §3.
* **`script.fn_log_and_raise_error`**: la firma non cambia. L'helper la **chiama**,
  non la sostituisce, e chi indaga continua a trovare quel nome nei corpi.
* **L'ordine dell'array dei motivi**: è il contratto della `fn_check_*`, e si
  cambia lì.
* **Le `fn_check_*`**: hanno predicati diversi, non c'è niente da unire.
* **Nessuna migrazione si applica** senza che Tid lo dica, per quel comando.
