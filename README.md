# AI-influencer-bot: Maja

Boten tar fram och publicerar inlägg för en virtuell influencer som är märkt som AI. Just nu är bara Maja aktiv, och hon postar bara på Instagram.

| | Nisch | Inlägg/vecka | Tider |
|---|---|---|---|
| **Maja** (aktiv) | Gym, löpning och vardag | 7 (1 per dag) | mån 18:30, tis 07:15, ons 18:30, tor 12:00, fre 17:00, lör 10:00, sön 10:30 |
| Ebba (pausad) | Skandinavisk inredning | 3 | – |
| Sara (pausad) | Skidor och fjällliv | 3 | – |

**Majas ansikte:** lägg din bästa bild på henne som `personas/maja/reference.jpg` (i full upplösning). Alla bilder utgår från den.

## Så funkar det varje vecka

1. **Torsdag morgon** tar boten fram nästa veckas inlägg: idéer och captions (Claude) och bilder med samma ansikte varje gång (Flux via Replicate). Allt hamnar i en **Pull Request** på GitHub.
2. **Du godkänner.** Öppna PR:en i GitHub-appen och titta igenom bilderna och texterna. Tryck **Merge**. Det tar ca 5 minuter.
3. **Boten publicerar** automatiskt på Instagram och TikTok på angiven tid. Den kollar var 30:e minut.

Bara godkända inlägg publiceras. Om du inte gör Merge händer ingenting.

> **TikTok:** tills din TikTok-app är granskad hamnar inläggen i TikTok-appens inkorg. Du får en notis och trycker *Publicera* (ca 10 sek per inlägg). När appen är godkänd ändrar du `tiktok: mode: direct` i `config.yaml`, och sedan publiceras allt helt automatiskt.

---

## Installation (en gång, ca 1–2 timmar)

### 1. GitHub
1. Skapa gärna ett **separat GitHub-konto** för projektet.
2. Skapa ett nytt repo, t.ex. `ai-influencer-bot`, och ladda upp alla filer.
   - **Publikt repo:** gratis. Koden och kommande bilder syns för den som letar.
   - **Privat repo:** kräver GitHub Pro (ca 4 USD/mån), eftersom GitHub Pages behövs för bilderna.
3. **Settings → Pages:** *Deploy from a branch* → `main` → mappen `/docs`. Kopiera adressen, t.ex. `https://dittnamn.github.io/ai-influencer-bot`.
4. Öppna `config.yaml` och ersätt `public_base_url` med den adressen.
5. **Settings → Actions → General → Workflow permissions:** välj *Read and write permissions* och kryssa i *Allow GitHub Actions to create and approve pull requests*.

### 2. API-nycklar
Lägg in dem under **Settings → Secrets and variables → Actions → New repository secret**:

| Namn | Var du får den |
|---|---|
| `REPLICATE_API_TOKEN` | replicate.com → Account → API tokens (lägg in kort, betalning per bild) |
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |
| `GH_PAT` | github.com → Settings → Developer settings → Fine-grained token → bara detta repo → behörighet **Secrets: Read and write**. Används för att boten själv ska kunna förnya tokens. |

### 3. Skapa ansiktena
För varje tjej:
1. **Actions → Skapa ansikte → Run workflow** → välj tjej, `create`.
2. Öppna länken i körningens sammanfattning och titta på de 6 förslagen.
3. Kör igen med `pick` och numret du gillar bäst.

Ansiktet sparas som `personas/<namn>/reference.jpg` och används i alla bilder framöver. Utseende, personlighet och scener ändrar du i `personas/<namn>/persona.yaml`.

### 4. Instagram (för varje tjej)
1. Skapa Instagram-kontot. Ställ om det till **Professionellt konto** (Creator eller Business): Inställningar → Kontotyp.
2. Skriv i bion att det är AI, t.ex. *"AI-genererad virtuell influencer 🤖"*.
3. Gå till developers.facebook.com, skapa **en** app av typen *Business* (den räcker för alla tre kontona) och lägg till produkten **Instagram → API setup with Instagram business login**.
4. Under *App roles* lägger du till de tre Instagram-kontona som **Instagram testers**. Godkänn inbjudan i varje konto (Inställningar → Webbplatsbehörigheter → Appar och webbplatser).
5. I Instagram-inställningen i appen: *Add account* → *Generate token* för varje konto.
6. Spara som hemligheter, t.ex. för Lina:
   - `IG_USER_ID_LINA`: id-numret som visas bredvid kontot
   - `IG_TOKEN_LINA`: token
   - Gör samma sak för `_EBBA` och `_MAJA`.

