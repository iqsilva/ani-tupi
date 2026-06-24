# Pesquisa de Plugins — v1.3.0

Documento os sites avaliados para adição como novos plugins no ani-tupi, incluindo os que falharam e os motivos.

---

## Critérios de seleção

- Sem proteção Cloudflare (bloquearia scraping sem browser completo)
- URL de vídeo obtível diretamente da página do episódio
- Conteúdo em PT-BR (dublado ou legendado)
- Site acessível a partir do ambiente de teste (Hetzner VPS, IPv6)

---

## Sites avaliados

### animesdigital.com — DESCARTADO (plugin já existe)

Plugin existente em `scrapers/plugins/animesdigital.py`. Nenhuma investigação adicional.

---

### animefire.io — DESCARTADO (CDN inacessível)

Plugin já existe. Ao testar playback, o CDN de vídeo (`lightspeedst.net`, IP `62.182.80.148`) retorna timeout completo a partir do VPS Hetzner — bloqueio geográfico. O site funciona normalmente na máquina do usuário. Plugin existente mantido sem alteração.

---

### anitube (domínio antigo: `anitube.news`) — CORRIGIDO

Plugin existente estava com domínio morto. Domínio correto: `anitube.zip`.

Além disso, `search_player_src` usava Selenium para extrair o iframe do player — desnecessário, pois a página renderiza o iframe via HTML estático. Substituído por `requests` + BeautifulSoup.

**Arquivo:** `scrapers/plugins/anitube.py`

---

### goyabu.io — SUCESSO

Sem Cloudflare. Estrutura da página estável e previsível.

**`search_anime`**

```
GET /?s={query}
→ article.boxAN → a[href*='/anime/'] + div.title
```

**`search_episodes`**

Variável JavaScript `allEpisodes = [...]` na página do anime contém array de objetos `{episodio, link, episode_name}`. Links são paths relativos, concatenados com `BASE_URL`.

**`search_player_src`**

`var playersData = [...]` contém campo `url` com URL completa do blogger embed.

**Problema encontrado:** o campo `blogger_token` no JSON é o token em base64, não o token literal. Usado diretamente causava erro `[5]` (token inválido) na API do blogger. Fix: extrair token do campo `url` via regex `token=([^&\s]+)`.

**Nota:** episódios antigos (ex: Naruto ep 1) têm tokens expirados — comportamento normal do blogger, não bug do plugin. Testado com One Punch Man S3 ep 12 (recente) — funcionou.

**Arquivo:** `scrapers/plugins/goyabu.py`

---

### animesonlinecc.to — SUCESSO

Sem Cloudflare. Usa blogger.com como CDN de vídeo, igual ao goyabu.

**`search_anime`**

```
GET /search/{query}
→ article.item.se.tvshows → h3 (sem classe)
```

**Bug encontrado:** código inicial buscava `h3` com `class_=re.compile(r"title|name")` — o `h3` não tem classe. Resultado: 0 animes encontrados. Fix: `article.find(["h2", "h3"])` sem filtro de classe.

**`search_episodes`**

Links `a[href*="/episodio/"]` na página do anime. Problema: existe link de navegação com `href="/episodio/"` (path relativo sem número) misturado com os links reais como `https://animesonlinecc.to/episodio/naruto-classico-episodio-1/`.

**Bug encontrado:** o link relativo `/episodio/` causava `ValidationError` do Pydantic: `Episode URL must be http(s), got: /episodio/`. Fix: filtro duplo — `ep_url.startswith("http")` AND regex `-episodio-\d+/?$`.

**`search_player_src`**

`iframe[src*="blogger.com/video.g"]` na página do episódio. Token extraído do atributo `src`.

**Arquivo:** `scrapers/plugins/animesonlinecc.py`

---

## Descoberta central: blogger_resolver.py

Ambos os novos sites usam blogger.com como CDN de vídeo. O yt-dlp (2026.03.17) não resolve `blogger.com/video.g` — erro "Unable to extract JSON data". Solução: chamada direta à API interna do blogger.

**Fluxo de resolução:**

```
1. GET https://www.blogger.com/video.g?token=TOKEN
   → extrair f.sid (campo FdrFJe) e bl (campo cfb2h) do HTML

2. POST /_/BloggerVideoPlayerUi/data/batchexecute
   params: rpcids=WcwnYd, f.sid=..., bl=...
   body:   f.req=[[["WcwnYd", json.dumps([token, null, 0]), null, "generic"]]]

3. Resposta: prefixo )]}'  (anti-CSRF) + chunk size + JSON duplamente codificado
   outer = json.loads(linha que começa com "[[")
   inner = json.loads(outer[0][2])
   url   = inner[2][0][0]  → URL googlevideo.com
```

**Arquivo:** `scrapers/core/blogger_resolver.py`

---

## Bug MPV com googlevideo

URL válida retornava HTTP 403 no MPV. Causa: ffmpeg usa `User-Agent: Lavf/XX.X.X` por padrão; Google rejeita qualquer UA que não seja browser.

Fix em `utils/video_player.py`:
- `--user-agent=Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0` nos args do subprocess MPV
- `user_agent=` no objeto `mpv.MPV` para playback via IPC

---

## Bugs extras corrigidos no mesmo PR

| Arquivo | Problema | Fix |
|---|---|---|
| `services/anime/anilist_integration.py` | `ImportError: format_episode_list_with_skip` — função removida em `dbe750e` (remoção do aniskip) mas 2 call sites esquecidos | Substituído por `list(episode_list)` |
| `services/settings_management_service.py` | Validação de `priority_order` checava contra `current_order` (lista salva), rejeitando novos plugins não listados | Validação agora checa contra arquivos em `scrapers/plugins/*.py` |
| `models/config.py` | Usuário com `settings.json` antigo não recebia novos plugins na lista de prioridade | `field_validator` no `PluginSettings` auto-appenda plugins instalados ausentes da lista salva |
