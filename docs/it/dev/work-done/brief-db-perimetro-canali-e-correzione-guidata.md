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
>
> ✅ **CHIUSO il 2026-08-28**, lo stesso giorno. Il team DB ha consegnato
> entrambe le richieste (§3-bis), il backend e il frontend le hanno consumate
> (§10.9 e registro del brief BE/FE), e la correzione guidata e' il gesto che
> chiude il cantiere incassi.
>
> 🔵 **Due cose restano, e nessuna delle due e' codice**:
>
> * **C-1** — le righe di correzione nascono con fattura e rata compilate ma in
>   `DA_ABBINARE`. E' la quarta strada trovata dalla misura del team DB, ed e'
>   quella implementata; ⚠️ **la decisione formale e' di Tid** (§5.8).
> * **P-1** — `sepa_mandati` sotto RLS: 🔵 *non ora, e non con quel predicato*
>   (§5.4). Quando quella tabella avra' un consumatore, si riapre da li'.

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

## 5. ✅ Risposte del team DB — misurate il 2026-08-28

> ⭐ **La diagnosi di §1 regge**: `enti_incasso` non ha row security, la tabella
> porta dato **per emittente**, e la funzione giusta esiste già. Il piano è
> **§2.3-quater e §6.17** del [piano DB](brief-db-posting-e-abbinamento-rata.md).
> Qui stanno le risposte, e **tre correzioni** che cambiano cosa si scrive.

### 5.1 🔴 La policy proposta, così com'è, rende la tabella NON SCRIVIBILE

⛔ È la cosa più importante di questa risposta. Una policy `FOR ALL` **senza**
`WITH CHECK` usa la `USING` anche per le righe nuove. E la `USING` proposta
chiede `fn_scope_ef_whitelist_via_ente_incasso(user, id)`, che risolve
l'emittente **rileggendo `enti_incasso` per quell'id**.

⚠️ **Il motivo vero non è che «l'id non esiste ancora»** (§1.3): l'id c'è, lo
mette il default prima del controllo. È che **la riga non è ancora visibile** a
una query che parte da dentro lo stesso comando — la funzione risolve `NULL`,
la canonica risponde `false`, e ogni `INSERT` viene rifiutato. È la stessa
famiglia della trappola RLS+CTE già pagata dal progetto: *chi legge dentro il
comando che scrive non vede ciò che quel comando sta scrivendo*.

⭐ **Il rimedio è più semplice della diagnosi**: un predicato **solo**, scritto
sul **conto** — che è una colonna della riga (`NOT NULL`) e punta a una tabella
senza row security. Vale identico in lettura e in scrittura, quindi `USING` e
`WITH CHECK` dicono la stessa cosa e non ci sono due formulazioni della stessa
regola da tenere allineate.

```sql
-- La forma che il piano DB realizza (S6-1).
USING / WITH CHECK:
    current_setting('app.ruolo_applicativo', true) = 'OPERATORE'
    AND EXISTS (
        SELECT 1 FROM anagrafiche.soggetti_ruoli_conti_bancari src
         WHERE src.id = enti_incasso.soggetto_ruolo_conto_bancario_id
           AND script.fn_scope_ef_whitelist_via_sr(
                   NULLIF(current_setting('app.current_user_id', true), '')::integer,
                   src.soggetto_ruolo_id))
```

✅ `fn_scope_ef_whitelist_via_ente_incasso` **resta** e non è sprecata: la usa la
policy di `vendite_contabili`, dove l'`ente_incasso_id` è una colonna della riga
e il giro non si richiude su sé stesso.

### 5.2 ⚠️ Un buco che la policy nuova EREDITA, e che non è suo

`script.fn_check_user_emittente_scope` risponde **`true`** con
`p_auth_user_id` a `NULL` — lo avete scritto in §1.4 per la vostra lettura, ma
vale anche **dentro le policy**: se `app.current_user_id` è vuota, il predicato
di scope diventa vero e l'unico cancello rimasto è il primo congiunto
(`ruolo_applicativo = 'OPERATORE'`).

⚠️ **Non è un difetto introdotto da questa policy: ce l'hanno tutte e quattro
quelle già in esercizio.** Lo si scrive perché una policy in più su uno stampo
condiviso è il momento in cui lo stampo va guardato, non perché blocchi
qualcosa. ⛔ Non si «corregge» in questo giro: cambiare la regola 1 di quella
funzione tocca ogni percorso batch del progetto, ed è un cantiere suo.

### 5.3 ✅ P-2 — risposta dal modello, non dall'opinione

`pagamenti.centri_riscossione` **non ha nessuna colonna di emittente**: `id,
codice, codice_interno, descrizione, is_compensazione, is_fondo_fattura, attivo,
meta` più l'audit. ⇒ I centri sono **condivisi per costruzione**, non per scelta
non rivista: non c'è nessun secondo difetto, e la tendina dell'apertura distinta
non propone niente di altrui. ⛔ Nessuna policy: metterla vorrebbe dire prima
inventare un proprietario che il modello non ha.

