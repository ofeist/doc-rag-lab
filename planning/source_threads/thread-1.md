ChatGPT

Daj komentiraj ovaj razgovor i prijedloge. Sto valja sto ne valja. Budi max kritican i pragmatican.

0.Dobro — Aurix je zapravo odličan prvi RAG target jer je “hard truth” dokumentacija (za razliku od Vector/AUTOSAR koji su slojeviti i apstraktni).
Idemo praktično.
**0. Što točno uzeti (VAŽNO)**
Nemoj “sve Aurix PDF-ove na hrpu”.
Uzmi **1 kontroler + 1 reference manual set**.
**Preporuka:**
👉 **Infineon AURIX TC3xx User Manual (odaberi jedan MCU, npr. TC397)**
I to:
**OBAVEZNO:**
- CPU / Core architecture
- Interrupt system
- Memory protection unit (MPU)
- Cache subsystem
- DMA / GTM (ako postoji u dokumentu)
- Startup / boot flow

**OPCIONALNO (kasnije):**
- SCU (System Control Unit)
- CAN / ETH / SPI chapters
- Watchdog
- Clock system

**NE uzimaj odmah:**
- datasheet + errata + app notes + safety manual + everything

To kasnije.
**1. Cilj ovog RAG-a (bitno)**
Ovo nije:
“AI zna Aurix”
nego:
“AI može naći relevantan dio dokumenta i objasniti ga u kontekstu tvog problema”
Primjer:
- “zašto DMA vraća stale data?”
- “što se događa kod warm reset-a?”
- “zašto interrupt latency varira?”
- “što MPU radi u ovom slučaju?”

**2. Pipeline (minimalni working setup)**
**STEP 1 — PDF → tekst**
Alati:
- pymupdf (fitz) ili pdfminer

Izvuci:
- page text
- chapter headings (ako možeš)

**STEP 2 — chunking (KRITIČNO)**
Nemoj:
- 1 page = 1 chunk ❌

Nego:
- 500–1000 tokens po chunku
- overlap 100–150 tokens

Primjer:
[CHAPTER: 5.3 CACHE SYSTEM]text...text...text...
**STEP 3 — dodaj metadata (JAKO VAŽNO)**
Svaki chunk treba imati:
{  "source": "aurix_tc397_um.pdf",  "chapter": "Cache System",  "page": 312,  "section": "5.3.2",  "keyword_hint": ["cache", "invalidate", "coherency"]}
Ovo kasnije OGROMNO pomaže.
**STEP 4 — embeddings**
Ako imaš lokalno:
👉 preporuka:
- bge-m3 (vrlo dobar general embedding model)
- ili e5-large

Ako ideš preko API:
- OpenAI embeddings (najstabilnije)

**STEP 5 — vector DB**
Najjednostavnije:
👉 ChromaDB
Zašto:
- 10 minuta setup
- lokalno radi
- dovoljno za start

**STEP 6 — retrieval**
Kad pitaš:
"DMA vraća stare podatke nakon reset-a"
radi se:
1. embed question
2. similarity search top-k (npr. 5–10 chunks)
3. filtriraj po metadata (ako možeš)
4. ubaci u prompt

**STEP 7 — LLM (Qwen 3.5)**
👉 Da, Qwen 3.5 je OK
Ali bitno:
- koristi instruction-tuned verziju
- ne “base model”

**3. Prompt (VAŽNO — ovo čini 50% kvalitete)**
Koristi nešto ovako:
You are an embedded systems assistant.Use ONLY the provided context from Aurix documentation.If answer is not in context, say "not found in documentation".CONTEXT:{retrieved_chunks}QUESTION:{user_question}Explain clearly and relate to embedded behavior.
**4. Minimal architecture**
PDF↓chunker↓embeddings↓ChromaDB↓retriever↓Qwen 3.5↓answer
**5. Što ćeš dobiti (realno)**
Nakon ovog setupa:
**1. “Smart datasheet search”**
Umjesto Ctrl+F:
- pitaš prirodno
- dobiješ relevantne pasuse

**2. Better debugging support**
Primjeri:
- “zašto DMA ponekad ne flush-a cache?”
- “što se događa u reset sekvenci?”
- “koji interrupt ima prioritet?”

Model:
- nađe točan dio manuala
- objasni ga u kontekstu

**3. Cross-link razumijevanje**
Po prvi put:
- CPU + interrupt + cache + DMA

