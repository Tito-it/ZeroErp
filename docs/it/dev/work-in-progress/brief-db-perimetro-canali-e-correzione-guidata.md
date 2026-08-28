# Brief DB — il perimetro dei canali di incasso, e la madre della correzione guidata

> **Cos'è.** Due richieste al team DB che nascono dal cantiere incassi
> ([brief-be-fe-posting-e-abbinamento-rata.md](brief-be-fe-posting-e-abbinamento-rata.md)),
> tenute in un solo documento perché si consegnano insieme ma **non sono la
> stessa cosa**:
>
> - **§1 — un difetto di perimetro**, trovato misurando il 2026-08-28 (passo
>   E-4). ⛔ Non è una rifinitura: `pagamenti.enti_incasso` non ha row security,
>   e ogni operatore vede i canali — **IBAN compreso** — di tutti gli emittenti.
> - **§2 — la funzione madre della correzione guidata** (Q-7), differita per
>   scelta il 2026-08-24 e adesso dovuta: è **l'unica cosa** che tiene aperto il
>   cantiere.
>
> ⛔ **Niente è stato applicato al database.** Questo documento è una richiesta.
> Il backend ha chiuso la sua metà (§1.4) e non tocca DDL.
>
> **Scritto il 2026-08-28**, misurando contro il database di sviluppo.

---

## 0. In una pagina

| | Cosa | Dove |
| --- | --- | --- |
| 🔴 **Il difetto** | `pagamenti.enti_incasso` ha `relrowsecurity = false` e **zero policy**. Il canale porta il conto su cui atterra il denaro, cioè **di chi sono i soldi**: senza policy, l'elenco dei canali è comune a tutti gli emittenti | §1.1 |
| ⭐ **La misura** | 4 tabelle su 12 hanno la RLS accesa. Otto no — e sei di quelle otto **è giusto** che non l'abbiano (cataloghi, matrici, tabella-ponte). Le due che restano sono `enti_incasso` e `sepa_mandati` | §1.2 |
| 🔧 **Il rimedio proposto** | Una policy `FOR ALL` sullo stampo di quella di `vendite_contabili`, con la funzione che **esiste già**: `script.fn_scope_ef_whitelist_via_ente_incasso(user, id)` | §1.3 |
| ✅ **La metà del backend** | **Fatta il 28/08**: il conti-incasso ora rifiuta un emittente fuori perimetro con `E_SCOPE_EMITTENTE` (403), presidiato da un test sul DB vero. ⚠️ Quella lettura esce dalla RLS **per costruzione** e resterà a carico del backend anche dopo la policy | §1.4 |
| ❓ **Le tre domande** | `sepa_mandati` · `centri_riscossione` · se la policy debba mordere anche in **scrittura** | §1.5 |
| 📮 **La seconda richiesta** | `fn_crea_distinta_correzione(contabile_id)` — apre una distinta nuova con le righe di **segno opposto** già dentro. ⛔ Si chiama **correzione**, mai «storno» | §2 |

---

## 1. 🔴 Il perimetro dei canali di incasso

### 1.1 Che cosa non va, e perché conta

`pagamenti.enti_incasso` è la tabella dei **canali di incasso**. Ogni riga porta
`soggetto_ruolo_conto_bancario_id` — il conto su cui atterra il denaro di quel
canale — ed è **obbligatorio su tutti i tipi**. Quella colonna esiste per una
ragione sola, che il modello dichiara a chiare lettere (D5):

> *quando mille euro arrivano in banca non hanno ancora una fattura, e il
> perimetro dell'operatore si risolve dalla fattura: senza questa colonna la coda
> «da abbinare» sarebbe invisibile a tutti. Il denaro ha un padrone dal primo
> istante — l'ha deciso il cliente scegliendo su quale conto pagare.*

⛔ **Ma la tabella che tiene quel padrone non ha row security.** Misurato il
2026-08-28:

```
 tabella                          | rls_accesa | policy
----------------------------------+------------+--------
 enti_incasso                     | f          |      0
```

Ne discende che **l'elenco dei canali è comune a tutti gli emittenti**. Non è
teoria: la schermata dei canali di incasso è stata scritta il 28/08 e mostra, per
ogni canale, il suo **IBAN** e la **utility** del conto (BE-11). Un operatore
dell'emittente A vede i conti di incasso dell'emittente B.

⚠️ **E si vede come un dato, non come un errore.** È la forma peggiore: una
lista più lunga del vero non la mette in dubbio nessuno.