### 5.4 🔵 P-1 — `sepa_mandati`: sì un giorno, ma **non con quel predicato**

⚠️ La somiglianza con `enti_incasso` è apparente e porta fuori strada.
`soggetto_ruolo_conto_id` su un mandato è il conto **da addebitare**, cioè quello
del **cliente**: risolvere l'emittente da lì darebbe il cliente, non
l'emittente. Il commento della tabella lo dice — *«legati a conto di ruolo e
perimetro **BA/istanza utility**»* — e il perimetro giusto è quello del
**billing account**, come per le fatture.

📊 Misurato: **0 righe**, **zero** consumatori in `backend/` e `frontend/`, un
solo trigger di guard nel database. ⇒ **Non adesso**: una policy su una tabella
che nessuno legge non protegge niente e fissa un predicato prima che il cantiere
che la userà abbia deciso la sua forma. Resta il *pezzo di modello orfano* che il
brief madre dichiara da agosto.

### 5.5 ✅ P-3 — sì, e non è una scelta

Vedi §5.1: senza `WITH CHECK` la tabella non si scrive. Con il predicato sul
conto, la scrittura è presidiata **gratis** — e impedisce di creare un canale sul
conto di un altro emittente, che oggi non impedisce nessuno.

### 5.6 🟡 `vendite_contabili_lotti` — misurata, e va bene com'è

È la tabella-ponte fra distinta e lotto: due FK e nient'altro. ⛔ Nessun dato
proprio, quindi niente da nascondere; e le due tabelle che collega hanno
entrambe il loro perimetro. ⭐ Ma vale la nota generale: **un ponte senza policy
dice che un legame esiste**, e su volumi veri quello è già un'informazione. Oggi
`vendite_contabili` ha 0 righe: si guarderà quando ne avrà.

### 5.7 ⚠️ Una correzione di inquadramento su §1.1

*«Un operatore dell'emittente A vede i conti di incasso dell'emittente B»* — ✅
sarà vero, **non lo è oggi**: `pagamenti.enti_incasso` ha **0 righe**. ⭐ E la
conseguenza è a favore: si chiude la porta **prima** che ci passi qualcosa,
quindi niente bonifica, nessun dato da correggere, e la policy nasce su una
tabella vuota — il momento più economico che esista per accenderla.

---

### 5.8 📮 Le quattro domande della madre (C-1…C-4)

| | Risposta del team DB | Perché |
| --- | --- | --- |
| **C-1** | 🔴 **DOMANDA APERTA — la mia prima risposta era sbagliata, e l'ha smentita la prova** | ⛔ Avevo scritto «già abbinata, e il guard la regge per costruzione». **Falso, misurato il 28/08**: una riga `-100` su una rata **saldata dal movimento che si sta correggendo** viene **RIFIUTATA** — «restano 0.00 da regolare: un importo di -100.00 non ci rientra». R = 0 non è spazio in nessuna direzione, e il commento del guard lo dice. ⇒ «Già abbinata» è possibile **solo** scrivendo anche `forzata = true`, cioè **forzando al posto dell'operatore** — il contrario di ciò per cui il doppio tempo esiste. ⭐ **La misura ha però trovato una quarta strada**, che nessuno dei due aveva visto: la riga nasce con **fattura e rata già compilate** ma in stato **`DA_ABBINARE`** — il guard verifica la capienza *solo* sulle righe in stato postabile, quindi passa. La correzione guida **tutto tranne l'ultimo clic**, e il doppio tempo resta il gesto di una persona. ✅ Provata: accettata. **Decide Tid** |
| **C-2** | Si **saltano** e l'esito **le conta** | Una riga non postata non ha prodotto movimenti: non c'è niente da correggere. Ma il silenzio lascia l'operatore a chiedersi dove sono finite ⇒ la madre risponde `righe_saltate`, **lo stesso vocabolario di `fn_posta_contabile`**. Un secondo verbo che risponde come il primo si impara una volta sola |
| **C-3** | Una **colonna** `contabile_corretta_id` su `vendite_contabili`, con FK | ⛔ Non `meta`: un legame che nessuno interroga non è un legame. ⛔ Non `vendite_contabili_lotti`: quella dice «questa distinta appartiene a quel lotto», un'altra cosa. ⭐ Lo stampo esiste già ed è `sistemazioni.contabile_id` con `uq_sistemazioni_contabile`: il documento **nuovo** tiene l'id di quello da cui nasce |
| **C-4** | **Una sola correzione per distinta**, con un `UNIQUE` parziale sul legame | ⭐ E non blocca il caso vero: se è la **correzione** a essere sbagliata, si corregge **lei** — il legame punta alla correzione, non all'originale, e la catena resta leggibile. Senza il vincolo, due gemelle sullo stesso documento e nessuno sa quale vale |