počinju biti povezani u odgovoru.
**4. Ubrzava učenje platforme**
Ovo je OGROMNO:
- junior → senior skok
- novi MCU onboarding
- debugging novih bugova

**6. Ograničenja (bitno da ne očekuješ čudo)**
RAG NEĆE:
❌ popraviti pogrešan firmware❌ razumjeti tvoju konkretnu bug kombinaciju bez logova❌ zamijeniti iskustvo s hardwareom❌ riješiti timing/race probleme sam
**7. Najčešće greške (bitno za tebe)**
**Greška 1: preveliki chunks**
→ model “ne nađe ništa konkretno”
**Greška 2: previše dokumenata odjednom**
→ noise > signal
**Greška 3: loš prompt**
→ model halucinira iako ima context
**Greška 4: nema metadata**
→ retrieval je “random”
**8. Kako znaš da radi dobro?**
Testiraj:
**pitanja tipa:**
- “gdje u manualu piše X?”
- “što uzrokuje Y ponašanje?”
- “koji register kontrolira Z?”

Ako:
- vraća točan section + objašnjenje → radi dobro
- daje generičan odgovor → problem u retrievalu

**9. Moj realni savjet za tebe**
Nemoj odmah:
“napravit 100% RAG system”
nego:
**Phase 1 (1–2 dana)**
- 1 PDF
- chunking
- Chroma
- Qwen

**Phase 2**
- metadata tuning
- better prompts

**Phase 3**
- dodaj Vector docs

**Phase 4**
- dodaj tvoje debug noteove (OVO je najjače)

**10. Najvažnija stvar (iskustvo iz prakse)**
Najveća vrijednost neće doći iz Aurix PDF-a.
Nego iz:
kombinacije Aurix + tvoji real bugovi
Jer tada dobiješ:
- “što piše u manualu”

-  

- “što se stvarno događa u ECU-u”

i tu nastaje pravi “engineering assistant”.
Ako želiš, mogu ti u sljedećem koraku dati:
- konkretan Python skeleton (PDF → Chroma → Qwen)
- ili optimal chunking strategiju za tehničke PDF-ove
- ili kako dodati Obsidian kao frontend za RAG

samo reci koliko low-level želiš ići.
 
 
 
 
1.Super — ovo je pravi start. Idemo jako konkretno, bez teorije.
**🧱** **STEP 1 — napravi Python projekt**
**1.1 Kreiraj folder**
mkdir aurix-ragcd aurix-rag
**1.2 (preporuka) virtual environment**
python -m venv .venv
Aktivacija:
**Linux / Mac:**
source .venv/bin/activate
**Windows:**
.venv\Scripts\activate
**1.3 instaliraj library**
Koristit ćemo:PyMuPDF (fitz)
pip install pymupdf
**📄 STEP 2 — ubaci PDF**
U folder stavi bilo koji PDF:
aurix-rag/├── sample.pdf├── extract.py
Može doslovno:
- random manual
- random ebook
- bilo što

**🧠 STEP 3 — Python skripta (PDF → tekst)**
Kreiraj file:
extract.py
i ubaci ovo:
import fitz  # PyMuPDFPDF_PATH = "sample.pdf"def extract_pdf(pdf_path):    doc = fitz.open(pdf_path)    all_pages = []    for page_num in range(len(doc)):        page = doc[page_num]        text = page.get_text("text")        all_pages.append({            "page": page_num + 1,            "text": text        })    return all_pagesif __name__ == "__main__":    pages = extract_pdf(PDF_PATH)    for p in pages[:3]:  # prikaži prve 3 stranice        print("\n" + "="*80)        print(f"PAGE {p['page']}")        print("="*80)        print(p["text"][:1000])  # limit za pregled
**▶️ STEP 4 — pokretanje**
python extract.py
**🧾 Što dobiješ ovim**
Dobiješ:
- page-by-page tekst iz PDF-a
- spremno za chunking
- spremno za embeddings

**⚠️ Bitno (za RAG kasnije)**
Ovo je RAW ekstrakcija.
Neki PDF-ovi će imati:
- loš line break
- splitane rečenice
- header/footer noise

👉 to je normalno
Kasnije ćemo to čistiti.
**🧭 Što ćemo dalje (sljedeći korak)**
Kad ovo radi, idemo na:
**STEP 2 — chunking**
- split po 500–1000 tokena
- overlap
- dodavanje metadata:
  - page
  - section


