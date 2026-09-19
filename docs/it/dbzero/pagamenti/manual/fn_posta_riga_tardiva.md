## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_posta_riga_tardiva`

> 👀 **Vedi anche**
>
> **La madre gemella:** [pagamenti.fn_posta_contabile](/dbzero/pagamenti/funzioni/fn_posta_contabile) — il posting di una distinta intera
>
> **I guard che attraversa:**
>
> • [trgfn_vendite_contabili_righe_guard_distinta_finale](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_distinta_finale) — la quarta mossa, e la sua **porta**
> • [trgfn_vendite_contabili_righe_guard_rata](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_rata) — coerenza e capienza, col doppio tempo
> • [trgfn_vendite_contabili_righe_guard_stato_dati](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_stato_dati) · [trgfn_vendite_contabili_righe_guard_transizione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_transizione)
> • [trgfn_vendite_movimenti_sync_contabile_from_riga](/dbzero/pagamenti/funzioni/trgfn_vendite_movimenti_sync_contabile_from_riga) — il mirror che deriva i riferimenti del movimento dalla riga
>
> **Approfondimento tabelle:** [vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) · [vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)
>
> **Piano:** [brief-db-validata-e-registrazione-tardiva](/dev/work-done/brief-db-validata-e-registrazione-tardiva) §2.2 (D20-b), §4 P-5, §4.1

---

### 🎯 Scopo Principale
(scritta il 18-09-2026)

Registra **in ritardo** una riga contabile rimasta **`SOSPESA`** sotto una distinta
**già registrata**: la abbina — fattura, cliente, rata facoltativa, forzatura a
due tempi — e la registra **nello stesso gesto**. Movimento scritto, riga a
`POSTATA`, distinta che **resta `CHIUSA`** e non tocca `data_conferma` /
`user_conferma`.

È la strada del «resto» di D3-a (*«registra il pronto, lascia lì il resto»*).
Dalla chiusura automatica in poi il resto **non ne aveva**: sotto una `CHIUSA`
la quarta mossa rifiuta a qualunque riga di diventare pronta, la correzione
salta le non postate, nessun verbo la sposta altrove — una sospesa poteva solo
restare, o oscillare con `SCARTATA`. *Il buco è la somma di tre decisioni giuste
prese in momenti diversi* (brief §1).

---

### Chi chiama, e che cosa passa

```sql
SELECT * FROM pagamenti.fn_posta_riga_tardiva(
    p_riga_id            => 4711,
    p_fattura_id         => 820,
    p_billing_account_id => 31,
    p_scadenza_id        => 1290,          -- facoltativa
    p_forzata            => false,         -- il primo tempo
    p_motivo_forzatura   => NULL);
```

Risponde **una riga**: `movimento_id, riga_id, importo, esito` (`'POSTATA'`).

Chi la chiama è **solo** il verbo BE `POST /pagamenti/righe/{id}/registra/`
(BE-3) — dalla coda «Sospese» quando la distinta è registrata («Abbina e
registra») e dal drawer di una distinta chiusa — con lo **stesso cancello della
registrazione** (`registra_distinta`): rovescia denaro. ⛔ **Mai un job**: la
tardiva è una **decisione** di chi ha identificato il denaro.

---

### ⭐ Passa da `ABBINATA`, e alla quarta mossa si presenta

La madre non porta la riga da `SOSPESA` a `POSTATA` in un colpo. La porta prima
ad **`ABBINATA`** con la destinazione, così girano **tutti** i guard
dell'abbinamento normale: la transizione (`SOSPESA → ABBINATA` è in matrice), i
dati (fattura e cliente), la **rata** — coerenza rifiutata, capienza col doppio
tempo: primo tentativo senza forzatura → `E_RIGA_CONTABILE_CAPIENZA_SUPERATA`
(`confirm_and_retry`), secondo con `forzata = true` — e lo scope.

Alla **quarta mossa** del guard sulla distinta finale — che rifiuterebbe l'ingresso
in uno stato pronto sotto una `CHIUSA` — si **presenta** con la GUC transazionale
`app.registrazione_tardiva_riga_id = <id>` (`set_config(…, true)`): il guard apre
**solo** per quella riga, **solo** in quella transazione, **solo** nel ramo del
cambio di stato. Precedente in casa: `app.cessazione_automatica`. ⚠️ La porta si
**richiude in coda alla madre**, non al `COMMIT`: dopo il ritorno nessun'altra
scrittura la trova aperta.