### 1.2 La misura completa, e che cosa NON è un difetto

Delle dodici tabelle di `pagamenti`, **quattro** hanno la RLS accesa con una
policy:

| Tabella | RLS | Giudizio |
| --- | --- | --- |
| `vendite_contabili` · `vendite_contabili_righe` · `vendite_movimenti` · `sistemazioni` | ✅ accesa, 1 policy | Corretto: sono le tabelle **transazionali** |
| `vendite_contabili_stati` · `vendite_contabili_righe_stati` · `transizioni_stati_contabile` · `transizioni_stati_contabile_riga` | spenta | ✅ **Giusto così**: sono **cataloghi** e matrici di transizione, vocabolario comune. Metterci una policy nasconderebbe uno stato a chi ha diritto di leggerlo |
| `vendite_contabili_lotti` | spenta | 🟡 Tabella-ponte. La proteggono i due lati? Da guardare, non da assumere |
| `centri_riscossione` | spenta | ❓ Configurazione condivisa, ed è in whitelist della lookup generica. **Domanda in §1.5** |
| 🔴 `enti_incasso` | spenta | ⛔ **Il difetto**: porta dato **per emittente** |
| 🔴 `sepa_mandati` | spenta | ⛔ Stessa famiglia: ha `soggetto_ruolo_conto_id` e `billing_account_id`, più `iban_snapshot` e `intestatario_snapshot`. **Domanda in §1.5** |

⭐ **La riga che il brief BE/FE dava per vera e non lo è.** §2.6 di quel
documento dice *«le dodici tabelle di `pagamenti` hanno la RLS accesa con policy
`FOR ALL`»*. Sono **quattro**, e la riga è stata corretta il 28/08. Non è un
rimprovero a nessuno: è il motivo per cui E-4 esisteva.

### 1.3 Il rimedio proposto — e la funzione c'è già

⭐ **Non serve niente di nuovo.** `script.fn_scope_ef_whitelist_via_ente_incasso`
esiste, ed è esattamente la domanda giusta: risolve il canale → il conto → il
soggetto → l'emittente, e delega alla canonica. La catena vive dentro
`fn_resolve_emittente_fiscale_id`, che è **`SECURITY DEFINER`** — quindi una
policy che la usa **non rientra** nella row security della tabella che sta
proteggendo.

Sullo stampo esatto della policy che già esiste su `vendite_contabili`:

```sql
-- PROPOSTA, non applicata.
ALTER TABLE pagamenti.enti_incasso ENABLE ROW LEVEL SECURITY;

CREATE POLICY rls_enti_incasso_perimetro_incasso ON pagamenti.enti_incasso
    FOR ALL
    USING (
        current_setting('app.ruolo_applicativo', true) = 'OPERATORE'
        AND script.fn_scope_ef_whitelist_via_ente_incasso(
                NULLIF(current_setting('app.current_user_id', true), '')::integer,
                id)
    );
```

⚠️ **Due cose da decidere insieme al `WITH CHECK`**, e sono in §1.5.

⚠️ **Attenzione al giro in creazione**: `fn_scope_ef_whitelist_via_ente_incasso`
risolve l'emittente **partendo dall'id del canale**, che in `INSERT … RETURNING`
non esiste ancora quando la `WITH CHECK` valuta. Se la policy deve mordere anche
in scrittura, la clausola di `WITH CHECK` va scritta sul **conto**
(`fn_scope_ef_whitelist_via_sr` sul soggetto del conto) e non sull'id del canale.
⛔ È il punto in cui una policy scritta di fretta rende la tabella non
scrivibile, e l'errore sembra un difetto dell'applicazione.

### 1.4 ✅ La metà che era del backend è già fatta

C'è una seconda porta sullo stesso perimetro, e **quella non la chiude nessuna
policy**: `GET /api/v1/pagamenti/conti-incasso/?soggetto_ruolo_id=…`, l'elenco
dei conti agganciabili a un canale. Legge
`anagrafiche.soggetti_ruoli_conti_bancari`, che ha la row security **spenta di
proposito** — lo dice il commento di
`trgfn_enti_incasso_guard_conto_incasso`. Su quella lettura il database non
filtra niente: se il perimetro non lo mette il backend, non lo mette nessuno.

⛔ **Misurato, non immaginato.** Prima del rimedio:

```
operatore EF 32 -> soggetto 72  : LETTO   (IT00TESTINCASSO0000000001)
operatore EF 32 -> soggetto 159 : LETTO   (IT00TESTINCASSO0000000002)   ⛔ dell'altro emittente
```