**STEP 3 — embeddings (bge-m3)**
**STEP 4 — vector DB (Chroma)**
**STEP 5 — Qwen query**
**💡 mini-savjet (bitno za tebe)**
Nemoj još gledati “Aurix PDF”.
👉 prvo testiraj s bilo kojim PDF-om
Cilj ovog koraka je samo:
“mogu izvući tekst stabilno”
**Ako želiš next step**
Samo reci:
👉 “STEP 2”
i vodim te dalje na chunking (to je prvi “RAG-critical” dio gdje se sve odlučuje).
2.Super — ovo je prvi dio gdje RAG zapravo počinje “postajati pametan”.
**🧱 STEP 2 — chunking (PDF → mali komadi teksta)**
**🎯 cilj**
Pretvoriti:
velike stranice PDF-a
u:
male, smisleno pretražive “knowledge chunks”
Jer embedding modeli ne rade dobro na velikim blokovima teksta.
**1. Što radimo u ovom step-u**
Ulaz:
page 1: 2000+ riječipage 2: 1800+ riječi
Izlaz:
chunk 1: 500–1000 tokenschunk 2: 500–1000 tokenschunk 3: ...
**2. Instaliraj još jednu stvar**
Trebat će nam tokenizer helper:
pip install tiktoken
(ovo pomaže procijeniti “veličinu” chunkova)
**3. Novi file: chunking.py**
import fitzimport tiktokenPDF_PATH = "sample.pdf"# tokenizer (može i bez toga, ali ovo je preciznije)enc = tiktoken.get_encoding("cl100k_base")CHUNK_SIZE = 800      # cilj: ~800 tokenaOVERLAP = 120         # da se kontekst ne izgubidef extract_pages(pdf_path):    doc = fitz.open(pdf_path)    pages = []    for i in range(len(doc)):        text = doc[i].get_text("text")        pages.append({            "page": i + 1,            "text": text        })    return pagesdef chunk_text(text, chunk_size=800, overlap=120):    tokens = enc.encode(text)    chunks = []    start = 0    while start < len(tokens):        end = start + chunk_size        chunk_tokens = tokens[start:end]        chunk_text = enc.decode(chunk_tokens)        chunks.append(chunk_text)        start += chunk_size - overlap  # overlap    return chunksif __name__ == "__main__":    pages = extract_pages(PDF_PATH)    all_chunks = []    for p in pages:        page_chunks = chunk_text(p["text"], CHUNK_SIZE, OVERLAP)        for i, ch in enumerate(page_chunks):            all_chunks.append({                "page": p["page"],                "chunk_id": i,                "text": ch            })    # test output    print(f"Total chunks: {len(all_chunks)}")    print("\n--- SAMPLE CHUNK ---\n")    print(all_chunks[0]["text"][:1000])
**4. Pokreni**
python chunking.py
**5. Što dobiješ**
Vidjet ćeš:
Total chunks: 120--- SAMPLE CHUNK ---...
**6. Zašto je ovo KRITIČNO (RAG “make or break”)**
**❌ loš chunking:**
- cijela stranica
- predugi blokovi
- izgubi se smisao

**❌ pre mali chunkovi:**
- nema konteksta
- model ne razumije

**✅ dobar chunking:**
- 500–1000 tokens
- overlap 10–20%
- “jedna ideja po chunku”

**7. Što ćemo kasnije dodati (bitno za Aurix)**
U sljedećem koraku ćemo dodati:
**metadata (JAKO VAŽNO)**
{  "page": 12,  "chunk_id": 3,  "section": "DMA Controller",  "source": "sample.pdf"}
To kasnije čini RAG puno pametnijim.
**8. Mini intuicija**
Zamisli:
- PDF = knjiga
- chunk = odlomak koji ima smisao sam za sebe

RAG ne voli:
“cijele knjige”
voli:
“dobro rezane odlomke”
**9. Sljedeći korak (STEP 3)**
U STEP 3 radimo:
**👉 embeddings (bge-m3)**
tu prvi put dobiješ:
- “semantičku pretragu”
- ne više keyword search

**Ako želiš dalje**
Samo napiši:
👉 **STEP 3**

Proći ću ovo kao “engineering review”, ne kao motivacijski feedback: što je dobro, gdje su rupe, i što bih promijenio da ovo postane ozbiljan PoC umjesto tutorial igračke.