Poi il **movimento**, poi **`POSTATA`**: tre statement separati con `WHERE id =
<id>` — con la RLS attiva padre e figlio nella stessa snapshot non si vedono, la
stessa ragione dei due statement della madre del posting.

**Perché così e non altrimenti** (brief §2.2):

| Alternativa | Perché no |
| --- | --- |
| ricreare la riga in una distinta «di recupero» | raddoppia l'euro: una scartata il giorno 1, una nuova il giorno 30, più un legame per non contarla due volte |
| allentare la quarta mossa (`ABBINATA` ammessa sotto `CHIUSA`, poi «Registra riga») | riapre esattamente il caso che la mossa chiude — una riga «in lavorazione» nei saldi che aspetta qualcuno |
| `SOSPESA → POSTATA` diretta in matrice | salta il guard della capienza, che gira solo entrando in uno stato pronto |

---

### Le date del movimento, e l'audit

`data_effettiva = COALESCE(data_pagamento della riga, data_contabile della
testata)`; `data_contabile` della testata; **`data_registrazione` e
`data_contabilizzazione = oggi`** — è registrata **oggi**: la testata porta la data
della *prima* registrazione, il movimento la sua. `meta.origine =
'POSTING_TARDIVO'`: nel giornale si distingue dal `POSTING` della madre.
Fattura, cliente, distinta e rata **non si passano**: li deriva dalla riga il
mirror, che a quel punto li ha.

La distinta **non cambia**: stato, `data_conferma`, `user_conferma` restano quelli
della prima registrazione. La **quadratura del giorno regge**: la riga era già
contata (D12-e conta tutte le righe attive, sospese comprese). Chi ha registrato
tardi sta sull'audit del movimento.

---

### ⛔ Nessun `NULLA_DA_POSTARE`

A differenza della madre del posting, una tardiva su una riga che non si può
registrare è un **rifiuto**, non un esito: chi preme ha identificato quel denaro,
e *«non ho fatto niente»* detto con un 200 sarebbe una bugia.

### ⚠️ Error handling

| Codice | Classe | Quando |
| --- | --- | --- |
| `E_PAGAMENTI_CHIAMATA_NON_VALIDA` | TECNICO | riga o fattura nulle o `<= 0`, cliente o rata `<= 0`: un chiamante rotto (il backend valida il form prima). Il cliente a `NULL` **non** è un guard di qui: risponde il guard sui dati entrando in `ABBINATA`, col campo |
| `E_RIGA_CONTABILE_NON_TROVATA` | NON_TROVATO | la riga non si legge — inesistente o di un altro, no-leak |
| `E_RIGA_CONTABILE_TARDIVA_STATO` | CONFLITTO_STATO | la riga non è attiva o non è `SOSPESA`: da `SCARTATA` si passa prima da «Riprendi»; da `POSTATA` il movimento c'è già |
| `E_RIGA_CONTABILE_TARDIVA_DISTINTA_NON_REGISTRATA` | CONFLITTO_STATO | la distinta non è registrata (finale **e** con `data_conferma`): annullata, chiusa senza registrazione, o ancora aperta — *«usa il giro normale»* |
| `E_RIGA_CONTABILE_CAPIENZA_SUPERATA` · `E_RIGA_CONTABILE_RATA_INCOERENTE` · `E_RIGA_CONTABILE_ABBINAMENTO_INCOMPLETO` | — | dai guard dell'abbinamento, com'è sul giro normale |
| `E_CONTABILE_STATO_NON_CONFIGURATO` | TECNICO | manca a catalogo `ABBINATA` o `POSTATA` |

Forzatura senza motivo **ammessa** (Q-8), come sull'abbinamento normale.

### Presidio

`db/pgtap/pagamenti/test-posta-riga-tardiva-v1.sql` — 20 asserzioni: il caso
buono con i suoi cinque invarianti (movimento, riga, testata invariata, somma
invariata, saldo della rata), il doppio tempo della capienza, i quattro rifiuti,
e la **porta** (un `UPDATE` a mano resta rifiutato; la GUC su un altro id non
apre; dopo la madre è vuota).

{% include-markdown "signature-core.md" %}