Dopo:

```
operatore EF 32 -> soggetto 72  : LETTO (1 conto)
operatore EF 32 -> soggetto 159 : RIFIUTATO (E_SCOPE_EMITTENTE, 403)
operatore EF 44 -> soggetto 72  : RIFIUTATO (E_SCOPE_EMITTENTE, 403)
operatore EF 44 -> soggetto 159 : LETTO (1 conto)
admin globale   -> entrambi     : LETTO
SENZA contesto  -> soggetto 72  : RIFIUTATO (E_SCOPE_EMITTENTE, 403)
```

Il cancello sta nel **repository**, accanto all'SQL e nello stesso posto di
`_guard_canale_sistema`, con un test che gira sul database provvisto
(`ZEROERP_TEST_DB_E2E=1`) e che **è stato provato rimettendo il difetto**:
diventa rosso.

⚠️ **Due cose che vale la pena sapere, per chi scriverà altre letture così.**

1. `script.fn_check_user_emittente_scope` risponde **`true`** quando
   `p_auth_user_id` è `NULL` (regola 1, «job batch»). Delegarle la domanda su un
   percorso senza GUC **apre** il perimetro invece di chiuderlo. Il backend
   quindi rifiuta **prima**, se non c'è utente: «non so chi sei» vale **no**.
2. La GUC si chiama **`app.current_user_id`**, non `app.auth_user_id`. Col nome
   sbagliato `current_setting` risponde `NULL` e il cancello rifiuta *tutti*,
   compreso chi ha diritto — ⚠️ e i test col doppio restano **verdi**, perché un
   doppio non ha un perimetro.

### 1.5 ❓ Le tre domande

| | Domanda | Perché la chiedo invece di decidere |
| --- | --- | --- |
| **P-1** | `sepa_mandati` va sotto RLS? | Ha `soggetto_ruolo_conto_id`, `billing_account_id`, `iban_snapshot` e `intestatario_snapshot`: sembra dato **per cliente e per emittente**. ⚠️ Ma è una tabella che il cantiere incassi **non usa**, e non conosco chi la legge: una policy messa alla cieca può rendere invisibile una coda a chi ci lavora |
| **P-2** | `centri_riscossione` va lasciata comune? | Oggi è comune, è in whitelist della lookup generica e la schermata dei canali la usa come tendina. ⭐ Se i centri sono **condivisi fra emittenti** va lasciata così; se sono **di un emittente** allora la tendina di apertura distinta sta proponendo centri altrui — ed è un secondo difetto, non una domanda |
| **P-3** | La policy morde anche in **scrittura**? | La `USING` basta per la lettura. Un `WITH CHECK` impedirebbe di **creare** un canale sul conto di un altro emittente — che oggi è impedito solo dal fatto che nessuno lo prova. ⚠️ E va scritto sul **conto**, non sull'id (§1.3) |

---

## 2. 📮 La funzione madre della correzione guidata (Q-7)

### 2.1 Il gesto, e perché non esiste ancora

Q-7 è chiusa da Tid il 2026-08-24 sulla strada **(a)**: un'azione «Correggi» su
una distinta **registrata** apre una distinta **nuova** con le righe di **segno
opposto già precompilate**. ⛔ Non ricopiatura a mano: su venti righe è lì che
nasce il secondo errore.

⭐ **La correzione non è un documento speciale** (D3-d): è una contabile con
importi di segno opposto. Non serve un tipo nuovo, non serve uno stato nuovo.

⛔ **Non è una sistemazione, e la differenza è il punto.** Le sistemazioni
decidono che fare di un'eccedenza **vera** — denaro davvero arrivato in più. La
correzione rimedia a una registrazione **sbagliata** — un importo digitato male.
Due mestieri: confonderli significherebbe registrare come credito del cliente un
errore di battitura.

⛔ **E si chiama correzione, mai «storno».** `STORNATA` è stata ritirata dal
catalogo il 21/08 e rimetterne la parola nell'interfaccia riaprirebbe una porta
che il lotto 2 ha chiuso.

### 2.2 Perché serve una madre, e non un ciclo nel backend

Precompilare significa creare **N righe in un colpo**, dentro una distinta nuova,
in modo atomico. Un ciclo nel service produrrebbe una distinta a metà se qualcosa
si rompe a metà elenco — cioè esattamente il documento che nessuno sa più
leggere. È la stessa ragione per cui il posting è **una sola `SELECT`**.