Da, smjer je dobar, ali prijedlozi su još dosta “tutorial RAG”, ne “engineering-grade RAG”. Kao prvi PoC — solidno. Kao nešto što bi firma mogla koristiti za Aurix/debugging — ima ozbiljnih rupa.
Moj brutalno pragmatičan verdict

Valja:

    dobro je što se kreće s jednim MCU/manualom, ne sa svim PDF-ovima;

    dobro je što se jasno kaže da RAG nije “AI zna Aurix”, nego “AI pronađe i objasni relevantan dio dokumentacije”;

    dobro je što se naglašava metadata;

    dobro je što se dodaju interni bug/debug notes kasnije — to je realno najveća vrijednost;

    dobro je što se ide fazno, ne odmah enterprise platforma.

Ne valja / premalo je zrelo:

    chunking je previše naivan;

    extraction iz PDF-a je podcijenjen problem;

    nema evaluacije;

    nema citiranja izvora u odgovoru kao hard requirement;

    nema keyword/BM25 + vector hybrid searcha;

    nema rerankera;

    nema sigurnosnog sloja protiv halucinacija;

    nema verzioniranja dokumentacije;

    nema jasnog odgovora na pitanje: “kako znamo da je odgovor točan?”

To zadnje je najvažnije.
0. Izbor Aurix dokumentacije — dobar prijedlog

Ovo je vjerojatno najbolji dio.

“Nemoj sve PDF-ove na hrpu” je 100% ispravno. Ako odmah ubaciš datasheet, user manual, errata, safety manual, app notes, AUTOSAR, Vector docs, interni wiki — dobit ćeš smeće retrieval. Ne zato što RAG ne radi, nego zato što ne znaš što si zapravo testirao.

Za prvi target bih čak bio još stroži:

Uzmi samo jedan problem-domain, npr.:

    cache + DMA coherency;

    interrupt + priority + latency;

    reset/startup flow;

    MPU/access violation.

Ne bih odmah uzimao “CPU, interrupts, MPU, cache, DMA, GTM, boot”. To je već puno.

Bolji prvi PoC:

    “Može li RAG pouzdano odgovoriti na 20 pitanja o cache/DMA coherency iz TC3xx manuala, s točnim page/section citatima?”

To je puno jači test nego “imam Aurix chatbot”.
1. Cilj RAG-a — dobro postavljen, ali treba još strože

Rečenica:

    “Ovo nije AI zna Aurix, nego AI može naći relevantan dio dokumenta”

To je odlična mentalna mapa.

Ali bih dodao još strože pravilo:

    RAG odgovor bez section/page reference je neupotrebljiv.

Za tehničku dokumentaciju, pogotovo automotive/embedded, odgovor mora imati:

    naziv dokumenta;

    section;

    page;

    kratak citirani/sažeti dokaz;

    razinu sigurnosti;

    što nije pronađeno.

Bez toga dobiješ “pametnog lažljivca”.
2. PDF → tekst — jako podcijenjeno

Prijedlog kaže “PyMuPDF ili pdfminer”. To je OK za početak, ali previše lagano zvuči.

Kod tehničkih manuala problem nije samo izvući tekst. Problem je:

    tablice registara;

    bitfieldovi;

    footnoteovi;

    multi-column layout;

    header/footer noise;

    figure captions;

    section numbering;

    line breaks;

    formule;

    “Table continues on next page”;

    register reset values;

    upozorenja i notes.

Za Aurix/manuale, običan page.get_text("text") često neće biti dovoljno.

Za prvi PoC može, ali moraš odmah znati: ovo nije ingestion pipeline, ovo je smoke test extractor.

Bolji pristup:

    prvo extract raw text;

    onda inspect 10 relevantnih stranica ručno;

    posebno inspect tablice;

    tek onda odlučiti je li PyMuPDF dovoljan.

Ako su register tablice važne, možda trebaš poseban table extraction flow, ne samo plain text.
3. Chunking — najveća rupa u prijedlogu

“500–1000 tokens + overlap” je OK kao početna heuristika, ali za tehničke manuale je često premalo pametno.

Problem: tehnički PDF nije roman.

Ako chunk režeš čisto po tokenima, možeš razbiti:

    section naslov od sadržaja;

    register description od bitfield tablice;

    warning/note od objašnjenja;

    uvjet ponašanja od posljedice;

    “If X then Y” preko granice chunkova.