Appen kan stå kvar i utvecklingsläge eftersom det bara är dina egna konton. Boten förnyar tokens varje vecka så att de inte går ut efter 60 dagar.

### 5. TikTok (för varje tjej)
1. Gå till developers.tiktok.com, skapa en app och lägg till **Login Kit** och **Content Posting API**.
2. Redirect URI: `<din public_base_url>/callback.html`
3. **Verifiera URL-prefixet** `<din public_base_url>/media/`. TikTok ger dig en verifieringsfil, som du laddar upp i mappen `docs/media/`.
4. Hemligheter: `TIKTOK_CLIENT_KEY` och `TIKTOK_CLIENT_SECRET`.
5. Lägg till de tre TikTok-kontona som testanvändare (*Sandbox → Target users*) tills appen är granskad.
6. För varje konto: logga in i webbläsaren med rätt TikTok-konto och öppna
   `https://www.tiktok.com/v2/auth/authorize/?client_key=DIN_CLIENT_KEY&scope=user.info.basic,video.publish,video.upload&response_type=code&redirect_uri=DIN_PUBLIC_BASE_URL/callback.html`
   Godkänn och kopiera koden som visas.
7. **Actions → Koppla TikTok-konto → Run workflow** → välj tjej och klistra in koden. Klart.

TikTok ändrar sina krav för appar ganska ofta. Om något steg ser annorlunda ut, följ deras egna instruktioner för *Content Posting API*.

### 6. Testkör
**Actions → Skapa veckans inlägg → Run workflow.** Efter några minuter dyker en PR upp. Ser allt bra ut? Gör Merge.

---

## Vanliga ändringar

- **Fler eller färre inlägg:** ändra `posts_per_week` och `schedule` i `persona.yaml`.
- **Pausa en tjej:** sätt `active: false`.
- **Bara Instagram:** `platforms: [instagram]`.
- **Ta bort ett inlägg innan det publiceras:** radera dess json-fil i `queue/<namn>/` (i PR:en eller på `main`).
- **Generera om en tjej:** Actions → Skapa veckans inlägg → fyll i persona. Radera först hennes json-filer för den veckan.

## Kostnad (uppskattning)
- Bilder: ca 10 inlägg × 1–3 bilder ≈ 20–25 bilder/vecka med Flux Kontext Pro på Replicate. Räkna med **ca 40–80 kr/mån**. Kolla aktuellt pris på Replicate.
- Text (Claude Haiku): några kronor i månaden.
- GitHub: gratis med publikt repo, ca 45 kr/mån för Pro med privat repo.

## Regler som boten följer, och som du måste följa
- Varje inlägg får automatiskt raden *"🤖 AI-genererad karaktär och bild."* och `#AI #AIgenererad`. Krav enligt EU:s AI-förordning (art. 50) och plattformarnas regler. **Ta inte bort den.**
- Inga riktiga varumärken eller loggor i bilderna förrän du har ett avtal. Ingen ska likna en verklig person.
- **Samarbeten:** betalda inlägg ska märkas *Reklam* enligt marknadsföringslagen, utöver AI-märkningen. Lägg till det i captionen när det gäller.
- Om någon i DM frågar om hon är verklig: svara ärligt.

## Felsökning
- **Inlägg publiceras inte:** Actions → Publicera inlägg → öppna senaste körningen. Felet står också under `status` i inläggets json-fil. Boten försöker 3 gånger. Inlägg som missats med mer än 12 h hoppas över.
- **"bilderna är inte publika än":** GitHub Pages har inte uppdaterats än. Det löser sig oftast av sig själv inom några minuter.
- **Instagram-token ogiltig:** generera en ny i Meta-appen och uppdatera `IG_TOKEN_<NAMN>`.
- **Testa lokalt utan kostnad:** `DRY_RUN=1 python -m bot.generate_week` använder platshållarbilder och gör inga API-anrop.