### 2.3 La firma proposta

```sql
-- PROPOSTA, non applicata.
CREATE FUNCTION pagamenti.fn_crea_distinta_correzione(
    p_contabile_id  bigint,
    p_data_contabile date DEFAULT CURRENT_DATE,
    p_motivo        text DEFAULT NULL
) RETURNS TABLE (
    contabile_id  bigint,   -- la distinta NUOVA
    righe_create  integer,
    esito         text      -- 'CREATA' | 'NULLA_DA_CORREGGERE'
)
```

**Che cosa dovrebbe fare**, come lo vedo dal lato che la chiamerà:

1. la distinta di partenza dev'essere **registrata** (`CHIUSA`): correggere una
   bozza non ha senso — si modifica e basta;
2. apre una distinta nuova **sullo stesso centro e sullo stesso canale**, in
   `BOZZA`, con `origine = 'MANUALE'`;
3. per ogni riga **postata** dell'originale crea una riga con `importo` di segno
   opposto, conservando `data_pagamento`, `riferimento_ente` e — ⚠️ questa è la
   domanda vera — **l'abbinamento** a fattura e rata;
4. lascia una traccia del legame fra le due distinte;
5. ⭐ **non registra niente**: la distinta nuova nasce in bozza e la registra una
   persona, guardandola. Precompilare è un aiuto, non una decisione.

### 2.4 ❓ Le quattro domande su cui non decido io

| | Domanda | Perché conta |
| --- | --- | --- |
| **C-1** | La riga di correzione nasce **già abbinata** alla stessa rata, o `DA_ABBINARE`? | ⭐ È la domanda di modello. Già abbinata: il giro si chiude da sé e il saldo torna subito. `DA_ABBINARE`: qualcuno deve rilavorare N righe, e la correzione «guidata» guida a metà. ⚠️ Ma già abbinata significa **scrivere un abbinamento che nessuno ha scelto** |
| **C-2** | Che cosa si fa delle righe **non postate** dell'originale (sospese, scartate)? | Non hanno prodotto movimenti, quindi non c'è niente da correggere — ma ignorarle in silenzio lascia l'operatore a chiedersi dove sono finite. Preferirei che l'esito lo **dicesse** |
| **C-3** | Dove vive il legame fra le due distinte? | Una colonna `contabile_corretta_id`, una riga in `vendite_contabili_lotti`, o solo `meta`? ⚠️ Se il legame sta in `meta` non lo interroga nessuno |
| **C-4** | Si può correggere **due volte** la stessa distinta? | Il caso c'è (una correzione sbagliata), ma senza un vincolo si moltiplicano le distinte gemelle. Un `UNIQUE` sul legame lo chiuderebbe |

⚠️ **E una richiesta di forma, non di sostanza**: qualunque rifiuto abbia un
**codice a catalogo** con il suo ripiego. Un codice non registrato cade su
`E_GENERICO`, cioè su un **500**, e il cantiere ci ha già pagato una volta.

---

## 3. Che cosa faccio appena rispondete

| Se la risposta è | Il backend fa |
| --- | --- |
| §1 policy applicata | Rimisuro E-4 sui due operatori e **tolgo la riga sbagliata** da §2.6 del brief BE/FE, che a quel punto diventa vera |
| P-2 «i centri sono di un emittente» | Aggiungo il filtro alla tendina dei centri e lo segnalo come secondo difetto trovato |
| §2 madre scritta | Slice della **correzione guidata**: una rotta (`POST /distinte/{id}/correggi/`), il pulsante sulla distinta registrata, e la distinta nuova che si apre subito nel drawer |
| §2 «non adesso» | Il cantiere si chiude senza quel gesto, e la riga resta 🔴 nel brief. ⛔ Non lo si sostituisce con «apri una distinta e digita i negativi»: è la strada (b), che Tid ha scartato |

---

## 4. Registro delle revisioni

| Data | Cosa |
| --- | --- |
| **2026-08-28** | Stesura. §1 nasce dal passo **E-4** del brief BE/FE («riverifica di tutte le liste sotto RLS, dentro e fuori perimetro, e si guarda la differenza»): la riverifica ha trovato che `enti_incasso` non ha row security e che l'elenco dei conti agganciabili usciva dal perimetro — **misurato su due operatori di due emittenti veri**, non dedotto. La metà del backend è chiusa lo stesso giorno, con un test sul DB provvisto provato rimettendo il difetto. §2 formalizza la richiesta differita di Q-7 |
