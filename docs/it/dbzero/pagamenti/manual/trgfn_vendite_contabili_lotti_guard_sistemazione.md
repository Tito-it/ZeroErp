## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_vendite_contabili_lotti_guard_sistemazione`

### 🎯 Scopo Principale

(rev 2026-08-22 — sostituisce `trgfn_vendite_contabili_lotti_guard_compensazione`)

Una distinta contabile **nata da una sistemazione** non si aggancia a un **lotto
di fatturazione**.

⭐ Sono due mondi: un lotto raccoglie le fatture prodotte in un **giro di
emissione**; una distinta di sistemazione registra un rimborso o una
compensazione decisi su documenti **già emessi**. Non appartiene a nessun giro.

---

### ⭐ Il predicato si è allargato, e da due porte è diventato una

Prima diceva *«di compensazione»*, adesso dice *«di sistemazione»* — cioè **tutte
e tre** le destinazioni. Non è un'estensione arbitraria: anche una distinta di
**rimborso** non ha niente a che fare con un lotto di fatturazione, e la regola
vecchia non la copriva solo perché il rimborso non esisteva ancora come atto
registrato.

La regola aveva **due guardiani**: questo, e il ramo 2 di
`trgfn_vendite_contabili_guard_ente_centro` — la stessa regola letta nei due
versi. ⭐ Girato il verso del legame (D15-e), **la contabile non sa più di essere
nata da un atto**: lo sa l'atto. Il guard sulla contabile ha perso il dato su cui
si appoggiava, e resta **una** porta — quella giusta: *il pericolo è agganciare
al lotto, e si presidia dove si aggancia.*

### 🔴 E la lettura va fuori dalla row security

⚠️ Questo è **nuovo** rispetto alla versione vecchia: prima il guard leggeva una
colonna di `vendite_contabili`, che l'utente sta già toccando. Adesso legge
`pagamenti.sistemazioni`, **che ha la RLS**.

> 🔴 Il caso è raggiungibile, e viene dal lotto 6: la contabile di una
> **compensazione** è una distinta **interna** (centro dedicato, nessun canale), e
> le distinte interne sono **visibili a tutti**. Un operatore dell'azienda B vede
> la distinta di compensazione dell'azienda A e potrebbe agganciarla a un proprio
> lotto — con un guard `SECURITY INVOKER` non se ne accorgerebbe nessuno.

La domanda passa perciò da
[fn_get_sistemazione_di_contabile](/dbzero/script/funzioni/fn_get_sistemazione_di_contabile),
che è `SECURITY DEFINER`.

### ⚠️ Il codice è cambiato, e il vecchio si deprecato

`E_CONTABILE_SISTEMAZIONE_CON_LOTTO` sostituisce
`E_CONTABILE_COMPENSAZIONE_CON_LOTTO`, marcato `obsoleto_dal`: un codice che
nomina **una** delle tre destinazioni direbbe meno di ciò che presidia.

---

{% include-markdown "signature-core.md" %}