To može ubiti retrieval.

Bolje:

    section-aware chunking

        chunk mora nositi hijerarhiju:

        Chapter → Section → Subsection → Page range.

    semantic boundaries

        ne rezati usred register opisa ili procedure.

    parent-child retrieval

        indeksiraš manje chunkove;

        u prompt vraćaš širi parent section.

    special handling za tablice

        register tablice, bitfieldovi i reset values možda trebaju odvojeni format.

Naivni token chunking je OK za “hello world RAG”. Za Aurix debugging — nedovoljno.
4. Metadata — dobra ideja, ali primjer je preplitak

Ovo je dobro:

{
  "source": "aurix_tc397_um.pdf",
  "chapter": "Cache System",
  "page": 312,
  "section": "5.3.2",
  "keyword_hint": ["cache", "invalidate", "coherency"]
}

Ali bih dodao:

{
  "doc_version": "x.y",
  "device_family": "TC3xx",
  "device": "TC397",
  "doc_type": "user_manual",
  "section_path": "CPU > Cache > Coherency",
  "page_start": 312,
  "page_end": 314,
  "content_type": "concept|register|procedure|warning|table",
  "extraction_quality": "ok|suspect|table_broken",
  "chunk_hash": "..."
}

Za firmu je verzioniranje ključno. Inače će netko pitati pitanje, RAG će odgovoriti iz stare verzije manuala, i svi će misliti da je “AI pogriješio”, a zapravo ingestion nije kontroliran.
5. Embeddings — OK, ali nije dovoljno

bge-m3 / e5-large / OpenAI embeddings — sve OK kao start.

Ali za ovakve dokumente ne bih se oslanjao samo na vector similarity.

Za embedded/manuale ima puno exact pojmova:

    register names;

    bit names;

    module abbreviations;

    trap names;

    interrupt names;

    acronyms;

    “PCON0”, “DSPR”, “PSPR”, “SRI”, “SPB”, “GTM”, “DMA channel”, itd.

Vector search zna biti loš za exact technical terms.

Pragmatično:

minimum ozbiljniji retrieval:

    vector search;

    keyword/BM25 search;

    merge results;

    rerank top 20;

    vrati top 5–8.

Bez hybrid searcha, RAG će često promašiti baš ono što embedded engineer traži.
6. ChromaDB — OK za PoC, ne bih ga romantizirao

Chroma je dobar jer je brz za probati.

Ali ne bih ga prikazivao kao “solution”. To je PoC storage.

Za ozbiljnije bih gledao:

    Qdrant;

    pgvector;

    OpenSearch/Elasticsearch hybrid;

    Weaviate možda, ali ne bih odmah.

Ako firma već ima Elasticsearch/OpenSearch iskustvo, možda je hybrid search tamo prirodniji.

Ali za prvi vikend/PoC: Chroma je sasvim OK.
7. Qwen 3.5 — ideja OK, ali treba biti precizan

“Qwen 3.5 je OK” je preopćenito. Treba znati koji točno model, veličina, context window, instruct/chat varijanta, deployment način, quantization, latency, memory.

Postoje Qwen3.5 modeli i open-weight varijante, ali moraš konkretno odabrati model/repo/serving format, ne samo reći “Qwen 3.5”. Qwen3.5 je predstavljen kao model family, a npr. Hugging Face ima konkretne repozitorije poput Qwen/Qwen3.5-4B; Reuters je izvijestio da je Alibaba predstavila Qwen3.5 u veljači 2026 kao model za “agentic AI era”.

Za RAG nad Aurix dokumentacijom, često je važnije:

    dobar retrieval;

    dobar prompt;

    dovoljno context windowa;

    striktno citiranje;

    niska temperatura;

nego najjači model.

Za PoC bih koristio nešto tipa:

    lokalni Qwen instruct model preko vLLM/Ollama/llama.cpp;

    temperature 0–0.2;

    obavezno “answer only from context”.

Ali za firmu: možda prvo koristiti jak API model za evaluaciju kvalitete, pa tek onda lokalni model za cost/privacy.
8. Prompt — dobar početak, ali prejednostavan

Ovaj prompt:

    Use ONLY the provided context. If answer is not in context, say not found.

Dobar je, ali nije dovoljan.

Trebaš strukturirani output, npr.:

Answer:
Evidence:
- source, section, page
Reasoning:
Limitations:
Not found / needs other document:

