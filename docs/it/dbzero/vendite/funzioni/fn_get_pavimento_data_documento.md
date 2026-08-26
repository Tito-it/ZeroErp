{% include-markdown "it/dbzero/vendite/manual/fn_get_pavimento_data_documento.md" %}
# ⚙️ Funzione `fn_get_pavimento_data_documento`

```sql
CREATE FUNCTION fn_get_pavimento_data_documento(p_registro_id bigint, p_serie character varying, p_competenza_mese date)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_pavimento_data_documento(p_registro_id bigint, p_serie character varying, p_competenza_mese date)
 RETURNS TABLE(pavimento date, origine text)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_seq vendite.registri_fatturazione_progressivi.ultima_data%TYPE;
    v_emi vendite.fatture.data%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il pavimento EFFETTIVO della data di un documento — il
    --   maggiore fra quello della sequenza e quello del limite di
    --   emissione — e QUALE dei due ha vinto.
    --
    -- Regole:
    --   - una sede sola: nascita, targa e cancello leggono qui;
    --   - `pavimento` e' sempre il maggiore, mai quello di
    --     `origine`;
    --   - il pareggio va a SEQUENZA, perche' la sua frase puo'
    --     portare un bersaglio.
    -- =========================================================

    -- ℹ️ I guard di parametro stanno nelle due primitive, che li
    --    hanno gia' entrambi: qui sarebbero una seconda copia
    --    della stessa validazione, e due copie divergono.
    v_seq := vendite.fn_get_pavimento_sequenza(p_registro_id, p_serie);
    v_emi := vendite.fn_get_pavimento_emissione(p_registro_id, p_competenza_mese);

    -- ⚠️ GREATEST IGNORA I NULL (torna NULL solo se lo sono
    --    tutti): la sequenza risponde NULL quando non e' ancora
    --    uscito niente, e il GREATEST se la cava da solo. Nessun
    --    COALESCE difensivo.
    RETURN QUERY
    SELECT GREATEST(v_seq, v_emi),
           CASE
               -- ⭐ Il pareggio va a SEQUENZA: a parita' di data
               --    si sceglie la frase che puo' portare
               --    l'operatore su un documento vero.
               WHEN v_seq IS NOT NULL
                    AND (v_emi IS NULL OR v_seq >= v_emi) THEN 'SEQUENZA'::text
               WHEN v_emi IS NOT NULL                     THEN 'EMISSIONE'::text
               -- Nessun pavimento da nessuna delle due parti:
               -- «nessun vincolo». Oggi non capita — il limite di
               -- emissione c'e' sempre — ma la funzione lo regge.
               ELSE NULL::text
           END;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_pavimento_data_documento(p_registro_id bigint, p_serie character varying, p_competenza_mese date)
IS 'Il pavimento EFFETTIVO della data di un documento — il maggiore fra il pavimento della SEQUENZA (vendite.fn_get_pavimento_sequenza) e quello del LIMITE DI EMISSIONE (vendite.fn_get_pavimento_emissione) — e quale dei due ha vinto. ⛔ E'' LA SEDE UNICA, e il motivo per cui esiste e'' che il pavimento effettivo serve in TRE posti: la nascita del documento (fn_calcola_data_documento), la targa del dialog (fn_get_pavimento_lotto) e il cancello (fn_get_next_progressivo). Tre GREATEST scritti a mano sarebbero tre implementazioni della stessa regola, e il giorno in cui una cambia le altre due mentono in silenzio: si condivide la funzione, non una copia della sua logica. ⭐ `pavimento` e'' SEMPRE QUELLO EFFETTIVO, mai quello di `origine`: e'' il valore che va nella frase dell''errore e nella minDate del dialog, e nominare il pavimento di sequenza mentre a mordere e'' il limite direbbe all''operatore di scegliere una data CHE VERRA'' RIFIUTATA DI NUOVO — un messaggio che manda a sbattere due volte e'' peggio di uno generico. ⭐ `origine` (SEQUENZA | EMISSIONE) esiste per scegliere il CODICE ERRORE: «piu'' vecchio del limite di emissione» e «anteriore all''ultimo numero emesso» sono due cose diverse, si rimediano in due modi diversi, e dire la seconda quando e'' la prima manda a cercare la cosa sbagliata. ⚠️ IL PAREGGIO VA A SEQUENZA (decisione D-4): a parita'' di data le frasi non sono equivalenti — quella della sequenza puo'' portare un BERSAGLIO, cioe'' un pulsante che apre la fattura gia'' numerata, quella del limite puo'' solo dire una data. ℹ️ GREATEST ignora i NULL e qui serve: la sequenza risponde NULL finche'' non e'' uscito niente. Se un giorno fossero NULL entrambi la risposta e'' «nessun vincolo» (pavimento e origine NULL), e chi legge deve trattarla come tale. ℹ️ I guard di parametro stanno nelle due primitive: qui sarebbero una seconda copia, e l''errore nomina quindi la primitiva. Brief: brief-db-limite-emissione-e-data-verificata §11 DB-4.';
```

---
{% include-markdown "signature-core.md" %}