⚠️ **E una trappola che la firma proposta non vede.** ⛔ La madre **non deve**
usare `fn_get_or_create_vendite_contabile`: quella è un *get-or-create* la cui
chiave di riuso, su `MANUALE`, comprende **giornata + canale + operatore** —
chiamarla farebbe atterrare le righe di correzione **dentro la distinta di
lavoro di oggi** dell'operatore, mescolando una correzione col lavoro corrente.
La distinta di correzione è un documento **proprio**: si crea con un `INSERT`.

✅ **E una buona notizia sul modello**: l'unico `CHECK` sull'importo di riga è
`importo <> 0`. ⇒ Le righe negative **sono già ammesse**: la correzione non
chiede nessuna modifica di schema oltre alla colonna del legame.

---

## 3-bis. ✅ Risposto, scritto e provato — 2026-08-28

⛔ **Niente applicato**: il migrate lo chiede Tid. Ma le due richieste sono
**scritte e provate**, e il piano riga per riga è
[§2.3-quater e §6.17 del brief DB](brief-db-posting-e-abbinamento-rata.md).

| Richiesta | Esito |
| --- | --- |
| §1 — la policy sui canali | ✅ scritta (`20260828-11`), **con `WITH CHECK`** e il predicato sul **conto**: quella proposta avrebbe reso la tabella **non scrivibile** (§5.1). Provata: **5 su 5**, e la prima è che **creare un canale sul proprio conto passa** |
| §2 — la madre della correzione | ✅ scritta (`20260828-14`) con la colonna del legame e il `UNIQUE` (`-12`). Provata: **14 su 14** |
| P-1 `sepa_mandati` | 🔵 **non ora**, e non con quel predicato (§5.4) |
| P-2 `centri_riscossione` | ✅ **resta comune**: non ha nessuna colonna di emittente (§5.3) |
| P-3 scrittura | ✅ **sì**, e non è una scelta (§5.5) |
| C-1 | 🔴 **cambiata da una misura**: le righe nascono con fattura e rata **compilate** ma in `DA_ABBINARE` (§5.8) |

📮 **Che cosa cambia per il backend, quando il migrate sarà passato:**

* la rotta `POST /distinte/{id}/correggi/` chiama
  `pagamenti.fn_crea_distinta_correzione(id, data, motivo)` — **una sola
  `SELECT`**, come le altre tre madri;
* la risposta porta `contabile_id · righe_create · righe_saltate · esito`, e
  ⛔ **`NULLA_DA_CORREGGERE` non è un errore**: si passa intatto, come
  `NULLA_DA_POSTARE`;
* ⚠️ **la distinta di correzione si apre con le righe DA ABBINARE**: il pulsante
  «abbina» incontrerà il **409 della capienza** con `confirm_and_retry` — è
  voluto, ed è lo stesso doppio tempo già costruito per la slice 3;
* due codici nuovi da rigenerare nelle policy:
  `E_CONTABILE_CORREZIONE_NON_REGISTRATA` e `E_CONTABILE_GIA_CORRETTA`;
* ⚠️ e **una fixture vostra potrebbe rompersi allo stesso modo della nostra**:
  con la policy accesa, un canale si crea solo nel contesto del suo padrone.

🔴 **E una cosa che vi capitera' identica.** Con la policy accesa, **creare il
conto e il canale in una sola istruzione non funziona**: la `WITH CHECK` cerca
il legame che quella stessa istruzione sta scrivendo, e la snapshot del comando
non contiene le righe del comando. E' la trappola RLS + CTE, ed e' gia' costata
un pgTAP il 28/08. ⭐ Il rimedio e' **due statement**: prima il conto e il suo
legame, poi il canale. ⚠️ Se il drawer dei canali fa entrambe le cose in un
`transaction.atomic()` va bene — quello che non deve essere unico e' lo
**statement**, non la transazione.

⚠️ **Un rosso annunciato**: `db/pgtap/rls/test-rls-pagamenti-perimetro.sql` è a
**15 su 18** finché la policy non è applicata — i tre rossi sono i test nuovi, e
diventano verdi col migrate.

---

## 4. Registro delle revisioni

| Data | Cosa |
| --- | --- |
| **2026-08-28** | Stesura. §1 nasce dal passo **E-4** del brief BE/FE («riverifica di tutte le liste sotto RLS, dentro e fuori perimetro, e si guarda la differenza»): la riverifica ha trovato che `enti_incasso` non ha row security e che l'elenco dei conti agganciabili usciva dal perimetro — **misurato su due operatori di due emittenti veri**, non dedotto. La metà del backend è chiusa lo stesso giorno, con un test sul DB provvisto provato rimettendo il difetto. §2 formalizza la richiesta differita di Q-7 |