I još važnije:

    Ako context ne sadrži direktan dokaz, ne smiješ zaključivati kao da je dokazano.

Kod embedded/debugging pitanja model će često “spojiti točkice”. Nekad je to korisno, ali mora biti označeno kao inference.

Primjer:

    “Manual explicitly says X”

    “Likely implication is Y”

    “Need to verify with cache state / register dump / debugger trace”

To je razlika između korisnog asistenta i opasnog bullshit generatora.
9. Testiranje “kako znaš da radi” — preslabo

Ovo je najveći missing piece.

Prijedlog kaže:

    Ako vraća točan section + objašnjenje → radi dobro.

To je previše ručno i neformalno.

Trebaš napraviti eval set.

Minimalno:

    30 pitanja;

    za svako pitanje očekivani manual section/page;

    kategorije:

        direct lookup;

        conceptual explanation;

        register lookup;

        cross-section relation;

        “not found” question;

        misleading question.

Primjer evaluacije:
Test	Pitanje	Expected source	Pass criteria
DMA-01	Kada treba invalidirati cache kod DMA read?	Cache/DMA section	navede relevantan section + ne izmišlja
RESET-02	Što ostaje nakon warm reset?	Reset chapter	razlikuje reset types
NEG-01	Koji register omogućuje magic feature X?	none	kaže not found

Bez ovoga nemaš pojma radi li RAG ili samo lijepo priča.
10. “Smart datasheet search” — realno i korisno

Ovo je realan prvi benefit.

Ne bih ga prodavao kao “junior → senior skok”. To je pretjerano.

Bolje:

    junior brže pronalazi relevantne dijelove;

    senior brže provjerava manual;

    onboarding se ubrzava;

    manje vremena na Ctrl+F;

    bolje povezivanje pojmova.

Ali “junior to senior skok” je marketing. Senior nije senior jer zna gdje je rečenica u manualu, nego jer zna kada je manual nepotpun, kada je silicon errata relevantna, kada timing mjeriš osciloskopom, i kada bug nije u kodu nego u pretpostavci.
11. Dodavanje Vector/AUTOSAR docs — oprezno

Prijedlog kaže Phase 3 dodaj Vector docs. Tu bih bio jako oprezan.

Vector/AUTOSAR nisu isti tip dokumentacije kao Aurix manual.

Aurix manual:

    hardware truth;

    relativno konkretan;

    device-specific.

AUTOSAR/Vector:

    apstraktni slojevi;

    konfiguracijski model;

    tooling-specific behavior;

    generated code;

    licensing/proprietary docs;

    puno implicitnog znanja.

Ako ih pomiješaš prerano, retrieval će početi vraćati “apstraktno točne, ali konkretno beskorisne” odgovore.

Bolji redoslijed:

    Aurix user manual;

    errata za isti chip;

    interni debug notes;

    relevantni compiler/linker/startup docs;

    tek onda Vector/AUTOSAR za jedan konkretan stack/problem.

12. Interni debug notes — ovo je stvarno zlato

Ovo je najjači dio cijelog prijedloga.

Prava vrijednost nije:

    “Što kaže manual?”

Nego:

    “Manual kaže X, ali u našem projektu se već dogodilo Y, i workaround je bio Z.”

Tu nastaje engineering assistant.

Ali to zahtijeva disciplinu:

    postmortemi;

    known-bad patterns;

    debug notes;

    register dumps;

    root cause summaries;

    “do not do this” pravila;

    codebase-specific conventions.

Ako firma to nema, RAG neće magično popraviti kulturu dokumentiranja. Samo će lijepo pokazati koliko je znanje rasuto.
13. Python skeleton — dobar za učenje, loš kao ozbiljna osnova

Onaj extract.py i chunking.py su OK za prvi dan.

Ali ima problema:

    nema output formata;

    nema spremanja chunkova;

    nema cleaninga;

    nema section detectiona;

    nema error handlinga;

    nema logginga;

    nema reproducibilnosti;

    nema hashiranja dokumenata;

    nema testova;

    nema CLI;

    nema ingestion manifest filea.

Za “igram se doma” — OK.

Za firmu bih odmah išao prema minimalnom, ali urednom CLI-ju:

rag ingest docs/aurix_tc397.pdf --doc-id aurix_tc397_um --version x.y
rag eval evalsets/cache_dma.yaml
rag ask "Why can DMA return stale data?"

Ne full platforma, ali ne ni random skripte.
Što bih ja promijenio u planu

Umjesto ovoga:

    PDF → chunking → embeddings → Chroma → Qwen

Ja bih napravio:
Phase 1 — Retrieval-only PoC

Bez LLM-a.

Cilj: za 30 pitanja, možeš li vratiti prave sections/pages?

Ako retrieval ne radi, LLM ti samo uljepšava grešku.
Phase 2 — RAG answer with citations

Dodaj LLM, ali odgovor mora imati izvore.

Nema izvora = fail.
Phase 3 — Eval set

Mjeri:

    hit@5;

    je li točan section vraćen;

    je li odgovor grounded;

    koliko često kaže “not found” kad treba.

Phase 4 — Internal notes

Dodaj realne bugove, ali odvojeno od vendor docs.

Npr. metadata:

"source_type": "vendor_manual|internal_bug_note|postmortem|code_comment"

Phase 5 — Multi-doc reasoning

Tek sada dodaj Vector/AUTOSAR/errata.
Najveći rizici

    Ljudi će vjerovati lijepom odgovoru bez provjere.
    Zato citations i “not found” moraju biti obavezni.

    PDF extraction će tiho pokvariti važne tablice.
    Zato treba manual inspection i extraction quality flag.

    Chunking će uništiti kontekst.
    Zato section-aware chunking, ne samo token slicing.

    Vector-only retrieval će promašiti register/bit names.
    Zato hybrid search.

    Dodavanje previše dokumenata prerano će smanjiti kvalitetu.
    Zato jedan domain, jedan eval set.

    Firma će misliti da treba trenirati model.
    U 90% slučajeva prvo treba bolji RAG + bolja dokumentacija + eval, ne fine-tuning.

Moj konačni sud

Prijedlog je dobar kao početni edukativni razgovor. Ima zdravu intuiciju: mali scope, metadata, RAG nije magija, interni bugovi su vrijedni.

Ali kao engineering plan je previše naivan u tri mjesta:

    PDF extraction;

    chunking/retrieval;

    evaluacija kvalitete.

Najpragmatičniji sljedeći korak nije “STEP 3 embeddings”.

Najbolji sljedeći korak je:

    Uzmi jedan Aurix chapter/problem domain, napravi 20–30 zlatnih pitanja s očekivanim page/section odgovorima, pa tek onda gradi ingestion i retrieval oko toga.

Bez eval seta gradiš demo.
S eval setom gradiš alat.

Text mi se cini valjda ok
Pitanje: Linije 2,3,4 gdje je page start null 
To tako ok?

Mislim da je bolje.
Npr. Page 10 i 30 su razdijeljene na vise chunkova.
To je valjda ok.
Sto sad?

Naravno — moja greška. Evo README na engleskom:


Na lin masini na poslu sad ponovo probam

~/git/test-rag$ python scripts/embed_chunks.py \
  --input data/chunks.jsonl \
  --persist-dir vector_db \
  --collection infineon_manual
usage: embed_chunks.py [-h] [--chunks CHUNKS] [--db DB] [--collection COLLECTION]
                       [--model MODEL] [--batch-size BATCH_SIZE] [--reset]
embed_chunks.py: error: unrecognized arguments: --input data/chunks.jsonl --persist-dir vector_db

Da — ovo je samo mismatch između README komande i stvarne skripte. Skripta očekuje:

--chunks
--db

ne:

--input
--persist-dir

Pokreni ovako:

python scripts/embed_chunks.py \
  --chunks data/chunks.jsonl \
  --db vector_db \
  --collection infineon_manual \
  --reset

Za search onda vjerojatno isto koristiš --db, npr.:

python scripts/search_chunks.py \
  --db vector_db \
  --collection infineon_manual \
  --query "DMA cache coherency"

Moja greška u README-u: stavio sam ljepša/novija imena argumenata, ali skripta ima druga. Za sada ne mijenjaj skriptu, samo koristi ove stvarne argumente.

memoriraj gdje smo stali

Zapamtio.

Stali smo na RAG PoC-u ovdje:

Step 1 ✅ PDF extraction radi
Step 2 ✅ chunking radi, page metadata fixan
Step 3 ✅ embeddings + Chroma search izgleda OK
Step 4 ⏳ RAG answer je sljedeći realni korak, ali prvo treba ispraviti README CLI mismatch (--chunks/--db umjesto --input/--persist-dir)


